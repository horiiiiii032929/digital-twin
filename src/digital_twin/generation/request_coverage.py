"""V7 request-focused composition; semantic adequacy remains independently judged."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.grounding.models import TutorAnswer
from .citations import authoritative_citation_for_chunk
from .continuation import ContinuationProposal, InstructionalContinuationGenerator, PartialGuidance
from .generator import _trace
from .instructional import AttemptFeedback, ExplanationStep, InstructionalQuestion
from .models import PolicyAction
from .question_specific import RequestedAspect, SupportSpan

TASK = "question_specific_request_coverage"
CANDIDATE_ID = "question-specific-profile-grounded-v7"


class FocusedRequestedAspect(RequestedAspect):
    request_focus: str = Field(min_length=1, max_length=160)
    goal: Literal["assess_attempt", "apply_rule", "explain_rule", "define_term", "provide_information"]

    @model_validator(mode="after")
    def unsupported_aspects_have_no_support(self):
        if not self.supported and self.spans:
            raise ValueError("unsupported requested aspect cannot declare support spans")
        return self


class CurrentMessageFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_reference: Literal["current_message"]
    status: Literal["supported", "revise", "partial"]
    text: str = Field(min_length=1, max_length=300)
    support: list[SupportSpan] = Field(min_length=1, max_length=2)


class RequestCoverageProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    boundary: Literal["answerable", "insufficient", "clarify"]
    aspects: list[FocusedRequestedAspect] = Field(max_length=4)
    teaching_move: Literal["ask", "hint", "explain"]
    instructional_question: InstructionalQuestion | None = None
    feedback: CurrentMessageFeedback | None = None
    explanation_steps: list[ExplanationStep] = Field(max_length=3)
    partial_guidance: PartialGuidance | None = None
    boundary_reason: Literal["none", "missing_evidence", "third_party_private_request", "ambiguous"] = "none"
    supported_response_aspect_indexes: list[int] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def boundary_contract(self):
        if self.boundary == "answerable" and (not self.aspects or self.boundary_reason != "none"
                or self.supported_response_aspect_indexes):
            raise ValueError("answerable request coverage has inconsistent boundary fields")
        if self.boundary == "insufficient" and (not self.aspects or self.boundary_reason not in {
                "missing_evidence", "third_party_private_request"}):
            raise ValueError("insufficient request coverage needs requested aspects and a reason")
        return self


class RequestCoverageInstructionalGenerator(InstructionalContinuationGenerator):
    proposal_model = RequestCoverageProposal
    task = TASK
    additional_response_contract = {
        **InstructionalContinuationGenerator.additional_response_contract,
        "feedback_learner_reference": "current_message",
        "server_display_excerpt_characters": 200,
        "max_request_focus_characters": 160,
        "missing_details_derived_from_all_unsupported_requested_aspects": True,
        "pure_definition_rendering": "selected_exact_source_spans",
        "definition_span_selection_semantics_verified": False,
    }
    rendering_instruction = (
        "First enumerate every distinct request in the CURRENT message, including checking an attempt, "
        "applying a rule to supplied values, explaining or defining a term, and each requested unavailable item. "
        "For each aspect, request_focus must be an exact current-message substring and goal must identify "
        "assess_attempt, apply_rule, explain_rule, define_term or provide_information. Keep separate goals "
        "when the student asks both 'is this correct' and a concrete application. Do not silently replace "
        "a requested application with another quiz after a correct attempt when the approved help ladder "
        "permits explanation. Work through the supplied case and give its outcome in that permitted stage. "
        "After an incorrect attempt give specific correction/partial help according to the profile. "
        "Feedback uses learner_reference=current_message; do NOT copy the student's long message into a "
        "student_excerpt field. The server links feedback to that message and labels a bounded excerpt. "
        "Do not claim mastery or invent what the learner said. Keep feedback text within300 characters "
        "with exact approved support. Each explanation step references all aspects it actually serves. "
        "Include only requested and relevant content. Preserve source conditions, scope, alternatives and "
        "role exceptions; never turn one actor's permission into an exclusive access rule. A request to "
        "define a term does not request an extra access-policy paragraph. Pure define_term steps are rendered "
        "from their selected exact source spans: choose the actual concise definition, not neighboring policy. "
        "If a step also serves explanation, comparison or application, preserve those requested goals. "
        "Other explanatory steps use bounded evidence-linked prose; source binding is not semantic validation. "
        "For ask, provide one concrete, bounded instructional_question (questions or imperatives permitted), "
        "explanation_steps empty and partial_guidance null; feedback is allowed only for an actual current "
        "attempt. For hint, use partial_guidance text and supported one-based aspect_indexes, feedback when "
        "appropriate, explanation_steps empty, and a useful next instructional_question. For explain, give "
        "up to three bounded explanation_steps covering every aspect and selected support span, optional "
        "feedback, and optional next prompt AFTER supplying the requested explanation/application. "
        "The instructional_question focus must be an exact current substring or supplied approved concept "
        "label with declared lineage. Do not give a withheld solution in a question, guidance or feedback. "
        "For insufficient/missing_evidence, mark EVERY unavailable requested item as unsupported with no "
        "spans; all their request_focus values will be shown. Assess any requested known part separately. "
        "Use supported_response_aspect_indexes only for useful requested known facts when the approved "
        "teaching stage permits their disclosure. For post-attempt mixed requests, combine supported indexes "
        "with feedback and explanation_steps that assess the attempt and supply the requested supported "
        "application; keep step aspect_indexes in original request order. The missing notices still remain. "
        "Factual feedback/steps on an insufficient boundary require those supported indexes. "
        "For initial Socratic mixed requests, leave those indexes "
        "empty and supply a specific instructional_question about the supported part without its answer; "
        "a generic offer to help is not a useful initial instructional move. "
        "Do not let a missing unrelated fact override stage-aware withholding of the known solution. "
        "If known next steps are requested and permitted, return their supported indexes rather than merely "
        "offer to help. For actual third-party private-information disclosure use third_party_private_request; "
        "own-record requests and discussions of privacy terms are not third-party disclosures. For answerable "
        "use reason none and empty supported_response_aspect_indexes. For clarify use ambiguous. "
        "Keep all counts/lengths within the supplied contracts; no trailing unstructured response or judge loop. "
    )

    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v7-development"

    @staticmethod
    def _legacy_proposal(proposal, question):
        feedback = None
        if proposal.feedback is not None:
            # Reference the actual message. Only its labeled display excerpt is
            # bounded; the model's feedback and the full stored message remain.
            excerpt = question.lstrip()[:200]
            feedback = AttemptFeedback(student_excerpt=excerpt, status=proposal.feedback.status,
                text=proposal.feedback.text, support=proposal.feedback.support)
        return ContinuationProposal(boundary="answerable",
            aspects=[RequestedAspect(requirement=a.requirement, supported=a.supported, spans=a.spans)
                for a in proposal.aspects], teaching_move=proposal.teaching_move,
            instructional_question=proposal.instructional_question, feedback=feedback,
            explanation_steps=proposal.explanation_steps, partial_guidance=proposal.partial_guidance,
            hint_span=None, question_focus="", boundary_reason="none")

    def _render_proposal(self, proposal, *, question, evidence, selected, initial_elicitation,
                         trace_args, authorized_concept_labels=()):
        adapted = self._legacy_proposal(proposal, question)
        steps = []
        for step in adapted.explanation_steps:
            if any(not 1 <= i <= len(proposal.aspects) for i in step.aspect_indexes):
                raise ValueError("request coverage step references unknown aspect")
            if all(proposal.aspects[i - 1].goal == "define_term" for i in step.aspect_indexes):
                support = self._aspect_support(step.aspect_indexes, proposal, evidence)
                definition = "\n\n".join(dict.fromkeys(text for text, _ in support))
                if len(definition) > 500:
                    raise ValueError("selected exact definition exceeds the bounded step; do not truncate")
                step = ExplanationStep(text=definition, aspect_indexes=step.aspect_indexes)
            steps.append(step)
        adapted = adapted.model_copy(update={"explanation_steps": steps})
        answer = super()._render_proposal(adapted, question=question, evidence=evidence, selected=selected,
            initial_elicitation=initial_elicitation, trace_args=trace_args,
            authorized_concept_labels=authorized_concept_labels)
        if proposal.feedback is not None:
            excerpt = adapted.feedback.student_excerpt
            prefix = f'Your attempt: “{excerpt}”'
            if answer.content.startswith(prefix):
                answer = answer.model_copy(update={"content":
                    f'Your message (excerpt): “{excerpt}”' + answer.content[len(prefix):]})
        return answer

    def _render_boundary(self, proposal, *, question, evidence, trace_args, authorized_concept_labels=()):
        for aspect in proposal.aspects:
            if not aspect.request_focus.strip() or aspect.request_focus not in question:
                raise ValueError("assessed requested focus is not an exact current-message span")
        if proposal.boundary == "clarify":
            return TutorAnswer(content="Which concept or part of the question should we focus on?",
                trace=_trace(policy_action=PolicyAction.CLARIFY, **trace_args))
        missing = [a for a in proposal.aspects if not a.supported or not a.spans]
        if proposal.boundary == "answerable" and not missing:
            return None
        if proposal.boundary_reason == "third_party_private_request":
            return TutorAnswer(content="I cannot disclose another person's private information.",
                trace=_trace(policy_action=PolicyAction.NO_EVIDENCE, **trace_args))
        if proposal.boundary_reason != "missing_evidence" or not missing:
            raise ValueError("missing-evidence boundary does not identify its unsupported requested aspects")
        missing_foci = list(dict.fromkeys(a.request_focus for a in missing))
        content = "The approved material does not establish:\n" + "\n".join(f'- “{focus}”' for focus in missing_foci)
        unresolved = "; ".join(missing_foci)
        if proposal.supported_response_aspect_indexes:
            for index in proposal.supported_response_aspect_indexes:
                if not 1 <= index <= len(proposal.aspects) or not proposal.aspects[index - 1].supported:
                    raise ValueError("partial request coverage references an unsupported aspect")
            chosen = list(dict.fromkeys(proposal.supported_response_aspect_indexes))
            support = self._aspect_support(chosen, proposal, evidence)
            if proposal.explanation_steps or proposal.feedback is not None or proposal.partial_guidance is not None:
                mapping = {original: index for index, original in enumerate(chosen, 1)}
                def remap(indexes):
                    if any(index not in mapping for index in indexes):
                        raise ValueError("partial instructional unit escapes its selected supported requests")
                    return [mapping[index] for index in indexes]
                steps = [step.model_copy(update={"aspect_indexes": remap(step.aspect_indexes)})
                    for step in proposal.explanation_steps]
                guidance = (proposal.partial_guidance.model_copy(update={
                    "aspect_indexes": remap(proposal.partial_guidance.aspect_indexes)})
                    if proposal.partial_guidance is not None else None)
                focused = proposal.model_copy(update={"boundary": "answerable", "boundary_reason": "none",
                    "aspects": [proposal.aspects[index - 1] for index in chosen],
                    "supported_response_aspect_indexes": [], "explanation_steps": steps,
                    "partial_guidance": guidance})
                rendered = self._render_proposal(focused, question=question, evidence=evidence,
                    selected=support, initial_elicitation=False, trace_args=trace_args,
                    authorized_concept_labels=authorized_concept_labels)
                return rendered.model_copy(update={"content": content + "\n\n" + rendered.content,
                    "warnings": [*rendered.warnings, "Partial response: the listed requested details remain unavailable."],
                    "trace": rendered.trace.model_copy(update={"unresolved_detail": unresolved})})
            citations = []
            for _, hit in support:
                citation = authoritative_citation_for_chunk(hit.chunk)
                if citation not in citations:
                    citations.append(citation)
            content += "\n\nKnown from the approved material:\n" + "\n\n".join(text for text, _ in support)
            return TutorAnswer(content=content, citations=citations,
                atomic_claims=[self._claim(f"claim-partial-known-{index}", text, [(text, hit)])
                    for index, (text, hit) in enumerate(support, 1)],
                warnings=["Partial response: the listed requested details remain unavailable."],
                trace=_trace(policy_action=PolicyAction.ANSWER, **trace_args).model_copy(update={"unresolved_detail": unresolved}))
        if proposal.feedback is not None or proposal.explanation_steps or proposal.partial_guidance is not None:
            raise ValueError("mixed factual instruction requires selected supported request indexes")
        supported = [a for a in proposal.aspects if a.supported and a.spans]
        for aspect in supported:
            self._validated_support(aspect.spans, evidence)
        if proposal.instructional_question is not None:
            if not supported:
                raise ValueError("mixed-boundary instructional prompt needs assessed supported material")
            content += "\n\n" + self._question(proposal, question, authorized_concept_labels)
        elif supported:
            content += "\n\nI can help with " + ", ".join(f'“{a.request_focus}”' for a in supported) + " using the available course material."
        else:
            content += "\n\nPlease ask the instructor about those missing details."
        return TutorAnswer(content=content, trace=_trace(policy_action=PolicyAction.NO_EVIDENCE, **trace_args).model_copy(update={"unresolved_detail": unresolved}))
