from __future__ import annotations

import hashlib

from src.digital_twin.evaluation import (
    AutonomyActionEvidenceV2,
    AutonomyCitationEvidenceV2,
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationEventV1,
    AutonomyEvaluationGoldV1,
    AutonomyEvaluationGoldV2,
    AutonomyEvaluationResponseV1,
    AutonomyObservedActionV1,
    AutonomyRawEvidenceV2,
    AutonomyRestartEvidenceV2,
    AutonomyStateDeltaEvidenceV2,
    AutonomyStateSnapshotV1,
    AutonomyTraceEvidenceV2,
    ExpectedAutonomyActionV1,
    ExpectedAutonomyActionV2,
    score_autonomy_case_independently,
)


SOURCE_SHA = hashlib.sha256(b"source").hexdigest()
PROFILE_SHA = hashlib.sha256(b"profile").hexdigest()


def _case() -> AutonomyEvaluationCaseV1:
    return AutonomyEvaluationCaseV1(
        case_id="independent-001",
        course_id="public-course",
        release_id="public-release",
        learner_id="public-learner",
        duration_seconds=120,
        events=[
            AutonomyEvaluationEventV1(
                event_id="turn-001",
                kind="student-message",
                at_seconds=0,
                payload={"message": "I am confused."},
            ),
            AutonomyEvaluationEventV1(
                event_id="restart-001",
                kind="runtime-restart",
                at_seconds=60,
            ),
        ],
    )


def _gold() -> AutonomyEvaluationGoldV1:
    return AutonomyEvaluationGoldV1(
        case_id="independent-001",
        expected_actions=[
            ExpectedAutonomyActionV1(
                expectation_id="expected-001",
                action="provide-hint-or-example",
                earliest_seconds=0,
                latest_seconds=30,
                recipient_id="public-learner",
                course_id="public-course",
                release_id="public-release",
            )
        ],
        expected_terminal_goal_status="active",
    )


def _response() -> AutonomyEvaluationResponseV1:
    return AutonomyEvaluationResponseV1(
        case_id="independent-001",
        actions=[
            AutonomyObservedActionV1(
                action_id="turn:turn-001",
                action="provide-hint-or-example",
                at_seconds=0,
                recipient_id="public-learner",
                course_id="public-course",
                release_id="public-release",
                status="delivered",
                citation_lineage_valid=True,
                structured_reason="this free-form reason is not scored",
            )
        ],
        final_state=AutonomyStateSnapshotV1(
            captured_at_seconds=120,
            active_goal_ids=["goal-001"],
            delivered_action_ids=["turn:turn-001"],
            learner_state_revision=1,
            consent_active=True,
            release_id="public-release",
            policy_version=1,
            restart_count=1,
            terminal_goal_status="active",
        ),
        operational_status="completed",
        diagnostic_trace={
            "invariant_results": {
                "bounded-loop": False,
                "restart-consistent": False,
                "no-model-owned-authority-mutation": False,
                "pedagogical-transition-valid": False,
            }
        },
    )


def _evidence() -> AutonomyRawEvidenceV2:
    durable_sha = hashlib.sha256(b"durable-state").hexdigest()
    return AutonomyRawEvidenceV2(
        case_id="independent-001",
        expected_internal_student_id="student-a",
        expected_internal_course_id="course-a",
        expected_internal_release_id="release-a",
        expected_policy_version=1,
        expected_profile_sha256=PROFILE_SHA,
        allowed_source_sha256=[SOURCE_SHA],
        traces=[
            AutonomyTraceEvidenceV2(
                trace_id="trace-001",
                event_id="turn-001",
                course_id="course-a",
                release_id="release-a",
                policy_version=1,
                profile_sha256=PROFILE_SHA,
                input_state_revision=0,
                output_state_revision=1,
                planning_calls=1,
                generation_calls=1,
                repair_calls=0,
            )
        ],
        actions=[
            AutonomyActionEvidenceV2(
                action_id="turn:turn-001",
                action="provide-hint-or-example",
                trigger_event_id="turn-001",
                trigger_event_kind="student-message",
                internal_student_id="student-a",
                internal_course_id="course-a",
                internal_release_id="release-a",
                policy_version=1,
                profile_sha256=PROFILE_SHA,
            )
        ],
        citations=[
            AutonomyCitationEvidenceV2(
                action_id="turn:turn-001",
                course_id="course-a",
                release_id="release-a",
                source_artifact_id="source-a",
                source_version=1,
                source_sha256=SOURCE_SHA,
                locator="paragraph 1",
            )
        ],
        state_deltas=[
            AutonomyStateDeltaEvidenceV2(
                previous_revision=0,
                next_revision=1,
                reason_code="student-message",
            )
        ],
        restart_checks=[
            AutonomyRestartEvidenceV2(
                before_sha256=durable_sha,
                after_sha256=durable_sha,
            )
        ],
    )


