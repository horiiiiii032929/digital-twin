"""Replaceable learner-state estimators behind one interface.

Three implementations share the `LearnerEstimator` protocol so that the same
observation stream can be scored through each of them:

- `EvidenceCountEstimator` reproduces the current product rule (assessed
  evidence counts, confidence `n / (n + 2)`, no decay) and exposes it as a
  Laplace-smoothed proportion so that it can be scored with a Brier score.
- `BktEstimator` is the two-state Bayesian Knowledge Tracing model with an
  explicit per-day forgetting term.
- `PfaEstimator` is a logistic Performance Factors model whose success and
  failure counts decay with elapsed time.

None of these read text. They consume `AssessedObservation` records only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from math import exp, log
from typing import Protocol


@dataclass(frozen=True)
class AssessedObservation:
    """One observed, assessed learner attempt on one concept."""

    concept_id: str
    correct: bool
    observed_at: datetime


@dataclass(frozen=True)
class ConceptEstimate:
    probability: float
    uncertainty: float
    evidence_count: int


@dataclass(frozen=True)
class ConceptRecord:
    """Per-concept sufficient statistics shared by the estimators."""

    successes: float = 0.0
    failures: float = 0.0
    evidence_count: int = 0
    posterior: float | None = None
    last_observed_at: datetime | None = None


@dataclass(frozen=True)
class EstimatorState:
    concepts: dict[str, ConceptRecord] = field(default_factory=dict)


class LearnerEstimator(Protocol):
    implementation_id: str

    def initial_state(self) -> EstimatorState: ...

    def update(self, state: EstimatorState, observation: AssessedObservation) -> EstimatorState: ...

    def estimate(self, state: EstimatorState, concept_id: str, now: datetime) -> ConceptEstimate: ...


def _days_between(earlier: datetime | None, later: datetime) -> float:
    if earlier is None:
        return 0.0
    return max(0.0, (later - earlier).total_seconds() / 86400.0)


def _confidence_rule(evidence_count: int) -> float:
    """The product's current confidence rule: two assessed observations reach one half."""

    return min(0.95, evidence_count / (evidence_count + 2))


class EvidenceCountEstimator:
    """Current behaviour: counts only, no decay, no prior beyond Laplace smoothing."""

    implementation_id = "evidence-count-laplace-v1"

    def __init__(self, prior_probability: float = 0.5, prior_weight: float = 2.0) -> None:
        self.prior_probability = prior_probability
        self.prior_weight = prior_weight

    def initial_state(self) -> EstimatorState:
        return EstimatorState()

    def update(self, state: EstimatorState, observation: AssessedObservation) -> EstimatorState:
        record = state.concepts.get(observation.concept_id, ConceptRecord())
        updated = replace(
            record,
            successes=record.successes + (1.0 if observation.correct else 0.0),
            failures=record.failures + (0.0 if observation.correct else 1.0),
            evidence_count=record.evidence_count + 1,
            last_observed_at=observation.observed_at,
        )
        return EstimatorState({**state.concepts, observation.concept_id: updated})

    def estimate(self, state: EstimatorState, concept_id: str, now: datetime) -> ConceptEstimate:
        record = state.concepts.get(concept_id, ConceptRecord())
        probability = (record.successes + self.prior_probability * self.prior_weight) / (
            record.evidence_count + self.prior_weight
        )
        return ConceptEstimate(
            probability=probability,
            uncertainty=1.0 - _confidence_rule(record.evidence_count),
            evidence_count=record.evidence_count,
        )


