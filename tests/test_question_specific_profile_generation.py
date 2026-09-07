import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_final_profile_longitudinal import CARDS
from scripts.teaching_profile_responsiveness_packet import PROFILES
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.generation.question_specific import QuestionSpecificProfileGroundedGenerator, TASK
from src.digital_twin.grounding.models import GenerationUsage, RetrievalHit
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse
from src.digital_twin.student.autonomy_models import AutonomousActionKind, PedagogicalPlanV2
from src.digital_twin.student.tutoring_graph import _grounded_response_v2
from services.llm.openai_responses_client import OpenAiResponsesClient


class ProposalClient:
    def __init__(self):
        self.payloads = []
        self.proposal = None

    async def chat(self, messages, task):
        self.payloads.append((task, json.loads(messages[-1].content)))
        if task != TASK or self.proposal is None:
            raise LlmMalformedResponseError(stage="synthetic-failure", usage=GenerationUsage(approximate_cost_usd=0))
        return LlmResponse(content=json.dumps(self.proposal), provider_model="gpt-5.6-luna",
            usage=GenerationUsage(input_tokens=20, output_tokens=20, total_tokens=40, approximate_cost_usd=0.0001))


@pytest.fixture
def setup(tmp_path, request):
    client = ProposalClient()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="question-specific-fresh", planner_client=client, teaching_profile_context_enabled=True,
        question_specific_generation_enabled=True,
        teaching_profile_values=(PROFILES[request.param] if hasattr(request, "param") else None))
    runtime = factory(SimpleNamespace(case_id="fresh-question-specific"), VirtualUtcClock(datetime(2026, 9, 7, tzinfo=UTC)))
    release = runtime.repository.get_release(runtime.release_id)
    hit = RetrievalHit(chunk=release.chunks[0], relevance_score=1, raw_score=1)
    client.proposal = {"boundary": "answerable", "aspects": [{"requirement": "detect changed bytes",
        "supported": True, "spans": [{"citation_id": "S1", "text": "compares a newly computed digest during retrieval to detect altered bytes"}]}],
        "teaching_move": "explain", "question_focus": "checksum audit"}
    yield runtime, client, release, hit
    runtime.close_runtime(runtime)


async def generate(setup, intent="explain_concept"):
    runtime, _client, release, hit = setup
    return await runtime.tutoring.generator.generate_for_intent("How does checksum audit detect altered bytes?",
        [hit], release.policy, intent=intent, help_level=0,
        teaching_profile_context={"preferences": {"tone": "precise"}},
        learner_history=[{"role": "student", "content": "I compared the digest."}])


@pytest.mark.asyncio
async def test_explanation_selects_requested_span_without_dumping_source(setup):
    answer = await generate(setup)
    assert answer.trace.policy_action == "answer"
    assert answer.content == setup[1].proposal["aspects"][0]["spans"][0]["text"]
    assert "stores the digest separately" not in answer.content
    assert len(answer.atomic_claims) == len(answer.citations) == 1
    payload = setup[1].payloads[-1][1]
    assert payload["learner_history"]
    assert payload["approved_teaching_profile"]["preferences"]["tone"] == "precise"


@pytest.mark.asyncio
async def test_absent_requested_detail_abstains_even_when_model_boundary_says_answerable(setup):
    setup[1].proposal["aspects"].append({"requirement": "exact numeric digest width", "supported": False, "spans": []})
    answer = await generate(setup)
    assert answer.trace.policy_action == "no-evidence"
    assert not answer.atomic_claims and not answer.citations
    assert setup[3].chunk.text not in answer.content


@pytest.mark.asyncio
async def test_socratic_stage_withholds_answer_with_explicit_question_action(setup):
    setup[1].proposal["teaching_move"] = "ask"
    answer = await generate(setup, "ask_next_step")
    assert answer.trace.policy_action == "question"
    assert "checksum audit" in answer.content
    assert "digest" not in answer.content
    assert not answer.citations and not answer.atomic_claims
    plan = PedagogicalPlanV2(action=AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        reason_code="fresh-test", stop_condition="Wait for attempt.", replan_condition="Attempt received.")
    response = _grounded_response_v2(answer, plan)
    assert response.policy_action == "question"
    assert not response.atomic_claims


