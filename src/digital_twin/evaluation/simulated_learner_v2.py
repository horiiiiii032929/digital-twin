"""Versioned learner-text realization for persona-robust product evaluation.

Hidden learner dynamics remain owned by :mod:`learner_simulator`.  This module
changes only the public wording submitted to the product.  Frozen LLM wording
is an input perturbation: it cannot modify hidden state, expected actions, or
gold labels, and missing or invalid entries fall back visibly to the canonical
semantic frame.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.evaluation.learner_simulator import AssessedAttempt
from src.digital_twin.evaluation.simulated_learner_v1 import (
    ConceptCardV1,
    LearnerUtterance,
    TextRealisingLearnerV1,
)


class ResponseRealizationMethod(StrEnum):
    DETERMINISTIC_FRAME = "deterministic-semantic-frame"
    SEEDED_TEMPLATE = "seeded-stochastic-template"
    FROZEN_LLM_ROLEPLAY = "frozen-llm-roleplay"


class FrozenLearnerUtteranceV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=16, max_length=512)
    text: str = Field(min_length=4, max_length=800)
    model_id: str = Field(min_length=2, max_length=160)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FrozenLearnerUtteranceBankV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_id: str = Field(min_length=4, max_length=160)
    entries: list[FrozenLearnerUtteranceV1]

    @model_validator(mode="after")
    def require_unique_keys(self) -> "FrozenLearnerUtteranceBankV1":
        keys = [entry.key for entry in self.entries]
        if len(keys) != len(set(keys)):
            raise ValueError("frozen learner utterance keys must be unique")
        return self

    def by_key(self) -> dict[str, FrozenLearnerUtteranceV1]:
        return {entry.key: entry for entry in self.entries}


_CORRECT_TEMPLATES = (
    "My attempt on {label}: {description}",
    "My current explanation of {label} is this: {description}",
    "I think {label} works as follows: {description}",
)
_INCORRECT_TEMPLATES = (
    "My attempt on {label}: I think it {distractor}.",
    "My current explanation of {label} is that it {distractor}.",
    "I believe {label} {distractor}.",
)
_QUESTION_TEMPLATES = (
    "How does {label} work according to the course source?",
    "Could you explain {label} using the approved course material?",
    "What should I understand about {label} from this course?",
)
_MISCONCEPTION_TEMPLATES = (
    "I thought {label} must always {distractor}.",
    "Doesn't {label} mean it {distractor}?",
    "I am sure {label} must always {distractor}.",
)


@dataclass
class TextRealisingLearnerV2(TextRealisingLearnerV1):
    realization_method: ResponseRealizationMethod = ResponseRealizationMethod.DETERMINISTIC_FRAME
    frozen_bank: FrozenLearnerUtteranceBankV1 | None = None
    _realization_random: random.Random = field(init=False, repr=False)
    _realization_counts: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    realization_fallbacks: list[str] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        self._realization_random = random.Random(
            f"realization-v2:{self.family}:{self.persona.name}:{self.seed}:"
            f"{self.realization_method}"
        )
        if (
            self.realization_method is ResponseRealizationMethod.FROZEN_LLM_ROLEPLAY
            and self.frozen_bank is None
        ):
            raise ValueError("frozen-llm-roleplay requires a frozen utterance bank")

    def question(self, concept_id: str) -> LearnerUtterance:
        card = self._card(concept_id)
        canonical = _QUESTION_TEMPLATES[0].format(label=card.label)
        text, source, fallback, key = self._realize(
            kind="question",
            card=card,
            hidden_correct=None,
            prompted=False,
            canonical=canonical,
            templates=_QUESTION_TEMPLATES,
            values={"label": card.label},
        )
        return LearnerUtterance(
            text=text,
            concept_id=concept_id,
            kind="question",
            hidden_correct=None,
            prompted=False,
            realization_method=str(self.realization_method),
            realization_source=source,
            realization_fallback_reason=fallback,
            realization_key=key,
        )

    def misconception_statement(self, concept_id: str) -> LearnerUtterance:
        card = self._card(concept_id)
        distractor = self._next_distractor()
        canonical = _MISCONCEPTION_TEMPLATES[0].format(
            label=card.label, distractor=distractor
        )
        text, source, fallback, key = self._realize(
            kind="misconception",
            card=card,
            hidden_correct=None,
            prompted=False,
            canonical=canonical,
            templates=_MISCONCEPTION_TEMPLATES,
            values={"label": card.label, "distractor": distractor},
        )
        return LearnerUtterance(
            text=text,
            concept_id=concept_id,
            kind="misconception",
            hidden_correct=None,
            prompted=False,
            realization_method=str(self.realization_method),
            realization_source=source,
            realization_fallback_reason=fallback,
            realization_key=key,
        )

    def _render(self, attempt: AssessedAttempt, *, prompted: bool) -> LearnerUtterance:
        card = self._card(attempt.concept_id)
        distractor = self._next_distractor() if not attempt.correct else ""
        templates = _CORRECT_TEMPLATES if attempt.correct else _INCORRECT_TEMPLATES
        values = {
            "label": card.label,
            "description": card.description,
            "distractor": distractor,
        }
        canonical = templates[0].format(**values)
        text, source, fallback, key = self._realize(
            kind="attempt",
            card=card,
            hidden_correct=attempt.correct,
            prompted=prompted,
            canonical=canonical,
            templates=templates,
            values=values,
        )
        return LearnerUtterance(
            text=text,
            concept_id=attempt.concept_id,
            kind="attempt",
            hidden_correct=attempt.correct,
            prompted=prompted,
            realization_method=str(self.realization_method),
            realization_source=source,
            realization_fallback_reason=fallback,
            realization_key=key,
        )

    def _realize(
        self,
        *,
        kind: str,
        card: ConceptCardV1,
        hidden_correct: bool | None,
        prompted: bool,
        canonical: str,
        templates: tuple[str, ...],
        values: dict[str, str],
    ) -> tuple[str, str, str | None, str]:
        key = self._next_key(
            kind=kind,
            concept_id=card.concept_id,
            hidden_correct=hidden_correct,
            prompted=prompted,
            canonical=canonical,
        )
        if self.realization_method is ResponseRealizationMethod.DETERMINISTIC_FRAME:
            return canonical, "canonical", None, key
        if self.realization_method is ResponseRealizationMethod.SEEDED_TEMPLATE:
            return (
                self._realization_random.choice(templates).format(**values),
                "template",
                None,
                key,
            )
        entry = self.frozen_bank.by_key().get(key) if self.frozen_bank is not None else None
        if entry is None:
            reason = f"missing:{key}"
            self.realization_fallbacks.append(reason)
            return canonical, "canonical-fallback", reason, key
        failure = validate_frozen_utterance(
            text=entry.text,
            kind=kind,
            card=card,
            hidden_correct=hidden_correct,
        )
        if failure is not None:
            reason = f"invalid:{failure}:{key}"
            self.realization_fallbacks.append(reason)
            return canonical, "canonical-fallback", reason, key
        return entry.text, f"frozen-bank:{self.frozen_bank.bank_id}", None, key

    def _next_key(
        self,
        *,
        kind: str,
        concept_id: str,
        hidden_correct: bool | None,
        prompted: bool,
        canonical: str,
    ) -> str:
        semantic_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        signature = ":".join(
            (
                self.persona.name,
                self.family.value,
                str(self.seed),
                kind,
                concept_id,
                "na" if hidden_correct is None else str(hidden_correct).lower(),
                str(prompted).lower(),
                semantic_sha256[:16],
            )
        )
        ordinal = self._realization_counts.get(signature, 0)
        self._realization_counts[signature] = ordinal + 1
        return f"{signature}:{ordinal:03d}"


def validate_frozen_utterance(
    *,
    text: str,
    kind: str,
    card: ConceptCardV1,
    hidden_correct: bool | None,
) -> str | None:
    """Reject wording that no longer preserves the frozen semantic frame."""

    normalized = text.casefold()
    label_tokens = set(re.findall(r"[a-z0-9][a-z0-9_-]+", card.label.casefold()))
    observed = set(re.findall(r"[a-z0-9][a-z0-9_-]+", normalized))
    if not label_tokens.intersection(observed):
        return "missing-concept-anchor"
    if kind == "question" and "?" not in text:
        return "missing-question-form"
    if kind == "misconception" and not re.search(
        r"\b(i thought|isn't|doesn't|must always|can never|i am sure)\b", normalized
    ):
        return "missing-misconception-cue"
    if kind == "attempt" and not re.search(
        r"\b(my attempt|my (?:current )?explanation|i think|i believe|because)\b",
        normalized,
    ):
        return "missing-attempt-cue"
    if kind == "attempt" and hidden_correct:
        expected = {
            token
            for token in re.findall(r"[a-z0-9][a-z0-9_-]+", card.description.casefold())
            if len(token) >= 4
        }
        if expected and len(expected.intersection(observed)) / len(expected) < 0.45:
            return "insufficient-correct-answer-content"
    return None


def frozen_utterance_key(
    *,
    persona: str,
    family: str,
    seed: int,
    kind: str,
    concept_id: str,
    hidden_correct: bool | None,
    prompted: bool,
    canonical: str,
    ordinal: int,
) -> str:
    """Public key constructor for offline bank generation and validation."""

    correct = "na" if hidden_correct is None else str(hidden_correct).lower()
    semantic_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return (
        f"{persona}:{family}:{seed}:{kind}:{concept_id}:{correct}:"
        f"{str(prompted).lower()}:{semantic_sha256[:16]}:{ordinal:03d}"
    )


def utterance_bank_sha256(bank: FrozenLearnerUtteranceBankV1) -> str:
    return hashlib.sha256(bank.model_dump_json(exclude_none=False).encode()).hexdigest()
