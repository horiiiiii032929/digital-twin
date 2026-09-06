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
from src.digital_twin.generation.compact_instruction import CompactInstructionProposal, INSTRUCTION, TASK
from src.digital_twin.generation.instructional import InstructionalSourceBindingValidator
from src.digital_twin.grounding.models import GenerationUsage, RetrievalHit
from src.digital_twin.llm import LlmMalformedResponseError, LlmMessage, LlmResponse

RULE = "Cobalt ticket rejects an update from a retired epoch even if its sequence number is larger."
QUESTION = "Explain the retired epoch rule for cobalt ticket."
CARDS = (ConceptCardV1(concept_id="cobalt", label="cobalt ticket", description=RULE, objective="Apply the rule."),)


def unit(text=RULE, kind="explanation", ids=None):
    return {"kind": kind, "text": text, "source_ids": ["S1"] if ids is None else ids}


def proposal():
    return {"action": "instruction", "units": [unit()], "missing_details": []}


class Client:
    def __init__(self):
        self.value = proposal()

    async def chat(self, messages, task):
        if task != TASK:
            raise LlmMalformedResponseError(stage="contract-planner", usage=GenerationUsage(approximate_cost_usd=0))
        payload = json.loads(messages[-1].content)
        actual = next(e["citation_id"] for e in payload["evidence"] if RULE in e["text"])
        value = json.loads(json.dumps(self.value))
        for item in value["units"]:
            item["source_ids"] = [actual if value == "S1" else value for value in item["source_ids"]]
        return LlmResponse(content=json.dumps(value), provider_model="gpt-5.6-luna",
            usage=GenerationUsage(input_tokens=10, output_tokens=10, total_tokens=20, approximate_cost_usd=.0001))


@pytest.fixture
def runtime(tmp_path):
    client = Client()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="compact-contract", planner_client=client, teaching_profile_context_enabled=True,
        question_specific_generation_enabled=True, bounded_generation_contract_enabled=True,
        named_referent_context_enabled=True, instructional_compact_response_enabled=True,
        teaching_profile_values=PROFILES["explanatory"])
    rt = factory(SimpleNamespace(case_id="compact"), VirtualUtcClock(datetime(2026, 9, 25, tzinfo=UTC)))
    release = rt.repository.get_release(rt.release_id)
    hits = [RetrievalHit(chunk=c, relevance_score=1, raw_score=1) for c in release.chunks]
    yield rt, client, release, hits
    rt.close_runtime(rt)


async def generate(runtime, question=QUESTION):
    rt, _, release, hits = runtime
    return await rt.tutoring.generator.generate_for_intent(question, hits, release.policy,
        intent="explain_concept", help_level=0, teaching_profile_context={"preferences": {"tone": "precise"}},
        authorized_concept_labels=("cobalt ticket",))


@pytest.mark.asyncio
async def test_actual_graph_links_feedback_and_application_to_full_current_message(runtime):
    rt, client, _, _ = runtime
    question = "My attempt: " + "I check the epoch first. " * 16 + " Is this correct? Apply it to an older epoch."
    client.value["units"] = [unit("Your epoch-first check is correct.", "feedback"),
        unit("Reject the older-epoch update even when its sequence is larger."),
        unit("Which check prevents that stale update?", "elicitation", [])]
    result = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content=question, client_request_id="compact-long")
    assert result.tutor_message.action == "answer"
    assert "Reject the older-epoch" in result.tutor_message.content
    assert rt.repository.list_messages(rt.conversation_id)[0].content == question
    assert result.tutor_message.response_to_message_id == result.student_message.id
    assert result.tutor_message.trace.prompt_version == "question-specific-profile-grounded-v8"
    assert "semantic-support-unverified" in result.tutor_message.trace.validation_scope


