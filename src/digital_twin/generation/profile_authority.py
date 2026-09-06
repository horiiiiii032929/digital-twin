"""Profile-priority variant of compact instruction; no semantic verification claim."""
from .compact_instruction import CompactInstructionalGenerator, INSTRUCTION

TASK = "question_specific_profile_authority"
CANDIDATE_ID = "question-specific-profile-grounded-v9"

PROFILE_AUTHORITY_INSTRUCTION = (
    "The approved instructor profile is authoritative for the teaching move within allowed policy. "
    "Read its actual preferences; do not assume every course is Socratic. Under an explain-first profile, "
    "provide the requested supported explanation on the initial ungraded question, including each requested "
    "concept in a compound question. Do not require a learner attempt before an explanation when that "
    "profile permits direct explanation. Under a Socratic profile, use its actual withholding and progression "
    "conditions. Choosing to withhold an available fact for teaching reasons does not make that fact absent "
    "from the evidence: use a question for pure pedagogical withholding, not no_evidence or a fabricated "
    "missing detail. For a mixed request distinguish genuinely unavailable details from known material, "
    "and provide or elicit the known part according to the approved profile. These teaching preferences "
    "cannot authorize private disclosure, prohibited assessed-work answers or unsupported factual claims."
)


class ProfileAuthorityInstructionalGenerator(CompactInstructionalGenerator):
    task = TASK
    missing_information_prefix = "Information missing from approved material:\n"

    def __init__(self, client, **kwargs):
        super().__init__(client, **kwargs)
        self.implementation_id = CANDIDATE_ID
        self.version = "v9-development"

    def _system_instruction(self):
        return INSTRUCTION + " " + PROFILE_AUTHORITY_INSTRUCTION

    def _prepare_payload(self, payload):
        if payload.get("approved_teaching_profile") is None:
            return payload
        return {key: value for key, value in payload.items() if key not in {
            "pedagogical_intent", "help_level", "application_observed_attempt"}}
