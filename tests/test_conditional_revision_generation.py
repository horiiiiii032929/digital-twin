import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.teaching_profile_responsiveness_packet import PROFILES
from services.api.app.factory import create_app
from services.llm import OpenAiResponsesClient
from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.generation.conditional_revision import (
    ConditionalRevisionDecision, TASK, conditionally_revise_instructional_proposal,
)
from src.digital_twin.generation.typed_instruction import TASK as DRAFT_TASK
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse, LlmUnavailableError
from tests.services.test_openai_responses_client import _response
from tests.test_compact_instruction_generation import CARDS, QUESTION, RULE, proposal
from tests.test_factual_revision_generation import usage, generate
from tests.test_bounded_revision_generation import question


def decision(replacement=None, move="instructional"):
    return {"disposition": "keep" if replacement is None else "repair",
        "fault": "none" if replacement is None else "missing_requested_answer",
        "proposed_move": "preserve" if replacement is None else move,
        "target_concept": "synthetic epoch", "diagnosis": "Observable synthetic contract check.",
        "replacement": replacement}


@pytest.mark.parametrize("change", [
    {"replacement": proposal()}, {"fault": "incorrect_boundary"}, {"proposed_move": "instructional"},
    {"disposition": "repair"}, {"target_concept": " "},
])
def test_keep_requires_null_replacement_and_consistent_assessment(change):
    with pytest.raises(ValidationError):
        ConditionalRevisionDecision.model_validate({**decision(), **change})


@pytest.mark.parametrize("move,action", [
    ("elicitation", "question"), ("instructional", "instruction"), ("instructional", "partial"),
    ("clarification", "clarify"), ("missing_evidence", "no_evidence"), ("private", "private"), ("graded", "graded"),
])
def test_repair_move_action_contract_allows_contextual_change(move, action):
    value = proposal() if move == "instructional" else question()
    value["action"] = action
    if action == "partial":
        value["missing_details"] = ["Requested launch year is unavailable."]
    result = ConditionalRevisionDecision.model_validate(decision(value, move))
    assert result.replacement.action == action
    with pytest.raises(ValidationError):
        ConditionalRevisionDecision.model_validate({**decision(value, move), "proposed_move": "preserve"})
    with pytest.raises(ValidationError):
        ConditionalRevisionDecision.model_validate({**decision(value, move), "proposed_move": "graded" if action != "graded" else "private"})


class Client:
    def __init__(self, output=None, *, draft=None, error=None, model="gpt-5.6-sol", known=True):
        self.output = decision() if output is None else output
        self.draft = proposal() if draft is None else draft
        self.draft_bytes = json.dumps(self.draft, indent=3)
        self.error, self.model, self.known = error, model, known
        self.calls = []

    async def chat(self, messages, task):
        if task not in {TASK, DRAFT_TASK}:
            raise LlmMalformedResponseError(usage=usage(0))
        self.calls.append((task, messages))
        if task == DRAFT_TASK:
            return LlmResponse(content=self.draft_bytes, provider_model="gpt-5.6-luna", usage=usage())
        if self.error:
            raise self.error
        return LlmResponse(content=json.dumps(self.output), provider_model=self.model, usage=usage(.01 if self.known else None))


@pytest.fixture
def make_runtime(tmp_path):
    opened = []
    def make(client):
        factory = build_final_profile_runtime_factory(tmp_path / str(len(opened)), "t1-v2-reactive", concept_cards=CARDS,
            fixture_id="conditional-revision", planner_client=client, teaching_profile_values=PROFILES["explanatory"],
            **experimental_tutoring_configuration("v14-luna-sol")["runtime_flags"])
        rt = factory(SimpleNamespace(case_id="v14"), VirtualUtcClock(datetime(2026, 9, 25, tzinfo=UTC)))
        opened.append(rt)
        return rt
    yield make
    for rt in opened:
        rt.close_runtime(rt)


