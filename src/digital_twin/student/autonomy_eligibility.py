"""Deterministic event-scoped action eligibility for governed autonomy.

The professor policy defines the broad set of actions that a course permits.
This module narrows that broad authority to the actions that are semantically
eligible for one durable event.  A model may choose within the resulting
envelope, but it cannot widen it.
"""

from __future__ import annotations

from types import MappingProxyType

from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
)


ACTION_ELIGIBILITY_VERSION = "event-scoped-action-eligibility-v1"


_EVENT_ACTIONS = MappingProxyType(
    {
        AutonomousEventKind.STUDENT_MESSAGE: (
            AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
        ),
        AutonomousEventKind.REPEATED_CONFUSION: (
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
            AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        ),
        AutonomousEventKind.MISCONCEPTION: (
            AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
        ),
        AutonomousEventKind.INCOMPLETE_OBJECTIVE: (
            AutonomousActionKind.SEND_IN_APP_CHECK_IN,
        ),
        AutonomousEventKind.SPACED_REVIEW_DUE: (
            AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE,
        ),
        AutonomousEventKind.STUDENT_INACTIVITY: (
            AutonomousActionKind.SEND_IN_APP_CHECK_IN,
        ),
        AutonomousEventKind.EVIDENCE_RECOVERED: (
            AutonomousActionKind.RECOMMEND_APPROVED_SOURCE,
        ),
        AutonomousEventKind.NEW_COURSE_RELEASE: (
            AutonomousActionKind.RECOMMEND_APPROVED_SOURCE,
        ),
        AutonomousEventKind.PRACTICE_INCOMPLETE: (
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
            AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        ),
        AutonomousEventKind.PROFESSOR_SCHEDULED: (
            AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE,
        ),
        AutonomousEventKind.CONSENT_CHANGED: (),
        AutonomousEventKind.MEMBERSHIP_CHANGED: (),
        AutonomousEventKind.RELEASE_CHANGED: (),
        AutonomousEventKind.POLICY_CHANGED: (),
    }
)


def event_scoped_eligible_actions(
    event_kind: AutonomousEventKind,
    policy_actions: list[AutonomousActionKind],
) -> tuple[AutonomousActionKind, ...]:
    """Return the policy intersection for one event, plus safe no-action.

    Ordering is deterministic and pedagogically meaningful: the first active
    action is the fallback used when a provider response is malformed or tries
    to leave the envelope.  ``NO_ACTION`` is always available because declining
    an intervention never expands professor-granted authority.
    """

    policy_set = set(policy_actions)
    eligible = tuple(
        action for action in _EVENT_ACTIONS[event_kind] if action in policy_set
    )
    return (*eligible, AutonomousActionKind.NO_ACTION)


def preferred_event_action(
    event_kind: AutonomousEventKind,
    policy_actions: list[AutonomousActionKind],
) -> AutonomousActionKind:
    """Return the deterministic event fallback within professor policy."""

    return event_scoped_eligible_actions(event_kind, policy_actions)[0]


def event_action_contract() -> dict[str, list[str]]:
    """Expose the complete inspectable mapping for manifests and tests."""

    return {
        event.value: [action.value for action in actions]
        for event, actions in _EVENT_ACTIONS.items()
    }

