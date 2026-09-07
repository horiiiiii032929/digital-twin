"""Experimental revision with a structural ceiling, not disclosure verification."""
from typing import Literal

from pydantic import Field

from src.digital_twin.llm import LlmMalformedResponseError
from .factual_revision import (
    FactualRevisionInstructionalGenerator, REVISION_MODEL, _check_response,
    build_revision_messages, revise_instructional_proposal,
)
from .typed_instruction import TypedInstructionProposal, ElicitationInstructionUnit

CANDIDATE_ID = "question-specific-profile-grounded-v13"
BOUNDED_REVISION_TASK = "question_specific_bounded_revision"
BOUNDED_INSTRUCTION = (
    " This draft has a protected elicitation or boundary move. Make only needed corrections within "
    "that ceiling, preserving an already appropriate question. You must return only question, "
    "no_evidence, clarify, private or graded with elicitation units; never instruction, partial, "
    "explanation or feedback. Do not replace an initial question with its solution even when the "
    "source establishes that solution. Do not embed the decisive condition, result or complete "
    "procedure inside an elicitation. A prior attempt on another concept does not authorize the "
    "new concept's solution. If the draft already respects this boundary, preserve its useful "
    "focus rather than unnecessarily rewriting it. This restriction does not certify semantic safety."
)


class BoundedRevisionProposal(TypedInstructionProposal):
    action: Literal["question", "no_evidence", "clarify", "private", "graded"]
    units: list[ElicitationInstructionUnit] = Field(max_length=4)


def requires_bounded_revision(draft: TypedInstructionProposal) -> bool:
    return draft.action in {"question", "private", "graded"} or (
        draft.action == "no_evidence" and bool(draft.units))


def build_bounded_revision_messages(*, payload, draft):
    messages = build_revision_messages(payload=payload, draft=draft)
    return [messages[0].model_copy(update={"content": messages[0].content + BOUNDED_INSTRUCTION}), messages[1]]


async def revise_bounded_instructional_proposal(client, *, payload, draft):
    """Exactly one revision; eligible drafts cannot escalate to factual units."""
    draft = TypedInstructionProposal.model_validate(draft)
    if not requires_bounded_revision(draft):
        return await revise_instructional_proposal(client, payload=payload, draft=draft)
    response = await client.chat(build_bounded_revision_messages(payload=payload, draft=draft), BOUNDED_REVISION_TASK)
    _check_response(response, REVISION_MODEL)
    try:
        # Server-side defense also applies to injected/alternative transports.
        BoundedRevisionProposal.model_validate_json(response.content)
    except ValueError as error:
        raise LlmMalformedResponseError(stage="bounded_revision_contract", provider_model=response.provider_model,
            provider_revision=response.provider_revision, usage=response.usage) from error
    return response


class BoundedRevisionInstructionalGenerator(FactualRevisionInstructionalGenerator):
    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v13-development"

    async def _revise_proposal(self, *, payload, draft):
        return await revise_bounded_instructional_proposal(self.client, payload=payload, draft=draft)
