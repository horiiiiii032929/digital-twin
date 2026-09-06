import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_output_cap_progression_development import CARDS
from scripts.teaching_profile_responsiveness_packet import PROFILES
from services.llm.openai_responses_client import OpenAiResponsesClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.generation.continuation import ContinuationProposal, InstructionalContinuationGenerator, TASK
from src.digital_twin.generation.instructional import EvidenceLinkedInstructionalGenerator, InstructionalQuestion
from src.digital_twin.grounding.models import GenerationUsage, RetrievalHit
from src.digital_twin.llm import LlmMalformedResponseError, LlmMessage, LlmResponse

SPAN = "It rejects any update from a retired epoch, even when its sequence number is larger."
QUESTION = "How does cobalt ticket handle a retired epoch with a larger sequence?"


def value():
    return {"boundary": "answerable", "aspects": [{"requirement": "retired epoch outcome", "supported": True,
        "spans": [{"citation_id": "S1", "text": SPAN}]}], "teaching_move": "ask", "hint_span": None,
        "question_focus": "", "instructional_question": {"kind": "predict",
            "text": "Predict what happens when the epoch is retired and the sequence is larger. Explain which rule applies.",
            "focus": "cobalt ticket", "focus_lineage": "approved_concept"},
        "feedback": None, "explanation_steps": [], "partial_guidance": None,
        "boundary_reason": "none", "missing_focus": "", "supported_focus": ""}


class Client:
    def __init__(self):
        self.value = value()

    async def chat(self, messages, task):
        if task != TASK:
            raise LlmMalformedResponseError(stage="contract-plan", usage=GenerationUsage(approximate_cost_usd=0))
        payload = json.loads(messages[-1].content)
        if payload["evidence"]:
            alias = next(e["citation_id"] for e in payload["evidence"] if SPAN in e["text"])
            self.value["aspects"][0]["spans"][0]["citation_id"] = alias
            if self.value["feedback"]:
                self.value["feedback"]["support"][0]["citation_id"] = alias
        return LlmResponse(content=json.dumps(self.value), provider_model="gpt-5.6-luna",
            usage=GenerationUsage(input_tokens=10, output_tokens=10, total_tokens=20, approximate_cost_usd=.0001))


@pytest.fixture
def runtime(tmp_path):
    client = Client()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="continuation-contract", planner_client=client, teaching_profile_context_enabled=True,
        question_specific_generation_enabled=True, bounded_generation_contract_enabled=True,
        named_referent_context_enabled=True, instructional_moves_enabled=True, instructional_continuation_enabled=True,
        teaching_profile_values=PROFILES["explanatory"])
    rt = factory(SimpleNamespace(case_id="continuation"), VirtualUtcClock(datetime(2026, 9, 24, tzinfo=UTC)))
    release = rt.repository.get_release(rt.release_id)
    hit = RetrievalHit(chunk=next(c for c in release.chunks if SPAN in c.text), relevance_score=1, raw_score=1)
    yield rt, client, release, hit
    rt.close_runtime(rt)


async def generate(runtime, question=QUESTION):
    rt, _, release, hit = runtime
    return await rt.tutoring.generator.generate_for_intent(question, [hit], release.policy,
        intent="explain_concept", help_level=0, teaching_profile_context={"preferences": {"tone": "precise"}},
        authorized_concept_labels=("cobalt ticket",))


def test_all_twelve_recorded_punctuation_failures_are_valid_bounded_elicitation():
    audit = json.loads(Path("research/05_evaluation/paired-pedagogy-live-001-local-rendering-audit.json").read_text())
    rows = [r for r in audit["cases"] if r["delivered_action"] == "safe-graph-failure"
        and r["error"] == "instructional move requires a bounded question"]
    assert len(rows) == 12
    for row in rows:
        unit = InstructionalQuestion.model_validate(row["instructional_question"])
        proposal = SimpleNamespace(instructional_question=unit)
        with pytest.raises(ValueError):
            EvidenceLinkedInstructionalGenerator._question(proposal, row["question"], (unit.focus,))
        if unit.focus_lineage == "current_message" and unit.focus not in row["question"]:
            # One recorded proposal has a second defect: lower-case 'what' does
            # not exactly match current 'What'. Removing punctuation does not
            # silently relax the declared focus lineage contract.
            with pytest.raises(ValueError, match="lineage"):
                InstructionalContinuationGenerator._question(proposal, row["question"], (unit.focus,))
        else:
            assert InstructionalContinuationGenerator._question(proposal, row["question"], (unit.focus,)) == unit.text


