from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
    event_action_contract,
    event_scoped_eligible_actions,
    preferred_event_action,
)
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
)


ALL_POLICY_ACTIONS = list(AutonomousActionKind)


def test_event_action_contract_is_total_and_versioned() -> None:
    contract = event_action_contract()

    assert ACTION_ELIGIBILITY_VERSION == "event-scoped-action-eligibility-v1"
    assert set(contract) == {event.value for event in AutonomousEventKind}
    assert contract[AutonomousEventKind.INCOMPLETE_OBJECTIVE.value] == [
        AutonomousActionKind.SEND_IN_APP_CHECK_IN.value
    ]
    assert contract[AutonomousEventKind.STUDENT_INACTIVITY.value] == [
        AutonomousActionKind.SEND_IN_APP_CHECK_IN.value
    ]
    assert contract[AutonomousEventKind.CONSENT_CHANGED.value] == []


def test_event_envelope_intersects_professor_policy_and_keeps_no_action() -> None:
    eligible = event_scoped_eligible_actions(
        AutonomousEventKind.REPEATED_CONFUSION,
        [AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION],
    )

    assert eligible == (
        AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        AutonomousActionKind.NO_ACTION,
    )
    assert preferred_event_action(
        AutonomousEventKind.INCOMPLETE_OBJECTIVE,
        [AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE],
    ) == AutonomousActionKind.NO_ACTION


def test_proactive_event_defaults_are_exact_and_policy_bounded() -> None:
    expected = {
        AutonomousEventKind.INCOMPLETE_OBJECTIVE: (
            AutonomousActionKind.SEND_IN_APP_CHECK_IN
        ),
        AutonomousEventKind.STUDENT_INACTIVITY: (
            AutonomousActionKind.SEND_IN_APP_CHECK_IN
        ),
        AutonomousEventKind.SPACED_REVIEW_DUE: (
            AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE
        ),
        AutonomousEventKind.EVIDENCE_RECOVERED: (
            AutonomousActionKind.RECOMMEND_APPROVED_SOURCE
        ),
        AutonomousEventKind.NEW_COURSE_RELEASE: (
            AutonomousActionKind.RECOMMEND_APPROVED_SOURCE
        ),
        AutonomousEventKind.PRACTICE_INCOMPLETE: (
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
        ),
        AutonomousEventKind.PROFESSOR_SCHEDULED: (
            AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE
        ),
    }

    for event, action in expected.items():
        assert preferred_event_action(event, ALL_POLICY_ACTIONS) == action

