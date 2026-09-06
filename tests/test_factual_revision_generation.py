import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.teaching_profile_responsiveness_packet import PROFILES
from services.api.app.factory import create_app
from services.llm import OpenAiResponsesClient
from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.generation.evidence_strength import EvidenceStrengthInstructionalGenerator
from src.digital_twin.generation.factual_revision import (
    FactualRevisionInstructionalGenerator, REVISION_TASK, build_revision_messages, revise_instructional_proposal)
from src.digital_twin.generation.typed_instruction import TASK, TypedInstructionProposal
from src.digital_twin.grounding.models import GenerationUsage, RetrievalHit
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse, LlmUnavailableError
from tests.services.test_openai_responses_client import _response
from tests.test_compact_instruction_generation import CARDS, QUESTION, RULE, proposal


def usage(cost=.01):
    return GenerationUsage(input_tokens=10, output_tokens=20, total_tokens=30, approximate_cost_usd=cost)


class Client:
    def __init__(self, *, bad_draft=False, revision_error=None, revised_text="The retired epoch is rejected."):
        self.calls = []
        self.bad_draft, self.revision_error, self.revised_text = bad_draft, revision_error, revised_text

    async def chat(self, messages, task):
        if task not in {TASK, REVISION_TASK}:
            raise LlmMalformedResponseError(stage="test-planner", usage=usage(0))
        payload = json.loads(messages[-1].content)
        self.calls.append((task, payload))
        await asyncio.sleep(0)
        if task == REVISION_TASK and self.revision_error:
            raise self.revision_error
        value = proposal()
        if task == TASK and self.bad_draft:
            value["units"][0]["source_ids"] = ["S99"]
        if task == REVISION_TASK:
            value["units"][0]["text"] = self.revised_text
        return LlmResponse(content=json.dumps(value), provider_model="gpt-5.6-sol" if task == REVISION_TASK else "gpt-5.6-luna", provider_revision="test-revision", usage=usage())


@pytest.fixture
def make_runtime(tmp_path):
    opened = []
    def make(client):
        factory = build_final_profile_runtime_factory(tmp_path / str(len(opened)), "t1-v2-reactive", concept_cards=CARDS,
            fixture_id="revision-contract", planner_client=client, teaching_profile_values=PROFILES["explanatory"],
            **experimental_tutoring_configuration("v12-luna-sol")["runtime_flags"])
        rt = factory(SimpleNamespace(case_id="revision"), VirtualUtcClock(datetime(2026, 9, 25, tzinfo=UTC)))
        opened.append(rt)
        return rt
    yield make
    for rt in opened:
        rt.close_runtime(rt)


async def generate(rt, question=QUESTION):
    release = rt.repository.get_release(rt.release_id)
    return await rt.tutoring.generator.generate_for_intent(question,
        [RetrievalHit(chunk=c, relevance_score=1, raw_score=1) for c in release.chunks], release.policy,
        intent="explain_concept", help_level=0, teaching_profile_context={"tone": "precise"},
        learner_history=[{"role": "student", "content": "I checked epoch first."}],
        authorized_concept_labels=("cobalt ticket",))


def test_v11_draft_prompt_payload_schema_and_explicit_revision_selector():
    kwargs = dict(model_id="gpt-5.6-luna", named_referent_context_enabled=True, bounded_contract_enabled=True)
    old, new = EvidenceStrengthInstructionalGenerator(None, **kwargs), FactualRevisionInstructionalGenerator(None, **kwargs)
    assert old._system_instruction() == new._system_instruction()
    assert old.task == new.task == TASK
    assert old.proposal_model is new.proposal_model
    assert OpenAiResponsesClient._schema(TASK) == OpenAiResponsesClient._schema(REVISION_TASK)
    payload = {"question": QUESTION, "approved_teaching_profile": {"tone": "direct"}, "pedagogical_intent": "ask", "evidence": []}
    assert old._prepare_payload(payload) == new._prepare_payload(payload)
    prepared = new._prepare_payload(payload)
    actual = json.loads(build_revision_messages(payload=prepared, draft=TypedInstructionProposal.model_validate(proposal()))[-1].content)
    assert {k: v for k, v in actual.items() if k != "draft_proposal"} == prepared
    assert "pedagogical_intent" not in actual
    with pytest.raises(ValueError, match="requires evidence strength"):
        create_app(instructional_factual_revision_enabled=True)


