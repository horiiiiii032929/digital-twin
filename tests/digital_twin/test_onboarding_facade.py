import pytest

from src.digital_twin import onboarding_workflow
from src.digital_twin.onboarding import (
    InMemorySessionRepository,
    OnboardingSession,
    ScopedSessionRepository,
    SessionWriteConflictError,
    SQLiteSessionRepository,
    confirm_revision_proposal,
    create_session,
    submit_message,
)


def test_compatibility_facade_exports_existing_onboarding_api() -> None:
    expected_exports = {
        "OnboardingSession",
        "add_custom_preview_case",
        "add_source_inventory_item",
        "confirm_revision_proposal",
        "create_session",
        "discard_revision_proposal",
        "set_preview_decision",
        "submit_message",
        "update_approval_checklist_item",
        "update_policy_field_value",
        "update_source_inventory_item",
    }

    assert expected_exports.issubset(set(onboarding_workflow.__all__))
    assert onboarding_workflow.create_session is create_session
    assert onboarding_workflow.OnboardingSession is OnboardingSession


def test_sqlite_repository_preserves_revision_history_across_restart(tmp_path) -> None:
    path = tmp_path / "onboarding-history.sqlite3"
    repository = SQLiteSessionRepository(path)
    session = create_session(session_id="history-session")
    for answer in (
        "Use syllabus, slides, assignments, and rubrics only.",
        "Balance concise explanations with guiding questions.",
        "Ask what the student tried first, then give hints.",
        "Correct directly, then show a contrastive example.",
        "Reject full graded-work answers and unapproved sources.",
    ):
        session = submit_message(session, answer)
    session = submit_message(session, "The tone should be friendlier.")
    session = confirm_revision_proposal(session)
    repository.save(session)
    repository.close()

    reopened = SQLiteSessionRepository(path)
    restored = reopened.get("history-session")
    assert restored is not None
    assert restored.policy_version == 2
    assert restored.revision_history[-1].status == "confirmed"
    reopened.close()


def test_in_memory_repository_isolates_saved_session_state() -> None:
    repository = InMemorySessionRepository()
    session = create_session(session_id="repository-session")

    saved = repository.save(session)
    saved.current_step = "changed-outside-repository"

    restored = repository.get("repository-session")
    assert restored is not None
    assert restored.current_step == "source_permissions"

    restored.current_step = "changed-after-read"
    assert repository.get("repository-session").current_step == "source_permissions"

    repository.clear()
    assert repository.get("repository-session") is None


@pytest.mark.parametrize("repository_kind", ["memory", "sqlite"])
def test_session_repository_rejects_stale_snapshot(tmp_path, repository_kind) -> None:
    repository = (
        InMemorySessionRepository()
        if repository_kind == "memory"
        else SQLiteSessionRepository(tmp_path / "onboarding.sqlite3")
    )
    first = repository.save(create_session(session_id="session-race"))
    stale = repository.get(first.session_id)
    current = repository.get(first.session_id)
    assert stale is not None and current is not None

    current.current_step = "teaching_approach"
    saved = repository.save(current)
    stale.current_step = "academic_integrity"

    with pytest.raises(SessionWriteConflictError):
        repository.save(stale)

    assert repository.get(first.session_id) == saved
    if isinstance(repository, SQLiteSessionRepository):
        repository.close()


@pytest.mark.parametrize("repository_kind", ["memory", "sqlite"])
def test_scoped_session_repository_cannot_take_over_existing_owner(
    tmp_path,
    repository_kind,
) -> None:
    repository = (
        InMemorySessionRepository()
        if repository_kind == "memory"
        else SQLiteSessionRepository(tmp_path / "owned-onboarding.sqlite3")
    )
    if isinstance(repository, SQLiteSessionRepository):
        with repository._connection:
            repository._connection.executemany(
                "INSERT INTO accounts (id, role, status) VALUES (?, 'professor', 'active')",
                [("professor-a",), ("professor-b",)],
            )
    owner_a = ScopedSessionRepository(repository, "professor-a")
    owner_b = ScopedSessionRepository(repository, "professor-b")
    created = owner_a.save(create_session(session_id="owned-session"))
    collision = create_session(session_id="owned-session")

    with pytest.raises(PermissionError):
        owner_b.save(collision)

    assert owner_a.get(created.session_id) is not None
    assert owner_b.get(created.session_id) is None
    if isinstance(repository, SQLiteSessionRepository):
        repository.close()
