from src.digital_twin.tutor_policy import (
    ApprovalItem,
    FieldStatus,
    PolicyField,
    ReleaseStatus,
    TutorPolicy,
    build_initial_policy,
)


def test_initial_policy_blocks_release_until_source_and_approval_are_resolved():
    policy = build_initial_policy()

    assert policy.release_status == ReleaseStatus.BLOCKED
    assert "approved_source_permissions" in policy.blocker_ids
    assert "professor_release_approval" in policy.blocker_ids


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
