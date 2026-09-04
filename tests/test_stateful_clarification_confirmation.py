import asyncio

from scripts.run_stateful_clarification_confirmation import (
    run_confirmation,
    validate_instrument,
)


def test_frozen_stateful_clarification_instrument_is_finite_and_network_free():
    instrument = validate_instrument()

    assert instrument["dataset"]["case_count"] == 200
    assert instrument["execution"]["provider_calls"] == 0
    assert instrument["execution"]["maximum_clarification_turns"] == 1


def test_actual_product_stateful_clarification_simulation_passes(tmp_path):
    result = asyncio.run(run_confirmation(tmp_path / "product.sqlite3"))

    assert result.status == "completed-keep"
    assert result.failed_gates == []
    assert result.metrics.case_count == 200
    assert result.metrics.candidate_grounded_completion == 1
    assert result.metrics.control_grounded_completion == 0.25
    assert result.metrics.paired_completion_delta == 0.75
    assert result.metrics.provider_calls == 0
