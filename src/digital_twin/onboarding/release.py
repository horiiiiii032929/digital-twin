from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.onboarding.policy import find_policy_field
from src.digital_twin.tutor_policy import (
    FieldStatus,
    ReleaseStatus,
    SourcePermissionStatus,
)


REQUIRED_PREVIEW_CASE_IDS = frozenset(
    {"external-grounding", "academic-integrity", "misconception"}
)
CUSTOM_PREVIEW_REQUIRED_BLOCKER = (
    "Add and accept a professor custom prompt preview."
)


def _recompute_release_state(session: OnboardingSession) -> None:
    blockers = {
        "source_inventory": _source_inventory_blockers(session),
        "policy_fields": _policy_field_blockers(session),
        "approval_checklist": _approval_checklist_blockers(session),
        "preview_decisions": _preview_decision_blockers(session),
        "preview_acceptance": _preview_acceptance_blockers(session),
        "revision_proposal": _revision_proposal_blockers(session),
    }
    session.release_blockers = blockers

    if session.policy is None:
        return

    is_approved = all(not values for values in blockers.values())
    session.policy.release_status = (
        ReleaseStatus.APPROVED if is_approved else ReleaseStatus.BLOCKED
    )
    session.policy.status = ReleaseStatus.APPROVED if is_approved else ReleaseStatus.DRAFT


def _source_inventory_blockers(session: OnboardingSession) -> list[str]:
    blockers: list[str] = []
    approved_count = 0
    for source in session.source_inventory:
        if source.excluded:
            continue
        if source.permission_status == SourcePermissionStatus.APPROVED:
            approved_count += 1
        if source.permission_status == SourcePermissionStatus.PENDING:
            blockers.append(
                f"{source.name} needs an approve or exclude decision."
            )
        if source.sensitive:
            blockers.append(
                f"{source.name} is sensitive and must remain excluded unless documented."
            )
    if approved_count == 0:
        blockers.append("Add at least one approved, included source.")
    return blockers


def _policy_field_blockers(session: OnboardingSession) -> list[str]:
    if session.policy is None:
        return []
    blockers = [field.id for field in session.policy.all_fields if field.blocks_release]
    knowledge_field = find_policy_field(session.policy, "knowledge_source_policy")
    if (
        knowledge_field is not None
        and isinstance(knowledge_field.value, dict)
        and not knowledge_field.value.get("confirmed", False)
        and "knowledge_source_policy" not in blockers
    ):
        blockers.append("knowledge_source_policy")
    return blockers


def _approval_checklist_blockers(session: OnboardingSession) -> list[str]:
    return [
        item.id
        for item in session.approval_checklist
        if item.is_blocking_incomplete
    ]


def _preview_decision_blockers(session: OnboardingSession) -> list[str]:
    blockers: list[str] = []
    for case_id, record in session.preview_decisions.items():
        if record.policy_version != session.policy_version:
            blockers.append(f"{case_id} decision is for a stale policy version.")
        elif record.decision == "rejected" and not record.revision_resolved:
            blockers.append(f"{case_id} is rejected and unresolved.")
    return blockers


def _preview_acceptance_blockers(session: OnboardingSession) -> list[str]:
    if not session.preview_cases:
        return []
    required_ids = set(REQUIRED_PREVIEW_CASE_IDS)
    custom_preview_ids = {
        preview.id
        for preview in session.preview_cases
        if preview.id.startswith("custom-")
    }
    required_ids.update(custom_preview_ids)

    blockers: list[str] = []
    for preview_id in sorted(required_ids):
        record = session.preview_decisions.get(preview_id)
        preview = next(
            (item for item in session.preview_cases if item.id == preview_id),
            None,
        )
        if (
            record is None
            or preview is None
            or record.policy_version != session.policy_version
            or preview.policy_version != session.policy_version
            or record.decision != "accepted"
            or preview.decision != "accepted"
        ):
            blockers.append(f"{preview_id} preview is not accepted.")
    if not custom_preview_ids:
        blockers.append(CUSTOM_PREVIEW_REQUIRED_BLOCKER)
    return blockers


def _revision_proposal_blockers(session: OnboardingSession) -> list[str]:
    if session.revision_proposal is None:
        return []
    return ["Resolve or discard the pending policy revision proposal."]


def _invalidate_release_approval(session: OnboardingSession) -> None:
    """Require a new explicit final approval after reviewed state changes."""

    for item in session.approval_checklist:
        if item.id == "professor_release_approval":
            item.checked = False
    if session.policy is None:
        return
    field = find_policy_field(session.policy, "professor_release_approval")
    if field is not None:
        field.value = "pending"
        field.status = FieldStatus.BLOCKS_RELEASE
        field.warning = "Professor must approve the current reviewed version."


def _uncheck_approval_items(
    session: OnboardingSession,
    item_ids: set[str] | frozenset[str],
) -> None:
    for item in session.approval_checklist:
        if item.id in item_ids:
            item.checked = False
