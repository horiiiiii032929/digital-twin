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
from src.digital_twin.generation.compact_instruction import CompactInstructionalGenerator, CompactInstructionProposal, INSTRUCTION
from src.digital_twin.generation.profile_authority import ProfileAuthorityInstructionalGenerator, TASK
from src.digital_twin.grounding.models import GenerationUsage, RetrievalHit
from src.digital_twin.llm import LlmMalformedResponseError, LlmMessage, LlmResponse

RULE = "Cobalt ticket rejects an update from a retired epoch even if its sequence number is larger."
VALUE = {"action": "instruction", "units": [{"kind": "explanation", "text": RULE, "source_ids": ["S1"]}], "missing_details": []}


class Client:
    def __init__(self):
        self.requests = []
        self.value = VALUE

    async def chat(self, messages, task):
        if task not in {TASK, "question_specific_compact_instruction"}:
            raise LlmMalformedResponseError(stage="contract-planner", usage=GenerationUsage(approximate_cost_usd=0))
        self.requests.append((task, messages))
        return LlmResponse(content=json.dumps(self.value), provider_model="gpt-5.6-luna",
            usage=GenerationUsage(input_tokens=10, output_tokens=10, total_tokens=20, approximate_cost_usd=.0001))


@pytest.fixture
def runtime(tmp_path):
    client = Client()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=(
        ConceptCardV1(concept_id="cobalt", label="cobalt ticket", description=RULE, objective="Apply the rule."),),
        fixture_id="profile-authority-contract", planner_client=client, teaching_profile_context_enabled=True,
        question_specific_generation_enabled=True, bounded_generation_contract_enabled=True,
        named_referent_context_enabled=True, instructional_compact_response_enabled=True,
        instructional_profile_authority_enabled=True, teaching_profile_values=PROFILES["explanatory"])
    rt = factory(SimpleNamespace(case_id="authority"), VirtualUtcClock(datetime(2026, 9, 25, tzinfo=UTC)))
    release = rt.repository.get_release(rt.release_id)
    hits = [RetrievalHit(chunk=c, relevance_score=1, raw_score=1) for c in release.chunks]
    yield rt, client, release, hits
    rt.close_runtime(rt)


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", [None, {"preferences": {"tone": "precise"}}])
async def test_only_model_advisory_fields_omitted_with_approved_profile(runtime, profile):
    rt, client, release, hits = runtime
    history = [{"role": "student", "content": "My attempt is to check the epoch first."}]
    answer = await rt.tutoring.generator.generate_for_intent("Explain cobalt ticket.", hits, release.policy,
        intent="diagnose_understanding", help_level=0, learner_attempt_present=False,
        teaching_profile_context=profile, learner_history=history, authorized_concept_labels=("cobalt ticket",))
    assert answer.trace.policy_action == "answer"
    task, messages = client.requests[-1]
    payload = json.loads(messages[-1].content)
    assert task == TASK and payload["approved_teaching_profile"] == profile
    assert payload["learner_history"] == history and payload["question"] == "Explain cobalt ticket."
    assert payload["evidence"][0]["text"] == RULE
    advisory = {"pedagogical_intent", "help_level", "application_observed_attempt"}
    assert advisory.isdisjoint(payload) if profile is not None else advisory.issubset(payload)


def test_v8_default_hook_preserves_archived_prompt_and_payload_exactly():
    generator = CompactInstructionalGenerator(object(), bounded_contract_enabled=True, named_referent_context_enabled=True)
    assert hashlib.sha256(generator._system_instruction().encode()).hexdigest() == "ae8c85c23965ff49f0aaff5e90618d82f32eb7cd71e506d2c2fedafeafa57259"
    payload = {"pedagogical_intent": "diagnose_understanding", "help_level": 0,
        "application_observed_attempt": False, "approved_teaching_profile": {"preferences": {}}, "question": "Q"}
    assert generator._prepare_payload(payload) is payload
    assert generator.task == "question_specific_compact_instruction"
    assert generator.missing_information_prefix == "The approved material does not establish:\n"
    assert generator._system_instruction() == INSTRUCTION


@pytest.mark.asyncio
async def test_v9_neutral_missing_heading_and_actual_graph_version(runtime):
    rt, client, _, _ = runtime
    client.value = {"action": "partial", "units": VALUE["units"], "missing_details": ["The exact bit width is not specified."]}
    result = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content="Explain cobalt ticket and its exact bit width.", client_request_id="authority")
    assert result.tutor_message.action == "answer"
    assert result.tutor_message.content.startswith("Information missing from approved material:\n")
    assert result.tutor_message.trace.prompt_version == "question-specific-profile-grounded-v9"
    assert "The exact bit width is not specified." in result.tutor_message.content


@pytest.mark.asyncio
async def test_same_compact_schema_under_distinct_http_task(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        assert set(kwargs["json"]["text"]["format"]["schema"]["properties"]) == {"action", "units", "missing_details"}
        return httpx.Response(200, request=httpx.Request("POST", OpenAiResponsesClient.API_URL), json={
            "status": "completed", "model": "gpt-5.6-luna", "usage": {"input_tokens": 10, "output_tokens": 20},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(VALUE)}]}]})
    response = await OpenAiResponsesClient("gpt-5.6-luna", post=post, max_output_tokens=3000).chat(
        [LlmMessage(role="user", content="Explain cobalt ticket.")], TASK)
    assert CompactInstructionProposal.model_validate_json(response.content).action == "instruction"


def test_profile_variant_retains_boundaries_and_permitted_followup_checks():
    generator = ProfileAuthorityInstructionalGenerator(object(), bounded_contract_enabled=True, named_referent_context_enabled=True)
    text = generator._system_instruction()
    assert text.startswith(INSTRUCTION)
    assert "cannot authorize private disclosure" in text
    assert "question for pure pedagogical withholding" in text
    assert generator.proposal_model is CompactInstructionProposal
