"""Typed factual-source requirement and narrow initial-reference priority candidate."""
from typing import Literal

from pydantic import Field

from .compact_instruction import CompactInstructionProposal, CompactUnit
from .profile_authority import ProfileAuthorityInstructionalGenerator

TASK = "question_specific_typed_instruction"
CANDIDATE_ID = "question-specific-profile-grounded-v10"


class FactualInstructionUnit(CompactUnit):
    kind: Literal["explanation", "feedback"]
    source_ids: list[str] = Field(min_length=1, max_length=5)


class ElicitationInstructionUnit(CompactUnit):
    kind: Literal["elicitation"]


class TypedInstructionProposal(CompactInstructionProposal):
    units: list[FactualInstructionUnit | ElicitationInstructionUnit] = Field(max_length=4)


class TypedInstructionalGenerator(ProfileAuthorityInstructionalGenerator):
    task = TASK
    proposal_model = TypedInstructionProposal
    supports_initial_reference_priority = True

    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v10-development"

    def _system_instruction(self):
        return super()._system_instruction() + (
            " For initial Socratic elicitation, ask the learner to derive the decisive condition or "
            "outcome; do not embed that answer condition or result in the question itself. "
            "Each explanatory or feedback unit MUST cite at least one supplied source ID. "
            "Only elicitation units may have no source IDs. Put absence notices exclusively in "
            "missing_details, because the server prints that list; never add a second explanatory "
            "unit describing the absence without evidence. Generic partial response SHAPE only: "
            '{"action":"partial","units":[{"kind":"explanation","text":"<supported requested explanation>",'
            '"source_ids":["<actual supplied source ID>"]}],"missing_details":["<unavailable requested detail>"]}. '
            "These angle-bracket entries are placeholders, not source facts or literal output."
        )
