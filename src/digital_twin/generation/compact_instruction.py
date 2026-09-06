"""Experimental compact composition with approved-source association, not entailment."""
from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.grounding.models import AtomicAnswerClaim, ClaimSourceBinding, TutorAnswer
from src.digital_twin.llm import LlmError, LlmMalformedResponseError, LlmMessage
from .citations import authoritative_citation_for_chunk
from .generator import _approved_hits, _policy_answer, _provider_failure, _trace
from .models import PolicyAction
from .question_specific import QuestionSpecificProfileGroundedGenerator

TASK = "question_specific_compact_instruction"
CANDIDATE_ID = "question-specific-profile-grounded-v8"
SCOPE = "experimental-whole-chunk-source-association-only; semantic-support-unverified"


class CompactUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["explanation", "feedback", "elicitation"]
    text: str = Field(min_length=1, max_length=700)
    source_ids: list[str] = Field(max_length=5)


class CompactInstructionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["question", "instruction", "partial", "no_evidence", "clarify", "private", "graded"]
    units: list[CompactUnit] = Field(max_length=4)
    missing_details: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(max_length=4)


class CompactContractError(ValueError):
    """Only fixed, non-sensitive invariant codes are recorded."""


INSTRUCTION = (
    "Compose useful tutoring for the current student message using only the approved evidence, "
    "conversation and instructor profile. Follow the approved teaching style and help ladder: "
    "initial Socratic help must pose a specific useful task without its solution; a correct attempt "
    "may advance to the permitted explanation and requested concrete application. After an incorrect "
    "attempt acknowledge and correct its particular error with the permitted degree of help. "
    "A wrong student statement is not missing course evidence: the evidence may establish why it is wrong. "
    "On repeated difficulty, offer a concrete next step rather than repeating a generic explanation request. "
    "A new concept starts a new episode; never infer permission to reveal a solution from message count alone. "
    "Identify every requested goal and missing detail; preserve source conditions, actor exceptions and "
    "qualifications. Provide the requested application outcome when the profile permits it. Do not add "
    "unrequested access rules or neighboring policies when defining a term. Stay with the requested "
    "concept: do not volunteer a secondary concept's complete rule as a workaround for Socratic withholding. "
    "A secondary concept needs its own relevant request and profile-permitted teaching stage. Do not invent a value, "
    "capability or absence. Assess missing details against all supplied evidence. "
    "Return only the compact JSON schema. action question means only elicitation units. instruction "
    "means explanation or feedback, optionally followed by elicitation. partial means permitted known "
    "material plus all missing requested details. For initial Socratic mixed questions choose no_evidence "
    "with the missing details and a specific elicitation about the known part, without revealing its answer. "
    "For post-attempt mixed requests use partial with specific feedback/application and the missing details. "
    "The server prints missing_details itself, so do not duplicate absence notices in factual units. "
    "Use private only for requests to disclose another person's private information, not own-record requests "
    "or discussion of privacy terms. Use clarify for genuinely unresolved ambiguity and graded for "
    "prohibited completed assessed work. Private/clarify/graded/no_evidence may contain only permitted "
    "elicitation units; their boundary wording is supplied by the server. "
    "Each explanation/feedback unit requires one or more IDs from the supplied evidence. Elicitation may "
    "have no IDs but must not smuggle unsupported claims or a withheld answer. Reference source IDs only; "
    "do not copy source spans, request spans, student excerpts or aspect indexes. The server associates "
    "each factual unit with the referenced approved chunks; this association does not prove entailment. "
    "No more than four units, 700 characters per unit, five source IDs per unit or four missing details "
    "of at most 300 characters each. Keep all prose nonblank. Missing detail descriptions must accurately "
    "identify the requested unavailable information, not invent a new request. Do not include hidden reasoning."
)


