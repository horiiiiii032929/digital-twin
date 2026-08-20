"""Compatibility facade for the modular onboarding domain package."""

from src.digital_twin.onboarding import (
    InMemorySessionRepository,
    OnboardingSession,
    SessionRepository,
    add_custom_preview_case,
    add_source_inventory_item,
    bind_session_to_course,
    confirm_revision_proposal,
    create_session,
    create_supervisor_demo_session,
    discard_revision_proposal,
    set_preview_decision,
    submit_message,
    update_approval_checklist_item,
    update_policy_field_value,
    update_source_inventory_item,
)

__all__ = [
    "InMemorySessionRepository",
    "OnboardingSession",
    "SessionRepository",
    "add_custom_preview_case",
    "add_source_inventory_item",
    "bind_session_to_course",
    "confirm_revision_proposal",
    "create_session",
    "create_supervisor_demo_session",
    "discard_revision_proposal",
    "set_preview_decision",
    "submit_message",
    "update_approval_checklist_item",
    "update_policy_field_value",
    "update_source_inventory_item",
]