@pytest.mark.asyncio
@pytest.mark.parametrize("repair", [False, True])
async def test_actual_runtime_final_provider_usage_and_restart(make_runtime, repair):
    client = Client(decision(proposal()) if repair else decision())
    rt = make_runtime(client)
    answer = await generate(rt)
    assert answer.trace.policy_action == "answer"
    assert [task for task, _ in client.calls] == [DRAFT_TASK, TASK]
    assert answer.trace.provider_model == ("gpt-5.6-sol" if repair else "gpt-5.6-luna")
    assert answer.trace.usage.total_tokens == 60 and answer.trace.usage.approximate_cost_usd == .02
    assert "disposition=" + ("repair" if repair else "keep") in answer.trace.validation_scope
    assert "semantic-certification=false" in answer.trace.validation_scope
    assert "Observable synthetic" not in answer.model_dump_json()
    restarted = rt.restart_runtime(rt)
    try:
        assert restarted.tutoring.generator.implementation_id.endswith("v14")
    finally:
        restarted.close_runtime(restarted)


@pytest.mark.asyncio
async def test_keep_returns_exact_draft_content_and_local_hashes(make_runtime):
    from src.digital_twin.grounding.models import RetrievalHit
    client = Client()
    rt = make_runtime(client)
    chunks = rt.repository.get_release(rt.release_id).chunks
    response = await rt.tutoring.generator._request_proposal({"question": QUESTION},
        evidence={"S1": RetrievalHit(chunk=chunks[0], relevance_score=1, raw_score=1)}, started=0)
    assert response.content == client.draft_bytes
    result = await conditionally_revise_instructional_proposal(Client(), payload={"question": QUESTION}, draft=proposal())
    assert len(result.input_sha256) == len(result.draft_sha256) == 64
    assert result.proposal.model_dump() == proposal()


@pytest.mark.asyncio
@pytest.mark.parametrize("client", [Client(error=LlmUnavailableError()), Client(known=False),
    Client(model="unexpected"), Client({**decision(), "replacement": proposal()})])
async def test_invalid_assessment_never_falls_back_to_draft(make_runtime, client):
    answer = await generate(make_runtime(client))
    assert answer.trace.policy_action == "safe-provider-failure"
    assert RULE not in answer.content
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_semantic_false_keep_and_disclosure_are_not_structural_certification(make_runtime):
    wrong = proposal()
    wrong["units"][0]["text"] = "All old epochs are accepted."
    answer = await generate(make_runtime(Client(draft=wrong)))
    assert answer.content == wrong["units"][0]["text"]
    leak = question("The retired epoch is rejected; which epoch is rejected?")
    answer = await generate(make_runtime(Client(decision(leak, "elicitation"))))
    assert answer.content == leak["units"][0]["text"]
    assert "semantic-certification=false" in answer.trace.validation_scope


@pytest.mark.asyncio
async def test_provider_schema_and_actual_role(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        fmt = kwargs["json"]["text"]["format"]
        assert fmt["name"] == TASK
        assert fmt["schema"]["$defs"]["FactualInstructionUnit"]["properties"]["source_ids"]["minItems"] == 1
        return _response(model="gpt-5.6-sol", text=json.dumps(decision()))
    client = OpenAiResponsesClient("gpt-5.6-sol", post=post, max_output_tokens=3000,
        reasoning_effort="low", experimental_sol_enabled=True)
    result = await conditionally_revise_instructional_proposal(client, payload={"question": QUESTION}, draft=proposal())
    assert result.decision.disposition == "keep"
    config = experimental_tutoring_configuration("v14-luna-sol")["role_configuration"]
    router = ExperimentalGenerationRoleRouter(planner_client=object(), generation_client=object(), revision_client=object(), role_configuration=config)
    assert router.role_for_task(TASK) == "revision"
    assert router.role_for_task(DRAFT_TASK) == "generation"
    with pytest.raises(ValueError, match="requires factual revision"):
        create_app(instructional_conditional_revision_enabled=True)