class CompactInstructionalGenerator(QuestionSpecificProfileGroundedGenerator):
    """Reuse only policy/config initialization; prompt and composition are standalone."""
    task = TASK
    missing_information_prefix = "The approved material does not establish:\n"
    proposal_model = CompactInstructionProposal

    def __init__(self, client, **kwargs):
        if not kwargs.get("named_referent_context_enabled"):
            raise ValueError("compact candidate requires named-referent context")
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v8-development"

    def _system_instruction(self):
        return INSTRUCTION

    def _prepare_payload(self, payload):
        return payload

    async def generate_for_intent(self, question, hits, policy, *, intent, help_level,
            repair_reason=None, teaching_profile_context=None, learner_history=None,
            learner_attempt_present=False, authorized_concept_labels=()):
        started = self.clock()
        approved = _approved_hits(hits)
        decision = self.policy_enforcer.evaluate(question, approved, policy,
            authorized_referents=tuple(authorized_concept_labels))
        boundary = _policy_answer(decision.action, generator_id=self.implementation_id,
            started=started, clock=self.clock)
        if boundary is not None:
            return boundary
        evidence = {f"S{i}": hit for i, hit in enumerate(approved, 1)}
        payload = {"question": question, "learner_history": learner_history or [],
            "approved_teaching_profile": teaching_profile_context,
            "approved_concept_labels": list(authorized_concept_labels),
            "application_observed_attempt": bool(learner_attempt_present),
            "pedagogical_intent": intent, "help_level": help_level,
            "evidence": [{"citation_id": key, "text": hit.chunk.text} for key, hit in evidence.items()]}
        response = None
        try:
            response = await self._request_proposal(payload, evidence=evidence, started=started)
            proposal = self.proposal_model.model_validate_json(response.content)
            return self._compose(proposal, evidence=evidence, trace_args={
                "generator_id": self.implementation_id, "provider_model": response.provider_model,
                "provider_revision": response.provider_revision, "prompt_version": self.implementation_id,
                "started": started, "clock": self.clock, "usage": response.usage})
        except (LlmError, ValueError) as error:
            return self._failure_answer(error, response=response, started=started)

    async def _request_proposal(self, payload, *, evidence, started):
        return await self.client.chat([LlmMessage(role="system", content=self._system_instruction()),
            LlmMessage(role="user", content=json.dumps(self._prepare_payload(payload), sort_keys=True))], self.task)

    def _failure_answer(self, error, *, response, started):
        answer = _provider_failure(error if isinstance(error, LlmError) else LlmMalformedResponseError(),
            started=started, clock=self.clock,
            **({"provider_model": response.provider_model, "usage": response.usage} if response else {}))
        if answer.trace is not None:
            code = str(error) if isinstance(error, CompactContractError) else "provider_or_schema_failure"
            answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                "validation_scope": SCOPE + "; compact_contract=" + code})})
        return answer

    def _compose(self, proposal, *, evidence, trace_args):
        factual = [unit for unit in proposal.units if unit.kind != "elicitation"]
        if any(not unit.text.strip() for unit in proposal.units):
            raise CompactContractError("empty_unit")
        if any(not detail.strip() or len(detail) > 300 for detail in proposal.missing_details):
            raise CompactContractError("invalid_missing_detail")
        if proposal.action in {"question", "no_evidence", "clarify", "private", "graded"} and factual:
            raise CompactContractError("boundary_contains_factual_units")
        if proposal.action in {"instruction", "partial"} and not factual:
            raise CompactContractError("instruction_without_factual_unit")
        if proposal.action == "partial" and not proposal.missing_details:
            raise CompactContractError("partial_without_missing_detail")
        if proposal.action == "question" and not proposal.units:
            raise CompactContractError("empty_question")
        parts, claims, citations = [], [], []
        prefixes = {"private": "I cannot disclose another person's private information.",
            "clarify": "Please clarify which concept or part you want help with.",
            "graded": "I cannot provide a completed answer to prohibited assessed work."}
        if proposal.action in prefixes:
            parts.append(prefixes[proposal.action])
        if proposal.missing_details:
            parts.append(self.missing_information_prefix + "\n".join(
                "- " + detail for detail in dict.fromkeys(proposal.missing_details)))
        elif proposal.action == "no_evidence":
            parts.append("The approved material does not establish the information needed for this question.")
        factual_ids = list(dict.fromkeys(source_id for unit in factual for source_id in unit.source_ids))
        for number, unit in enumerate(proposal.units, 1):
            # Every generated prose unit in a factual response is declared.
            # Association for a question is not a claim of semantic entailment.
            ids = list(dict.fromkeys(unit.source_ids or (factual_ids if unit.kind == "elicitation" and factual else [])))
            if any(source_id not in evidence for source_id in ids):
                raise CompactContractError("unknown_source_id")
            if unit.kind != "elicitation" or factual:
                if not ids:
                    raise CompactContractError("factual_unit_without_source")
                selected = [evidence[source_id] for source_id in ids]
                if any(len(hit.chunk.text) > 2400 for hit in selected):
                    raise CompactContractError("whole_chunk_binding_too_long")
                claims.append(AtomicAnswerClaim(claim_id=f"claim-compact-unit-{number}", text=unit.text,
                    evidence_hit_ids=[hit.chunk.id for hit in selected], source_bindings=[
                        ClaimSourceBinding(evidence_hit_id=hit.chunk.id, text=hit.chunk.text) for hit in selected]))
                for hit in selected:
                    citation = authoritative_citation_for_chunk(hit.chunk)
                    if citation not in citations:
                        citations.append(citation)
            parts.append(unit.text)
        action = (PolicyAction.ANSWER if factual else PolicyAction.QUESTION if proposal.action == "question"
            else PolicyAction.CLARIFY if proposal.action == "clarify"
            else PolicyAction.REDIRECT_GRADED_WORK if proposal.action == "graded" else PolicyAction.NO_EVIDENCE)
        return TutorAnswer(content="\n\n".join(parts), citations=citations, atomic_claims=claims,
            trace=_trace(policy_action=action, **trace_args).model_copy(update={
                "validation_scope": SCOPE,
                "unresolved_detail": "; ".join(proposal.missing_details) or None}))
