import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.teaching_profile_responsiveness_packet import PROFILES
from services.api.app.factory import create_app
from services.llm import OpenAiResponsesClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.generation.evidence_strength import EvidenceStrengthInstructionalGenerator, EVIDENCE_STRENGTH_INSTRUCTION
from src.digital_twin.generation.typed_instruction import TypedInstructionalGenerator, TASK
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmMessage, LlmResponse, LlmMalformedResponseError
from tests.services.test_openai_responses_client import _response

RULE = "Opal sensor flashes when its input exceeds 8. Inputs at or below 8 produce no flash."
VALUE = {"action": "instruction", "units": [{"kind": "explanation", "text": "Input 9 exceeds 8, so the sensor flashes.", "source_ids": ["S1"]}], "missing_details": []}


def generators():
    kwargs = dict(model_id="gpt-5.6-luna", named_referent_context_enabled=True, bounded_contract_enabled=True)
    return TypedInstructionalGenerator(None, **kwargs), EvidenceStrengthInstructionalGenerator(None, **kwargs)


def test_v10_exact_prompt_schema_payload_and_task_preserved():
    old, new = generators()
    assert hashlib.sha256(old._system_instruction().encode()).hexdigest() == "69d61435cace0e70d3c9aff8ad3118aac8b50fab840fe7f7b9b82607e42b2724"
    assert new._system_instruction() == old._system_instruction() + " " + EVIDENCE_STRENGTH_INSTRUCTION
    assert old.task == new.task == TASK
    assert old.proposal_model is new.proposal_model
    payload = {"approved_teaching_profile": {"tone": "direct"}, "question": "Apply the rule", "pedagogical_intent": "ask", "evidence": [{"citation_id": "S1", "text": RULE}]}
    assert new._prepare_payload(payload) == old._prepare_payload(payload)
    assert old.implementation_id == "question-specific-profile-grounded-v10"
    assert new.implementation_id == "question-specific-profile-grounded-v11"
    assert "causal or sequential workflow" in new._system_instruction()


def test_v11_is_explicit_and_cannot_skip_typed_dependency():
    with pytest.raises(ValueError, match="requires typed"):
        create_app(instructional_evidence_strength_enabled=True)
    old = experimental_tutoring_configuration("v10-luna-low")
    new = experimental_tutoring_configuration("v11-luna-low")
    assert old["role_configuration"] == new["role_configuration"]
    assert "instructional_evidence_strength_enabled" not in old["runtime_flags"]
    assert new["runtime_flags"]["instructional_evidence_strength_enabled"]


@pytest.mark.asyncio
async def test_actual_provider_serializes_v11_instruction_with_unchanged_typed_schema(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    old, new = generators()
    async def post(**kwargs):
        body = kwargs["json"]
        assert body["input"][0]["content"][0]["text"] == new._system_instruction()
        assert body["text"]["format"]["schema"] == OpenAiResponsesClient("gpt-5.6-luna")._schema(old.task)
        return _response(model="gpt-5.6-luna", text=json.dumps(VALUE))
    result = await OpenAiResponsesClient("gpt-5.6-luna", post=post, max_output_tokens=3000, reasoning_effort="low").chat(
        [LlmMessage(role="system", content=new._system_instruction()), LlmMessage(role="user", content="Apply the supplied rule.")], new.task)
    assert json.loads(result.content) == VALUE


class Client:
    def __init__(self, text):
        self.text, self.messages = text, []
    async def chat(self, messages, task):
        if task != TASK:
            raise LlmMalformedResponseError(stage="injected-planner", usage=GenerationUsage(approximate_cost_usd=0))
        self.messages.append(messages)
        value = {**VALUE, "units": [{"kind": "explanation", "text": self.text, "source_ids": ["S1"]}]}
        return LlmResponse(content=json.dumps(value), provider_model="gpt-5.6-luna", usage=GenerationUsage(input_tokens=10, output_tokens=10, approximate_cost_usd=0))


@pytest.mark.asyncio
@pytest.mark.parametrize("text", [VALUE["units"][0]["text"], "The sensor always flashes for every input, including zero."])
async def test_actual_runtime_v11_trace_restart_and_semantic_limit(tmp_path, text):
    client = Client(text)
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=(ConceptCardV1(concept_id="opal", label="opal sensor", description=RULE, objective="Apply the sensor rule."),),
        fixture_id="evidence-strength-contract", planner_client=client, teaching_profile_values=PROFILES["explanatory"], **experimental_tutoring_configuration("v11-luna-low")["runtime_flags"])
    runtime = factory(SimpleNamespace(case_id="v11"), VirtualUtcClock(datetime(2026, 9, 25, tzinfo=UTC)))
    try:
        turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id, content="Apply the opal sensor rule to input 9.", client_request_id="q1")
        assert turn.tutor_message.action == "answer"
        assert turn.tutor_message.trace.prompt_version == "question-specific-profile-grounded-v11"
        assert "semantic-support-unverified" in turn.tutor_message.trace.validation_scope
        assert turn.tutor_message.content == text
        assert EVIDENCE_STRENGTH_INSTRUCTION in client.messages[-1][0].content
        runtime = runtime.restart_runtime(runtime)
        assert runtime.tutoring.generator.implementation_id == "question-specific-profile-grounded-v11"
        assert runtime.tutoring.generator.task == TASK
        # Deliberately false prose is structurally associated but NOT semantically verified.
        # A later independent meaning review must reject the planted zero-input claim.
    finally:
        runtime.close_runtime(runtime)