@pytest.mark.asyncio
async def test_invalid_span_fails_closed_without_deterministic_passage_fallback(setup):
    setup[1].proposal["aspects"][0]["spans"][0]["text"] = "The digest is 128 bits."
    answer = await generate(setup)
    assert answer.trace.policy_action == "safe-provider-failure"
    assert not answer.citations
    assert "128" not in answer.content


@pytest.mark.asyncio
async def test_provider_failure_and_invalid_focus_cannot_release_source(setup):
    setup[1].proposal["teaching_move"] = "ask"
    setup[1].proposal["question_focus"] = "the digest is 128 bits"
    answer = await generate(setup, "ask_next_step")
    assert answer.trace.policy_action == "safe-provider-failure"
    setup[1].proposal = None
    answer = await generate(setup)
    assert answer.trace.policy_action == "safe-provider-failure"


def test_candidate_schema_and_factory_are_explicit(setup):
    assert isinstance(setup[0].tutoring.generator, QuestionSpecificProfileGroundedGenerator)
    assert setup[0].tutoring.tutoring_graph.generator_model_id == "gpt-5.6-luna"
    schema = OpenAiResponsesClient._schema(TASK)
    assert set(schema["required"]) == {"boundary", "aspects", "teaching_move", "question_focus", "hint_span"}


@pytest.mark.asyncio
async def test_actual_service_persists_question_without_disguising_it_as_abstention(setup):
    runtime, client, _release, _hit = setup
    client.proposal["teaching_move"] = "ask"
    turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
        content="How does checksum audit detect altered bytes?", client_request_id="fresh-question-stage")
    assert turn.tutor_message.action == "question"
    assert not turn.citations
    assert "digest" not in turn.tutor_message.content
    responses = runtime.repository.list_grounded_responses_v2(runtime.conversation_id)
    assert responses[-1].policy_action == "question"


@pytest.mark.asyncio
async def test_actual_service_paraphrase_reaches_async_assessor_despite_lexical_sufficiency_failure(setup):
    runtime, client, _release, hit = setup
    from services.api.app.factory import _configured_evidence_gate
    from services.api.app.config import AppSettings, EvidenceGateMode
    question = "How can retrieval reveal tampering?"
    gate = _configured_evidence_gate(AppSettings(evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3))
    assert not gate.assess(question, [hit]).sufficient
    client.proposal["question_focus"] = "retrieval"
    await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
        content=question, client_request_id="fresh-paraphrase")
    assert any(task == TASK for task, _payload in client.payloads)
    assert runtime.tutoring.evidence_gate.implementation_id == "authorized-top5-async-answerability-admission-v1"


@pytest.mark.asyncio
async def test_assessed_attempt_allows_profile_governed_progression_to_explanation(setup):
    runtime, client, release, hit = setup
    client.proposal["teaching_move"] = "ask"
    parameters = dict(intent="ask_next_step", help_level=0,
        teaching_profile_context={"preferences": {"help_ladder": ["diagnostic question", "explanation after attempt"]}})
    first = await runtime.tutoring.generator.generate_for_intent("How does checksum audit detect altered bytes?",
        [hit], release.policy, **parameters, learner_attempt_present=False)
    client.proposal["teaching_move"] = "explain"
    following = await runtime.tutoring.generator.generate_for_intent("How does checksum audit detect altered bytes?",
        [hit], release.policy, **parameters, learner_attempt_present=True,
        learner_history=[{"role": "student", "content": "I would compare the stored digest with a fresh digest."}])
    assert first.trace.policy_action == "question"
    assert following.trace.policy_action == "answer"
    assert following.atomic_claims and following.citations
    assert client.payloads[-1][1]["application_observed_attempt"] is True


@pytest.mark.asyncio
async def test_actual_service_does_not_promote_prior_assessment_to_current_attempt(setup):
    runtime, client, release, _hit = setup
    await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
        content="My attempt for checksum audit: " + release.chunks[0].text,
        client_request_id="fresh-attempt-before-explanation")
    client.proposal["teaching_move"] = "explain"
    turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
        content="How does checksum audit detect altered bytes?", client_request_id="fresh-after-attempt")
    candidate_payloads = [payload for task, payload in client.payloads if task == TASK]
    assert candidate_payloads[-1]["application_observed_attempt"] is False
    assert candidate_payloads[-1]["learner_history"][-1]["action"] == "answer"
    assert turn.tutor_message.action == "answer"


