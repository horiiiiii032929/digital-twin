import pytest

from src.digital_twin.onboarding_workflow import (
    add_custom_preview_case,
    add_source_inventory_item,
    confirm_revision_proposal,
    create_session,
    set_preview_decision,
    submit_message,
    update_approval_checklist_item,
    update_policy_field_value,
    update_source_inventory_item,
)
from src.digital_twin.tutor_policy import (
    FieldStatus,
    ReleaseStatus,
    SourceLabel,
    SourcePermissionStatus,
)


def test_create_session_starts_with_source_permissions_prompt():
    session = create_session(session_id="test-session")

    assert session.session_id == "test-session"
    assert session.current_step == "source_permissions"
    assert session.messages[-1].role == "assistant"
    assert "Which course materials" in session.messages[-1].content


def test_vague_answer_gets_follow_up_without_advancing():
    session = create_session(session_id="test-session")

    updated = submit_message(session, "Use all my materials.")

    assert updated.current_step == "source_permissions"
    assert "too broad" in updated.messages[-1].content
    assert updated.trace[-1].status == "warning"


def test_valid_source_answer_stores_answer_advances_and_prompts_teaching_approach():
    session = create_session(session_id="test-session")
    source_answer = "Use syllabus, lecture slides, assignments, and rubrics only."

    updated = submit_message(session, source_answer)

    assert updated.answers["source_permissions"] == source_answer
    assert updated.current_step == "teaching_approach"
    assert updated.messages[-1].role == "assistant"
    assert "When a student asks a conceptual question" in updated.messages[-1].content


def test_submit_message_does_not_mutate_original_session():
    session = create_session(session_id="test-session")
    original_message_count = len(session.messages)
    original_trace_count = len(session.trace)

    updated = submit_message(
        session,
        "Use syllabus, lecture slides, assignments, and rubrics only.",
    )

    assert updated.current_step == "teaching_approach"
    assert session.current_step == "source_permissions"
    assert session.answers == {}
    assert len(session.messages) == original_message_count
    assert len(session.trace) == original_trace_count


def test_blank_answer_gets_warning_without_advancing_or_storing_answer():
    session = create_session(session_id="test-session")

    updated = submit_message(session, "   ")

    assert updated.current_step == "source_permissions"
    assert "source_permissions" not in updated.answers
    assert updated.messages[-1].role == "assistant"
    assert "concrete answer" in updated.messages[-1].content
    assert updated.trace[-1].status == "warning"


def test_concrete_academic_integrity_answer_with_vague_phrase_advances_and_stores():
    session = _advance_to_academic_integrity()
    answer = (
        "Do not cheat by giving full graded answers; ask what they tried first "
        "and give hints only."
    )

    updated = submit_message(session, answer)

    assert updated.current_step == "misconception_handling"
    assert updated.answers["academic_integrity"] == answer
    assert updated.messages[-1].role == "assistant"
    assert "When a student has a wrong idea" in updated.messages[-1].content
    assert updated.trace[-1].id.startswith("academic_integrity-captured")
    assert updated.trace[-1].status == "complete"


def test_repeated_blank_answers_append_unique_trace_ids():
    session = create_session(session_id="test-session")

    first_update = submit_message(session, " ")
    second_update = submit_message(first_update, "")

    warning_ids = [item.id for item in second_update.trace if item.status == "warning"]

    assert second_update.current_step == "source_permissions"
    assert warning_ids == [
        "source_permissions-empty-answer-2",
        "source_permissions-empty-answer-3",
    ]
    assert len(warning_ids) == len(set(warning_ids))


