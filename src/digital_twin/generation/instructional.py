"""Typed instructional candidate; source binding is not semantic validation."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.grounding.models import AtomicAnswerClaim, ClaimSourceBinding, TutorAnswer
from src.digital_twin.grounding.claim_validation import AtomicClaimValidationDecision
from .citations import authoritative_citation_for_chunk
from .generator import _trace
from .models import PolicyAction
from .question_specific import QuestionSpecificProfileGroundedGenerator, QuestionSpecificProposal, SupportSpan

TASK = "question_specific_instructional_tutoring"
CANDIDATE_ID = "question-specific-profile-grounded-v5"


class InstructionalQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["predict", "compare", "justify", "identify_condition"]
    text: str = Field(min_length=1, max_length=240)
    focus: str = Field(min_length=1, max_length=160)
    focus_lineage: Literal["current_message", "approved_concept"]


class ExplanationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)
    aspect_indexes: list[int] = Field(min_length=1, max_length=4)


class AttemptFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_excerpt: str = Field(min_length=1, max_length=200)
    status: Literal["supported", "revise", "partial"]
    text: str = Field(min_length=1, max_length=300)
    support: list[SupportSpan] = Field(min_length=1, max_length=2)


class InstructionalProposal(QuestionSpecificProposal):
    instructional_question: InstructionalQuestion | None = None
    feedback: AttemptFeedback | None = None
    explanation_steps: list[ExplanationStep] = Field(max_length=3)


class EvidenceLinkedInstructionalGenerator(QuestionSpecificProfileGroundedGenerator):
    proposal_model = InstructionalProposal
    task = TASK
    additional_response_contract = {
        "max_explanation_steps": 3, "max_step_characters": 500,
        "max_support_spans_per_unit": 2, "max_question_characters": 240,
        "max_feedback_characters": 300, "max_student_excerpt_characters": 200,
        "aspect_indexes_are_one_based": True,
        "explain_must_cover_every_aspect_and_selected_support_span": True,
        "question_focus_lineage": ["current_message", "approved_concept"],
        "no_semantic_correctness_guarantee_from_source_binding": True,
    }
    additional_instruction = (
        "Use the typed instructional fields to teach, not to repeat a generic request for an explanation. "
        "For ask, provide one specific predict/compare/justify/identify-condition question that a learner "
        "can actually work on. Never disclose its answer or embed the full solution in a question. "
        "Do not use 'what is your current explanation' or merely ask which step is unclear. "
        "instructional_question.focus must be an exact current-message substring or an exact approved "
        "concept label; declare its lineage. If the current message is a short follow-up, use a relevant "
        "approved concept label rather than an answer sentence from evidence. "
        "For explain, use up to three concise instructional steps that explain the requested mechanism, "
        "comparison or application. Connect the rule to the learner's actual case without adding unsupported "
        "facts. Do not simply copy whole source paragraphs. Every step needs one-based aspect_indexes referring to the already checked exact support spans. Cover every requested aspect and every selected aspect support span; "
        "group only without omission. If complete support cannot fit the instructional_contract, clarify "
        "rather than truncate. For an actual attempt, provide feedback tied to an exact current learner "
        "excerpt: acknowledge the correct idea, identify a specific error or missing link, then help advance. "
        "A correct attempt should not trigger the same starting question again. Feedback must have approved "
        "support, must not infer mastery, and must not claim the learner said something absent from their message. "
        "For hint, the existing exact hint_span remains the only displayed factual guidance; add a specific "
        "instructional_question that helps apply it without giving the full solution. Keep feedback and "
        "explanation_steps empty for ask/hint. For explain, instructional_question is null; for ask, "
        "feedback is null and explanation_steps empty. For insufficient/clarify all instructional fields "
        "are empty/null. Respect all field limits. These instructions never override the approved teaching profile. "
    )

    def __init__(self, client, **kwargs):
        if not kwargs.get("named_referent_context_enabled"):
            raise ValueError("instructional candidate requires named-referent context")
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v5-development"

    async def generate_for_intent(self, *args, **kwargs):
        answer = await super().generate_for_intent(*args, **kwargs)
        if answer.trace is not None:
            answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                "validation_scope": "experimental-source-binding-only; semantic-support-unverified"})})
        return answer

    @staticmethod
    def _validated_support(spans, evidence):
        result = []
        for span in spans:
            hit = evidence.get(span.citation_id)
            if hit is None or not span.text.strip() or span.text not in hit.chunk.text:
                raise ValueError("instructional support is not exact approved evidence")
            result.append((span.text, hit))
        return result

    @staticmethod
    def _question(proposal, question, authorized_concept_labels):
        unit = proposal.instructional_question
        if unit is None or not unit.text.strip().endswith("?"):
            raise ValueError("instructional move requires a bounded question")
        valid_focus = (unit.focus in question if unit.focus_lineage == "current_message"
            else unit.focus in authorized_concept_labels)
        if not valid_focus or not unit.focus.strip():
            raise ValueError("instructional focus has no declared current-question or approved-concept lineage")
        return unit.text

    def _render_proposal(self, proposal, *, question, evidence, selected, initial_elicitation,
                         trace_args, authorized_concept_labels=()):
        if initial_elicitation or proposal.teaching_move == "ask":
            if proposal.feedback is not None or proposal.explanation_steps:
                raise ValueError("ask cannot carry explanatory or feedback content")
            text = self._question(proposal, question, authorized_concept_labels)
            return TutorAnswer(content=text, trace=_trace(policy_action=PolicyAction.QUESTION, **trace_args))
        if proposal.teaching_move == "hint":
            if proposal.feedback is not None or proposal.explanation_steps:
                raise ValueError("hint cannot carry full explanation or feedback")
            hint = proposal.hint_span
            if hint is None:
                raise ValueError("hint requires an approved support span")
            support = self._validated_support([hint], evidence)
            if all(text in hint.text for text, _ in selected):
                raise ValueError("hint discloses every proposed answer span")
            prompt = self._question(proposal, question, authorized_concept_labels)
            text, hit = support[0]
            return TutorAnswer(content=f"Hint: {text}\n\n{prompt}",
                citations=[authoritative_citation_for_chunk(hit.chunk)],
                atomic_claims=[AtomicAnswerClaim(claim_id="claim-instructional-hint", text=text,
                    evidence_hit_ids=[hit.chunk.id],
                    source_bindings=[ClaimSourceBinding(evidence_hit_id=hit.chunk.id, text=text)])],
                trace=_trace(policy_action=PolicyAction.ANSWER, **trace_args))
        if proposal.instructional_question is not None or not proposal.explanation_steps:
            raise ValueError("explain requires steps without an elicitation question")
        parts, claims, citations, covered, displayed = [], [], [], set(), set()

        def add_unit(text, support, claim_id):
            for span, hit in support:
                displayed.add((span, hit.chunk.id))
                citation = authoritative_citation_for_chunk(hit.chunk)
                if citation not in citations:
                    citations.append(citation)
            claims.append(AtomicAnswerClaim(claim_id=claim_id, text=text,
                evidence_hit_ids=list(dict.fromkeys(hit.chunk.id for _, hit in support)),
                source_bindings=[ClaimSourceBinding(evidence_hit_id=hit.chunk.id, text=span)
                    for span, hit in support]))
            parts.append(text)

        if proposal.feedback is not None:
            feedback = proposal.feedback
            if not feedback.student_excerpt.strip() or feedback.student_excerpt not in question:
                raise ValueError("feedback does not quote the current learner message")
            support = self._validated_support(feedback.support, evidence)
            parts.append(f'Your attempt: “{feedback.student_excerpt}”')
            add_unit(feedback.text, support, "claim-instructional-feedback")
        for index, step in enumerate(proposal.explanation_steps, 1):
            support = []
            for aspect_index in step.aspect_indexes:
                if not 1 <= aspect_index <= len(proposal.aspects):
                    raise ValueError("instructional aspect index is outside assessed requirements")
                for item in self._validated_support(proposal.aspects[aspect_index - 1].spans, evidence):
                    if item not in support:
                        support.append(item)
                covered.add(aspect_index)
            add_unit(step.text, support, f"claim-instructional-step-{index}")
        if covered != set(range(1, len(proposal.aspects) + 1)):
            raise ValueError("instructional steps omit an assessed requested aspect")
        if not {(text, hit.chunk.id) for text, hit in selected}.issubset(displayed):
            raise ValueError("instructional rendering omits selected aspect support")
        return TutorAnswer(content="\n\n".join(parts), citations=citations, atomic_claims=claims,
            trace=_trace(policy_action=PolicyAction.ANSWER, **trace_args))


class InstructionalSourceBindingValidator:
    """Experimental provenance admission; never reports semantic entailment."""
    implementation_id = "instructional-source-binding-admission-v1"
    version = "1.0.0-development"

    def validate(self, claims, hits):
        eligible = {h.chunk.id: h for h in hits[:5] if h.chunk.retrieval_allowed}
        reason = "experimental source bindings checked; semantic support remains unverified"
        valid = bool(claims) and len(claims) <= 8
        valid = valid and len({c.claim_id for c in claims}) == len(claims)
        checked = 0
        for claim in claims:
            ids = set(claim.evidence_hit_ids)
            if not ids or not ids.issubset(eligible):
                valid = False
                continue
            if claim.source_bindings:
                binding_ids = {b.evidence_hit_id for b in claim.source_bindings}
                if binding_ids != ids:
                    valid = False
                for binding in claim.source_bindings:
                    hit = eligible.get(binding.evidence_hit_id)
                    if hit is None or not binding.text.strip() or binding.text not in hit.chunk.text:
                        valid = False
                    else:
                        checked += 1
            else:
                # Existing deterministic/proactive exact claims retain their
                # literal provenance route; paraphrases need explicit bindings.
                if not any(claim.text in eligible[hit_id].chunk.text for hit_id in ids):
                    valid = False
                else:
                    checked += 1
        return AtomicClaimValidationDecision(releasable=valid, score=1.0 if valid else 0.0,
            reason=reason if valid else "experimental source binding or lineage invalid",
            claim_count=len(claims), supported_claim_count=0,
            unsupported_claim_ids=[], features={"semantic_support_unverified": True,
                "score_kind": "structural-source-binding-only", "checked_source_bindings": checked,
                "lineage_valid": valid, "verifier_called": False})