@pytest.mark.asyncio
async def test_no_profile_retains_initial_elicitation_fallback(setup):
    runtime, client, release, hit = setup
    client.proposal["teaching_move"] = "explain"
    answer = await runtime.tutoring.generator.generate_for_intent("How does checksum audit detect altered bytes?",
        [hit], release.policy, intent="diagnose_understanding", help_level=0)
    assert answer.trace.policy_action == "question"


@pytest.mark.asyncio
@pytest.mark.parametrize("setup", ["explanatory"], indirect=True)
async def test_explanatory_profile_overrides_advisory_initial_diagnosis_in_actual_service(setup):
    runtime, client, _release, _hit = setup
    client.proposal["teaching_move"] = "explain"
    turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
        content="How does checksum audit detect altered bytes?",
        client_request_id="fresh-explanatory-initial-diagnosis")
    payload = next(payload for task, payload in client.payloads if task == TASK)
    assert payload["pedagogical_intent"] == "diagnose_understanding"
    assert payload["approved_teaching_profile"]["preferences"] == PROFILES["explanatory"]
    assert turn.tutor_message.action == "answer"
    assert turn.citations


@pytest.mark.asyncio
async def test_unused_empty_focus_is_valid_for_explanation(setup):
    setup[1].proposal["question_focus"] = ""
    answer = await generate(setup)
    assert answer.trace.policy_action == "answer"
    assert answer.atomic_claims and answer.citations


@pytest.mark.asyncio
@pytest.mark.parametrize("boundary,action", [("clarify", "clarify"), ("insufficient", "no-evidence")])
async def test_nonanswer_boundary_allows_empty_aspects_and_focus(setup, boundary, action):
    setup[1].proposal.update(boundary=boundary, aspects=[], question_focus="")
    answer = await generate(setup)
    assert answer.trace.policy_action == action
    assert not answer.atomic_claims and not answer.citations


@pytest.mark.asyncio
async def test_answerable_empty_aspects_cannot_pass_vacuously(setup):
    setup[1].proposal.update(aspects=[], question_focus="")
    answer = await generate(setup)
    assert answer.trace.policy_action == "safe-provider-failure"
    assert not answer.citations


@pytest.mark.asyncio
@pytest.mark.parametrize("focus", ["", " "])
async def test_actual_ask_requires_nonblank_question_focus(setup, focus):
    setup[1].proposal.update(teaching_move="ask", question_focus=focus)
    answer = await generate(setup)
    assert answer.trace.policy_action == "safe-provider-failure"
    assert not answer.citations


@pytest.mark.asyncio
async def test_insufficient_private_question_does_not_solicit_source_upload(setup):
    runtime, client, release, hit = setup
    client.proposal.update(boundary="insufficient", aspects=[], question_focus="")
    answer = await runtime.tutoring.generator.generate_for_intent(
        "What did another student privately tell the instructor about checksum audit?",
        [hit], release.policy, intent="explain_concept", help_level=0)
    assert answer.trace.policy_action == "no-evidence"
    assert "Please ask the instructor" in answer.content
    assert "provide" not in answer.content.lower() and "upload" not in answer.content.lower()
    assert not answer.citations and not answer.atomic_claims


@pytest.mark.asyncio
async def test_actual_service_forwards_its_question_action_on_declarative_attempt(setup):
    runtime, client, release, _hit = setup
    client.proposal.update(teaching_move="ask", question_focus="checksum audit")
    await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
        content="How does checksum audit detect altered bytes?", client_request_id="progress-v2-question")
    client.proposal.update(teaching_move="hint", hint_span={"citation_id": "S1", "text": "compares a newly computed digest"})
    turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
        content="My attempt for checksum audit: I would skip the comparison.", client_request_id="progress-v2-attempt")
    payload = [p for task, p in client.payloads if task == TASK][-1]
    assert payload["dialogue_progression"]["previous_tutor_asked_question"] is True
    assert payload["learner_history"][-1]["action"] == "question"
    assert turn.tutor_message.action == "answer"
    assert turn.tutor_message.content.startswith("Hint: compares a newly computed digest")
    assert "to detect altered bytes" not in turn.tutor_message.content
    assert len(turn.citations) == 1


