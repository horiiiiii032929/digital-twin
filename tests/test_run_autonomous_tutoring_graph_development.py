from __future__ import annotations

import asyncio
import copy

from scripts.run_autonomous_tutoring_graph_development import (
    RUN_ID,
    evaluate_development,
    load_instrument,
    validate_preflight,
)


def test_network_free_development_preflight_is_ready_for_temporary_output(
    tmp_path,
):
    instrument = load_instrument()

    result = validate_preflight(
        instrument,
        output=tmp_path / "unused.json",
        require_clean=False,
    )

    assert result == {
        "run_id": RUN_ID,
        "status": "ready",
        "blockers": [],
        "provider_calls": 0,
        "tokens": 0,
        "cost_usd": 0.0,
        "private_or_heldout_data_read": False,
    }


def test_network_free_t0_t1_development_run_passes_every_hard_gate(tmp_path):
    instrument = load_instrument()

    result = asyncio.run(
        evaluate_development(instrument, temporary_root=tmp_path)
    )

    assert result["status"] == "completed-go-deeper"
    assert result["decision"] == "go-deeper"
    assert result["trajectory_count_per_condition"] == 10
    assert result["turn_count_per_condition"] == 13
    assert all(result["hard_gates"].values())
    assert result["metrics"]["t1_transition_validity"] == 1.0
    assert result["metrics"]["safe_fallback_rate"] == 1.0
    assert result["metrics"]["atomic_state_persistence_rate"] == 1.0
    assert result["metrics"]["citation_validity"] == 1.0
    assert result["provider_calls"] == 0
    assert result["input_tokens"] == result["output_tokens"] == 0
    assert result["cost_usd"] == 0.0
    assert result["private_or_heldout_data_read"] is False
    assert result["automatic_promotion"] is False


def test_method_failure_records_refine_without_automatic_rerun(tmp_path):
    instrument = copy.deepcopy(load_instrument())
    instrument["development_trajectories"][0]["turns"][0][
        "expected_intent"
    ] = "give_hint"

    result = asyncio.run(
        evaluate_development(instrument, temporary_root=tmp_path)
    )

    assert result["status"] == "completed-refine"
    assert result["decision"] == "refine"
    assert result["hard_gates"]["exact_t1_transition_validity"] is False
    assert result["automatic_promotion"] is False


def test_invalid_execution_is_preserved(tmp_path):
    instrument = copy.deepcopy(load_instrument())
    instrument["development_trajectories"][0]["turns"][0]["message"] = ""

    result = asyncio.run(
        evaluate_development(instrument, temporary_root=tmp_path)
    )

    assert result["status"] == "invalid-execution"
    assert result["provider_calls"] == 0
    assert result["private_or_heldout_data_read"] is False
    assert result["trajectories"] == []
