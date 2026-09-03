"""Tests for the prospective persona-robust release-selection runner."""

from __future__ import annotations

import asyncio
from pathlib import Path

from scripts.run_governed_full_autonomy_v2_1_persona_robust_selection_022 import (
    _is_ablation_cell,
    run_case,
    select_release_condition,
)
from src.digital_twin.evaluation.learner_simulator import (
    PERSONA_ROBUST_PERSONAS,
    SimulatorFamily,
)
from src.digital_twin.evaluation.simulated_learner_v2 import (
    FrozenLearnerUtteranceBankV1,
    ResponseRealizationMethod,
)


def test_ablation_subset_has_exactly_eighteen_balanced_cells() -> None:
    cells = [
        (persona_index, method_index, family)
        for persona_index in range(6)
        for method_index in range(3)
        for family in SimulatorFamily
        if _is_ablation_cell(
            persona_index=persona_index,
            method_index=method_index,
            family=family,
            seed=3101,
        )
    ]
    assert len(cells) == 18
    assert sum(family is SimulatorFamily.BKT_LIKE for _, _, family in cells) == 9
    assert sum(family is SimulatorFamily.LOGISTIC_LIKE for _, _, family in cells) == 9
    assert not _is_ablation_cell(
        persona_index=0,
        method_index=0,
        family=SimulatorFamily.BKT_LIKE,
        seed=3102,
    )


def test_real_product_case_records_wording_and_observable_safety(tmp_path: Path) -> None:
    result, score, gates = asyncio.run(
        run_case(
            root=tmp_path,
            condition="t1-v2-autonomous",
            persona=PERSONA_ROBUST_PERSONAS[0],
            family=SimulatorFamily.BKT_LIKE,
            method=ResponseRealizationMethod.SEEDED_TEMPLATE,
            seed=3101,
            days=5,
            bank=None,
            code_revision="test-revision",
        )
    )
    assert result.response.operational_status == "completed"
    assert result.response.provider_calls == 0
    assert score.response_realization_method == "seeded-stochastic-template"
    assert score.realization_fallback_rate == 0
    assert all(gates.values())


def test_missing_frozen_wording_is_explicitly_counted(tmp_path: Path) -> None:
    result, score, gates = asyncio.run(
        run_case(
            root=tmp_path,
            condition="t0-grounded-control",
            persona=PERSONA_ROBUST_PERSONAS[5],
            family=SimulatorFamily.LOGISTIC_LIKE,
            method=ResponseRealizationMethod.FROZEN_LLM_ROLEPLAY,
            seed=3101,
            days=5,
            bank=FrozenLearnerUtteranceBankV1(
                bank_id="empty-development-bank",
                entries=[],
            ),
            code_revision="test-revision",
        )
    )
    assert result.truth.utterances
    assert score.realization_fallback_rate == 1
    assert all(
        item.realization_source == "canonical-fallback"
        and item.realization_fallback_reason is not None
        for item in result.truth.utterances
    )
    assert all(gates.values())


def _condition_row(*, mastery: float) -> dict[str, object]:
    return {
        "worst_persona_final_mastery": mastery,
        "final_hidden_mastery": mastery,
        "follow_up_fraction": 0.5,
        "wasted_rate": 0.1,
        "attribution_accuracy": 1.0,
        "messages_delivered": 1.0,
        "provider_calls": 0.0,
        "cost_usd": 0.0,
        "hard_gates": {
            "zero_quiet_hour_violations": True,
            "zero_frequency_violations": True,
            "zero_cooldown_violations": True,
        },
    }


def test_release_selection_prefers_safe_stronger_worst_persona() -> None:
    summary = {
        "aggregate": {
            "t0-grounded-control": _condition_row(mastery=0.60),
            "t1-v2-autonomous": _condition_row(mastery=0.70),
        }
    }
    decision = select_release_condition(summary, [])
    assert decision["status"] == "completed-keep"
    assert decision["selected_condition"] == "t1-v2-autonomous"


def test_release_selection_excludes_observable_safety_failure() -> None:
    summary = {
        "aggregate": {
            "t0-grounded-control": _condition_row(mastery=0.60),
            "t1-v2-autonomous": _condition_row(mastery=0.90),
        }
    }
    rows = [
        {
            "condition": "t1-v2-autonomous",
            "case_id": "unsafe",
            "gates": {"bounded-loop": False},
        }
    ]
    decision = select_release_condition(summary, rows)
    assert decision["selected_condition"] == "t0-grounded-control"
    assert "t1-v2-autonomous" in decision["excluded_conditions"]


def test_release_selection_refines_when_no_primary_condition_is_safe() -> None:
    summary = {
        "aggregate": {
            "t0-grounded-control": _condition_row(mastery=0.60),
            "t1-v2-autonomous": _condition_row(mastery=0.90),
        }
    }
    rows = [
        {
            "condition": condition,
            "case_id": condition,
            "gates": {"restart-consistent": False},
        }
        for condition in ("t0-grounded-control", "t1-v2-autonomous")
    ]
    decision = select_release_condition(summary, rows)
    assert decision["status"] == "completed-refine"
    assert decision["selected_condition"] is None
