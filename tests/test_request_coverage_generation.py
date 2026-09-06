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
from src.digital_twin.generation.request_coverage import RequestCoverageProposal, TASK
from src.digital_twin.grounding.models import GenerationUsage, RetrievalHit
from src.digital_twin.llm import LlmMalformedResponseError, LlmMessage, LlmResponse

RULE = "Cobalt ticket rejects an update from a retired epoch even if its sequence number is larger."
DEFINITION = "Private tutoring history means the messages and feedback in a learner's own account."
ACCESS = "A learner may request their own record through the authenticated account portal."
POLICY = DEFINITION + " " + ACCESS + " Staff may review records for an authorized teaching purpose."
CARDS = (
    ConceptCardV1(concept_id="cobalt", label="cobalt ticket", description=RULE, objective="Apply the rule."),
    ConceptCardV1(concept_id="privacy", label="privacy terminology", description=POLICY, objective="Explain the definition and access rules."),
)
QUESTION = "Explain the retired epoch rule for cobalt ticket."


def aspect(focus, goal="explain_rule", text=RULE, supported=True):
    return {"requirement": focus, "request_focus": focus, "goal": goal, "supported": supported,
        "spans": [{"citation_id": "S1", "text": text}] if supported else []}


def proposal():
    return {"boundary": "answerable", "aspects": [aspect("retired epoch rule")], "teaching_move": "explain",
        "instructional_question": None, "feedback": None, "explanation_steps": [{"text": RULE, "aspect_indexes": [1]}],
        "partial_guidance": None, "boundary_reason": "none", "supported_response_aspect_indexes": []}


class Client:
    def __init__(self):
        self.value = proposal()

    async def chat(self, messages, task):
        if task != TASK:
            raise LlmMalformedResponseError(stage="contract-planner", usage=GenerationUsage(approximate_cost_usd=0))
        payload = json.loads(messages[-1].content)
        spans = [span for a in self.value["aspects"] for span in a["spans"]]
        if self.value["feedback"]:
            spans += self.value["feedback"]["support"]
        for span in spans:
            span["citation_id"] = next(e["citation_id"] for e in payload["evidence"] if span["text"] in e["text"])
        return LlmResponse(content=json.dumps(self.value), provider_model="gpt-5.6-luna",
            usage=GenerationUsage(input_tokens=10, output_tokens=10, total_tokens=20, approximate_cost_usd=.0001))


@pytest.fixture
def runtime(tmp_path):
    client = Client()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="coverage-contract", planner_client=client, teaching_profile_context_enabled=True,
        question_specific_generation_enabled=True, bounded_generation_contract_enabled=True,
        named_referent_context_enabled=True, instructional_moves_enabled=True, instructional_continuation_enabled=True,
        instructional_request_coverage_enabled=True, teaching_profile_values=PROFILES["explanatory"])
    rt = factory(SimpleNamespace(case_id="coverage"), VirtualUtcClock(datetime(2026, 9, 25, tzinfo=UTC)))
    release = rt.repository.get_release(rt.release_id)
    hits = [RetrievalHit(chunk=c, relevance_score=1, raw_score=1) for c in release.chunks]
    yield rt, client, release, hits
    rt.close_runtime(rt)


async def generate(runtime, question=QUESTION):
    rt, _, release, hits = runtime
    return await rt.tutoring.generator.generate_for_intent(question, hits, release.policy,
        intent="explain_concept", help_level=0, teaching_profile_context={"preferences": {"tone": "precise"}},
        authorized_concept_labels=("cobalt ticket", "privacy terminology"))


def feedback():
    return {"learner_reference": "current_message", "status": "supported",
        "text": "Your rejection step follows the rule; a larger sequence does not rescue a retired epoch.",
        "support": [{"citation_id": "S1", "text": RULE}]}


@pytest.mark.asyncio
async def test_long_actual_attempt_uses_reference_and_labeled_server_excerpt(runtime):
    rt, client, _, _ = runtime
    question = "My attempt: " + ("I check the epoch before the sequence. " * 12) + " Is this correct?"
    client.value["aspects"] = [aspect("Is this correct?", "assess_attempt")]
    client.value["feedback"] = feedback()
    turn = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content=question, client_request_id="long")
    assert turn.tutor_message.action == "answer"
    assert 'Your message (excerpt): “' + question[:200] + '”' in turn.tutor_message.content
    assert feedback()["text"] in turn.tutor_message.content
    assert rt.repository.list_messages(rt.conversation_id)[0].content == question
    assert turn.tutor_message.trace.prompt_version == "question-specific-profile-grounded-v7"


@pytest.mark.asyncio
async def test_all_missing_requested_items_remain_visible(runtime):
    runtime[1].value.update(boundary="insufficient", boundary_reason="missing_evidence", explanation_steps=[],
        aspects=[aspect("my messages", "provide_information", supported=False),
            aspect("my email", "provide_information", supported=False), aspect("how to request a copy", text=ACCESS)],
        supported_response_aspect_indexes=[3])
    answer = await generate(runtime, "Show my messages and my email, and explain how to request a copy.")
    assert answer.trace.policy_action == "answer"
    assert "my messages" in answer.content and "my email" in answer.content and ACCESS in answer.content
    assert "my messages" in answer.trace.unresolved_detail and "my email" in answer.trace.unresolved_detail


