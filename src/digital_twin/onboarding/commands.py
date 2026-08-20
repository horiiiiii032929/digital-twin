from typing import Any
from uuid import uuid4

from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.onboarding.policy import find_policy_field
from src.digital_twin.onboarding.preview import (
    _build_custom_preview_case,
    _decision_record_for,
    _field_value_as_signal,
    _regenerate_previews,
    _snapshot_for,
)
from src.digital_twin.onboarding.release import (
    _invalidate_release_approval,
    _recompute_release_state,
    _uncheck_approval_items,
)
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


def bind_session_to_course(
    session: OnboardingSession,
    course_id: str,
) -> OnboardingSession:
    normalized_course_id = course_id.strip()
    if not normalized_course_id:
        raise ValueError("course_id_required")
    if session.course_id not in {None, normalized_course_id}:
        raise ValueError("onboarding_course_scope_mismatch")
    if session.course_id == normalized_course_id:
        return session.model_copy(deep=True)

    updated = session.model_copy(deep=True)
    updated.course_id = normalized_course_id
    _invalidate_source_review(updated)
    _recompute_release_state(updated)
    return updated


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
    _invalidate_source_review(updated)
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
            _invalidate_source_review(updated)
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
            normalized_value = _validated_policy_value(field_id, value, status)
            changed = field.value != normalized_value or field.status != status
            field.value = normalized_value
            field.status = status
            if status == FieldStatus.RESOLVED:
                field.warning = None
            if changed and field_id != "professor_release_approval":
                updated.policy_version += 1
                _regenerate_previews(updated)
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
            policy_before = (
                updated.policy.model_dump(mode="json")
                if updated.policy is not None
                else None
            )
            item.checked = checked
            _sync_policy_from_approval(updated, item_id, checked)
            policy_after = (
                updated.policy.model_dump(mode="json")
                if updated.policy is not None
                else None
            )
            if (
                policy_before != policy_after
                and item_id != "professor_release_approval"
            ):
                updated.policy_version += 1
                _regenerate_previews(updated)
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
            existing = updated.preview_decisions.get(preview_case_id)
            changed = (
                existing is None
                or existing.decision != decision
                or existing.reason != reason
                or existing.policy_version != updated.policy_version
            )
            preview.decision = decision
            preview.decision_reason = reason
            updated.preview_decisions[preview_case_id] = PreviewDecisionRecord(
                preview_case_id=preview_case_id,
                decision=decision,
                reason=reason,
                policy_version=updated.policy_version,
            )
            updated.evidence_snapshots.append(_snapshot_for(preview))
            if changed:
                _invalidate_release_approval(updated)
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
    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise ValueError("custom_preview_prompt_required")

    custom_count = sum(
        1 for preview in updated.preview_cases if preview.id.startswith("custom-")
    )
    if custom_count >= 20:
        raise ValueError("custom_preview_limit_reached")
    preview = _build_custom_preview_case(
        case_id=f"custom-{custom_count + 1}",
        prompt=normalized_prompt,
        tag=tag,
        policy=updated.policy,
        policy_version=updated.policy_version,
    )
    updated.preview_cases.append(preview)
    updated.preview_decisions[preview.id] = _decision_record_for(preview)
    updated.evidence_snapshots.append(_snapshot_for(preview))
    _uncheck_approval_items(updated, frozenset({"preview_custom_prompt"}))
    _invalidate_release_approval(updated)
    _recompute_release_state(updated)
    return updated




def _sync_policy_from_approval(
    session: OnboardingSession,
    item_id: str,
    checked: bool,
) -> None:
    if session.policy is None:
        return

    if not checked:
        field_id_by_item = {
            "source_strictness": "knowledge_source_policy",
            "private_sources": "disallowed_private_sources",
            "sensitive_data": "sensitive_data_handling",
            "integrity": "academic_integrity_policy",
            "professor_release_approval": "professor_release_approval",
        }
        field = find_policy_field(session.policy, field_id_by_item.get(item_id, ""))
        if field is None:
            return
        if item_id == "source_strictness" and isinstance(field.value, dict):
            field.value = {**field.value, "confirmed": False}
        if item_id == "professor_release_approval":
            field.value = "pending"
        field.status = (
            FieldStatus.NEEDS_REVIEW
            if item_id == "integrity"
            else FieldStatus.BLOCKS_RELEASE
        )
        field.warning = "Professor confirmation is required."
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
            if checklist_id == "preview_custom_prompt":
                custom_ids = {
                    preview.id
                    for preview in session.preview_cases
                    if preview.id.startswith("custom-")
                }
                item.checked = bool(custom_ids) and all(
                    session.preview_decisions.get(case_id) is not None
                    and session.preview_decisions[case_id].decision == "accepted"
                    and session.preview_decisions[case_id].policy_version
                    == session.policy_version
                    for case_id in custom_ids
                )
            else:
                item.checked = decision == "accepted"


def _invalidate_source_review(session: OnboardingSession) -> None:
    _uncheck_approval_items(
        session,
        frozenset({"source_scope", "private_sources"}),
    )
    _invalidate_release_approval(session)


def _validated_policy_value(
    field_id: str,
    value: str | list[str] | dict,
    status: FieldStatus,
) -> str | list[str] | dict:
    if isinstance(value, str):
        normalized: str | list[str] | dict = value.strip()
    elif isinstance(value, list):
        normalized = [item.strip() for item in value if item.strip()]
    else:
        normalized = dict(value)

    if status == FieldStatus.RESOLVED and not normalized:
        raise ValueError("resolved_policy_value_required")

    if field_id == "knowledge_source_policy":
        policy = KnowledgeSourcePolicy.model_validate(normalized)
        if status == FieldStatus.RESOLVED and (
            not policy.confirmed
            or policy.source_strictness == "unresolved"
            or policy.source_strictness not in policy.allowed_values
            or not policy.external_sources_require_visible_labels
        ):
            raise ValueError("knowledge_source_policy_not_confirmed")
        return policy.model_dump(mode="json")

    if field_id == "disallowed_private_sources" and status == FieldStatus.RESOLVED:
        if not isinstance(normalized, list):
            raise ValueError("private_source_exclusions_required")
        required = {
            "private student data",
            "consent records",
            "raw transcripts",
            "private forum exports",
        }
        if not required.issubset({item.lower() for item in normalized}):
            raise ValueError("private_source_exclusions_required")

    if (
        field_id == "professor_release_approval"
        and status == FieldStatus.RESOLVED
        and normalized != "approved"
    ):
        raise ValueError("explicit_professor_approval_required")

    return normalized
