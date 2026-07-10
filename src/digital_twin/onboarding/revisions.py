from uuid import uuid4

from src.digital_twin.onboarding.interview import _normalize_for_vague_detection
from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.onboarding.policy import find_policy_field
from src.digital_twin.onboarding.preview import _regenerate_previews
from src.digital_twin.onboarding.release import _recompute_release_state
from src.digital_twin.tutor_policy import (
    FieldStatus,
    PreviewDecisionRecord,
    RevisionProposal,
)


def confirm_revision_proposal(session: OnboardingSession) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    proposal = updated.revision_proposal
    if proposal is None:
        raise ValueError("revision_proposal_not_found")
    if updated.policy is None:
        raise ValueError("policy_not_ready")

    for field_id in proposal.affected_policy_fields:
        field = find_policy_field(updated.policy, field_id)
        if field is None:
            continue
        if field_id == "tutoring_moves":
            field.value = ["guiding_question", "hints", "partial_structure"]
        else:
            field.value = proposal.proposed_value
        field.status = FieldStatus.RESOLVED
        field.warning = None

    updated.policy_version += 1
    _regenerate_previews(updated)
    if proposal.preview_case_id and proposal.preview_case_id in updated.preview_decisions:
        updated.preview_decisions[proposal.preview_case_id] = PreviewDecisionRecord(
            preview_case_id=proposal.preview_case_id,
            decision="pending",
            reason="Regenerated after confirmed revision.",
            policy_version=updated.policy_version,
            revision_resolved=True,
        )
        for preview in updated.preview_cases:
            if preview.id == proposal.preview_case_id:
                preview.decision = "pending"
                preview.decision_reason = "Regenerated after confirmed revision."

    updated.revision_proposal = None
    _recompute_release_state(updated)
    return updated


def discard_revision_proposal(session: OnboardingSession) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    if updated.revision_proposal is None:
        raise ValueError("revision_proposal_not_found")
    updated.revision_proposal = None
    _recompute_release_state(updated)
    return updated


def _proposal_from_feedback(
    session: OnboardingSession,
    feedback: str,
) -> RevisionProposal | None:
    normalized = feedback.lower()
    rejected_case_id = next(
        (
            case_id
            for case_id, record in session.preview_decisions.items()
            if record.decision == "rejected"
        ),
        None,
    )
    if any(
        phrase in normalized
        for phrase in (
            "homework",
            "graded",
            "too much",
            "full answer",
            "gives away",
        )
    ):
        return RevisionProposal(
            id=f"revision-{uuid4()}",
            preview_case_id=rejected_case_id or "academic-integrity",
            feedback=feedback,
            affected_policy_fields=[
                "academic_integrity_policy",
                "tutoring_moves",
            ],
            proposed_value=(
                "Require one guiding question before hints; never provide the "
                "full graded-work answer or complete solution structure."
            ),
            rationale=(
                "The feedback indicates an academic-integrity boundary problem "
                "and a tutoring-move adjustment."
            ),
        )
    if any(phrase in normalized for phrase in ("source", "citation", "cite")):
        return RevisionProposal(
            id=f"revision-{uuid4()}",
            preview_case_id=rejected_case_id or "external-grounding",
            feedback=feedback,
            affected_policy_fields=["knowledge_source_policy"],
            proposed_value=(
                "Require visible source labels and source audit entries for any "
                "external grounding."
            ),
            rationale="The feedback indicates a source-grounding or citation issue.",
        )
    if any(phrase in normalized for phrase in ("tone", "wording", "friendly")):
        return RevisionProposal(
            id=f"revision-{uuid4()}",
            preview_case_id=rejected_case_id,
            feedback=feedback,
            affected_policy_fields=["tone_guidance"],
            proposed_value="Use concise, direct, professor-reviewable wording.",
            rationale="The feedback indicates a tone or wording adjustment.",
        )
    return None


def _is_confirmation_message(message: str) -> bool:
    return _normalize_for_vague_detection(message) in {"confirm", "yes", "apply"}


def _is_discard_message(message: str) -> bool:
    return _normalize_for_vague_detection(message) in {
        "discard",
        "cancel",
        "no",
    }