def test_completed_interview_generates_policy_preview_and_approval_items():
    session = _complete_interview()

    assert session.current_step == "professor_approval"
    assert session.policy is not None
    assert session.policy.blocker_ids == [
        "knowledge_source_policy",
        "disallowed_private_sources",
        "sensitive_data_handling",
        "professor_release_approval",
    ]
    field_ids = {field.id for field in session.policy.all_fields}
    assert {
        "approved_source_permissions",
        "disallowed_private_sources",
        "knowledge_source_policy",
        "academic_integrity_policy",
        "sensitive_data_handling",
        "teaching_approach",
        "tutoring_moves",
        "feedback_policy",
        "proactive_support",
        "course_scope_boundary",
        "preferred_examples",
        "rejection_criteria",
        "tone_guidance",
        "professor_release_approval",
    }.issubset(field_ids)
    knowledge_field = next(
        field
        for field in session.policy.safety_compliance
        if field.id == "knowledge_source_policy"
    )
    assert knowledge_field.value["source_strictness"] == "unresolved"
    assert knowledge_field.value["preview_source_mode"] == "any_source_with_labels"
    assert knowledge_field.value["external_sources_require_visible_labels"] is True
    assert knowledge_field.value["source_labels"] == [
        "course-approved",
        "professor-approved-external",
        "system-suggested-trusted",
        "unapproved-external",
    ]
    academic_integrity_field = next(
        field
        for field in session.policy.safety_compliance
        if field.id == "academic_integrity_policy"
    )
    assert academic_integrity_field.status == FieldStatus.NEEDS_REVIEW
    assert (
        academic_integrity_field.warning
        == "Professor should confirm this before student release."
    )
    assert [case.id for case in session.preview_cases] == [
        "external-grounding",
        "academic-integrity",
        "misconception",
    ]
    assert session.policy_version == 1
    assert len(session.evidence_snapshots) == 3
    assert [
        item.id for item in session.approval_checklist if item.blocks_release
    ] == [
        "source_scope",
        "private_sources",
        "source_strictness",
        "integrity",
        "sensitive_data",
        "preview_external_grounding",
        "preview_academic_integrity",
        "preview_custom_prompt",
        "professor_release_approval",
    ]
    assert "Generated draft tutor policy" in [item.title for item in session.trace]
    assert session.messages[-1].role == "assistant"
    assert session.messages[-1].content == (
        "I generated a draft tutor policy and preview comparison. "
        "Review the policy fields, confirm release blockers, then "
        "use the approval checklist."
    )


@pytest.mark.parametrize(
    "vague_answer",
    [
        "Be helpful.",
        "Do not cheat.",
        "Use common sense.",
        "Teach like me.",
        "Use all my materials.",
        "Use the internet if needed.",
        "Make it friendly.",
    ],
)
def test_documented_vague_answers_get_followups_without_advancing(vague_answer):
    session = create_session(session_id="test-session")

    updated = submit_message(session, vague_answer)

    assert updated.current_step == "source_permissions"
    assert updated.messages[-1].role == "assistant"
    assert "too" in updated.messages[-1].content.lower()
    assert updated.trace[-1].status == "warning"


def test_source_inventory_approval_and_exclusion_update_release_blockers():
    session = _complete_interview()

    with_pending_source = add_source_inventory_item(
        session,
        name="week-01-slides.pdf",
        mime_type="application/pdf",
        size_bytes=12345,
    )

    assert with_pending_source.source_inventory[0].permission_status == (
        SourcePermissionStatus.PENDING
    )
    assert with_pending_source.release_blockers["source_inventory"] == [
        "week-01-slides.pdf needs an approve or exclude decision."
    ]

    approved = update_source_inventory_item(
        with_pending_source,
        with_pending_source.source_inventory[0].id,
        permission_status=SourcePermissionStatus.APPROVED,
        source_label=SourceLabel.COURSE_APPROVED,
    )

    assert approved.source_inventory[0].permission_status == (
        SourcePermissionStatus.APPROVED
    )
    assert approved.release_blockers["source_inventory"] == []

    sensitive = add_source_inventory_item(
        approved,
        name="private-student-forum-export.json",
        mime_type="application/json",
        size_bytes=999,
    )

    assert sensitive.source_inventory[-1].sensitive is True
    assert sensitive.source_inventory[-1].excluded is True
    assert sensitive.release_blockers["source_inventory"] == []


