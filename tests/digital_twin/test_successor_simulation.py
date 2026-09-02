"""Tests for the network-free successor simulation: simulator, estimators, policies, harness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.digital_twin.evaluation.learner_simulator import (
    DEFAULT_CONCEPTS,
    PERSONAS,
    LearnerSimulator,
    MoveKind,
    SimulatorFamily,
)
from src.digital_twin.evaluation.successor_simulation import (
    CONDITIONS,
    ProgramConfig,
    run_learner,
    run_program,
)
from src.digital_twin.student.intervention_policies import (
    ConceptView,
    EligibilityConfig,
    EligibilityGate,
    PolicyInputs,
    ReasonCode,
    SentMessage,
    build_policy,
)
from src.digital_twin.student.learner_estimators import (
    AssessedObservation,
    BktEstimator,
    ConceptEstimate,
    EvidenceCountEstimator,
    PfaEstimator,
    build_estimator,
)

NOW = datetime(2026, 9, 10, 10, 0, tzinfo=UTC)


# ---------------------------------------------------------------- simulator
def test_simulator_is_deterministic_under_seed() -> None:
    def trajectory() -> list[tuple[str, bool]]:
        sim = LearnerSimulator(persona=PERSONAS[0], family=SimulatorFamily.BKT_LIKE, seed=7)
        out = []
        for _ in range(15):
            sim.advance_one_day()
            attempt = sim.self_directed_activity()
            if attempt:
                out.append((attempt.concept_id, attempt.correct))
        return out

    assert trajectory() == trajectory()


def test_simulator_families_differ_and_stay_bounded() -> None:
    a = LearnerSimulator(persona=PERSONAS[2], family=SimulatorFamily.BKT_LIKE, seed=3)
    b = LearnerSimulator(persona=PERSONAS[2], family=SimulatorFamily.LOGISTIC_LIKE, seed=3)
    for _ in range(30):
        a.advance_one_day()
        b.advance_one_day()
        a.self_directed_activity()
        b.self_directed_activity()
    for sim in (a, b):
        for concept_id in DEFAULT_CONCEPTS:
            assert 0.0 < sim.hidden_mastery(concept_id) < 1.0
    assert [a.hidden_mastery(c) for c in DEFAULT_CONCEPTS] != [b.hidden_mastery(c) for c in DEFAULT_CONCEPTS]


def test_unwanted_intervention_crowds_out_receptivity() -> None:
    sim = LearnerSimulator(persona=PERSONAS[5], family=SimulatorFamily.BKT_LIKE, seed=1)
    sim.advance_one_day()
    concept = sim.state.concepts[DEFAULT_CONCEPTS[0]]
    concept.mastery = 0.95  # already mastered: message is unwanted
    assert sim.receive_intervention(DEFAULT_CONCEPTS[0], MoveKind.SPACED_REVIEW) is None
    assert not sim.is_receptive(sim.day)


# --------------------------------------------------------------- estimators
def _obs(concept: str, correct: bool, at: datetime) -> AssessedObservation:
    return AssessedObservation(concept_id=concept, correct=correct, observed_at=at)


def test_count_estimator_reproduces_product_confidence_rule() -> None:
    estimator = EvidenceCountEstimator()
    state = estimator.initial_state()
    assert estimator.estimate(state, "c", NOW).uncertainty == 1.0
    state = estimator.update(state, _obs("c", True, NOW))
    state = estimator.update(state, _obs("c", True, NOW))
    estimate = estimator.estimate(state, "c", NOW)
    assert estimate.uncertainty == pytest.approx(0.5)  # n/(n+2) with n=2
    assert estimate.probability == pytest.approx(3 / 4)  # Laplace smoothed
    # No decay: the estimate is identical thirty days later.
    assert estimator.estimate(state, "c", NOW + timedelta(days=30)).probability == pytest.approx(3 / 4)


def test_bkt_moves_with_evidence_and_forgets_with_time() -> None:
    estimator = BktEstimator(p_forget_per_day=0.05)
    state = estimator.initial_state()
    prior = estimator.estimate(state, "c", NOW).probability
    state = estimator.update(state, _obs("c", True, NOW))
    after_correct = estimator.estimate(state, "c", NOW).probability
    assert after_correct > prior
    state = estimator.update(state, _obs("c", False, NOW))
    after_incorrect = estimator.estimate(state, "c", NOW).probability
    assert after_incorrect < after_correct
    assert estimator.estimate(state, "c", NOW + timedelta(days=10)).probability < after_incorrect


def test_pfa_is_monotone_in_successes_and_failures() -> None:
    estimator = PfaEstimator()
    state = estimator.initial_state()
    base = estimator.estimate(state, "c", NOW).probability
    up = estimator.update(state, _obs("c", True, NOW))
    down = estimator.update(state, _obs("c", False, NOW))
    assert estimator.estimate(up, "c", NOW).probability > base
    assert estimator.estimate(down, "c", NOW).probability < base


def test_registry_rejects_unknown_estimator() -> None:
    with pytest.raises(ValueError):
        build_estimator("mystery")


# ----------------------------------------------------------------- policies
def _view(concept: str, p: float, u: float, days: float | None, n: int = 1) -> ConceptView:
    return ConceptView(concept, ConceptEstimate(p, u, n), days, 0)


def test_eligibility_gate_enforces_frequency_and_cooldown_and_quiet_hours() -> None:
    gate = EligibilityGate(EligibilityConfig())
    history = tuple(SentMessage(NOW - timedelta(days=d), "x", "spaced_review", "r") for d in (1, 2, 3))
    assert gate.check(NOW, "y", history) is ReasonCode.INELIGIBLE_FREQUENCY
    recent = (SentMessage(NOW - timedelta(hours=2), "y", "spaced_review", "r"),)
    assert gate.check(NOW, "y", recent) is ReasonCode.INELIGIBLE_COOLDOWN
    assert gate.check(NOW.replace(hour=23), "y", ()) is ReasonCode.INELIGIBLE_QUIET_HOURS
    assert gate.check(NOW, "y", ()) is None
    assert EligibilityGate(EligibilityConfig(consent=False)).check(NOW, "y", ()) is ReasonCode.INELIGIBLE_CONSENT


def test_policies_differ_on_a_recently_practised_goal() -> None:
    views = (_view("a", 0.7, 0.2, 0.2, 3), _view("b", 0.3, 0.9, None, 0))
    inputs = PolicyInputs(NOW, views, (), ("a", "b"))
    assert build_policy("constant").decide(inputs).sends
    assert build_policy("conditional").decide(inputs).reason_code is ReasonCode.NO_ACTION_NO_PREDICATE
    value = build_policy("value").decide(inputs)
    # `a` was just practised (low spacing value); `b` is unlocked (a >= 0.6) and is worth a message.
    assert value.sends and value.concept_id == "b"
    assert not build_policy("never").decide(inputs).sends


def test_value_policy_declines_low_value_messages() -> None:
    views = (_view("a", 0.84, 0.1, 0.1, 6),)
    decision = build_policy("value").decide(PolicyInputs(NOW, views, (), ("a",)))
    assert decision.reason_code is ReasonCode.NO_ACTION_LOW_VALUE


def test_oracle_requires_hidden_access() -> None:
    with pytest.raises(ValueError):
        build_policy("oracle").decide(PolicyInputs(NOW, (_view("a", 0.5, 0.5, None),), (), ("a",)))


# ------------------------------------------------------------------ harness
def test_run_learner_has_no_eligibility_violations_and_bounded_messages() -> None:
    for estimator_id, policy_id in CONDITIONS:
        result = run_learner(
            persona=PERSONAS[1],
            family=SimulatorFamily.LOGISTIC_LIKE,
            seed=11,
            estimator=build_estimator(estimator_id),
            policy=build_policy(policy_id),
            estimator_id=estimator_id,
            days=21,
        )
        assert result.eligibility_violations == 0
        assert result.messages_sent <= 9  # 3 per 7 days over 21 days
        assert 0.0 <= result.mse_vs_hidden <= 1.0
        if policy_id == "never":
            assert result.messages_sent == 0


def test_program_smoke_reports_every_condition_and_paired_contrasts() -> None:
    config = ProgramConfig(seeds=(2000,), development_seeds=(1000,), personas=PERSONAS[:2], days=8, bootstrap_resamples=20)
    program = run_program(config)
    aggregate = program["summary"]["aggregate"]
    assert set(aggregate) == {f"{e}+{p}" for e, p in CONDITIONS}
    for row in aggregate.values():
        assert row["n_learners"] == 4  # 2 families x 2 personas x 1 seed
        assert row["eligibility_violations"] == 0
    contrast = program["summary"]["paired_contrasts"]["bkt+constant vs count+constant"]["mse_vs_hidden"]
    assert contrast["n_pairs"] == 4
    assert len(contrast["ci95"]) == 2


def test_paired_bootstrap_is_deterministic() -> None:
    config = ProgramConfig(seeds=(2000, 2001), development_seeds=(1000,), personas=PERSONAS[:1], days=6, fit_parameters=False, bootstrap_resamples=30)
    a = run_program(config)["summary"]["paired_contrasts"]
    b = run_program(config)["summary"]["paired_contrasts"]
    assert a == b
