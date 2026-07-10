from src.digital_twin.tutor_policy import (
    ApprovalItem,
    FieldStatus,
    SourceInventoryItem,
    SourcePermissionStatus,
    PolicyField,
    ReleaseStatus,
    SourceLabel,
    TutorPolicy,
    build_initial_policy,
)


def test_initial_policy_blocks_release_until_source_and_approval_are_resolved():
    policy = build_initial_policy()

    assert policy.release_status == ReleaseStatus.BLOCKED
    assert set(policy.blocker_ids) == {
        "approved_source_permissions",
        "disallowed_private_sources",
        "knowledge_source_policy",
        "sensitive_data_handling",
        "professor_release_approval",
    }


def test_resolved_policy_field_is_not_a_blocker():
    field = PolicyField(
        id="approved_source_permissions",
        label="Approved source permissions",
        status=FieldStatus.RESOLVED,
        value=["syllabus", "slides"],
    )

    assert field.blocks_release is False


def test_checked_blocking_approval_item_is_complete():
    item = ApprovalItem(
        id="course_scope",
        label="Course scope confirmed",
        blocks_release=True,
        checked=True,
    )

    assert item.is_blocking_incomplete is False


def test_unchecked_blocking_approval_item_is_incomplete():
    item = ApprovalItem(
        id="course_scope",
        label="Course scope confirmed",
        blocks_release=True,
        checked=False,
    )

    assert item.is_blocking_incomplete is True


def test_unchecked_non_blocking_approval_item_is_complete():
    item = ApprovalItem(
        id="course_scope",
        label="Course scope confirmed",
        blocks_release=False,
        checked=False,
    )

    assert item.is_blocking_incomplete is False


def test_source_inventory_flags_sensitive_names_as_excluded_by_default():
    item = SourceInventoryItem(
        id="source-1",
        name="student-transcripts.csv",
        mime_type="text/csv",
        size_bytes=2048,
    )

    assert item.sensitive is True
    assert item.excluded is True
    assert item.permission_status == SourcePermissionStatus.EXCLUDED
    assert item.source_label == SourceLabel.COURSE_APPROVED
