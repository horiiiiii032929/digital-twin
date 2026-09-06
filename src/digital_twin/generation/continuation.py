"""V6 continuation candidate; evidence binding does not prove semantic safety."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.grounding.models import AtomicAnswerClaim, ClaimSourceBinding, TutorAnswer
from .citations import authoritative_citation_for_chunk
from .generator import _trace
from .instructional import EvidenceLinkedInstructionalGenerator, InstructionalProposal
from .models import PolicyAction

TASK = "question_specific_instructional_continuation"
CANDIDATE_ID = "question-specific-profile-grounded-v6"


class PartialGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=350)
    aspect_indexes: list[int] = Field(min_length=1, max_length=4)


class ContinuationProposal(InstructionalProposal):
    partial_guidance: PartialGuidance | None = None
    boundary_reason: Literal["none", "missing_evidence", "third_party_private_request", "ambiguous"] = "none"
    missing_focus: str = Field(default="", max_length=160)
    supported_focus: str = Field(default="", max_length=160)
    supported_response_aspect_indexes: list[int] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def answerable_cannot_declare_refusal_or_missing_details(self):
        if self.boundary == "answerable" and (self.boundary_reason != "none"
                or self.missing_focus or self.supported_focus or self.supported_response_aspect_indexes):
            raise ValueError("answerable proposal has contradictory boundary details")
        return self


class InstructionalContinuationGenerator(EvidenceLinkedInstructionalGenerator):
    proposal_model = ContinuationProposal
    task = TASK
    additional_response_contract = {
        **EvidenceLinkedInstructionalGenerator.additional_response_contract,
        "max_partial_guidance_characters": 350,
        "max_boundary_focus_characters": 160,
        "imperative_elicitation_allowed": True,
        "mixed_feedback_and_prompt_is_source_bound_answer_action": True,
        "partial_guidance_semantics_not_machine_verified": True,
    }
    additional_instruction = (
        "Produce useful bounded instruction through the typed fields. Specific elicitation can be a question "
        "or an imperative such as Predict, Compare or Explain; punctuation does not determine usefulness. "
        "Use a concrete case, condition or reasoning step, not a generic request for the current explanation. "
        "instructional_question.focus must be an exact current-message substring or an exact supplied approved "
        "concept label, with matching focus_lineage; short follow-ups can use a relevant approved label. "
        "For an actual attempt, quote its exact current-message excerpt in feedback, identify the correct or "
        "incorrect idea using approved support, and help advance. Feedback may accompany a next instructional "
        "question. Never pretend a request for help is an attempt, and never infer mastery. "
        "For ask, explanation_steps is empty and partial_guidance null; feedback is optional only for an actual "
        "current attempt. For hint, use partial_guidance with bounded text and one-based aspect_indexes "
        "pointing to approved support already assessed in aspects; hint_span is null, explanation_steps empty. "
        "Add a specific instructional_question and feedback when the current learner actually attempted it. "
        "Partial guidance must help with a next step, not reveal a full solution when the profile withholds it. "
        "A corrective fact after an attempt may be appropriate only when the approved help ladder allows it. "
        "Do not relabel a full initial solution as a hint or hide it in a question. For explain, use up to three "
        "bounded steps with one-based aspect_indexes covering every assessed aspect and selected support span. "
        "Optional feedback and a next instructional_question can accompany explanation. Explain the mechanism "
        "or apply the rule rather than dump whole source paragraphs. No unsupported additions. "
        "For insufficient, use missing_evidence or third_party_private_request. missing_focus must quote the "
        "exact requested missing detail in the current message. If some requested part is supported, set "
        "supported_focus to its exact current-message phrase and assess its approved support so the renderer "
        "can offer that part. When the supported material supplies a requested useful next step, set "
        "supported_response_aspect_indexes to its supported one-based aspect indexes so those exact supported "
        "facts can be returned as an explicitly partial response with the missing detail clearly stated. "
        "Respect initial withholding and the approved profile; leave that list empty when only an offer "
        "is appropriate. Do not invent a missing fact. third_party_private_request applies to disclosure "
        "of another person's private information, not a discussion of privacy policy or a person's own data; "
        "use missing_focus to quote that requested disclosure. For clarify, use ambiguous. For answerable, "
        "boundary_reason is none, missing_focus/supported_focus are empty, and supported_response_aspect_indexes "
        "is empty. Instructional fields are "
        "empty/null for insufficient/clarify. Legacy question_focus is unused and may be empty. "
        "Every wording unit is model-proposed; source binding does not establish entailment or safe disclosure. "
        "Respect all response and instructional contract limits, and the approved profile before choosing a move. "
    )

    rendering_instruction = additional_instruction
    additional_instruction = ""

    def _response_contract(self):
        return {**super()._response_contract(),
            "ask_requires_nonempty_exact_current_message_focus": False,
            "instructional_focus_requires_current_span_or_approved_label": True,
            "legacy_question_focus_used": False}

    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v6-development"

    @staticmethod
    def _question(proposal, question, authorized_concept_labels):
        unit = proposal.instructional_question
        if unit is None or not unit.text.strip():
            raise ValueError("instructional move requires nonblank elicitation")
        valid = unit.focus in question if unit.focus_lineage == "current_message" else unit.focus in authorized_concept_labels
        if not unit.focus.strip() or not valid:
            raise ValueError("instructional focus has no declared current-question or approved-concept lineage")
        return unit.text

    def _aspect_support(self, indexes, proposal, evidence):
        support = []
        for index in indexes:
            if not 1 <= index <= len(proposal.aspects):
                raise ValueError("guidance aspect index outside assessed requirements")
            for item in self._validated_support(proposal.aspects[index - 1].spans, evidence):
                if item not in support:
                    support.append(item)
        if not support:
            raise ValueError("guidance requires approved support")
        return support

    def _render_proposal(self, proposal, *, question, evidence, selected, initial_elicitation,
                         trace_args, authorized_concept_labels=()):
        if proposal.teaching_move == "explain" and not initial_elicitation:
            clean = proposal.model_copy(update={"instructional_question": None})
            answer = super()._render_proposal(clean, question=question, evidence=evidence, selected=selected,
                initial_elicitation=False, trace_args=trace_args, authorized_concept_labels=authorized_concept_labels)
            if proposal.instructional_question is None:
                return answer
            prompt = self._question(proposal, question, authorized_concept_labels)
            claim = self._claim("claim-instructional-next-prompt", prompt, selected)
            return answer.model_copy(update={"content": answer.content + "\n\n" + prompt,
                "atomic_claims": [*answer.atomic_claims, claim]})
        if proposal.explanation_steps:
            raise ValueError("elicitation and partial guidance cannot carry full explanatory steps")
        prompt = self._question(proposal, question, authorized_concept_labels)
        parts, units = [], []
        if proposal.feedback is not None:
            if initial_elicitation:
                raise ValueError("initial elicitation cannot render unestablished attempt feedback")
            feedback = proposal.feedback
            if not feedback.student_excerpt.strip() or feedback.student_excerpt not in question:
                raise ValueError("feedback does not quote the current learner message")
            support = self._validated_support(feedback.support, evidence)
            parts.append(f'Your attempt: “{feedback.student_excerpt}”')
            parts.append(feedback.text)
            units.append((feedback.text, support))
        if proposal.teaching_move == "hint" and not initial_elicitation:
            guidance = proposal.partial_guidance
            if guidance is None:
                raise ValueError("hint requires typed partial guidance")
            support = self._aspect_support(guidance.aspect_indexes, proposal, evidence)
            # Scope is model-proposed, not proved by quote overlap. Full copied
            # or paraphrased solutions can pass binding and must fail the
            # independent pedagogical gate when the profile withholds them.
            parts.append(guidance.text)
            units.append((guidance.text, support))
        elif proposal.partial_guidance is not None:
            raise ValueError("ask cannot carry partial guidance")
        if not units:
            return TutorAnswer(content=prompt, trace=_trace(policy_action=PolicyAction.QUESTION, **trace_args))
        parts.append(prompt)
        units.append((prompt, selected))
        citations = []
        for _, support in units:
            for _, hit in support:
                citation = authoritative_citation_for_chunk(hit.chunk)
                if citation not in citations:
                    citations.append(citation)
        return TutorAnswer(content="\n\n".join(parts), citations=citations,
            atomic_claims=[self._claim(f"claim-instructional-mixed-{index}", text, support)
                for index, (text, support) in enumerate(units, 1)],
            trace=_trace(policy_action=PolicyAction.ANSWER, **trace_args))

    @staticmethod
    def _claim(claim_id, text, support):
        return AtomicAnswerClaim(claim_id=claim_id, text=text,
            evidence_hit_ids=list(dict.fromkeys(hit.chunk.id for _, hit in support)),
            source_bindings=[ClaimSourceBinding(evidence_hit_id=hit.chunk.id, text=span) for span, hit in support])

    def _render_boundary(self, proposal, *, question, evidence, trace_args, authorized_concept_labels=()):
        if proposal.boundary == "clarify":
            return super()._render_boundary(proposal, question=question, evidence=evidence, trace_args=trace_args)
        if proposal.boundary == "answerable" and all(a.supported and a.spans for a in proposal.aspects):
            return None
        focus = proposal.missing_focus
        if not focus.strip() or focus not in question:
            raise ValueError("missing or private detail focus is not from the current question")
        if proposal.boundary_reason == "third_party_private_request":
            content = "I cannot disclose another person's private information."
        elif proposal.boundary_reason == "missing_evidence":
            content = f'The approved material does not establish “{focus}”.'
            if proposal.supported_response_aspect_indexes:
                for index in proposal.supported_response_aspect_indexes:
                    if not 1 <= index <= len(proposal.aspects) or not proposal.aspects[index - 1].supported:
                        raise ValueError("partial response references an unsupported aspect")
                support = self._aspect_support(proposal.supported_response_aspect_indexes, proposal, evidence)
                citations = []
                for _, hit in support:
                    citation = authoritative_citation_for_chunk(hit.chunk)
                    if citation not in citations:
                        citations.append(citation)
                text = content + "\n\nKnown from the approved material:\n" + "\n\n".join(span for span, _ in support)
                trace = _trace(policy_action=PolicyAction.ANSWER, **trace_args).model_copy(update={"unresolved_detail": focus})
                return TutorAnswer(content=text, citations=citations,
                    atomic_claims=[self._claim(f"claim-partial-known-{index}", span, [(span, hit)])
                        for index, (span, hit) in enumerate(support, 1)],
                    warnings=["Partial response: the requested missing detail remains unavailable."], trace=trace)
            if proposal.supported_focus:
                if proposal.supported_focus not in question:
                    raise ValueError("supported offer focus is not from the current question")
                supported = [a for a in proposal.aspects if a.supported and a.spans]
                if not supported:
                    raise ValueError("supported offer has no assessed approved support")
                for aspect in supported:
                    self._validated_support(aspect.spans, evidence)
                content += f' I can help explain “{proposal.supported_focus}” using the available course material.'
            else:
                content += " Please ask the instructor about that missing information."
        else:
            raise ValueError("insufficient response requires an explicit supported boundary reason")
        return TutorAnswer(content=content, trace=_trace(policy_action=PolicyAction.NO_EVIDENCE, **trace_args))
