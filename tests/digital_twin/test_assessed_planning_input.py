from datetime import UTC, datetime, timedelta

import pytest

from src.digital_twin.student.assessed_planning_input import build_assessed_planning_evidence
from src.digital_twin.student.autonomy_models import LearnerObservationV2, TurnPerceptionV2
from src.digital_twin.student.learner_estimators import EvidenceCountEstimator, BktEstimator, PfaEstimator

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def observation(identifier="one", outcome="correct", **changes):
    values = dict(observation_id=identifier, learner_key="a" * 64,
        course_id="course", release_id="release", event_kind="student-message",
        concept_ids=["cache"], assessment_concept_ids=["cache"],
        assessment_outcome=outcome, assessment_confidence=.8,
        source_turn_key="turn-" + identifier, evidence_keys=["approved-range"],
        perception=TurnPerceptionV2(event_kind="student-message", request_type="attempt", attempt_present=True),
        observed_at=(NOW - timedelta(days=1)).isoformat())
    values.update(changes)
    return LearnerObservationV2(**values)


def build(rows, estimator=None):
    return build_assessed_planning_evidence(rows, learner_key="a" * 64,
        course_id="course", release_id="release", concept_id="cache", now=NOW,
        estimator=estimator or EvidenceCountEstimator())


def test_assessment_direction_and_missing_data_are_distinct():
    missing = build([])
    assert missing.estimate.probability == .5
    assert missing.estimate.evidence_count == 0
    assert missing.days_since_last_observation is None
    assert build([observation()]).estimate.probability > .5
    incorrect = build([observation(outcome="incorrect")])
    assert incorrect.estimate.probability < .5
    assert incorrect.recent_incorrect_streak == 1
    assert incorrect.days_since_last_observation == 1


@pytest.mark.parametrize("estimator", [EvidenceCountEstimator(), BktEstimator(), PfaEstimator()])
def test_order_and_duplicate_delivery_cannot_change_the_evidence(estimator):
    earlier = observation("earlier", "incorrect", observed_at=(NOW - timedelta(days=2)).isoformat())
    later = observation("later", "correct")
    result = build([later, earlier, later], estimator)
    assert result == build([earlier, later], estimator)
    assert result.estimate.evidence_count == 2
    assert result.recent_incorrect_streak == 0


@pytest.mark.parametrize("changes,reason", [
    ({"assessment_outcome": "partial"}, "not-a-binary-assessment"),
    ({"assessment_outcome": "not-assessed", "assessment_concept_ids": []}, "concept-not-assessed"),
    ({"assessment_concept_ids": None}, "legacy-assessment-scope-unspecified"),
    ({"concept_ids": ["cache", "memory"], "assessment_concept_ids": ["memory"]}, "concept-not-assessed"),
    ({"evidence_keys": []}, "assessment-evidence-missing"),
    ({"source_turn_key": None}, "assessment-turn-missing"),
    ({"assessment_confidence": 0}, "assessment-confidence-insufficient"),
    ({"observed_at": (NOW + timedelta(days=1)).isoformat()}, "future-observation"),
])
def test_ineligible_observations_do_not_become_successes_or_failures(changes, reason):
    result = build([observation(**changes)])
    assert result.estimate.evidence_count == 0
    assert result.excluded_observations == (("one", reason),)


@pytest.mark.parametrize("changes", [{"learner_key": "b" * 64}, {"course_id": "other"}, {"release_id": "old"}])
def test_mixed_scope_is_rejected(changes):
    with pytest.raises(ValueError, match="authorized planning scope"):
        build([observation(**changes)])


def test_conflicting_duplicates_and_naive_time_are_rejected():
    with pytest.raises(ValueError, match="conflicting duplicate"):
        build([observation(), observation(outcome="incorrect")])
    with pytest.raises(ValueError, match="timezone-aware"):
        build([observation(observed_at="2026-09-07T12:00:00")])


def test_distinct_observation_ids_cannot_count_the_same_turn_twice():
    first = observation("one")
    duplicate = first.model_copy(update={"observation_id": "two"})
    result = build([first, duplicate])
    assert result.estimate.evidence_count == 1
    assert result.excluded_observations == (("two", "duplicate-source-turn"),)
    conflicting = duplicate.model_copy(update={"assessment_outcome": "incorrect"})
    with pytest.raises(ValueError, match="conflicting duplicate source-turn"):
        build([first, conflicting])


@pytest.mark.parametrize("estimator", [EvidenceCountEstimator(), BktEstimator(), PfaEstimator()])
def test_equal_time_contradictions_cannot_invent_an_observation_order(estimator):
    rows = [observation("first", "incorrect"), observation("second", "correct")]
    result = build(rows, estimator)
    assert result.estimate.evidence_count == 0
    assert result.recent_incorrect_streak == 0
    assert len(result.excluded_observations) == 2
    assert all(reason == "ambiguous-equal-time-assessments" for _, reason in result.excluded_observations)
