"""Experimental single independent revision, never a semantic certification."""
from __future__ import annotations

import json

from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmError, LlmMalformedResponseError, LlmMessage, LlmResponse
from .compact_instruction import SCOPE, CompactContractError
from .evidence_strength import EvidenceStrengthInstructionalGenerator
from .typed_instruction import TypedInstructionProposal

CANDIDATE_ID = "question-specific-profile-grounded-v12"
REVISION_TASK = "question_specific_factual_revision"
DRAFT_MODEL = "gpt-5.6-luna"
REVISION_MODEL = "gpt-5.6-sol"
REVISION_INSTRUCTION = (
    "Revise the supplied draft tutoring proposal once using the actual question, conversation, approved "
    "teaching profile and approved evidence. Return only the same typed proposal schema, not a score or "
    "a verdict. Preserve already adequate useful content and teaching moves. Check every statement, "
    "including feedback, examples and elicitation, against the evidence for its own named entity. Do not "
    "transfer rules between entities or infer a causal or sequential workflow from adjacent descriptions. "
    "Preserve implication direction, quantifiers, exceptions and explicit dependencies. Detection or a "
    "comparison does not establish a universal detection guarantee or its converse. Preserve complete "
    "stated case distinctions and apply clear supported rules directly; do not replace useful supported "
    "answers with blanket hedging. Correct unsupported strengthening, ownership and relationships. "
    "Retain every requested goal that can be supported, including the requested application after an "
    "attempt. If a referent is unresolved, ask a specific clarification. Preserve the approved instructor "
    "style: remove profile-prohibited solution disclosure, including decisive conditions embedded in an "
    "initial Socratic question. Do not volunteer a secondary concept's full rule without its own permitted "
    "stage. An explanation-first profile permits a direct supported explanation before optional checks. "
    "Use only supplied source IDs. Each explanation or feedback unit needs at least one source ID; "
    "elicitation may have none. Source association is not entailment. Keep missing requested information "
    "only in missing_details, not factual units; withholding an available fact is not missing evidence. "
    "instruction/partial require factual units; partial requires actual missing requested details. "
    "question/no_evidence/clarify/private/graded can contain only elicitation units. A question action "
    "must contain a useful elicitation. Respect privacy and assessed-work boundaries. At most four units, "
    "700 characters per unit, five IDs per unit, four missing details of 300 characters each. Do not "
    "include hidden reasoning, assessment labels, invented sources or an assurance of correctness."
)
REVISION_SCOPE = (
    "; draft_provider=gpt-5.6-luna; final_provider=gpt-5.6-sol; "
    "usage_scope=combined-draft-and-revision; revision_limit=1; semantic-certification=false"
)


def build_revision_messages(*, payload: dict, draft: TypedInstructionProposal) -> list[LlmMessage]:
    """Use the prepared product payload unchanged, adding only the validated draft."""
    validated = TypedInstructionProposal.model_validate(draft)
    return [LlmMessage(role="system", content=REVISION_INSTRUCTION),
        LlmMessage(role="user", content=json.dumps(
            {**payload, "draft_proposal": validated.model_dump(mode="json")}, sort_keys=True))]


def _sum_usage(first: GenerationUsage, second: GenerationUsage) -> GenerationUsage:
    return GenerationUsage(input_tokens=first.input_tokens + second.input_tokens,
        output_tokens=first.output_tokens + second.output_tokens,
        total_tokens=first.total_tokens + second.total_tokens,
        approximate_cost_usd=(first.approximate_cost_usd + second.approximate_cost_usd
            if first.approximate_cost_usd is not None and second.approximate_cost_usd is not None else None))


def _check_response(response: LlmResponse, model: str) -> TypedInstructionProposal:
    try:
        if response.provider_model != model:
            raise ValueError("identity")
        if response.usage.approximate_cost_usd is None:
            raise ValueError("usage")
        return TypedInstructionProposal.model_validate_json(response.content)
    except ValueError as error:
        raise LlmMalformedResponseError(stage="revision_protocol", provider_model=response.provider_model,
            provider_revision=response.provider_revision, usage=response.usage) from error


