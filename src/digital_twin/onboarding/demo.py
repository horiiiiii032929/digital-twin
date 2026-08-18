"""Deterministic synthetic state for the local supervisor product walkthrough."""

from src.digital_twin.onboarding.commands import add_source_inventory_item
from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.onboarding.service import create_session, submit_message
from src.digital_twin.tutor_policy import SourceLabel, SourcePermissionStatus


SUPERVISOR_DEMO_ANSWERS = (
    "Use syllabus, public slides, and instructor-approved examples only.",
    "Balance short explanations with guiding questions.",
    "Refuse full graded-work answers, then offer hints or a similar example.",
    "Correct directly, then show a contrastive example.",
    "Reject responses that use unapproved sources or solve graded work directly.",
)


def create_supervisor_demo_session(
    session_id: str | None = None,
) -> OnboardingSession:
    """Create a populated review state without real course or student data."""

    session = create_session(session_id=session_id)
    for answer in SUPERVISOR_DEMO_ANSWERS:
        session = submit_message(session, answer)

    return add_source_inventory_item(
        session,
        name="synthetic-course-outline.pdf",
        mime_type="application/pdf",
        size_bytes=12_400,
        permission_status=SourcePermissionStatus.APPROVED,
        source_label=SourceLabel.COURSE_APPROVED,
        excluded=False,
        sensitive=False,
        notes=(
            "Synthetic metadata-only supervisor demo source; no file contents "
            "or private course data are stored."
        ),
    )
