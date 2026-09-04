import hashlib
import json
from typing import Literal
from uuid import uuid4

from src.digital_twin.onboarding.interview import _normalize_for_vague_detection
from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.onboarding.policy import find_policy_field
from src.digital_twin.onboarding.preview import _regenerate_previews
from src.digital_twin.onboarding.release import _recompute_release_state
from src.digital_twin.tutor_policy import (
    FieldStatus,
    PreviewDecisionRecord,
    RevisionAlternative,
    RevisionDecisionRecordV1,
    RevisionProposal,
)


def _review_artifact_sha256(session: OnboardingSession) -> str:
    payload = {
        "policy_version": session.policy_version,
        "policy": session.policy.model_dump(mode="json") if session.policy else None,
        "previews": [row.model_dump(mode="json") for row in session.preview_cases],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _history_record(
    proposal: RevisionProposal,
    *,
    status: Literal["confirmed", "discarded", "superseded"],
    target_policy_version: int,
) -> RevisionDecisionRecordV1:
    return RevisionDecisionRecordV1(
        proposal_id=proposal.id,
        preview_case_id=proposal.preview_case_id,
        feedback=proposal.feedback,
        affected_policy_fields=proposal.affected_policy_fields,
        proposed_value=proposal.proposed_value,
        rationale=proposal.rationale,
        status=status,
        base_policy_version=proposal.base_policy_version,
        target_policy_version=target_policy_version,
        review_artifact_sha256=proposal.review_artifact_sha256,
        selected_alternative_id=proposal.selected_alternative_id,
        created_at=proposal.created_at,
    )


def confirm_revision_proposal(session: OnboardingSession) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    proposal = updated.revision_proposal
    if proposal is None:
        raise ValueError("revision_proposal_not_found")
    if updated.policy is None:
        raise ValueError("policy_not_ready")
    if proposal.base_policy_version != updated.policy_version:
        raise ValueError("revision_proposal_stale")
    if proposal.review_artifact_sha256 != _review_artifact_sha256(updated):
        raise ValueError("revision_artifact_stale")
    if len(proposal.alternatives) > 1 and proposal.selected_alternative_id is None:
        raise ValueError("revision_alternative_required")

    for field_id in proposal.affected_policy_fields:
        field = find_policy_field(updated.policy, field_id)
        if field is None:
            continue
        if field_id == "tutoring_moves":
            field.value = ["guiding_question", "hints", "partial_structure"]
        else:
            field.value = proposal.proposed_value
        if field_id == "knowledge_source_policy":
            field.status = FieldStatus.NEEDS_REVIEW
            field.warning = "Confirm the course source strictness before release."
        else:
            field.status = FieldStatus.RESOLVED
            field.warning = None

    updated.policy_version += 1
    _regenerate_previews(updated)
    if (
        proposal.preview_case_id
        and proposal.preview_case_id in updated.preview_decisions
    ):
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

    updated.revision_history.append(
        _history_record(
            proposal,
            status="confirmed",
            target_policy_version=updated.policy_version,
        )
    )
    updated.revision_proposal = None
    _recompute_release_state(updated)
    return updated


def discard_revision_proposal(session: OnboardingSession) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    proposal = updated.revision_proposal
    if proposal is None:
        raise ValueError("revision_proposal_not_found")
    updated.revision_history.append(
        _history_record(
            proposal,
            status="discarded",
            target_policy_version=updated.policy_version,
        )
    )
    updated.revision_proposal = None
    _recompute_release_state(updated)
    return updated


def select_revision_alternative(
    session: OnboardingSession,
    alternative_id: str,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    proposal = updated.revision_proposal
    if proposal is None:
        raise ValueError("revision_proposal_not_found")
    if proposal.base_policy_version != updated.policy_version:
        raise ValueError("revision_proposal_stale")
    matches = [row for row in proposal.alternatives if row.id == alternative_id]
    if len(matches) != 1:
        raise ValueError("revision_alternative_not_found")
    selected = matches[0]
    proposal.selected_alternative_id = selected.id
    proposal.affected_policy_fields = list(selected.affected_policy_fields)
    proposal.proposed_value = selected.proposed_value
    proposal.rationale = selected.rationale
    updated.revision_proposal = proposal
    return updated


def supersede_revision_proposal(session: OnboardingSession) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    proposal = updated.revision_proposal
    if proposal is not None:
        updated.revision_history.append(
            _history_record(
                proposal,
                status="superseded",
                target_policy_version=updated.policy_version,
            )
        )
        updated.revision_proposal = None
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
    alternatives: list[RevisionAlternative] = []
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
        alternatives.append(
            RevisionAlternative(
                id="academic-integrity",
                category="academic_integrity",
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
        )
    if any(phrase in normalized for phrase in ("source", "citation", "cite")):
        current_value: dict = {}
        if session.policy is not None:
            field = find_policy_field(session.policy, "knowledge_source_policy")
            if field is not None and isinstance(field.value, dict):
                current_value = dict(field.value)
        current_value["external_sources_require_visible_labels"] = True
        alternatives.append(
            RevisionAlternative(
                id="source-grounding",
                category="source_grounding",
                affected_policy_fields=["knowledge_source_policy"],
                proposed_value=current_value,
                rationale=(
                    "The feedback requires visible source labels while preserving "
                    "the professor's current source-scope decision."
                ),
            )
        )
    if any(phrase in normalized for phrase in ("tone", "wording", "friendly")):
        alternatives.append(
            RevisionAlternative(
                id="tone",
                category="tone",
                affected_policy_fields=["tone_guidance"],
                proposed_value="Use concise, direct, professor-reviewable wording.",
                rationale="The feedback indicates a tone or wording adjustment.",
            )
        )
    if not alternatives:
        return None
    first = alternatives[0]
    default_preview = {
        "academic_integrity": "academic-integrity",
        "source_grounding": "external-grounding",
        "tone": rejected_case_id,
    }[first.category]
    return RevisionProposal(
        id=f"revision-{uuid4()}",
        preview_case_id=rejected_case_id or default_preview,
        feedback=feedback,
        affected_policy_fields=list(first.affected_policy_fields),
        proposed_value=first.proposed_value,
        rationale=first.rationale,
        base_policy_version=session.policy_version,
        review_artifact_sha256=_review_artifact_sha256(session),
        alternatives=alternatives,
        selected_alternative_id=first.id if len(alternatives) == 1 else None,
    )


def _is_confirmation_message(message: str) -> bool:
    return _normalize_for_vague_detection(message) in {"confirm", "yes", "apply"}


def _is_discard_message(message: str) -> bool:
    return _normalize_for_vague_detection(message) in {
        "discard",
        "cancel",
        "no",
    }