async def revise_instructional_proposal(client, *, payload: dict,
        draft: TypedInstructionProposal) -> LlmResponse:
    """One real revision call; no generation, repair loop, quality verdict or fallback."""
    response = await client.chat(build_revision_messages(payload=payload, draft=draft), REVISION_TASK)
    _check_response(response, REVISION_MODEL)
    return response


class FactualRevisionInstructionalGenerator(EvidenceStrengthInstructionalGenerator):
    """V11 draft and one Sol revision, with request-local response accounting."""
    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v12-development"

    async def _request_proposal(self, payload, *, evidence, started):
        draft_response = None
        revision_started = False
        try:
            draft_response = await super()._request_proposal(payload, evidence=evidence, started=started)
            draft = _check_response(draft_response, DRAFT_MODEL)
            # Pure structural/source admission before spending on a revision.
            super()._compose(draft, evidence=evidence, trace_args={
                "generator_id": self.implementation_id, "provider_model": draft_response.provider_model,
                "provider_revision": draft_response.provider_revision, "prompt_version": self.implementation_id,
                "started": started, "clock": self.clock, "usage": draft_response.usage})
            revision_started = True
            revised = await self._revise_proposal(payload=self._prepare_payload(payload), draft=draft)
            return revised.model_copy(update={"usage": _sum_usage(draft_response.usage, revised.usage)})
        except (LlmError, ValueError) as error:
            error_usage = getattr(error, "usage", None)
            if draft_response is None:
                usage = error_usage or GenerationUsage()
            elif revision_started:
                usage = _sum_usage(draft_response.usage, error_usage or GenerationUsage())
            else:
                usage = draft_response.usage
            raise LlmMalformedResponseError(stage="revision_stage" if revision_started else "draft_stage",
                provider_model=getattr(error, "provider_model", None) or (REVISION_MODEL if revision_started else DRAFT_MODEL),
                provider_revision=getattr(error, "provider_revision", None) or (draft_response.provider_revision if draft_response is not None and not revision_started else None),
                usage=usage, diagnostics={"contract_code": str(error) if isinstance(error, CompactContractError) else "provider_or_schema_failure"}) from error

    async def _revise_proposal(self, *, payload, draft):
        return await revise_instructional_proposal(self.client, payload=payload, draft=draft)

    def _compose(self, proposal, *, evidence, trace_args):
        answer = super()._compose(proposal, evidence=evidence, trace_args=trace_args)
        if answer.trace is not None:
            answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                "validation_scope": (answer.trace.validation_scope or SCOPE) + REVISION_SCOPE})})
        return answer

    def _failure_answer(self, error, *, response, started):
        # A failed revision must never expose the unchecked draft. Preserve known
        # prior spend; unknown failed-call usage leaves combined cost unknown.
        if response is None:
            response = LlmResponse(content="{}", provider_model=getattr(error, "provider_model", None) or DRAFT_MODEL,
                provider_revision=getattr(error, "provider_revision", None), usage=getattr(error, "usage", None) or GenerationUsage())
        answer = super()._failure_answer(error, response=response, started=started)
        if answer.trace is not None:
            stage = getattr(error, "stage", "composition")
            attempted = stage != "draft_stage"
            code = str(error) if isinstance(error, CompactContractError) else getattr(error, "diagnostics", {}).get("contract_code", "provider_or_schema_failure")
            scope = (SCOPE + "; configured_revision_provider=gpt-5.6-sol; revision_attempted=" + str(attempted).lower()
                + "; usage_scope=" + ("combined-draft-and-revision" if attempted else "draft-only")
                + "; revision_failure=" + stage + "; compact_contract=" + code)
            answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                "generator_id": self.implementation_id, "prompt_version": self.implementation_id,
                "validation_scope": scope})})
        return answer
