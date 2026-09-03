"""Tests for the prospective persona-robust release-selection runner."""

from __future__ import annotations

import asyncio
from pathlib import Path

from scripts.run_governed_full_autonomy_v2_1_persona_robust_selection_022 import (
    _is_ablation_cell,
    run_case,
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
