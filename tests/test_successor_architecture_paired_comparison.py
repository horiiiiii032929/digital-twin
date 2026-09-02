import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.run_successor_architecture_paired_comparison_001 import (
    INSTRUMENT_PATH,
    simulate,
    validate,
)
from services.llm.openai_responses_client import OpenAiResponsesClient
from src.digital_twin.evaluation.autonomy_architecture_tournament import (
    AutonomyArchitectureTournamentProgramV1,
)


ROOT = Path(__file__).resolve().parents[1]


def _payload() -> dict:
    return json.loads(INSTRUMENT_PATH.read_text(encoding="utf-8"))


def test_tournament_instrument_is_finite_and_has_no_paid_authority():
    result = validate()

    assert result["status"] == "passed"
    assert result["provider_calls"] == 0
    assert result["cost_usd"] == 0


def test_tournament_binds_exact_a_b_c_cv_and_e1_e4_allocations():
    program = AutonomyArchitectureTournamentProgramV1.model_validate(_payload())

    assert len(program.architectures) == 4
    assert [item.allocation_id for item in program.engine_allocations] == [
        "e1",
        "e2",
        "e3",
        "e4",
    ]
    assert all(
        "gpt-5.6-sol" not in item.model_dump_json()
        for item in program.engine_allocations
    )
    assert [item.decision_id for item in program.prospective_amendments] == [
        "AFQC-152",
        "AFQC-155",
    ]
    assert all(
        not item.historical_results_changed
        and not item.original_development_folds_reopened
        for item in program.prospective_amendments
    )


def test_engine_allocation_drift_is_rejected():
    payload = _payload()
    payload["engine_allocations"][1]["generator_model"] = "gpt-5.4-mini-2026-03-17"

    with pytest.raises(ValidationError, match="E2 model allocation drifted"):
        AutonomyArchitectureTournamentProgramV1.model_validate(payload)


def test_active_sol_binding_is_rejected():
    payload = _payload()
    payload["engine_allocations"][0]["planner_model"] = "gpt-5.6-sol"

    with pytest.raises(ValidationError):
        AutonomyArchitectureTournamentProgramV1.model_validate(payload)


def test_network_free_simulation_runs_every_architecture_cell():
    result = simulate()

    assert result["passed"] is True
    assert len(result["rows"]) == 48
    assert all(result["gates"].values())
    assert result["provider_calls"]["deterministic-workflow-a"] == 0
    assert result["provider_calls"]["governed-single-planner-b"] == 12


def test_openai_client_has_strict_shapes_for_planner_and_verifier():
    planner = OpenAiResponsesClient._schema("hierarchical_autonomy_plan")
    verifier = OpenAiResponsesClient._schema("autonomy_plan_verifier")

    assert planner["additionalProperties"] is False
    assert set(planner["required"]) == set(planner["properties"])
    assert verifier["additionalProperties"] is False
    assert set(verifier["required"]) == {"accept", "reason_code"}