@pytest.mark.asyncio
async def test_hint_requires_exact_separate_span_and_never_uses_full_answer_fallback(setup):
    setup[1].proposal.update(teaching_move="hint", hint_span=None)
    answer = await generate(setup)
    assert answer.trace.policy_action == "safe-provider-failure"
    setup[1].proposal["hint_span"] = {"citation_id": "S1", "text": "invented hint"}
    answer = await generate(setup)
    assert answer.trace.policy_action == "safe-provider-failure"
    assert not answer.citations and not answer.atomic_claims


@pytest.mark.asyncio
async def test_profile_controlled_post_hint_explanation_and_never_answer_question(setup):
    runtime, client, release, hit = setup
    history = [{"role": "student", "action": "question", "content": "How does checksum audit work?"},
        {"role": "tutor", "action": "answer", "content": "Hint: compares a newly computed digest"}]
    client.proposal.update(teaching_move="explain", question_focus="")
    explanation = await runtime.tutoring.generator.generate_for_intent(
        "I still need help with checksum audit.", [hit], release.policy,
        intent="ask_next_step", help_level=0,
        teaching_profile_context={"preferences": PROFILES["socratic"]}, learner_history=history)
    assert explanation.trace.policy_action == "answer" and not explanation.content.startswith("Hint:")
    assert client.payloads[-1][1]["dialogue_progression"]["recent_hint_count"] == 1
    client.proposal.update(teaching_move="ask", question_focus="checksum audit")
    question = await runtime.tutoring.generator.generate_for_intent(
        "I still need help with checksum audit.", [hit], release.policy,
        intent="ask_next_step", help_level=0,
        teaching_profile_context={"preferences": {"help_ladder": ["diagnostic question", "never reveal the direct answer"]}},
        learner_history=history)
    assert question.trace.policy_action == "question" and not question.citations


@pytest.mark.asyncio
async def test_hint_cannot_copy_every_proposed_solution_span(setup):
    client = setup[1]
    full = client.proposal["aspects"][0]["spans"][0]["text"]
    client.proposal.update(teaching_move="hint", hint_span={"citation_id": "S1", "text": full})
    answer = await generate(setup)
    assert answer.trace.policy_action == "safe-provider-failure"
    client.proposal["aspects"][0]["spans"] = [
        {"citation_id": "S1", "text": "compares a newly computed digest"},
        {"citation_id": "S1", "text": "to detect altered bytes"}]
    answer = await generate(setup)
    assert answer.trace.policy_action == "safe-provider-failure"
    assert not answer.citations and not answer.atomic_claims


@pytest.mark.asyncio
async def test_v3_exposes_same_bounds_without_weakening_validation(setup):
    from src.digital_twin.generation.question_specific import (
        QuestionSpecificProposal, response_contract_limits, BOUNDED_CONTRACT_CANDIDATE_ID,
    )
    runtime, client, release, hit = setup
    generator = QuestionSpecificProfileGroundedGenerator(client, model_id="gpt-5.6-luna",
        bounded_contract_enabled=True, policy_enforcer=runtime.tutoring.generator.policy_enforcer)
    answer = await generator.generate_for_intent("How does checksum audit detect altered bytes?",
        [hit], release.policy, intent="explain_concept", help_level=0)
    assert answer.trace.prompt_version == BOUNDED_CONTRACT_CANDIDATE_ID
    limits = client.payloads[-1][1]["response_contract"]
    assert limits == response_contract_limits()
    assert limits["max_aspects"] == QuestionSpecificProposal.model_json_schema()["properties"]["aspects"]["maxItems"] == 4
    client.proposal["aspects"] *= 5
    failure = await generator.generate_for_intent("How does checksum audit detect altered bytes?",
        [hit], release.policy, intent="explain_concept", help_level=0)
    assert failure.trace.policy_action == "safe-provider-failure"
    assert not failure.citations and not failure.atomic_claims


@pytest.mark.asyncio
async def test_v2_control_omits_v3_contract_context(setup):
    answer = await generate(setup)
    assert answer.trace.prompt_version == "question-specific-profile-grounded-v2"
    assert "response_contract" not in setup[1].payloads[-1][1]
