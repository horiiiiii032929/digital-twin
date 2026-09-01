"""Hidden-state simulated learners for network-free architecture evaluation.

The simulator is the *truth source* that an engine under test never sees. It
is deterministic under a seed, text free (no model calls), and comes in two
transition families so that an estimator cannot win by sharing one family's
assumptions. It is deliberately simple: the purpose is a controlled
comparison of learner-state estimators and intervention-timing policies, not
a model of real students.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from math import exp, log


class SimulatorFamily(StrEnum):
    """Two transition models with different assumptions."""

    BKT_LIKE = "bkt-like"
    LOGISTIC_LIKE = "logistic-like"


class MoveKind(StrEnum):
    """Moves an engine can direct at a simulated learner."""

    SPACED_REVIEW = "spaced_review"
    CORRECTIVE_FEEDBACK = "corrective_feedback"
    REQUEST_ATTEMPT = "request_attempt"


@dataclass(frozen=True)
class LearnerPersona:
    """Frozen persona parameters; every field is a hidden quantity."""

    name: str
    learning_rate: float
    forgetting_rate_per_day: float
    misconception_probability: float
    activity_probability_per_day: float
    receptivity_probability: float
    crowd_out_days: int
    initial_mastery_mean: float


PERSONAS: tuple[LearnerPersona, ...] = (
    LearnerPersona("fast-learner", 0.45, 0.02, 0.10, 0.65, 0.80, 1, 0.35),
    LearnerPersona("slow-learner", 0.15, 0.03, 0.20, 0.45, 0.70, 2, 0.25),
    LearnerPersona("high-forgetting", 0.30, 0.10, 0.15, 0.50, 0.75, 1, 0.40),
    LearnerPersona("misconception-prone", 0.25, 0.03, 0.55, 0.50, 0.70, 2, 0.30),
    LearnerPersona("answer-seeking", 0.20, 0.04, 0.20, 0.70, 0.60, 2, 0.30),
    LearnerPersona("low-receptivity", 0.30, 0.03, 0.15, 0.35, 0.30, 4, 0.35),
)

DEFAULT_CONCEPTS: tuple[str, ...] = tuple(f"concept-{index:02d}" for index in range(1, 9))

GUESS = 0.20
SLIP = 0.10
MASTERY_THRESHOLD = 0.85


@dataclass
class HiddenConcept:
    mastery: float
    misconception: bool
    last_practiced_day: int | None = None


@dataclass(frozen=True)
class AssessedAttempt:
    """An observable outcome the engine may see."""

    day: int
    concept_id: str
    correct: bool
    prompted_by_intervention: bool


@dataclass
class HiddenLearnerState:
    concepts: dict[str, HiddenConcept]
    receptivity_blocked_until_day: int = -1
    attempts: list[AssessedAttempt] = field(default_factory=list)


class LearnerSimulator:
    """One simulated learner with hidden state and a private random stream."""

    def __init__(
        self,
        *,
        persona: LearnerPersona,
        family: SimulatorFamily,
        seed: int,
        concept_ids: tuple[str, ...] = DEFAULT_CONCEPTS,
    ) -> None:
        self.persona = persona
        self.family = family
        self.seed = seed
        self.concept_ids = concept_ids
        self._random = random.Random(f"{family}:{persona.name}:{seed}")
        self.state = HiddenLearnerState(
            concepts={
                concept_id: HiddenConcept(
                    mastery=_clip(self._random.gauss(persona.initial_mastery_mean, 0.12)),
                    misconception=self._random.random() < persona.misconception_probability,
                )
                for concept_id in concept_ids
            }
        )
        self.day = 0

    # ----------------------------------------------------------------- truth
    def hidden_mastery(self, concept_id: str) -> float:
        return self.state.concepts[concept_id].mastery

    def is_receptive(self, day: int) -> bool:
        return day > self.state.receptivity_blocked_until_day

    def needs_intervention(self, concept_id: str, day: int) -> bool:
        """Hidden need: below mastery and would act on a message."""

        concept = self.state.concepts[concept_id]
        return concept.mastery < MASTERY_THRESHOLD and self.is_receptive(day)

    # ------------------------------------------------------------ dynamics
    def advance_one_day(self) -> None:
        """Apply forgetting for one day."""

        self.day += 1
        rate = self.persona.forgetting_rate_per_day
        for concept in self.state.concepts.values():
            if self.family is SimulatorFamily.BKT_LIKE:
                # Exponential decay toward zero mastery.
                concept.mastery = _clip(concept.mastery * (1.0 - rate))
            else:
                # Decay in logit space, which forgets fastest near the middle.
                concept.mastery = _clip(_sigmoid(_logit(concept.mastery) - 0.5 * rate))

    def self_directed_activity(self) -> AssessedAttempt | None:
        """Optionally attempt one concept without being prompted."""

        if self._random.random() >= self.persona.activity_probability_per_day:
            return None
        concept_id = self._choose_concept_for_practice()
        return self._attempt(concept_id, prompted=False)

    def receive_intervention(self, concept_id: str, move: MoveKind) -> AssessedAttempt | None:
        """React to a proactive message; returns an attempt when acted on."""

        concept = self.state.concepts[concept_id]
        wanted = concept.mastery < MASTERY_THRESHOLD
        receptive = self.is_receptive(self.day)
        if not receptive:
            return None
        acted = self._random.random() < self.persona.receptivity_probability
        if not wanted or not acted:
            # Unwanted or ignored messages crowd out later receptivity.
            self.state.receptivity_blocked_until_day = self.day + self.persona.crowd_out_days
            return None
        if move is MoveKind.CORRECTIVE_FEEDBACK and concept.misconception:
            if self._random.random() < 0.6:
                concept.misconception = False
        return self._attempt(concept_id, prompted=True)

    # ------------------------------------------------------------- helpers
    def _choose_concept_for_practice(self) -> str:
        # Learners tend to practice the earliest unmastered concept, with noise.
        for concept_id in self.concept_ids:
            if self.state.concepts[concept_id].mastery < MASTERY_THRESHOLD:
                if self._random.random() < 0.75:
                    return concept_id
        return self._random.choice(self.concept_ids)

    def _attempt(self, concept_id: str, *, prompted: bool) -> AssessedAttempt:
        concept = self.state.concepts[concept_id]
        effective_mastery = concept.mastery * (0.5 if concept.misconception else 1.0)
        p_correct = effective_mastery * (1.0 - SLIP) + (1.0 - effective_mastery) * GUESS
        correct = self._random.random() < p_correct
        self._learn(concept, correct)
        concept.last_practiced_day = self.day
        attempt = AssessedAttempt(
            day=self.day, concept_id=concept_id, correct=correct, prompted_by_intervention=prompted
        )
        self.state.attempts.append(attempt)
        return attempt

    def _learn(self, concept: HiddenConcept, correct: bool) -> None:
        rate = self.persona.learning_rate
        if self.family is SimulatorFamily.BKT_LIKE:
            # Discrete transition: with probability `rate` the learner jumps
            # to high mastery after practice; incorrect attempts teach less.
            jump = rate if correct else rate * 0.5
            if self._random.random() < jump:
                concept.mastery = _clip(max(concept.mastery, 0.9))
        else:
            # Continuous logistic increment; correct attempts help more.
            increment = 2.0 * rate if correct else 0.8 * rate
            concept.mastery = _clip(_sigmoid(_logit(concept.mastery) + increment))
        if concept.misconception and correct and self._random.random() < 0.15:
            concept.misconception = False


def _clip(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return max(low, min(high, value))


def _logit(p: float) -> float:
    p = _clip(p)
    return log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + exp(-x))


def day_to_datetime(origin: datetime, day: int, hour: int = 10) -> datetime:
    """Map a simulation day to a fixed local-hour instant for the engine clock."""

    return origin + timedelta(days=day, hours=hour)