@pytest.mark.asyncio
async def test_pure_definition_does_not_render_unsolicited_paraphrased_restriction(runtime):
    runtime[1].value["aspects"] = [aspect("private tutoring history", "define_term", DEFINITION)]
    runtime[1].value["explanation_steps"] = [{"text": "Private tutoring history is a record. Only learners may access it.", "aspect_indexes": [1]}]
    answer = await generate(runtime, "Define private tutoring history.")
    assert answer.content == DEFINITION
    assert "Only learners" not in answer.content
    assert answer.citations and answer.atomic_claims[0].text == DEFINITION


@pytest.mark.asyncio
async def test_compound_definition_and_application_are_not_discarded(runtime):
    runtime[1].value["aspects"] = [aspect("private tutoring history", "define_term", DEFINITION),
        aspect("how to request a copy", "apply_rule", ACCESS)]
    content = DEFINITION + " To obtain your copy, use the authenticated account portal."
    runtime[1].value["explanation_steps"] = [{"text": content, "aspect_indexes": [1, 2]}]
    answer = await generate(runtime, "Define private tutoring history and explain how to request a copy.")
    assert answer.content == content


@pytest.mark.asyncio
async def test_initial_mixed_boundary_can_elicit_without_solution(runtime):
    runtime[1].value.update(boundary="insufficient", boundary_reason="missing_evidence", teaching_move="ask",
        aspects=[aspect("retired epoch rule"), aspect("exact bit width", "provide_information", supported=False)],
        explanation_steps=[], instructional_question={"kind": "identify_condition",
            "text": "Which field should be checked before comparing sequence numbers?", "focus": "cobalt ticket",
            "focus_lineage": "approved_concept"})
    question = "I have not attempted cobalt ticket: help with the retired epoch rule and its exact bit width."
    answer = await generate(runtime, question)
    assert answer.trace.policy_action == "no-evidence"
    assert "exact bit width" in answer.content and "Which field" in answer.content and RULE not in answer.content
    runtime[1].value["instructional_question"]["focus"] = "invented protocol"
    assert (await generate(runtime, question)).trace.policy_action == "safe-provider-failure"


@pytest.mark.asyncio
async def test_post_attempt_mixed_reply_renders_supported_feedback_application_and_missing_detail(runtime):
    runtime[1].value.update(boundary="insufficient", boundary_reason="missing_evidence", feedback=feedback(),
        aspects=[aspect("Is this correct?", "assess_attempt"),
            aspect("apply the retired epoch rule", "apply_rule"), aspect("exact bit width", "provide_information", supported=False)],
        supported_response_aspect_indexes=[1, 2],
        explanation_steps=[{"text": "Reject the retired-epoch update even with its larger sequence.", "aspect_indexes": [1, 2]}])
    answer = await generate(runtime, "My attempt is to reject the retired epoch. Is this correct? Please apply the retired epoch rule and give its exact bit width.")
    assert answer.trace.policy_action == "answer" and answer.citations
    assert "Your message (excerpt)" in answer.content and feedback()["text"] in answer.content
    assert "Reject the retired-epoch update" in answer.content and "exact bit width" in answer.content
    assert "exact bit width" in answer.trace.unresolved_detail


@pytest.mark.asyncio
async def test_unknown_request_focus_fails_closed(runtime):
    runtime[1].value["aspects"][0]["request_focus"] = "something absent"
    assert (await generate(runtime)).trace.policy_action == "safe-provider-failure"


def test_unsupported_aspect_cannot_claim_support():
    data = proposal()
    data["aspects"][0]["supported"] = False
    with pytest.raises(ValueError, match="cannot declare support"):
        RequestCoverageProposal.model_validate(data)


@pytest.mark.asyncio
async def test_compact_v7_http_schema_omits_copied_excerpt_and_legacy_fields(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    async def post(**kwargs):
        schema = kwargs["json"]["text"]["format"]["schema"]
        assert "missing_focus" not in schema["properties"] and "hint_span" not in schema["properties"]
        assert "student_excerpt" not in json.dumps(schema)
        return httpx.Response(200, request=httpx.Request("POST", OpenAiResponsesClient.API_URL), json={
            "status": "completed", "model": "gpt-5.6-luna", "usage": {"input_tokens": 10, "output_tokens": 20},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(proposal())}]}]})
    response = await OpenAiResponsesClient("gpt-5.6-luna", post=post, max_output_tokens=3000).chat(
        [LlmMessage(role="user", content=QUESTION)], TASK)
    assert RequestCoverageProposal.model_validate_json(response.content).aspects[0].request_focus == "retired epoch rule"