@pytest.mark.asyncio
async def test_initial_mixed_and_post_attempt_mixed_are_both_representable(runtime):
    client = runtime[1]
    client.value = {"action": "no_evidence", "units": [unit("Which should be checked first: epoch or sequence?", "elicitation", [])],
        "missing_details": ["exact bit width", "software release year"]}
    answer = await generate(runtime)
    assert answer.trace.policy_action == "no-evidence" and not answer.citations
    assert all(s in answer.content for s in ["exact bit width", "software release year", "Which should"])
    assert RULE not in answer.content
    client.value = {"action": "partial", "units": [unit("Your epoch-first check is correct.", "feedback"),
        unit("Reject the retired-epoch update.")], "missing_details": ["exact bit width", "software release year"]}
    answer = await generate(runtime)
    assert answer.trace.policy_action == "answer" and answer.citations
    assert "Your epoch-first" in answer.content and "Reject" in answer.content
    assert "software release year" in answer.trace.unresolved_detail


@pytest.mark.asyncio
@pytest.mark.parametrize("action,expected", [("private", "no-evidence"), ("graded", "redirect-graded-work"), ("clarify", "clarify")])
async def test_explicit_boundary_actions_render_without_false_factual_claims(runtime, action, expected):
    runtime[1].value = {"action": action, "units": [], "missing_details": []}
    answer = await generate(runtime)
    assert answer.trace.policy_action == expected and not answer.atomic_claims and not answer.citations


@pytest.mark.asyncio
@pytest.mark.parametrize("value,code", [
    ({"action": "instruction", "units": [unit(ids=["S99"])], "missing_details": []}, "unknown_source_id"),
    ({"action": "instruction", "units": [unit(ids=[])], "missing_details": []}, "factual_unit_without_source"),
    ({"action": "question", "units": [unit()], "missing_details": []}, "boundary_contains_factual_units"),
    ({"action": "question", "units": [], "missing_details": []}, "empty_question"),
])
async def test_fixed_codes_for_invalid_contracts_do_not_expose_model_text(runtime, value, code):
    runtime[1].value = value
    answer = await generate(runtime)
    assert answer.trace.policy_action == "safe-provider-failure"
    assert answer.trace.validation_scope.endswith("compact_contract=" + code)
    assert RULE not in answer.trace.validation_scope


@pytest.mark.asyncio
async def test_deliberately_false_paraphrase_passes_association_only_not_semantic_validation(runtime):
    runtime[1].value["units"] = [unit("Cobalt ticket accepts every retired-epoch update.")]
    answer = await generate(runtime)
    decision = InstructionalSourceBindingValidator().validate(answer.atomic_claims, runtime[3])
    assert decision.releasable
    assert decision.supported_claim_count == 0
    assert decision.features["semantic_support_unverified"] is True
    assert answer.content != RULE


def test_prompt_and_schema_have_no_copied_span_or_legacy_aspect_contract():
    schema = CompactInstructionProposal.model_json_schema()
    assert set(schema["properties"]) == {"action", "units", "missing_details"}
    assert "aspects may be empty" not in INSTRUCTION
    assert "student_excerpt" not in json.dumps(schema)


@pytest.mark.asyncio
async def test_real_http_schema_and_validation_use_compact_task(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        assert set(kwargs["json"]["text"]["format"]["schema"]["properties"]) == {"action", "units", "missing_details"}
        return httpx.Response(200, request=httpx.Request("POST", OpenAiResponsesClient.API_URL), json={
            "status": "completed", "model": "gpt-5.6-luna", "usage": {"input_tokens": 10, "output_tokens": 20},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(proposal())}]}]})
    response = await OpenAiResponsesClient("gpt-5.6-luna", post=post, max_output_tokens=3000).chat(
        [LlmMessage(role="user", content=QUESTION)], TASK)
    assert CompactInstructionProposal.model_validate_json(response.content).action == "instruction"


@pytest.mark.asyncio
async def test_mixed_answer_declares_elicitation_prose_with_server_association(runtime):
    runtime[1].value["units"] = [unit(), unit("Which check prevents the stale update?", "elicitation", [])]
    answer = await generate(runtime)
    assert len(answer.atomic_claims) == 2
    assert answer.atomic_claims[1].text == "Which check prevents the stale update?"
    assert answer.atomic_claims[1].evidence_hit_ids == answer.atomic_claims[0].evidence_hit_ids
    assert answer.atomic_claims[1].source_bindings == answer.atomic_claims[0].source_bindings
    assert "semantic-support-unverified" in answer.trace.validation_scope
