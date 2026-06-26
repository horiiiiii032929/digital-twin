from src.digital_twin.onboarding_workflow import create_session, submit_message
from src.digital_twin.tutor_policy import FieldStatus


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
        "sensitive_data_handling",
        "professor_release_approval",
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
        "csrf-homework",
        "csrf-misconception",
    ]
    assert [
        item.id for item in session.approval_checklist if item.blocks_release
    ] == [
        "source_scope",
        "privacy",
        "integrity",
    ]
    assert "Generated draft tutor policy" in [item.title for item in session.trace]
    assert session.messages[-1].role == "assistant"
    assert session.messages[-1].content == (
        "I generated a draft tutor policy and preview comparison. "
        "Review the policy fields, confirm release blockers, then "
        "use the approval checklist."
    )


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
