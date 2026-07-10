from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.onboarding.policy import find_policy_field
from src.digital_twin.tutor_policy import (
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
    for source in session.source_inventory:
        if source.excluded:
            continue
        if source.permission_status == SourcePermissionStatus.PENDING:
            blockers.append(
                f"{source.name} needs an approve or exclude decision."
            )
        if source.sensitive:
            blockers.append(
                f"{source.name} is sensitive and must remain excluded unless documented."
            )
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
    return [
        f"{case_id} is rejected and unresolved."
        for case_id, record in session.preview_decisions.items()
        if record.decision == "rejected" and not record.revision_resolved
    ]


def _preview_acceptance_blockers(session: OnboardingSession) -> list[str]:
    if not session.preview_cases:
        return []
    required_ids = set(REQUIRED_PREVIEW_CASE_IDS)
    custom_preview_id = next(
        (
            preview.id
            for preview in session.preview_cases
            if preview.id.startswith("custom-")
        ),
        None,
    )
    if custom_preview_id is not None:
        required_ids.add(custom_preview_id)

    blockers: list[str] = []
    for preview_id in sorted(required_ids):
        record = session.preview_decisions.get(preview_id)
        if record is None or record.decision != "accepted":
            blockers.append(f"{preview_id} preview is not accepted.")
    if custom_preview_id is None:
        blockers.append(CUSTOM_PREVIEW_REQUIRED_BLOCKER)
    return blockers
