import copy
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_output_cap_progression_development import CARDS
from scripts.teaching_profile_responsiveness_packet import PROFILES
from services.llm.openai_responses_client import OpenAiResponsesClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.generation.instructional import TASK, InstructionalProposal, InstructionalSourceBindingValidator
from src.digital_twin.grounding.models import AtomicAnswerClaim, ClaimSourceBinding, GenerationUsage, RetrievalHit
from src.digital_twin.llm import LlmMalformedResponseError, LlmMessage, LlmResponse

SPAN = "It rejects any update from a retired epoch, even when its sequence number is larger."
QUESTION = "How does cobalt ticket handle a retired epoch with a larger sequence?"


def proposal():
    return {"boundary": "answerable", "aspects": [{"requirement": "retired epoch outcome", "supported": True,
        "spans": [{"citation_id": "S1", "text": SPAN}]}], "teaching_move": "explain", "hint_span": None,
        "question_focus": "", "instructional_question": None, "feedback": None,
        "explanation_steps": [{"text": "Reject the update: a retired epoch is rejected even when the sequence is larger.",
            "aspect_indexes": [1]}]}


class Client:
    def __init__(self):
        self.value = proposal()
        self.requests = []

    async def chat(self, messages, task):
        payload = json.loads(messages[-1].content)
        self.requests.append((task, payload))
        if task != TASK:
            raise LlmMalformedResponseError(stage="contract-planner", usage=GenerationUsage(approximate_cost_usd=0))
        return LlmResponse(content=json.dumps(self.value), provider_model="gpt-5.6-luna",
            usage=GenerationUsage(input_tokens=10, output_tokens=10, total_tokens=20, approximate_cost_usd=.0001))


@pytest.fixture
def runtime(tmp_path):
    client = Client()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="instructional-contract", planner_client=client, teaching_profile_context_enabled=True,
        question_specific_generation_enabled=True, bounded_generation_contract_enabled=True,
        named_referent_context_enabled=True, instructional_moves_enabled=True,
        teaching_profile_values=PROFILES["explanatory"])
    runtime = factory(SimpleNamespace(case_id="instructional"), VirtualUtcClock(datetime(2026, 9, 23, tzinfo=UTC)))
    release = runtime.repository.get_release(runtime.release_id)
    hit = RetrievalHit(chunk=next(c for c in release.chunks if SPAN in c.text), relevance_score=1, raw_score=1)
    yield runtime, client, release, hit
    runtime.close_runtime(runtime)


async def generate(runtime, question=QUESTION):
    rt, _, release, hit = runtime
    return await rt.tutoring.generator.generate_for_intent(question, [hit], release.policy,
        intent="explain_concept", help_level=0, teaching_profile_context={"preferences": {"tone": "precise"}},
        authorized_concept_labels=("cobalt ticket",))


@pytest.mark.asyncio
async def test_explanation_records_honest_paraphrase_and_exact_binding(runtime):
    answer = await generate(runtime)
    assert answer.trace.policy_action == "answer"
    assert answer.content != SPAN
    assert answer.atomic_claims[0].text == answer.content
    assert answer.atomic_claims[0].source_bindings[0].text == SPAN
    assert "semantic-support-unverified" in answer.trace.validation_scope
    payload = runtime[1].requests[-1][1]
    assert payload["approved_concept_labels"] == ["cobalt ticket"]
    assert payload["instructional_contract"]["max_explanation_steps"] == 3


@pytest.mark.asyncio
async def test_specific_question_can_use_approved_label_for_short_followup(runtime):
    value = runtime[1].value
    value.update(teaching_move="ask", explanation_steps=[], instructional_question={"kind": "identify_condition",
        "text": "Which check should the receiver apply before comparing sequence numbers?",
        "focus": "cobalt ticket", "focus_lineage": "approved_concept"})
    answer = await generate(runtime, "I still don't know.")
    assert answer.trace.policy_action == "question"
    assert answer.content == value["instructional_question"]["text"]
    assert not answer.citations and not answer.atomic_claims
    assert SPAN not in answer.content


@pytest.mark.asyncio
async def test_feedback_is_tied_to_current_attempt_and_can_advance(runtime):
    question = "My attempt: the retired epoch should be rejected even with a larger sequence."
    runtime[1].value["feedback"] = {"student_excerpt": "the retired epoch should be rejected", "status": "supported",
        "text": "Your rejection step matches the approved rule; sequence size does not rescue a retired epoch.",
        "support": [{"citation_id": "S1", "text": SPAN}]}
    answer = await generate(runtime, question)
    assert answer.trace.policy_action == "answer"
    assert "Your attempt:" in answer.content and "matches the approved rule" in answer.content
    assert len(answer.atomic_claims) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["unknown-focus", "missing-aspect", "false-quote", "wrong-current-excerpt", "ask-with-explanation"])
