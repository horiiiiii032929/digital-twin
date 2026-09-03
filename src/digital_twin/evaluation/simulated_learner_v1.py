"""Text-realising simulated learner for driving the real product boundary.

The product accepts only message text, attributes concepts lexically, and
grades attempts by token overlap. This learner therefore keeps the hidden
state of `LearnerSimulator` and renders each hidden attempt as text whose
lexical properties are known: a correct attempt restates the approved concept
description, an incorrect attempt names the concept and then says something
unrelated. Whether the product recovers the hidden concept and correctness is
itself measured by the scorer, so the rendering rule is part of the frozen
instrument, not something tuned to the product.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.digital_twin.evaluation.learner_simulator import (
    AssessedAttempt,
    LearnerPersona,
    LearnerSimulator,
    MoveKind,
    SimulatorFamily,
)


@dataclass(frozen=True)
class ConceptCardV1:
    concept_id: str
    label: str
    description: str
    objective: str


_DISTRACTORS = (
    "keeps every copy stale forever and never checks anything",
    "just writes random values and hopes the other side agrees",
    "waits for nobody and skips every check on purpose",
    "is only about colours and fonts on the screen",
    "means restarting the machine until the number looks right",
)

_ACTION_TO_MOVE = {
    "issue-retrieval-practice": MoveKind.SPACED_REVIEW,
    "ask-diagnostic-question": MoveKind.REQUEST_ATTEMPT,
    "provide-hint-or-example": MoveKind.CORRECTIVE_FEEDBACK,
    "recommend-approved-source": MoveKind.SPACED_REVIEW,
    "send-in-app-check-in": MoveKind.REQUEST_ATTEMPT,
    "summarize-progress": MoveKind.SPACED_REVIEW,
    "schedule-follow-up": MoveKind.SPACED_REVIEW,
}


@dataclass
class LearnerUtterance:
    text: str
    concept_id: str
    kind: str  # "attempt" | "question" | "misconception"
    hidden_correct: bool | None
    prompted: bool
    realization_method: str = "deterministic-semantic-frame"
    realization_source: str = "canonical"
    realization_fallback_reason: str | None = None


@dataclass
class TextRealisingLearnerV1:
    persona: LearnerPersona
    family: SimulatorFamily
    seed: int
    cards: tuple[ConceptCardV1, ...]
    simulator: LearnerSimulator = field(init=False)
    _distractor_index: int = 0

    def __post_init__(self) -> None:
        self.simulator = LearnerSimulator(
            persona=self.persona,
            family=self.family,
            seed=self.seed,
            concept_ids=tuple(card.concept_id for card in self.cards),
        )

    # ---------------------------------------------------------------- truth
    def hidden_mastery(self, concept_id: str) -> float:
        return self.simulator.hidden_mastery(concept_id)

    def is_receptive(self) -> bool:
        return self.simulator.is_receptive(self.simulator.day)

    def needs_intervention(self, concept_id: str) -> bool:
        return self.simulator.needs_intervention(concept_id, self.simulator.day)

    @property
    def day(self) -> int:
        return self.simulator.day

    # -------------------------------------------------------------- dynamics
    def advance_one_day(self) -> None:
        self.simulator.advance_one_day()

    def self_directed_utterance(self) -> LearnerUtterance | None:
        attempt = self.simulator.self_directed_activity()
        if attempt is None:
            return None
        return self._render(attempt, prompted=False)

    def react_to_delivery(self, concept_id: str | None, action_kind: str) -> LearnerUtterance | None:
        """React to a delivered proactive message; may produce an attempt."""

        target = concept_id if concept_id in {c.concept_id for c in self.cards} else self.cards[0].concept_id
        move = _ACTION_TO_MOVE.get(action_kind, MoveKind.SPACED_REVIEW)
        attempt = self.simulator.receive_intervention(target, move)
        if attempt is None:
            return None
        return self._render(attempt, prompted=True)

    def question(self, concept_id: str) -> LearnerUtterance:
        card = self._card(concept_id)
        return LearnerUtterance(
            text=f"How does {card.label} work according to the course source?",
            concept_id=concept_id,
            kind="question",
            hidden_correct=None,
            prompted=False,
        )

    def misconception_statement(self, concept_id: str) -> LearnerUtterance:
        card = self._card(concept_id)
        return LearnerUtterance(
            text=f"I thought {card.label} must always {self._next_distractor()}.",
            concept_id=concept_id,
            kind="misconception",
            hidden_correct=None,
            prompted=False,
        )

    # --------------------------------------------------------------- helpers
    def _card(self, concept_id: str) -> ConceptCardV1:
        return next(card for card in self.cards if card.concept_id == concept_id)

    def _next_distractor(self) -> str:
        text = _DISTRACTORS[self._distractor_index % len(_DISTRACTORS)]
        self._distractor_index += 1
        return text

    def _render(self, attempt: AssessedAttempt, *, prompted: bool) -> LearnerUtterance:
        card = self._card(attempt.concept_id)
        if attempt.correct:
            text = f"My attempt on {card.label}: {card.description}"
        else:
            text = f"My attempt on {card.label}: I think it {self._next_distractor()}."
        return LearnerUtterance(
            text=text,
            concept_id=attempt.concept_id,
            kind="attempt",
            hidden_correct=attempt.correct,
            prompted=prompted,
        )
