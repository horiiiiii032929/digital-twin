"""One fallible keep/repair proposal; model judgments are not certification."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmError, LlmMalformedResponseError, LlmMessage, LlmResponse
from .compact_instruction import CompactContractError, SCOPE
from .evidence_strength import EvidenceStrengthInstructionalGenerator
from .factual_revision import DRAFT_MODEL, REVISION_MODEL, REVISION_INSTRUCTION, _check_response, _sum_usage
from .typed_instruction import TypedInstructionProposal

CANDIDATE_ID = "question-specific-profile-grounded-v14"
TASK = "question_specific_conditional_revision"
MOVE_ACTIONS = {
    "elicitation": {"question"},
    "instructional": {"instruction", "partial"},
    "clarification": {"clarify"},
    "missing_evidence": {"no_evidence"},
    "private": {"private"},
    "graded": {"graded"},
}
INSTRUCTION = (
    "Assess the supplied tutoring draft against the actual question, current-concept attempt, "
    "approved teaching profile and evidence. Return a conditional revision wrapper, not a bare proposal. "
    "If the draft already meets the request and teaching stage, KEEP it: disposition keep, fault none, "
    "proposed_move preserve, replacement null. Do not rewrite merely for wording or stylistic polish. "
    "Otherwise REPAIR it: identify one primary observable fault, propose the appropriate teaching move "
    "from the actual context and provide the complete corrected typed replacement. The draft's action "
    "is not authority: a mistaken refusal or under-helpful question can require an explanation. "
    "Distinguish an explicit third-party private-record request from an own-record request whose values "
    "are unavailable and from an ordinary explanation of privacy rules. Missing personal values do not "
    "make an own-record request a third-party disclosure. Do not invent extra requested details. "
    "A correct attempt on the current concept requires the requested supported application, not just "
    "asking the learner for the requested result again. An attempt on another concept does not "
    "authorize a newly requested concept's full solution. Keep an already useful initial question. "
    "Assess answer disclosure even inside question wording. Respect explanation-first profiles too. "
    "Use instructional for instruction or partial (supported response plus genuinely missing requested "
    "details), elicitation for question, clarification for clarify, missing_evidence for no_evidence, "
    "private for third-party refusal, graded for assessed-work refusal. These are model proposals, "
    "not permissions independently granted by the server. Give a brief observable diagnosis, not "
    "hidden reasoning. target_concept identifies the current request. "
    "The following replacement guidance applies only if repair is needed: " + REVISION_INSTRUCTION.replace(
        "Return only the same typed proposal schema, not a score or a verdict.",
        "Use the same typed proposal schema for the replacement field.")
    + " Return the outer conditional wrapper in all cases; the preceding bare-proposal instructions describe only its replacement field."
)


class ConditionalRevisionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disposition: Literal["keep", "repair"]
    fault: Literal["none", "unsupported_assertion", "incorrect_application", "missing_requested_answer",
        "incorrect_boundary", "premature_solution", "unresolved_referent", "profile_mismatch"]
    proposed_move: Literal["preserve", "elicitation", "instructional", "clarification", "missing_evidence", "private", "graded"]
    target_concept: str = Field(min_length=1, max_length=160)
    diagnosis: str = Field(min_length=1, max_length=300)
    replacement: TypedInstructionProposal | None

    @model_validator(mode="after")
    def consistent_disposition(self):
        if self.disposition == "keep":
            if self.fault != "none" or self.proposed_move != "preserve" or self.replacement is not None:
                raise ValueError("keep requires no fault, preserve and no replacement")
        elif self.fault == "none" or self.replacement is None or self.proposed_move == "preserve":
            raise ValueError("repair requires a fault, proposed move and replacement")
        elif self.replacement.action not in MOVE_ACTIONS[self.proposed_move]:
            raise ValueError("replacement action differs from proposed move")
        if not self.target_concept.strip() or not self.diagnosis.strip():
            raise ValueError("empty observable assessment")
        return self


@dataclass(frozen=True)
class ConditionalRevisionResult:
    decision: ConditionalRevisionDecision
    response: LlmResponse
    proposal: TypedInstructionProposal
    input_sha256: str
    draft_sha256: str


def build_conditional_revision_messages(*, payload, draft, instruction=INSTRUCTION):
    validated = TypedInstructionProposal.model_validate(draft)
    content = json.dumps({**payload, "draft_proposal": validated.model_dump(mode="json")}, sort_keys=True)
    return [LlmMessage(role="system", content=instruction), LlmMessage(role="user", content=content)]


async def conditionally_revise_instructional_proposal(client, *, payload, draft, instruction=INSTRUCTION):
    """One request; retain the original only after a schema-valid keep assessment."""
    draft = TypedInstructionProposal.model_validate(draft)
    messages = build_conditional_revision_messages(payload=payload, draft=draft, instruction=instruction)
    response = await client.chat(messages, TASK)
    try:
        if response.provider_model != REVISION_MODEL or response.usage.approximate_cost_usd is None:
            raise ValueError("identity or unknown usage")
        decision = ConditionalRevisionDecision.model_validate_json(response.content)
    except ValueError as error:
        raise LlmMalformedResponseError(stage="conditional_revision_contract", provider_model=response.provider_model,
            provider_revision=response.provider_revision, usage=response.usage) from error
    return ConditionalRevisionResult(decision=decision, response=response,
        proposal=draft if decision.disposition == "keep" else decision.replacement,
        input_sha256=hashlib.sha256(messages[1].content.encode()).hexdigest(),
        draft_sha256=hashlib.sha256(json.dumps(draft.model_dump(mode="json"), sort_keys=True).encode()).hexdigest())


class ConditionalRevisionInstructionalGenerator(EvidenceStrengthInstructionalGenerator):
    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v14-development"

    async def _request_proposal(self, payload, *, evidence, started):
        draft_response = None
        revision_started = False
        try:
            draft_response = await super()._request_proposal(payload, evidence=evidence, started=started)
            draft = _check_response(draft_response, DRAFT_MODEL)
            super()._compose(draft, evidence=evidence, trace_args={
                "generator_id": self.implementation_id, "provider_model": draft_response.provider_model,
                "provider_revision": draft_response.provider_revision, "prompt_version": self.implementation_id,
                "started": started, "clock": self.clock, "usage": draft_response.usage})
            revision_started = True
            result = await conditionally_revise_instructional_proposal(self.client,
                payload=self._prepare_payload(payload), draft=draft)
            usage = _sum_usage(draft_response.usage, result.response.usage)
            if result.decision.disposition == "keep":
                return draft_response.model_copy(update={"usage": usage})
            return result.response.model_copy(update={"content": result.proposal.model_dump_json(), "usage": usage})
        except (LlmError, ValueError) as error:
            error_usage = getattr(error, "usage", None)
            if draft_response is None:
                usage = error_usage or GenerationUsage()
            elif revision_started:
                usage = _sum_usage(draft_response.usage, error_usage or GenerationUsage())
            else:
                usage = draft_response.usage
            raise LlmMalformedResponseError(stage="conditional_revision_stage" if revision_started else "draft_stage",
                provider_model=getattr(error, "provider_model", None) or (REVISION_MODEL if revision_started else DRAFT_MODEL),
                provider_revision=getattr(error, "provider_revision", None), usage=usage,
                diagnostics={"contract_code": str(error) if isinstance(error, CompactContractError) else "provider_or_schema_failure"}) from error

    def _compose(self, proposal, *, evidence, trace_args):
        answer = super()._compose(proposal, evidence=evidence, trace_args=trace_args)
        if answer.trace is not None:
            disposition = "keep" if trace_args["provider_model"] == DRAFT_MODEL else "repair"
            answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                "validation_scope": (answer.trace.validation_scope or SCOPE)
                    + "; draft_provider=gpt-5.6-luna; assessment_provider=gpt-5.6-sol; disposition=" + disposition
                    + "; final_provider=" + trace_args["provider_model"]
                    + "; usage_scope=combined-draft-and-conditional-revision; revision_limit=1; semantic-certification=false"})})
        return answer

    def _failure_answer(self, error, *, response, started):
        if response is None:
            response = LlmResponse(content="{}", provider_model=getattr(error, "provider_model", None) or DRAFT_MODEL,
                provider_revision=getattr(error, "provider_revision", None), usage=getattr(error, "usage", None) or GenerationUsage())
        answer = super()._failure_answer(error, response=response, started=started)
        if answer.trace is not None:
            stage = getattr(error, "stage", "composition")
            scope = SCOPE + "; assessment_provider=gpt-5.6-sol; usage_scope=" + (
                "draft-only" if stage == "draft_stage" else "combined-draft-and-conditional-revision")
            answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                "generator_id": self.implementation_id, "prompt_version": self.implementation_id,
                "validation_scope": scope + "; failure_stage=" + stage})})
        return answer