@pytest.mark.asyncio
async def test_real_graph_final_sol_and_combined_usage_and_restart(make_runtime):
    client = Client()
    rt = make_runtime(client)
    turn = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content=QUESTION, client_request_id="revision-1")
    assert turn.tutor_message.action == "answer"
    assert turn.tutor_message.content == client.revised_text
    trace = turn.tutor_message.trace
    assert trace.provider_model == "gpt-5.6-sol" and trace.prompt_version.endswith("v12")
    assert trace.usage.total_tokens == 60 and trace.usage.approximate_cost_usd == .02
    assert "semantic-support-unverified" in trace.validation_scope
    assert [task for task, _ in client.calls] == [TASK, REVISION_TASK]
    first, second = [payload for _, payload in client.calls]
    assert {k: v for k, v in second.items() if k != "draft_proposal"} == first
    restarted = rt.restart_runtime(rt)
    try:
        assert restarted.tutoring.generator.implementation_id.endswith("v12")
    finally:
        restarted.close_runtime(restarted)


@pytest.mark.asyncio
async def test_invalid_draft_is_not_revised_and_spend_retained(make_runtime):
    client = Client(bad_draft=True)
    answer = await generate(make_runtime(client))
    assert answer.trace.policy_action == "safe-provider-failure"
    assert len(client.calls) == 1
    assert answer.trace.usage.total_tokens == 30 and answer.trace.usage.approximate_cost_usd == .01
    assert "revision_attempted=false" in answer.trace.validation_scope
    assert "unknown_source_id" in answer.trace.validation_scope
    assert "final_provider=gpt-5.6-sol" not in answer.trace.validation_scope


@pytest.mark.asyncio
@pytest.mark.parametrize("known", [True, False])
async def test_failed_revision_has_no_draft_fallback_and_honest_cost(make_runtime, known):
    error = LlmMalformedResponseError(stage="invalid", provider_model="gpt-5.6-sol", usage=usage(.02)) if known else LlmUnavailableError()
    answer = await generate(make_runtime(Client(revision_error=error)))
    assert answer.trace.policy_action == "safe-provider-failure" and RULE not in answer.content
    assert answer.trace.usage.total_tokens == (60 if known else 30)
    assert answer.trace.usage.approximate_cost_usd == (.03 if known else None)
    assert "revision_attempted=true" in answer.trace.validation_scope


@pytest.mark.asyncio
async def test_concurrent_requests_keep_actual_question_and_draft_local(make_runtime):
    client = Client()
    rt = make_runtime(client)
    answers = await asyncio.gather(generate(rt, QUESTION), generate(rt, "Apply cobalt ticket to an old epoch."))
    assert all(answer.trace.usage.total_tokens == 60 for answer in answers)
    drafts = [p for t, p in client.calls if t == TASK]
    revisions = [p for t, p in client.calls if t == REVISION_TASK]
    assert {p["question"] for p in drafts} == {p["question"] for p in revisions}
    assert all(p["draft_proposal"] == proposal() for p in revisions)


@pytest.mark.asyncio
async def test_revised_false_prose_still_only_association(make_runtime):
    answer = await generate(make_runtime(Client(revised_text="All old epochs are accepted.")))
    assert answer.trace.policy_action == "answer"
    assert "semantic-support-unverified" in answer.trace.validation_scope
    assert "semantic-certification=false" in answer.trace.validation_scope