def test_preview_generation_includes_source_audit_warnings_decisions_and_evidence():
    session = _complete_interview()

    grounding = next(
        preview for preview in session.preview_cases if preview.id == "external-grounding"
    )

    assert grounding.tag == "source_grounding"
    assert grounding.decision == "pending"
    assert grounding.policy_version == 1
    assert grounding.generated_at is not None
    assert grounding.source_audit[0].source_label in {
        SourceLabel.COURSE_APPROVED,
        SourceLabel.SYSTEM_SUGGESTED_TRUSTED,
    }
    assert grounding.source_audit[0].supports
    assert "Source labels:" in grounding.configured_response
    assert "no course comparison available for conflict checking" in grounding.warnings

    snapshot = next(
        item
        for item in session.evidence_snapshots
        if item.preview_case_id == grounding.id
    )
    assert snapshot.policy_version == 1
    assert snapshot.prompt == grounding.prompt
    assert snapshot.decision == "pending"
    assert snapshot.source_labels == [
        entry.source_label for entry in grounding.source_audit
    ]


def test_rejected_preview_blocks_release_until_revised_or_accepted():
    session = _complete_interview()

    rejected = set_preview_decision(
        session,
        "academic-integrity",
        "rejected",
        reason="Gives away too much structure.",
    )

    assert rejected.preview_decisions["academic-integrity"].decision == "rejected"
    assert rejected.policy.release_status == ReleaseStatus.BLOCKED
    assert rejected.release_blockers["preview_decisions"] == [
        "academic-integrity is rejected and unresolved."
    ]

    accepted = set_preview_decision(
        rejected,
        "academic-integrity",
        "accepted",
        reason="Now follows the homework boundary.",
    )

    assert accepted.preview_decisions["academic-integrity"].decision == "accepted"
    assert accepted.release_blockers["preview_decisions"] == []


def test_missing_custom_preview_has_actionable_release_blocker():
    session = _complete_interview()

    assert "custom-preview preview is not accepted." not in (
        session.release_blockers["preview_acceptance"]
    )
    assert session.release_blockers["preview_acceptance"] == [
        "academic-integrity preview is not accepted.",
        "external-grounding preview is not accepted.",
        "misconception preview is not accepted.",
        "Add and accept a professor custom prompt preview.",
    ]


def test_approval_checklist_persists_and_marks_release_ready_when_blockers_resolved():
    session = _complete_interview()
    session = add_source_inventory_item(
        session,
        name="week-01-slides.pdf",
        mime_type="application/pdf",
        size_bytes=12345,
        permission_status=SourcePermissionStatus.APPROVED,
    )
    session = _resolve_policy_blockers(session)
    session = add_custom_preview_case(
        session,
        prompt="Explain CSRF using only a hint and a guiding question.",
        tag="teaching_behavior",
    )

    for preview in session.preview_cases:
        session = set_preview_decision(session, preview.id, "accepted")
    for item in session.approval_checklist:
        if item.blocks_release:
            session = update_approval_checklist_item(session, item.id, True)

    assert all(
        item.checked for item in session.approval_checklist if item.blocks_release
    )
    assert session.policy.status == ReleaseStatus.APPROVED
    assert session.policy.release_status == ReleaseStatus.APPROVED
    assert all(not blockers for blockers in session.release_blockers.values())


