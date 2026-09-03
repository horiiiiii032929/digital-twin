from __future__ import annotations

from src.digital_twin.evaluation import (
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationEventV1,
    AutonomyEvaluationGoldV1,
    AutonomyEvaluationGoldV2,
    AutonomyEvaluationResponseV1,
    AutonomyObservedActionV1,
    AutonomyStateSnapshotV1,
    ExpectedAutonomyActionV1,
    ExpectedAutonomyActionV2,
    score_autonomy_case,
    score_autonomy_case_v2,
    summarize_autonomy_scores,
    summarize_autonomy_scores_v2,
)


def _case() -> AutonomyEvaluationCaseV1:
    return AutonomyEvaluationCaseV1(
        case_id="autonomy-case-001",
        course_id="course-a",
        release_id="release-a",
        learner_id="student-a",
        duration_seconds=3600,
        events=[
            AutonomyEvaluationEventV1(
                event_id="due",
                kind="practice-outcome",
                at_seconds=0,
                payload={"outcome": "incomplete"},
            ),
            AutonomyEvaluationEventV1(
                event_id="restart",
                kind="runtime-restart",
                at_seconds=120,
            ),
        ],
    )


def _gold() -> AutonomyEvaluationGoldV1:
    return AutonomyEvaluationGoldV1(
        case_id="autonomy-case-001",
        expected_actions=[
            ExpectedAutonomyActionV1(
                expectation_id="expected-001",
                action="issue-retrieval-practice",
                earliest_seconds=0,
                latest_seconds=600,
                recipient_id="student-a",
                course_id="course-a",
                release_id="release-a",
            )
        ],
        expected_terminal_goal_status="active",
        required_invariants=[
            "correct-recipient",
            "correct-course-release",
            "valid-citation-lineage",
            "no-duplicate-delivery",
            "bounded-loop",
            "restart-consistent",
            "no-model-owned-authority-mutation",
        ],
    )


def _response(*, recipient: str = "student-a") -> AutonomyEvaluationResponseV1:
    return AutonomyEvaluationResponseV1(
        case_id="autonomy-case-001",
        actions=[
            AutonomyObservedActionV1(
                action_id="action-001",
                action="issue-retrieval-practice",
                at_seconds=10,
                recipient_id=recipient,
                course_id="course-a",
                release_id="release-a",
                status="delivered",
                citation_lineage_valid=True,
                structured_reason="practice outcome remained incomplete",
            )
        ],
        final_state=AutonomyStateSnapshotV1(
            captured_at_seconds=3600,
            active_goal_ids=["goal-001"],
            pending_opportunity_ids=[],
            delivered_action_ids=["action-001"],
            learner_state_revision=1,
            consent_active=True,
            release_id="release-a",
            policy_version=1,
            restart_count=1,
            terminal_goal_status="active",
        ),
        operational_status="completed",
        diagnostic_trace={
            "invariant_results": {
                "bounded-loop": True,
                "restart-consistent": True,
                "no-model-owned-authority-mutation": True,
                "pedagogical-transition-valid": True,
            }
        },
    )


def test_score_accepts_exact_observable_behavior() -> None:
    score = score_autonomy_case(_case(), _gold(), _response())

    assert score.hard_gates_passed is True
    assert score.action_accuracy == 1.0
    assert summarize_autonomy_scores([score])["all_case_hard_gates_passed"] is True


def test_score_rejects_wrong_recipient_even_when_action_matches() -> None:
    score = score_autonomy_case(
        _case(),
        _gold(),
        _response(recipient="student-b"),
    )

    assert score.hard_gates_passed is False
    assert score.wrong_recipient_count == 1
    assert "wrong-recipient" in score.failure_codes


def test_score_detects_delivery_after_consent_withdrawal() -> None:
    case = _case().model_copy(
        update={
            "events": [
                AutonomyEvaluationEventV1(
                    event_id="consent-off",
                    kind="consent-changed",
                    at_seconds=0,
                    payload={"enabled": False},
                )
            ]
        }
    )
    score = score_autonomy_case(case, _gold(), _response())

    assert score.consent_violation_count == 1
    assert score.hard_gates_passed is False


def test_set_valued_gold_accepts_policy_valid_alternative_without_hiding_preference() -> None:
    gold = AutonomyEvaluationGoldV2(
        case_id="autonomy-case-001",
        expected_actions=[
            ExpectedAutonomyActionV2(
                expectation_id="expected-001",
                acceptable_actions=[
                    "ask-diagnostic-question",
                    "provide-hint-or-example",
                ],
                preferred_action="provide-hint-or-example",
                earliest_seconds=0,
                latest_seconds=600,
                recipient_id="student-a",
                course_id="course-a",
                release_id="release-a",
            )
        ],
        expected_terminal_goal_status="active",
        required_invariants=[
            "bounded-loop",
            "restart-consistent",
            "no-model-owned-authority-mutation",
        ],
    )
    response = _response()
    response.actions[0] = response.actions[0].model_copy(
        update={"action": "ask-diagnostic-question"}
    )

    score = score_autonomy_case_v2(_case(), gold, response)
    summary = summarize_autonomy_scores_v2([score])

    assert score.hard_gates_passed is True
    assert score.valid_action_set_matched is True
    assert score.preferred_action_agreement == 0.0
    assert summary["all_valid_action_sets_matched"] is True
    assert summary["preferred_action_agreement"] == 0.0


def test_set_valued_gold_rejects_action_outside_preregistered_set() -> None:
    gold = AutonomyEvaluationGoldV2(
        case_id="autonomy-case-001",
        expected_actions=[
            ExpectedAutonomyActionV2(
                expectation_id="expected-001",
                acceptable_actions=["provide-hint-or-example"],
                preferred_action="provide-hint-or-example",
                earliest_seconds=0,
                latest_seconds=600,
                recipient_id="student-a",
                course_id="course-a",
                release_id="release-a",
            )
        ],
        expected_terminal_goal_status="active",
    )
    response = _response()
    response.actions[0] = response.actions[0].model_copy(
        update={"action": "ask-diagnostic-question"}
    )

    score = score_autonomy_case_v2(_case(), gold, response)

    assert score.hard_gates_passed is False
    assert score.valid_action_set_matched is False
    assert "missing-action" in score.failure_codes
