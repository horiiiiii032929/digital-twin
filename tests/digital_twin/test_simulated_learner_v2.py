"""Contract tests for persona-robust learner response realization."""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from scripts.governed_full_autonomy_v2_1_hidden_state_runtime import (
    HIDDEN_STATE_CONCEPT_CARDS,
)
from src.digital_twin.evaluation.learner_simulator import (
    PERSONA_ROBUST_PERSONAS,
    SimulatorFamily,
)
from src.digital_twin.evaluation.simulated_learner_v2 import (
    FrozenLearnerUtteranceBankV1,
    FrozenLearnerUtteranceV1,
    ResponseRealizationMethod,
    TextRealisingLearnerV2,
    frozen_utterance_key,
)


def _entry(key: str, text: str) -> FrozenLearnerUtteranceV1:
    return FrozenLearnerUtteranceV1(
        key=key,
        text=text,
        model_id="frozen-test-model",
        prompt_sha256=hashlib.sha256(b"test-prompt").hexdigest(),
    )


def test_response_realization_rng_does_not_change_hidden_dynamics() -> None:
    canonical = TextRealisingLearnerV2(
        persona=PERSONA_ROBUST_PERSONAS[0],
        family=SimulatorFamily.BKT_LIKE,
        seed=9001,
        cards=HIDDEN_STATE_CONCEPT_CARDS,
        realization_method=ResponseRealizationMethod.DETERMINISTIC_FRAME,
    )
    stochastic = TextRealisingLearnerV2(
        persona=PERSONA_ROBUST_PERSONAS[0],
        family=SimulatorFamily.BKT_LIKE,
        seed=9001,
        cards=HIDDEN_STATE_CONCEPT_CARDS,
        realization_method=ResponseRealizationMethod.SEEDED_TEMPLATE,
    )
    canonical_events = []
    stochastic_events = []
    for _ in range(20):
        canonical.advance_one_day()
        stochastic.advance_one_day()
        left = canonical.self_directed_utterance()
        right = stochastic.self_directed_utterance()
        canonical_events.append(
            None if left is None else (left.concept_id, left.hidden_correct, left.prompted)
        )
        stochastic_events.append(
            None if right is None else (right.concept_id, right.hidden_correct, right.prompted)
        )
    assert canonical_events == stochastic_events
    assert canonical.simulator.state == stochastic.simulator.state


def test_seeded_template_is_reproducible_and_records_provenance() -> None:
    kwargs = dict(
        persona=PERSONA_ROBUST_PERSONAS[2],
        family=SimulatorFamily.LOGISTIC_LIKE,
        seed=73,
        cards=HIDDEN_STATE_CONCEPT_CARDS,
        realization_method=ResponseRealizationMethod.SEEDED_TEMPLATE,
    )
    first = TextRealisingLearnerV2(**kwargs)
    second = TextRealisingLearnerV2(**kwargs)
    left = first.question(HIDDEN_STATE_CONCEPT_CARDS[0].concept_id)
    right = second.question(HIDDEN_STATE_CONCEPT_CARDS[0].concept_id)
    assert left.text == right.text
    assert left.realization_method == "seeded-stochastic-template"
    assert left.realization_source == "template"
    assert left.realization_fallback_reason is None


def test_frozen_bank_accepts_valid_wording_and_falls_back_on_missing_entry() -> None:
    persona = PERSONA_ROBUST_PERSONAS[1]
    family = SimulatorFamily.BKT_LIKE
    seed = 17
    card = HIDDEN_STATE_CONCEPT_CARDS[0]
    key = frozen_utterance_key(
        persona=persona.name,
        family=family.value,
        seed=seed,
        kind="question",
        concept_id=card.concept_id,
        hidden_correct=None,
        prompted=False,
        ordinal=0,
    )
    bank = FrozenLearnerUtteranceBankV1(
        bank_id="bank-test-001",
        entries=[_entry(key, f"Could you help me understand {card.label}?")],
    )
    learner = TextRealisingLearnerV2(
        persona=persona,
        family=family,
        seed=seed,
        cards=HIDDEN_STATE_CONCEPT_CARDS,
        realization_method=ResponseRealizationMethod.FROZEN_LLM_ROLEPLAY,
        frozen_bank=bank,
    )
    first = learner.question(card.concept_id)
    second = learner.question(card.concept_id)
    assert first.text == f"Could you help me understand {card.label}?"
    assert first.realization_source == "frozen-bank:bank-test-001"
    assert second.realization_source == "canonical-fallback"
    assert second.realization_fallback_reason is not None
    assert second.realization_fallback_reason.startswith("missing:")


def test_invalid_frozen_semantics_fall_back_without_changing_hidden_truth() -> None:
    persona = PERSONA_ROBUST_PERSONAS[4]
    family = SimulatorFamily.LOGISTIC_LIKE
    seed = 33
    card = HIDDEN_STATE_CONCEPT_CARDS[2]
    key = frozen_utterance_key(
        persona=persona.name,
        family=family.value,
        seed=seed,
        kind="misconception",
        concept_id=card.concept_id,
        hidden_correct=None,
        prompted=False,
        ordinal=0,
    )
    bank = FrozenLearnerUtteranceBankV1(
        bank_id="bank-test-invalid",
        entries=[_entry(key, f"Please describe {card.label}.")],
    )
    learner = TextRealisingLearnerV2(
        persona=persona,
        family=family,
        seed=seed,
        cards=HIDDEN_STATE_CONCEPT_CARDS,
        realization_method=ResponseRealizationMethod.FROZEN_LLM_ROLEPLAY,
        frozen_bank=bank,
    )
    utterance = learner.misconception_statement(card.concept_id)
    assert utterance.realization_source == "canonical-fallback"
    assert "missing-misconception-cue" in (utterance.realization_fallback_reason or "")


def test_frozen_bank_rejects_duplicate_keys() -> None:
    key = "persona:bkt-like:1:question:concept:true:false:000"
    with pytest.raises(ValidationError, match="must be unique"):
        FrozenLearnerUtteranceBankV1(
            bank_id="bank-duplicate",
            entries=[_entry(key, "What about concept one?"), _entry(key, "Concept one?")],
        )


def test_frozen_method_requires_an_immutable_bank() -> None:
    with pytest.raises(ValueError, match="requires a frozen utterance bank"):
        TextRealisingLearnerV2(
            persona=PERSONA_ROBUST_PERSONAS[0],
            family=SimulatorFamily.BKT_LIKE,
            seed=1,
            cards=HIDDEN_STATE_CONCEPT_CARDS,
            realization_method=ResponseRealizationMethod.FROZEN_LLM_ROLEPLAY,
        )