async def test_structural_violations_fail_closed(runtime, mutation):
    value = runtime[1].value
    if mutation == "unknown-focus":
        value.update(teaching_move="ask", explanation_steps=[], instructional_question={"kind": "predict",
            "text": "What will happen?", "focus": "unknown protocol", "focus_lineage": "approved_concept"})
    elif mutation == "missing-aspect":
        value["aspects"].append(copy.deepcopy(value["aspects"][0]))
    elif mutation == "false-quote":
        value["aspects"][0]["spans"][0]["text"] = "There is a secret bypass."
    elif mutation == "wrong-current-excerpt":
        value["feedback"] = {"student_excerpt": "I solved everything", "status": "supported", "text": "Good.",
            "support": [{"citation_id": "S1", "text": SPAN}]}
    else:
        value.update(teaching_move="ask", instructional_question={"kind": "predict", "text": "What happens?",
            "focus": "retired epoch", "focus_lineage": "current_message"})
    answer = await generate(runtime)
    assert answer.trace.policy_action == "safe-provider-failure"
    assert not answer.citations


def test_planted_wrong_paraphrase_can_pass_binding_but_has_no_semantic_pass(runtime):
    hit = runtime[3]
    wrong = AtomicAnswerClaim(claim_id="claim-planted-wrong", text="Accept all retired epochs.",
        evidence_hit_ids=[hit.chunk.id], source_bindings=[ClaimSourceBinding(evidence_hit_id=hit.chunk.id, text=SPAN)])
    decision = InstructionalSourceBindingValidator().validate([wrong], [hit])
    assert decision.releasable  # Deliberate limitation, independently reviewed as incorrect.
    assert decision.supported_claim_count == 0
    assert decision.features["semantic_support_unverified"] is True
    assert decision.features["score_kind"] == "structural-source-binding-only"
    wrong.source_bindings[0].text = "Not an approved quote."
    assert not InstructionalSourceBindingValidator().validate([wrong], [hit]).releasable


@pytest.mark.asyncio
async def test_actual_graph_accepts_candidate_binding_and_persists_honest_scope(runtime):
    rt, client, _, _ = runtime
    # Actual retrieval alias assignment is inspectable rather than assumed.
    original_chat = client.chat
    async def chat(messages, task):
        if task == TASK:
            payload = json.loads(messages[-1].content)
            alias = next(e["citation_id"] for e in payload["evidence"] if SPAN in e["text"])
            client.value["aspects"][0]["spans"][0]["citation_id"] = alias
        return await original_chat(messages, task)
    client.chat = chat
    turn = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content=QUESTION, client_request_id="first")
    assert turn.tutor_message.action == "answer"
    assert turn.tutor_message.trace.prompt_version == "question-specific-profile-grounded-v5"
    assert "semantic-support-unverified" in turn.tutor_message.trace.validation_scope
    assert turn.citations
    events = rt.repository.list_audit_events()
    decisions = [event for event in events if event.event_type == "post-generation-claim-validation"]
    assert decisions[-1].details["semantic_support_unverified"]
    assert decisions[-1].details["supported_claim_count"] == 0


@pytest.mark.asyncio
async def test_actual_http_envelope_dispatches_new_schema_and_rejects_oversized_steps(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    value = proposal()
    captured = []
    async def post(**kwargs):
        captured.append(kwargs["json"])
        return httpx.Response(200, request=httpx.Request("POST", OpenAiResponsesClient.API_URL), json={
            "status": "completed", "model": "gpt-5.6-luna", "usage": {"input_tokens": 10, "output_tokens": 20},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}]})
    client = OpenAiResponsesClient("gpt-5.6-luna", post=post, max_output_tokens=1500)
    response = await client.chat([LlmMessage(role="user", content="Use approved evidence")], TASK)
    assert InstructionalProposal.model_validate_json(response.content).explanation_steps
    assert "instructional_question" in captured[-1]["text"]["format"]["schema"]["properties"]
    value["explanation_steps"] *= 4
    with pytest.raises(LlmMalformedResponseError):
        await client.chat([LlmMessage(role="user", content="Use approved evidence")], TASK)