class BktEstimator:
    """Two-state Bayesian Knowledge Tracing with per-day forgetting."""

    implementation_id = "bkt-forgetting-v1"

    def __init__(
        self,
        *,
        p_init: float = 0.30,
        p_learn: float = 0.20,
        p_guess: float = 0.20,
        p_slip: float = 0.10,
        p_forget_per_day: float = 0.02,
    ) -> None:
        self.p_init = p_init
        self.p_learn = p_learn
        self.p_guess = p_guess
        self.p_slip = p_slip
        self.p_forget_per_day = p_forget_per_day

    def initial_state(self) -> EstimatorState:
        return EstimatorState()

    def _decayed_posterior(self, record: ConceptRecord, now: datetime) -> float:
        posterior = self.p_init if record.posterior is None else record.posterior
        days = _days_between(record.last_observed_at, now)
        return posterior * (1.0 - self.p_forget_per_day) ** days

    def update(self, state: EstimatorState, observation: AssessedObservation) -> EstimatorState:
        record = state.concepts.get(observation.concept_id, ConceptRecord())
        prior = self._decayed_posterior(record, observation.observed_at)
        if observation.correct:
            likelihood_known = 1.0 - self.p_slip
            likelihood_unknown = self.p_guess
        else:
            likelihood_known = self.p_slip
            likelihood_unknown = 1.0 - self.p_guess
        evidence = prior * likelihood_known + (1.0 - prior) * likelihood_unknown
        conditioned = prior * likelihood_known / evidence if evidence > 0 else prior
        posterior = conditioned + (1.0 - conditioned) * self.p_learn
        updated = replace(
            record,
            successes=record.successes + (1.0 if observation.correct else 0.0),
            failures=record.failures + (0.0 if observation.correct else 1.0),
            evidence_count=record.evidence_count + 1,
            posterior=posterior,
            last_observed_at=observation.observed_at,
        )
        return EstimatorState({**state.concepts, observation.concept_id: updated})

    def estimate(self, state: EstimatorState, concept_id: str, now: datetime) -> ConceptEstimate:
        record = state.concepts.get(concept_id, ConceptRecord())
        probability = self._decayed_posterior(record, now)
        return ConceptEstimate(
            probability=probability,
            uncertainty=1.0 - _confidence_rule(record.evidence_count),
            evidence_count=record.evidence_count,
        )


class PfaEstimator:
    """Logistic Performance Factors Analysis with time-decayed counts."""

    implementation_id = "pfa-decay-v1"

    def __init__(
        self,
        *,
        beta: float = -0.85,
        gamma: float = 0.9,
        rho: float = 0.5,
        decay_per_day: float = 0.03,
    ) -> None:
        self.beta = beta
        self.gamma = gamma
        self.rho = rho
        self.decay_per_day = decay_per_day

    def initial_state(self) -> EstimatorState:
        return EstimatorState()

    def _decayed(self, record: ConceptRecord, now: datetime) -> tuple[float, float]:
        factor = (1.0 - self.decay_per_day) ** _days_between(record.last_observed_at, now)
        return record.successes * factor, record.failures * factor

    def update(self, state: EstimatorState, observation: AssessedObservation) -> EstimatorState:
        record = state.concepts.get(observation.concept_id, ConceptRecord())
        successes, failures = self._decayed(record, observation.observed_at)
        updated = replace(
            record,
            successes=successes + (1.0 if observation.correct else 0.0),
            failures=failures + (0.0 if observation.correct else 1.0),
            evidence_count=record.evidence_count + 1,
            last_observed_at=observation.observed_at,
        )
        return EstimatorState({**state.concepts, observation.concept_id: updated})

    def estimate(self, state: EstimatorState, concept_id: str, now: datetime) -> ConceptEstimate:
        record = state.concepts.get(concept_id, ConceptRecord())
        successes, failures = self._decayed(record, now)
        logit = self.beta + self.gamma * successes - self.rho * failures
        probability = 1.0 / (1.0 + exp(-logit))
        return ConceptEstimate(
            probability=probability,
            uncertainty=1.0 - _confidence_rule(record.evidence_count),
            evidence_count=record.evidence_count,
        )


ESTIMATOR_IDS: tuple[str, ...] = ("count", "bkt", "pfa")


def build_estimator(estimator_id: str, **parameters: float) -> LearnerEstimator:
    """Registry entry point so evaluation code never names a class."""

    if estimator_id == "count":
        return EvidenceCountEstimator(**parameters)
    if estimator_id == "bkt":
        return BktEstimator(**parameters)
    if estimator_id == "pfa":
        return PfaEstimator(**parameters)
    raise ValueError(f"unknown estimator id {estimator_id!r}")


def log_loss(probability: float, outcome: bool) -> float:
    clipped = min(max(probability, 1e-6), 1 - 1e-6)
    return -log(clipped) if outcome else -log(1.0 - clipped)
