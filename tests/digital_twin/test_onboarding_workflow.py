from src.digital_twin.onboarding_workflow import create_session, submit_message


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


def test_completed_interview_generates_policy_preview_and_approval_items():
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
    session = submit_message(
        session,
        "Reject answers that complete graded work or cite unapproved sources.",
    )

    assert session.current_step == "professor_approval"
    assert session.policy is not None
    assert session.preview_cases
    assert session.approval_checklist
    assert "Generated draft tutor policy" in [item.title for item in session.trace]
