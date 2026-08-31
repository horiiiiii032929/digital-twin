from __future__ import annotations

from copy import deepcopy

import pytest

from scripts import run_whole_system_architecture_round as runner
from src.digital_twin.evaluation.architecture_evolution import (
    ArchitectureRoundInstrumentV1,
)


def test_round_instrument_binds_three_complete_architectures() -> None:
    instrument = runner._load_instrument(runner.DEFAULT_INSTRUMENT)

    assert isinstance(instrument, ArchitectureRoundInstrumentV1)
    assert instrument.round_number == 1
    assert len(instrument.candidates) == 3
    assert sum(row.role == "baseline" for row in instrument.candidates) == 1
    assert all(len(row.plane_bindings) == 13 for row in instrument.candidates)
    assert all(not row.hidden_gold_available_to_runtime for row in instrument.candidates)


def test_round_validates_without_loading_hidden_gold() -> None:
    result = runner.validate(runner.DEFAULT_INSTRUMENT)

    assert result["status"] == "passed-build-only"
    assert result["case_count"] == 495
    assert result["candidate_count"] == 3
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False


def test_network_free_simulation_is_finite() -> None:
    result = runner.simulate(runner.DEFAULT_INSTRUMENT)

    assert result == {
        "instrument_id": "course-digital-twin-whole-system-architecture-round-1-001",
        "status": "passed-network-free-simulation",
        "case_count": 12,
        "candidate_count": 3,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded_after_responses": True,
    }


def test_public_response_generation_does_not_accept_gold() -> None:
    instrument = runner._load_instrument(runner.DEFAULT_INSTRUMENT)
    cases, chunks, _ = runner._load_inputs(instrument)

    package = runner._response_package(instrument.candidates[0], cases[:3], chunks)

    assert package["hidden_gold_loaded"] is False
    assert package["provider_calls"] == 0
    assert {row["case_id"] for row in package["responses"]} == {
        row.case_id for row in cases[:3]
    }


def test_unknown_retrieval_architecture_fails_closed() -> None:
    instrument = runner._load_instrument(runner.DEFAULT_INSTRUMENT)
    _, chunks, _ = runner._load_inputs(instrument)
    payload = instrument.candidates[0].model_dump(mode="json")
    payload["plane_bindings"]["retrieval"] = "unknown-retriever"
    candidate = type(instrument.candidates[0]).model_validate(payload)

    with pytest.raises(runner.ArchitectureRoundExecutionError, match="unsupported"):
        runner._build_retrievers(candidate, chunks)


def test_instrument_rejects_two_baselines() -> None:
    payload = runner._load_instrument(runner.DEFAULT_INSTRUMENT).model_dump(mode="json")
    payload = deepcopy(payload)
    payload["candidates"][1]["role"] = "baseline"

    with pytest.raises(ValueError, match="exactly one baseline"):
        ArchitectureRoundInstrumentV1.model_validate(payload)
