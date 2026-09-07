"""Experimental global support assessment; no independent semantic guarantee."""
from .conditional_revision import INSTRUCTION, conditionally_revise_instructional_proposal

CANDIDATE_ID = "question-specific-profile-grounded-v15"
SUPPORT_CHECK = (
    "Before choosing KEEP or REPAIR, check the factual support of the entire draft, "
    "including feedback, examples and assertions embedded in questions. These checks "
    "apply to KEEP too, not only to replacement text. A draft can satisfy a teaching "
    "profile and still be factually unsupported. For each asserted relationship, "
    "check whether the supplied evidence could be true while that assertion is false; "
    "if so, do not keep it as an established fact. Preserve the source's named entity, "
    "implication direction, quantifiers, exceptions and event conditions. A necessary "
    "condition does not guarantee an action; a consequence on an event does not establish "
    "that the event occurred. Conversely, explicit if/otherwise procedures support their "
    "stated positive and negative applications: apply those directly without blanket "
    "hedging. Identify unsupported assertions as a fault and repair them while retaining "
    "the supported answer and the authorized teaching stage. Give only the existing brief "
    "observable diagnosis, not hidden reasoning or a proof claim. "
)
GLOBAL_INSTRUCTION = SUPPORT_CHECK + INSTRUCTION

async def globally_assess_instructional_proposal(client, *, payload, draft):
    return await conditionally_revise_instructional_proposal(
        client, payload=payload, draft=draft, instruction=GLOBAL_INSTRUCTION
    )