def test_chat_feedback_creates_confirmable_revision_and_regenerates_preview():
    session = _complete_interview()
    session = set_preview_decision(
        session,
        "academic-integrity",
        "rejected",
        reason="The answer gives away too much homework help.",
    )

    proposed = submit_message(
        session,
        "This gives away too much homework help; require one guiding question before hints.",
    )

    assert proposed.revision_proposal is not None
    assert proposed.revision_proposal.preview_case_id == "academic-integrity"
    assert proposed.revision_proposal.affected_policy_fields == [
        "academic_integrity_policy",
        "tutoring_moves",
    ]
    assert "guiding question" in proposed.revision_proposal.proposed_value
    assert "Confirm" in proposed.messages[-1].content

    confirmed = confirm_revision_proposal(proposed)

    assert confirmed.revision_proposal is None
    assert confirmed.policy_version == 2
    assert confirmed.preview_decisions["academic-integrity"].decision == "pending"
    assert confirmed.preview_decisions["academic-integrity"].revision_resolved is True
    assert confirmed.release_blockers["preview_decisions"] == []
    assert any(snapshot.policy_version == 2 for snapshot in confirmed.evidence_snapshots)


def test_submitting_after_completion_preserves_review_state_and_artifacts():
    session = _complete_interview()
    policy = session.policy.model_copy(deep=True)
    preview_cases = [case.model_copy(deep=True) for case in session.preview_cases]
    approval_checklist = [
        item.model_copy(deep=True) for item in session.approval_checklist
    ]

    updated = submit_message(session, "This looks ready for policy review.")

    assert updated.current_step == "professor_approval"
    assert updated.policy == policy
    assert updated.preview_cases == preview_cases
    assert updated.approval_checklist == approval_checklist
    assert updated.messages[-2].role == "instructor"
    assert updated.messages[-2].content == "This looks ready for policy review."
    assert updated.messages[-1].role == "assistant"
    assert "ready for policy review" in updated.messages[-1].content


def _complete_interview():
    session = create_session(session_id="test-session")
    session = submit_message(
        session,
        "Use syllabus, slides, assignments, and rubrics only.",
    )
    session = submit_message(
        session,
        "Balance concise explanations with guiding questions.",
    )
    session = submit_message(
        session,
        "Ask what the student tried first, then give hints.",
    )
    session = submit_message(
        session,
        "Correct directly, then show a contrastive example.",
    )
    return submit_message(
        session,
        "Reject answers that complete graded work or cite unapproved sources.",
    )


def _resolve_policy_blockers(session):
    session = update_policy_field_value(
        session,
        "knowledge_source_policy",
        {
            "source_strictness": "any_source_with_labels",
            "recommended_value": "any_source_with_labels",
            "allowed_values": [
                "course_only",
                "trusted_only",
                "any_source_with_labels",
            ],
            "preview_source_mode": "any_source_with_labels",
            "source_labels": [
                "course-approved",
                "professor-approved-external",
                "system-suggested-trusted",
                "unapproved-external",
            ],
            "trusted_source_allowlist": {
                "professor_defined": [],
                "derived_from_course_materials": [],
            },
            "system_trusted_source_categories": [
                "official_documentation",
                "standards_or_security_bodies",
                "university_pages",
            ],
            "external_sources_require_visible_labels": True,
            "confirmed": True,
            "policy_level": "course",
        },
        FieldStatus.RESOLVED,
    )
    session = update_policy_field_value(
        session,
        "disallowed_private_sources",
        [
            "private student data",
            "consent records",
            "raw transcripts",
            "private forum exports",
        ],
        FieldStatus.RESOLVED,
    )
    session = update_policy_field_value(
        session,
        "sensitive_data_handling",
        "Sensitive data remains excluded; only synthetic examples are used.",
        FieldStatus.RESOLVED,
    )
    session = update_policy_field_value(
        session,
        "academic_integrity_policy",
        "Ask what the student tried first, then provide hints only.",
        FieldStatus.RESOLVED,
    )
    return update_policy_field_value(
        session,
        "professor_release_approval",
        "approved",
        FieldStatus.RESOLVED,
    )


def _advance_to_academic_integrity():
    session = create_session(session_id="test-session")
    session = submit_message(
        session,
        "Use syllabus, slides, assignments, and rubrics only.",
    )
    return submit_message(
        session,
        "Balance concise explanations with guiding questions.",
    )
