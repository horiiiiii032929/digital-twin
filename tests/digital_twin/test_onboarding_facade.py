from src.digital_twin import onboarding_workflow
from src.digital_twin.onboarding import (
    InMemorySessionRepository,
    OnboardingSession,
    create_session,
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
