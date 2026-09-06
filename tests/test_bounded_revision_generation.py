import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.teaching_profile_responsiveness_packet import PROFILES
from services.api.app.factory import create_app
from services.llm import OpenAiResponsesClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.generation.bounded_revision import (
    BoundedRevisionInstructionalGenerator, BoundedRevisionProposal, BOUNDED_REVISION_TASK,
    requires_bounded_revision, revise_bounded_instructional_proposal,
)
from src.digital_twin.generation.factual_revision import FactualRevisionInstructionalGenerator, REVISION_TASK
from src.digital_twin.generation.typed_instruction import TypedInstructionProposal, TASK
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse
from tests.services.test_openai_responses_client import _response
from tests.test_compact_instruction_generation import CARDS, QUESTION, RULE, proposal
from tests.test_factual_revision_generation import usage, generate


def question(text="Which epoch should be checked first?"):
    return {"action": "question", "units": [{"kind": "elicitation", "text": text, "source_ids": []}], "missing_details": []}


@pytest.mark.parametrize("action,has_units,expected", [
    ("question", True, True), ("private", False, True), ("graded", False, True),
    ("no_evidence", True, True), ("no_evidence", False, False), ("clarify", True, False),
    ("instruction", True, False), ("partial", True, False),
])
def test_precise_prospective_eligibility(action, has_units, expected):
    value = question()
    value["action"] = action
    if not has_units:
        value["units"] = []
    assert requires_bounded_revision(TypedInstructionProposal.model_validate(value)) is expected


def test_v12_unchanged_and_v13_explicit_dependency():
    args = dict(model_id="gpt-5.6-luna", named_referent_context_enabled=True, bounded_contract_enabled=True)
    old, new = FactualRevisionInstructionalGenerator(None, **args), BoundedRevisionInstructionalGenerator(None, **args)
    assert old._system_instruction() == new._system_instruction()
    assert old.proposal_model is new.proposal_model
    assert old.task == new.task == TASK
    assert old.implementation_id.endswith("v12") and new.implementation_id.endswith("v13")
    assert "instructional_bounded_revision_enabled" not in experimental_tutoring_configuration("v12-luna-sol")["runtime_flags"]
    with pytest.raises(ValueError, match="requires factual revision"):
        create_app(instructional_bounded_revision_enabled=True)
    with pytest.raises(ValidationError):
        BoundedRevisionProposal.model_validate(proposal())


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [False, True])
async def test_actual_http_restricted_schema_and_rejection(monkeypatch, bad):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        fmt = kwargs["json"]["text"]["format"]
        assert fmt["name"] == BOUNDED_REVISION_TASK
        assert "instruction" not in fmt["schema"]["properties"]["action"]["enum"]
        assert fmt["schema"]["$defs"]["ElicitationInstructionUnit"]["properties"]["kind"]["enum"] == ["elicitation"]
        return _response(model="gpt-5.6-sol", text=json.dumps(proposal() if bad else question()))
    client = OpenAiResponsesClient("gpt-5.6-sol", post=post, max_output_tokens=3000, reasoning_effort="low", experimental_sol_enabled=True)
    if bad:
        with pytest.raises(LlmMalformedResponseError):
            await revise_bounded_instructional_proposal(client, payload={"question": QUESTION}, draft=TypedInstructionProposal.model_validate(question()))
    else:
        result = await revise_bounded_instructional_proposal(client, payload={"question": QUESTION}, draft=TypedInstructionProposal.model_validate(question()))
        assert json.loads(result.content) == question()


class Client:
    def __init__(self, output=None, draft=None):
        self.output = output or question()
        self.draft = draft or question()
        self.tasks = []
    async def chat(self, messages, task):
        if task not in {TASK, REVISION_TASK, BOUNDED_REVISION_TASK}:
            raise LlmMalformedResponseError(usage=usage(0))
        self.tasks.append(task)
        return LlmResponse(content=json.dumps(self.draft if task == TASK else self.output),
            provider_model="gpt-5.6-luna" if task == TASK else "gpt-5.6-sol", usage=usage())


@pytest.mark.asyncio
@pytest.mark.parametrize("output,safe", [(question(), False), (proposal(), True),
    (question("The retired epoch is always rejected; which epoch is rejected?"), False)])
async def test_actual_runtime_restricted_guard_and_unverified_question_limit(tmp_path, output, safe):
    client = Client(output)
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="bounded-revision", planner_client=client, teaching_profile_values=PROFILES["socratic"],
        **experimental_tutoring_configuration("v13-luna-sol")["runtime_flags"])
    rt = factory(SimpleNamespace(case_id="v13"), VirtualUtcClock(datetime(2026, 9, 25, tzinfo=UTC)))
    try:
        answer = await generate(rt)
        assert client.tasks == [TASK, BOUNDED_REVISION_TASK]
        assert answer.trace.policy_action == ("safe-provider-failure" if safe else "question")
        assert answer.trace.usage.total_tokens == 60
        assert answer.trace.prompt_version.endswith("v13")
        assert "semantic-support-unverified" in answer.trace.validation_scope
        if not safe:
            assert answer.content == output["units"][0]["text"]
        # The planted complete answer inside an elicitation passes structure;
        # independent quality review must reject it. No disclosure proof claimed.
        restarted = rt.restart_runtime(rt)
        try:
            assert restarted.tutoring.generator.implementation_id.endswith("v13")
        finally:
            restarted.close_runtime(restarted)
    finally:
        rt.close_runtime(rt)


@pytest.mark.asyncio
async def test_unrestricted_instruction_keeps_exact_v12_task_and_payload():
    client = Client(proposal(), proposal())
    draft = TypedInstructionProposal.model_validate(proposal())
    response = await revise_bounded_instructional_proposal(client, payload={"question": QUESTION, "evidence": [{"citation_id": "S1", "text": RULE}]}, draft=draft)
    assert client.tasks == [REVISION_TASK]
    assert json.loads(response.content) == proposal()
