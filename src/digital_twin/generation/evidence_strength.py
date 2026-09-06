"""Experimental instruction-only calibration; association remains unverified support."""
from .typed_instruction import TypedInstructionalGenerator

CANDIDATE_ID = "question-specific-profile-grounded-v11"
EVIDENCE_STRENGTH_INSTRUCTION = (
    "Keep each factual statement attached to the named entity whose source establishes it; "
    "combining source IDs does not transfer one entity's rule to another. Adjacent descriptions "
    "do not establish a causal or sequential workflow without an explicit supported relation. Preserve the source's "
    "condition-to-result direction, quantifiers, exceptions and explicit dependencies. A implies B "
    "does not by itself establish that B implies A. A procedure that checks for or detects a "
    "condition is not automatically a guarantee that every instance is detected, or that a negative "
    "check proves the condition absent. Do not add a converse, uniqueness, certainty, or completeness "
    "claim that the source does not establish. Apply clearly stated rules and complete stated "
    "case distinctions directly to the supplied values; do not hedge established facts or refuse "
    "ordinary supported applications. Examples, corrective feedback and questions must respect "
    "the same evidential limits as explanations. State the supported conclusion at its actual "
    "strength, separating any specifically requested but unavailable guarantee from useful known "
    "information. Do not turn caution about an unsupported guarantee into a claim that all evidence "
    "is missing. Source association does not itself verify any of these semantic properties."
)


class EvidenceStrengthInstructionalGenerator(TypedInstructionalGenerator):
    """Retain V10 task/schema/rendering; change only the identified instruction."""
    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v11-development"

    def _system_instruction(self):
        return super()._system_instruction() + " " + EVIDENCE_STRENGTH_INSTRUCTION
