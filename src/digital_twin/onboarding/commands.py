from typing import Any
from uuid import uuid4

from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.onboarding.policy import find_policy_field
from src.digital_twin.onboarding.preview import (
    _build_custom_preview_case,
    _decision_record_for,
    _field_value_as_signal,
    _snapshot_for,
)
from src.digital_twin.onboarding.release import _recompute_release_state
from src.digital_twin.tutor_policy import (
    FieldStatus,
    KnowledgeSourcePolicy,
    PreviewDecisionRecord,
    PreviewDecisionValue,
    PromptTag,
    SourceInventoryItem,
    SourceLabel,
    SourcePermissionStatus,
    TutorPolicy,
)


def add_source_inventory_item(
    session: OnboardingSession,
    *,
    name: str,
    mime_type: str = "application/octet-stream",
    size_bytes: int = 0,
    permission_status: SourcePermissionStatus = SourcePermissionStatus.PENDING,
    source_label: SourceLabel = SourceLabel.COURSE_APPROVED,
    excluded: bool = False,
    sensitive: bool | None = None,
    notes: str = "",
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    updated.source_inventory.append(
        SourceInventoryItem(
            id=f"source-{uuid4()}",
            name=name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            permission_status=permission_status,
            source_label=source_label,
            excluded=excluded,
            sensitive=sensitive,
            notes=notes,
        )
    )
    _recompute_release_state(updated)
    return updated


def update_source_inventory_item(
    session: OnboardingSession,
    source_id: str,
    **changes: Any,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    for index, item in enumerate(updated.source_inventory):
        if item.id == source_id:
            payload = item.model_dump(mode="json")
            payload.update({key: value for key, value in changes.items() if value is not None})
            updated.source_inventory[index] = SourceInventoryItem.model_validate(payload)
            _recompute_release_state(updated)
            return updated
    raise ValueError("source_inventory_item_not_found")


def update_policy_field_value(
    session: OnboardingSession,
    field_id: str,
    value: str | list[str] | dict,
    status: FieldStatus,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    if updated.policy is None:
        raise ValueError("policy_not_ready")

    for field in updated.policy.all_fields:
        if field.id == field_id:
            field.value = value
            field.status = status
            if status == FieldStatus.RESOLVED:
                field.warning = None
            _recompute_release_state(updated)
            return updated

    raise ValueError("policy_field_not_found")


def update_approval_checklist_item(
    session: OnboardingSession,
    item_id: str,
    checked: bool,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    for item in updated.approval_checklist:
        if item.id == item_id:
            item.checked = checked
            _sync_policy_from_approval(updated, item_id, checked)
            _recompute_release_state(updated)
            return updated
    raise ValueError("approval_item_not_found")


def set_preview_decision(
    session: OnboardingSession,
    preview_case_id: str,
    decision: PreviewDecisionValue,
    reason: str | None = None,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    for preview in updated.preview_cases:
        if preview.id == preview_case_id:
            preview.decision = decision
            preview.decision_reason = reason
            updated.preview_decisions[preview_case_id] = PreviewDecisionRecord(
                preview_case_id=preview_case_id,
                decision=decision,
                reason=reason,
                policy_version=updated.policy_version,
            )
            updated.evidence_snapshots.append(_snapshot_for(preview))
            _sync_preview_checklist(updated, preview_case_id, decision)
            _recompute_release_state(updated)
            return updated
    raise ValueError("preview_case_not_found")


def add_custom_preview_case(
    session: OnboardingSession,
    *,
    prompt: str,
    tag: PromptTag,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    if updated.policy is None:
        raise ValueError("policy_not_ready")

    custom_count = sum(
        1 for preview in updated.preview_cases if preview.id.startswith("custom-")
    )
    preview = _build_custom_preview_case(
        case_id=f"custom-{custom_count + 1}",
        prompt=prompt,
        tag=tag,
        policy=updated.policy,
        policy_version=updated.policy_version,
    )
    updated.preview_cases.append(preview)
    updated.preview_decisions[preview.id] = _decision_record_for(preview)
    updated.evidence_snapshots.append(_snapshot_for(preview))
    _recompute_release_state(updated)
    return updated




def _sync_policy_from_approval(
    session: OnboardingSession,
    item_id: str,
    checked: bool,
) -> None:
    if session.policy is None or not checked:
        return

    field_updates: dict[str, tuple[str | list[str] | dict, FieldStatus]] = {
        "source_strictness": (
            _confirmed_knowledge_policy_value(session.policy),
            FieldStatus.RESOLVED,
        ),
        "private_sources": (
            [
                "private student data",
                "consent records",
                "raw transcripts",
                "private forum exports",
            ],
            FieldStatus.RESOLVED,
        ),
        "sensitive_data": (
            "Sensitive data remains excluded; only synthetic examples are used.",
            FieldStatus.RESOLVED,
        ),
        "integrity": (
            _field_value_as_signal(session.policy, "academic_integrity_policy"),
            FieldStatus.RESOLVED,
        ),
        "professor_release_approval": ("approved", FieldStatus.RESOLVED),
    }
    field_id_by_item = {
        "source_strictness": "knowledge_source_policy",
        "private_sources": "disallowed_private_sources",
        "sensitive_data": "sensitive_data_handling",
        "integrity": "academic_integrity_policy",
        "professor_release_approval": "professor_release_approval",
    }

    field_id = field_id_by_item.get(item_id)
    update = field_updates.get(item_id)
    if field_id is None or update is None:
        return

    field = find_policy_field(session.policy, field_id)
    if field is None:
        return
    field.value, field.status = update
    if field.status == FieldStatus.RESOLVED:
        field.warning = None


def _confirmed_knowledge_policy_value(policy: TutorPolicy) -> dict:
    field = find_policy_field(policy, "knowledge_source_policy")
    if field is not None and isinstance(field.value, dict):
        value = dict(field.value)
    else:
        value = KnowledgeSourcePolicy().model_dump(mode="json")
    value["source_strictness"] = (
        value.get("source_strictness")
        if value.get("source_strictness") != "unresolved"
        else "any_source_with_labels"
    )
    value["confirmed"] = True
    return value


def _sync_preview_checklist(
    session: OnboardingSession,
    preview_case_id: str,
    decision: PreviewDecisionValue,
) -> None:
    if decision != "accepted":
        return
    checklist_id_by_preview = {
        "external-grounding": "preview_external_grounding",
        "academic-integrity": "preview_academic_integrity",
    }
    checklist_id = checklist_id_by_preview.get(preview_case_id)
    if preview_case_id.startswith("custom-"):
        checklist_id = "preview_custom_prompt"
    if checklist_id is None:
        return
    for item in session.approval_checklist:
        if item.id == checklist_id:
            item.checked = True
