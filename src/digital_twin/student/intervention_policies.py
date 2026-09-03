"""Deterministic proactive-intervention timing policies behind one interface.

Every policy receives the same `PolicyInputs` (estimates from a replaceable
learner estimator, observation recency, the message history) and returns one
`InterventionDecision`. `no_action` is always a valid decision. A shared
`EligibilityGate` enforces consent, quiet hours, the seven-day frequency
ceiling, and the same-concept cooldown before any policy may send; the gate
is evaluated once, in one place, which is the successor design's rule.

Policies:

- `constant`: the current product behaviour, one wake-up every 24 h while a
  goal is active, sending whenever eligible.
- `conditional`: candidate B, send only when a closed replan predicate fires.
- `value`: candidate C, send only when an analytic forward model's expected
  gain over no action exceeds a margin, with spacing.
- `oracle` and `never`: evaluation bounds; `oracle` may read hidden state and
  therefore exists only for the harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from math import exp
from typing import Callable

from src.digital_twin.student.learner_estimators import ConceptEstimate


class TimingPolicyId(StrEnum):
    CONSTANT = "constant"
    CONDITIONAL = "conditional"
    VALUE = "value"
    ORACLE = "oracle"
    NEVER = "never"


class ReasonCode(StrEnum):
    SENT_CONSTANT_WAKEUP = "sent:constant-wakeup"
    SENT_REPLAN_STALLED = "sent:replan-stalled"
    SENT_REPLAN_LOW_UNCERTAIN = "sent:replan-low-uncertain"
    SENT_VALUE_MARGIN = "sent:value-margin"
    SENT_ORACLE = "sent:oracle"
    NO_ACTION_GOALS_COMPLETE = "no-action:goals-complete"
    NO_ACTION_NO_PREDICATE = "no-action:no-predicate"
    NO_ACTION_LOW_VALUE = "no-action:low-value"
    NO_ACTION_NEVER = "no-action:never"
    NO_ACTION_ORACLE = "no-action:oracle-no-need"
    INELIGIBLE_CONSENT = "ineligible:consent"
    INELIGIBLE_QUIET_HOURS = "ineligible:quiet-hours"
    INELIGIBLE_FREQUENCY = "ineligible:frequency"
    INELIGIBLE_COOLDOWN = "ineligible:cooldown"


@dataclass(frozen=True)
class EligibilityConfig:
    consent: bool = True
    quiet_hours_start_local: int = 22
    quiet_hours_end_local: int = 8
    max_messages_per_7_days: int = 3
    same_concept_cooldown_hours: int = 24
    timezone_offset_hours: int = 0


@dataclass(frozen=True)
class SentMessage:
    sent_at: datetime
    concept_id: str
    move: str
    reason_code: str


@dataclass(frozen=True)
class ConceptView:
    """What a policy may know about one concept: estimate and recency only."""

    concept_id: str
    estimate: ConceptEstimate
    days_since_last_observation: float | None
    recent_incorrect_streak: int


@dataclass(frozen=True)
class PolicyInputs:
    now: datetime
    concepts: tuple[ConceptView, ...]
    history: tuple[SentMessage, ...]
    prerequisite_order: tuple[str, ...]
    hidden_need: Callable[[str], bool] | None = None


@dataclass(frozen=True)
class InterventionDecision:
    concept_id: str | None
    move: str | None
    reason_code: str
    expected_gain: float = 0.0

    @property
    def sends(self) -> bool:
        return self.concept_id is not None


COMPLETION_PROBABILITY = 0.85
COMPLETION_MAX_UNCERTAINTY = 0.5


class EligibilityGate:
    """One deterministic gate evaluated before any policy may send."""

    def __init__(self, config: EligibilityConfig | None = None) -> None:
        self.config = config or EligibilityConfig()

    def check(self, now: datetime, concept_id: str, history: tuple[SentMessage, ...]) -> ReasonCode | None:
        if not self.config.consent:
            return ReasonCode.INELIGIBLE_CONSENT
        local_hour = (now + timedelta(hours=self.config.timezone_offset_hours)).hour
        start, end = self.config.quiet_hours_start_local, self.config.quiet_hours_end_local
        in_quiet = local_hour >= start or local_hour < end if start > end else start <= local_hour < end
        if in_quiet:
            return ReasonCode.INELIGIBLE_QUIET_HOURS
        window_start = now - timedelta(days=7)
        recent = [item for item in history if window_start < item.sent_at <= now]
        if len(recent) >= self.config.max_messages_per_7_days:
            return ReasonCode.INELIGIBLE_FREQUENCY
        cooldown = timedelta(hours=self.config.same_concept_cooldown_hours)
        if any(item.concept_id == concept_id and now - item.sent_at < cooldown for item in history):
            return ReasonCode.INELIGIBLE_COOLDOWN
        return None


def _is_complete(view: ConceptView) -> bool:
    return (
        view.estimate.probability >= COMPLETION_PROBABILITY
        and view.estimate.uncertainty <= COMPLETION_MAX_UNCERTAINTY
    )


def _active_goal(inputs: PolicyInputs) -> ConceptView | None:
    by_id = {view.concept_id: view for view in inputs.concepts}
    for concept_id in inputs.prerequisite_order:
        view = by_id[concept_id]
        if not _is_complete(view):
            return view
    return None


def _move_for(view: ConceptView) -> str:
    if view.recent_incorrect_streak >= 2:
        return "corrective_feedback"
    if view.estimate.evidence_count > 0:
        return "spaced_review"
    return "request_attempt"


@dataclass(frozen=True)
class AnalyticForwardModel:
    """Expected mastery gain of one review, from estimate and recency only.

    gain = (1 - p) * learn_prior * spacing(days) * receptivity_prior
    where spacing rises with days since the last observation (a review right
    after practice is worth little) and saturates at `spacing_tau` days. The
    interruption cost is a constant subtracted by the policy as its margin.
    """

    learn_prior: float = 0.30
    receptivity_prior: float = 0.65
    spacing_tau_days: float = 3.0
    unknown_recency_days: float = 3.0

    def expected_gain(self, view: ConceptView) -> float:
        days = view.days_since_last_observation
        if days is None:
            days = self.unknown_recency_days
        spacing = 1.0 - exp(-days / self.spacing_tau_days)
        need = 1.0 - view.estimate.probability
        return need * self.learn_prior * spacing * self.receptivity_prior


@dataclass
class TimingPolicy:
    policy_id: TimingPolicyId
    gate: EligibilityGate = field(default_factory=EligibilityGate)
    forward_model: AnalyticForwardModel = field(default_factory=AnalyticForwardModel)
    value_margin: float = 0.06
    stalled_days: float = 3.0
    low_probability: float = 0.6
    high_uncertainty: float = 0.5

    def decide(self, inputs: PolicyInputs) -> InterventionDecision:
        if self.policy_id is TimingPolicyId.NEVER:
            return InterventionDecision(None, None, ReasonCode.NO_ACTION_NEVER)
        if self.policy_id is TimingPolicyId.ORACLE:
            return self._oracle(inputs)
        if self.policy_id is TimingPolicyId.VALUE:
            return self._value(inputs)
        goal = _active_goal(inputs)
        if goal is None:
            return InterventionDecision(None, None, ReasonCode.NO_ACTION_GOALS_COMPLETE)
        if self.policy_id is TimingPolicyId.CONSTANT:
            return self._gated(inputs, goal, ReasonCode.SENT_CONSTANT_WAKEUP)
        # conditional
        days = goal.days_since_last_observation
        if days is None or days >= self.stalled_days:
            return self._gated(inputs, goal, ReasonCode.SENT_REPLAN_STALLED)
        if (
            goal.estimate.probability < self.low_probability
            and goal.estimate.uncertainty > self.high_uncertainty
        ):
            return self._gated(inputs, goal, ReasonCode.SENT_REPLAN_LOW_UNCERTAIN)
        return InterventionDecision(None, None, ReasonCode.NO_ACTION_NO_PREDICATE)

    def _gated(self, inputs: PolicyInputs, view: ConceptView, reason: ReasonCode, gain: float = 0.0) -> InterventionDecision:
        blocked = self.gate.check(inputs.now, view.concept_id, inputs.history)
        if blocked is not None:
            return InterventionDecision(None, None, blocked, gain)
        return InterventionDecision(view.concept_id, _move_for(view), reason, gain)

    def _value(self, inputs: PolicyInputs) -> InterventionDecision:
        by_id = {view.concept_id: view for view in inputs.concepts}
        best: tuple[float, ConceptView] | None = None
        previous_ready = True
        for concept_id in inputs.prerequisite_order:
            view = by_id[concept_id]
            if not previous_ready:
                break
            if not _is_complete(view):
                gain = self.forward_model.expected_gain(view)
                if best is None or gain > best[0]:
                    best = (gain, view)
            # A concept unlocks its successor once it is probably known.
            previous_ready = view.estimate.probability >= 0.6
        if best is None:
            return InterventionDecision(None, None, ReasonCode.NO_ACTION_GOALS_COMPLETE)
        gain, view = best
        if gain <= self.value_margin:
            return InterventionDecision(None, None, ReasonCode.NO_ACTION_LOW_VALUE, gain)
        return self._gated(inputs, view, ReasonCode.SENT_VALUE_MARGIN, gain)

    def _oracle(self, inputs: PolicyInputs) -> InterventionDecision:
        if inputs.hidden_need is None:
            raise ValueError("oracle policy requires hidden need access")
        for concept_id in inputs.prerequisite_order:
            if inputs.hidden_need(concept_id):
                view = next(v for v in inputs.concepts if v.concept_id == concept_id)
                return self._gated(inputs, view, ReasonCode.SENT_ORACLE)
        return InterventionDecision(None, None, ReasonCode.NO_ACTION_ORACLE)


def build_policy(policy_id: str, **parameters: float) -> TimingPolicy:
    return TimingPolicy(policy_id=TimingPolicyId(policy_id), **parameters)
