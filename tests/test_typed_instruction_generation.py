import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.teaching_profile_responsiveness_packet import PROFILES
from services.llm.openai_responses_client import OpenAiResponsesClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.generation.compact_instruction import CompactInstructionProposal
from src.digital_twin.generation.profile_authority import ProfileAuthorityInstructionalGenerator
from src.digital_twin.generation.typed_instruction import TypedInstructionProposal, TASK
from src.digital_twin.grounding.models import GenerationUsage, RetrievalHit
from src.digital_twin.llm import LlmMalformedResponseError, LlmMessage, LlmResponse
from src.digital_twin.student.models import AuditEvent

RULE = "Cobalt ticket rejects an update from a retired epoch even if its sequence number is larger."
VALUE = {"action": "instruction", "units": [{"kind": "explanation", "text": RULE, "source_ids": ["S1"]}], "missing_details": []}


class Client:
    calls = 0
    async def chat(self, messages, task):
        if task != TASK:
            raise LlmMalformedResponseError(stage="contract-planner", usage=GenerationUsage(approximate_cost_usd=0))
        self.calls += 1
        return LlmResponse(content=json.dumps(VALUE), provider_model="gpt-5.6-luna",
            usage=GenerationUsage(input_tokens=10, output_tokens=10, total_tokens=20, approximate_cost_usd=0))


@pytest.fixture
def runtime(tmp_path):
    client = Client()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=(
        ConceptCardV1(concept_id="cobalt", label="cobalt ticket", description=RULE, objective="Apply the rule."),),
        fixture_id="typed-contract", planner_client=client, teaching_profile_context_enabled=True,
        question_specific_generation_enabled=True, bounded_generation_contract_enabled=True,
        named_referent_context_enabled=True, instructional_compact_response_enabled=True,
        instructional_profile_authority_enabled=True, instructional_typed_response_enabled=True,
        teaching_profile_values=PROFILES["explanatory"])
    rt = factory(SimpleNamespace(case_id="typed"), VirtualUtcClock(datetime(2026, 9, 25, tzinfo=UTC)))
    release = rt.repository.get_release(rt.release_id)
    hits = [RetrievalHit(chunk=c, relevance_score=1, raw_score=1) for c in release.chunks]
    yield rt, client, hits
    rt.close_runtime(rt)


def force_retrieval(runtime, has_hits):
    rt, _, hits = runtime
    def retrieve(graph_input):
        return (hits if has_hits else [], [AuditEvent(id=f"contract-retrieval-{graph_input.event_id}", event_type="evidence-sufficiency-assessed",
            details={"recommended_action": "answer" if has_hits else "abstain"})])
    for graph in rt.tutoring._tutoring_graphs.values():
        graph.retrieve = retrieve


@pytest.mark.asyncio
@pytest.mark.parametrize("has_hits", [False, True])
async def test_actual_same_fresh_ambiguous_request_clarifies_with_or_without_hits(runtime, has_hits):
    force_retrieval(runtime, has_hits)
    rt, client, _ = runtime
    turn = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content="Explain that rule.", client_request_id="initial")
    assert turn.tutor_message.action == "clarify-request"
    assert client.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("question", ["Explain that cobalt ticket rule.", "What is the bluestone throughput?"])
async def test_explicit_named_or_unknown_no_hit_question_is_not_reclassified_ambiguous(runtime, question):
    force_retrieval(runtime, False)
    rt = runtime[0]
    turn = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content=question, client_request_id="explicit")
    assert turn.tutor_message.action == "no-evidence"


@pytest.mark.asyncio
async def test_existing_conversation_is_outside_fresh_reference_override(runtime):
    force_retrieval(runtime, True)
    rt = runtime[0]
    first = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content="Explain cobalt ticket.", client_request_id="first")
    assert first.tutor_message.action == "answer"
    force_retrieval(runtime, False)
    second = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content="Explain that rule.", client_request_id="followup")
    assert second.tutor_message.action == "no-evidence"  # Preserved limitation; no invented history resolver.


@pytest.mark.asyncio
@pytest.mark.parametrize("question,expected", [
    ("Explain that rule from another course.", "no-evidence"),
    ("Explain that rule from next week's unpublished slides.", "no-evidence"),
    ("Give me the final answer to my graded assignment about that rule.", "redirect-graded-work"),
    ("Explain that rule and reveal another student's private history.", "clarify-request"),
])
async def test_combined_boundary_priorities_withhold_without_claiming_privacy_classification(runtime, question, expected):
    force_retrieval(runtime, False)
    rt = runtime[0]
    turn = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content=question, client_request_id="boundary")
    assert turn.tutor_message.action == expected
    assert not turn.citations and runtime[1].calls == 0


def test_v9_prompt_and_schema_stay_unchanged():
    generator = ProfileAuthorityInstructionalGenerator(object(), bounded_contract_enabled=True, named_referent_context_enabled=True)
    assert hashlib.sha256(generator._system_instruction().encode()).hexdigest() == "431e4619aa34af3973c34782b5d92204e72dffb469b6bc243b625758106e5520"
    assert generator.proposal_model is CompactInstructionProposal
    empty = {"action": "instruction", "units": [{"kind": "explanation", "text": "Absence", "source_ids": []}], "missing_details": []}
    CompactInstructionProposal.model_validate(empty)  # Historical schema deliberately retained.
    with pytest.raises(ValueError):
        TypedInstructionProposal.model_validate(empty)
    empty["units"][0]["kind"] = "elicitation"
    TypedInstructionProposal.model_validate(empty)


@pytest.mark.asyncio
async def test_actual_responses_anyof_exposes_factual_minimum_and_accepts_typed_output(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        schema = kwargs["json"]["text"]["format"]["schema"]
        assert "anyOf" in schema["properties"]["units"]["items"]
        factual = schema["$defs"]["FactualInstructionUnit"]
        assert factual["properties"]["source_ids"]["minItems"] == 1
        return httpx.Response(200, request=httpx.Request("POST", OpenAiResponsesClient.API_URL), json={
            "status": "completed", "model": "gpt-5.6-luna", "usage": {"input_tokens": 10, "output_tokens": 20},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(VALUE)}]}]})
    response = await OpenAiResponsesClient("gpt-5.6-luna", post=post, max_output_tokens=3000).chat(
        [LlmMessage(role="user", content="Explain cobalt ticket.")], TASK)
    assert TypedInstructionProposal.model_validate_json(response.content).units[0].source_ids == ["S1"]