@pytest.mark.asyncio
async def test_actual_http_revision_task_and_identity(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        body = kwargs["json"]
        assert body["text"]["format"]["name"] == REVISION_TASK
        assert body["text"]["format"]["schema"]["$defs"]["FactualInstructionUnit"]["properties"]["source_ids"]["minItems"] == 1
        return _response(model="gpt-5.6-sol", text=json.dumps(proposal()))
    client = OpenAiResponsesClient("gpt-5.6-sol", post=post, max_output_tokens=3000, reasoning_effort="low", experimental_sol_enabled=True)
    response = await revise_instructional_proposal(client, payload={"question": QUESTION}, draft=TypedInstructionProposal.model_validate(proposal()))
    assert response.provider_model == "gpt-5.6-sol"


def test_three_role_router_preserves_planner_and_rejects_implicit_revision():
    configuration = experimental_tutoring_configuration("v12-luna-sol")["role_configuration"]
    router = ExperimentalGenerationRoleRouter(planner_client=object(), generation_client=object(), revision_client=object(), role_configuration=configuration)
    assert router.role_for_task(TASK) == "generation"
    assert router.role_for_task(REVISION_TASK) == "revision"
    assert router.role_for_task("reactive_tutoring_intent") == "planner"
    with pytest.raises(ValueError):
        ExperimentalGenerationRoleRouter(planner_client=object(), generation_client=object(), role_configuration=configuration)


@pytest.mark.asyncio
async def test_revised_unknown_source_rejected_after_both_calls(make_runtime):
    class UnknownSource(Client):
        async def chat(self, messages, task):
            response = await super().chat(messages, task)
            if task == REVISION_TASK:
                value = json.loads(response.content)
                value["units"][0]["source_ids"] = ["S999"]
                response = response.model_copy(update={"content": json.dumps(value)})
            return response
    client = UnknownSource()
    answer = await generate(make_runtime(client))
    assert answer.trace.policy_action == "safe-provider-failure"
    assert answer.trace.usage.total_tokens == 60
    assert "unknown_source_id" in answer.trace.validation_scope
    assert len(client.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("model,source_ids", [("gpt-5.6-luna", ["S1"]), ("gpt-5.6-sol", [])])
async def test_revision_rejects_actual_http_wrong_identity_or_invalid_union(monkeypatch, model, source_ids):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        value = proposal()
        value["units"][0]["source_ids"] = source_ids
        return _response(model=model, text=json.dumps(value))
    client = OpenAiResponsesClient("gpt-5.6-sol", post=post, max_output_tokens=3000, reasoning_effort="low", experimental_sol_enabled=True)
    from src.digital_twin.llm import LlmError
    with pytest.raises(LlmError) as captured:
        await revise_instructional_proposal(client, payload={"question": QUESTION}, draft=TypedInstructionProposal.model_validate(proposal()))
    if model == "gpt-5.6-sol":
        assert captured.value.usage.approximate_cost_usd is not None
    else:
        # Unexpected model pricing is not silently represented as known zero.
        assert captured.value.usage.approximate_cost_usd is None
        assert captured.value.usage.input_tokens == 12
        assert captured.value.usage.output_tokens == 5
        assert captured.value.usage.total_tokens == 17


@pytest.mark.asyncio
async def test_wrong_model_with_malformed_usage_keeps_usage_unknown(monkeypatch):
    import httpx
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        return httpx.Response(200, request=httpx.Request("POST", OpenAiResponsesClient.API_URL),
            json={"model": "unexpected-model", "usage": {"input_tokens": -1, "output_tokens": 4}})
    client = OpenAiResponsesClient("gpt-5.6-sol", post=post, max_output_tokens=3000, experimental_sol_enabled=True)
    from src.digital_twin.llm import LlmIdentityDriftError
    with pytest.raises(LlmIdentityDriftError) as captured:
        await revise_instructional_proposal(client, payload={"question": QUESTION}, draft=TypedInstructionProposal.model_validate(proposal()))
    assert captured.value.usage is None