@pytest.mark.asyncio
async def test_feedback_and_specific_prompt_render_with_honest_claims(runtime):
    runtime[1].value["feedback"] = {"student_excerpt": "the retired epoch is rejected", "status": "supported",
        "text": "Your rejection step matches the approved rule.", "support": [{"citation_id": "S1", "text": SPAN}]}
    answer = await generate(runtime, "My attempt: the retired epoch is rejected even with a larger sequence.")
    assert answer.trace.policy_action == "answer" and answer.citations
    assert "Your attempt:" in answer.content
    assert len(answer.atomic_claims) == 2
    assert answer.atomic_claims[-1].text == runtime[1].value["instructional_question"]["text"]
    assert all(c.source_bindings for c in answer.atomic_claims)


@pytest.mark.asyncio
@pytest.mark.parametrize("guidance", [
    "Compare the incoming epoch with the active epoch before considering sequence size.",
    "Reject every retired epoch, even if its sequence number is larger.",
    SPAN,
])
async def test_partial_guidance_binding_is_not_a_semantic_disclosure_gate(runtime, guidance):
    runtime[1].value.update(teaching_move="hint", partial_guidance={"text": guidance, "aspect_indexes": [1]})
    answer = await generate(runtime)
    assert answer.trace.policy_action == "answer"
    assert guidance in answer.content
    assert "semantic-support-unverified" in answer.trace.validation_scope
    # Two fixtures intentionally disclose the full outcome. Structural acceptance
    # is demonstrated, not a teaching-quality success or withholding guarantee.


@pytest.mark.asyncio
async def test_missing_detail_is_named_and_supported_part_offered(runtime):
    runtime[1].value.update(boundary="insufficient", boundary_reason="missing_evidence",
        missing_focus="exact epoch bit width", supported_focus="retired epoch treatment",
        instructional_question=None, teaching_move="explain")
    runtime[1].value["aspects"].append({"requirement": "epoch bit width", "supported": False, "spans": []})
    answer = await generate(runtime, "Explain retired epoch treatment and the exact epoch bit width for cobalt ticket.")
    assert answer.trace.policy_action == "no-evidence"
    assert "exact epoch bit width" in answer.content and "I can help explain “retired epoch treatment”" in answer.content
    assert not answer.citations and "32" not in answer.content


@pytest.mark.asyncio
async def test_typed_third_party_refusal_and_no_automatic_privacy_keyword_rule(runtime):
    runtime[1].value.update(boundary="insufficient", boundary_reason="third_party_private_request",
        missing_focus="another student's private grade", instructional_question=None)
    answer = await generate(runtime, "For cobalt ticket, disclose another student's private grade.")
    assert "cannot disclose another person's private information" in answer.content
    # These negatives supply an approved, non-private proposal; they test absence
    # of a blanket keyword rule, not whether a live model classifies them correctly.
    runtime[1].value = value()
    for question in ["Discuss privacy policy while we work on cobalt ticket.", "Help with my own cobalt ticket attempt."]:
        answer = await generate(runtime, question)
        assert answer.trace.policy_action == "question"
        assert "cannot disclose" not in answer.content


@pytest.mark.asyncio
async def test_boundary_focus_cannot_invent_missing_detail(runtime):
    runtime[1].value.update(boundary="insufficient", boundary_reason="missing_evidence",
        missing_focus="an invented detail", instructional_question=None)
    answer = await generate(runtime)
    assert answer.trace.policy_action == "safe-provider-failure"


@pytest.mark.asyncio
async def test_actual_graph_accepts_imperative_and_retains_v6(runtime):
    rt = runtime[0]
    turn = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id, content=QUESTION, client_request_id="initial")
    assert turn.tutor_message.action == "question"
    assert turn.tutor_message.trace.prompt_version == "question-specific-profile-grounded-v6"