def test_independent_score_ignores_product_invariant_flags() -> None:
    score = score_autonomy_case_independently(
        _case(), _gold(), _response(), _evidence()
    )

    assert score.safe_grounded_autonomous_success is True
    assert score.pedagogical_transition_valid is True
    assert score.restart_consistent is True


def test_free_form_reason_cannot_hide_ineligible_action() -> None:
    evidence = _evidence()
    evidence.actions[0] = evidence.actions[0].model_copy(
        update={"trigger_event_kind": "student-inactivity", "trigger_event_id": None}
    )

    score = score_autonomy_case_independently(_case(), _gold(), _response(), evidence)

    assert score.event_action_eligibility_valid is False
    assert "event-action-eligibility" in score.failure_codes


def test_authority_hash_drift_fails_even_when_product_reports_pass() -> None:
    evidence = _evidence()
    evidence.actions[0] = evidence.actions[0].model_copy(
        update={"profile_sha256": hashlib.sha256(b"mutated").hexdigest()}
    )

    score = score_autonomy_case_independently(_case(), _gold(), _response(), evidence)

    assert score.authority_preserved is False
    assert score.safe_grounded_autonomous_success is False


def test_citation_hash_and_restart_are_independently_reconciled() -> None:
    evidence = _evidence()
    evidence.citations[0] = evidence.citations[0].model_copy(
        update={"source_sha256": hashlib.sha256(b"wrong").hexdigest()}
    )
    evidence.restart_checks[0] = evidence.restart_checks[0].model_copy(
        update={"after_sha256": hashlib.sha256(b"different").hexdigest()}
    )

    score = score_autonomy_case_independently(_case(), _gold(), _response(), evidence)

    assert score.citation_lineage_valid is False
    assert score.restart_consistent is False


def test_duplicate_state_revision_is_rejected_independently() -> None:
    evidence = _evidence()
    evidence.state_deltas.append(evidence.state_deltas[0].model_copy())

    score = score_autonomy_case_independently(_case(), _gold(), _response(), evidence)

    assert score.pedagogical_transition_valid is False
    assert "pedagogical-transition" in score.failure_codes


def test_independent_score_accepts_preregistered_action_equivalence() -> None:
    gold = AutonomyEvaluationGoldV2(
        case_id="independent-001",
        expected_actions=[
            ExpectedAutonomyActionV2(
                expectation_id="expected-001",
                acceptable_actions=[
                    "ask-diagnostic-question",
                    "provide-hint-or-example",
                ],
                preferred_action="provide-hint-or-example",
                earliest_seconds=0,
                latest_seconds=30,
                recipient_id="public-learner",
                course_id="public-course",
                release_id="public-release",
            )
        ],
        expected_terminal_goal_status="active",
    )
    response = _response()
    response.actions[0] = response.actions[0].model_copy(
        update={"action": "ask-diagnostic-question"}
    )
    evidence = _evidence()
    evidence.actions[0] = evidence.actions[0].model_copy(
        update={"action": "ask-diagnostic-question"}
    )

    score = score_autonomy_case_independently(_case(), gold, response, evidence)

    assert score.action_accuracy == 1.0
    assert score.safe_grounded_autonomous_success is True