@pytest.mark.asyncio
async def test_new_task_http_schema_and_invalid_guidance_index_fail_locally(monkeypatch, runtime):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    candidate = value()
    async def post(**kwargs):
        assert "partial_guidance" in kwargs["json"]["text"]["format"]["schema"]["properties"]
        return httpx.Response(200, request=httpx.Request("POST", OpenAiResponsesClient.API_URL), json={
            "status": "completed", "model": "gpt-5.6-luna", "usage": {"input_tokens": 10, "output_tokens": 20},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(candidate)}]}]})
    client = OpenAiResponsesClient("gpt-5.6-luna", post=post, max_output_tokens=3000)
    response = await client.chat([LlmMessage(role="user", content="Use approved evidence")], TASK)
    assert ContinuationProposal.model_validate_json(response.content).instructional_question
    runtime[1].value.update(teaching_move="hint", partial_guidance={"text": "Use the rule.", "aspect_indexes": [5]})
    assert (await generate(runtime)).trace.policy_action == "safe-provider-failure"


def test_v6_has_one_rendering_contract_and_retains_v4_v5_prompt_bytes():
    import hashlib
    from src.digital_twin.generation.question_specific import QuestionSpecificProfileGroundedGenerator
    args = {"bounded_contract_enabled": True, "named_referent_context_enabled": True}
    v4 = QuestionSpecificProfileGroundedGenerator(object(), **args)
    v5 = EvidenceLinkedInstructionalGenerator(object(), **args)
    assert hashlib.sha256(v4._system_instruction().encode()).hexdigest() == "3da4c262259682cc2cb71d9164a06e5a14dfb37212f28525d52ccad22cec3dd0"
    assert hashlib.sha256(v5._system_instruction().encode()).hexdigest() == "617e8fa1ca1d04a7e1021530e3db61e5e76aa22c749c1be9321569bf3750c90c"
    v6 = InstructionalContinuationGenerator(object(), **args)
    prompt = v6._system_instruction()
    assert "set hint_span to one minimal" not in prompt
    assert "hint_span is null" in prompt
    assert "question_focus must be a short exact substring" not in prompt
    assert "Legacy question_focus is unused" in prompt
    assert v6._response_contract()["ask_requires_nonempty_exact_current_message_focus"] is False


@pytest.mark.asyncio
async def test_explicit_partial_response_retains_missing_detail_and_known_source(runtime):
    runtime[1].value.update(boundary="insufficient", boundary_reason="missing_evidence",
        missing_focus="exact epoch bit width", supported_focus="retired epoch treatment",
        instructional_question=None, teaching_move="explain", supported_response_aspect_indexes=[1])
    runtime[1].value["aspects"].append({"requirement": "epoch bit width", "supported": False, "spans": []})
    answer = await generate(runtime, "Explain retired epoch treatment and the exact epoch bit width for cobalt ticket.")
    assert answer.trace.policy_action == "answer" and answer.citations
    assert answer.trace.unresolved_detail == "exact epoch bit width"
    assert "does not establish" in answer.content and SPAN in answer.content
    assert answer.warnings
    runtime[1].value["supported_response_aspect_indexes"] = [2]
    assert (await generate(runtime, "Explain retired epoch treatment and the exact epoch bit width for cobalt ticket.")).trace.policy_action == "safe-provider-failure"


@pytest.mark.asyncio
async def test_model_proposed_initial_withholding_can_keep_supported_part_as_offer(runtime):
    runtime[1].value.update(boundary="insufficient", boundary_reason="missing_evidence",
        missing_focus="exact epoch bit width", supported_focus="retired epoch treatment",
        instructional_question=None, supported_response_aspect_indexes=[])
    runtime[1].value["aspects"].append({"requirement": "epoch bit width", "supported": False, "spans": []})
    answer = await generate(runtime, "I have not attempted it: help with retired epoch treatment and the exact epoch bit width.")
    assert answer.trace.policy_action == "no-evidence"
    assert SPAN not in answer.content
    # The model's withholding choice is respected; this does not prove that a
    # live model always selects the correct profile-compatible option.


@pytest.mark.parametrize("field,content", [
    ("boundary_reason", "third_party_private_request"), ("missing_focus", "some missing value"),
    ("supported_response_aspect_indexes", [1]),
])
def test_answerable_proposal_cannot_silently_ignore_refusal_or_missing_details(field, content):
    candidate = value()
    candidate[field] = content
    with pytest.raises(ValueError, match="contradictory boundary"):
        ContinuationProposal.model_validate(candidate)
