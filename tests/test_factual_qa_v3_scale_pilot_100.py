from __future__ import annotations

import asyncio
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.run_factual_qa_v3_scale_pilot_100 import (
    INSTRUMENT_ID,
    PlannedInterruption,
    ScalePilotError,
    SimulatedTransport,
    _maximum_reserved_cost,
    _simulation_transports,
    build_preflight,
    execute,
    load_assets,
    validate_instrument,
)
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


@pytest.fixture(scope="module")
def assets() -> dict:
    return load_assets()


def test_instrument_is_build_only_and_price_bounded(assets: dict) -> None:
    instrument = assets["instrument"]

    assert instrument["instrument_id"] == INSTRUMENT_ID
    assert instrument["status"] == "draft-reviewed-provider-execution-unauthorized"
    assert instrument["execution"]["provider_execution_authorized"] is False
    assert instrument["execution"]["dataset_write_authorized"] is False
    assert instrument["execution"]["automatic_stage_promotion"] is False
    assert instrument["execution"]["total_provider_call_limit"] == 246
    assert _maximum_reserved_cost(instrument) < instrument["execution"]["cost_stop_usd"]


def test_pilot_cases_are_exactly_stratified_and_source_linked(assets: dict) -> None:
    blueprints = assets["blueprints"]
    source_map = assets["source_map"]

    assert len(blueprints) == 100
    assert Counter(item["course_id"] for item in blueprints) == Counter(
        {f"dummy-course-{number:02d}": 5 for number in range(1, 21)}
    )
    assert all(item["checkpoint_stage"] == "pilot-100" for item in blueprints)
    assert all(
        set((*item["evidence_unit_ids"], *item["distractor_unit_ids"]))
        <= set(source_map)
        for item in blueprints
    )
    assert all(
        len(set(item["evidence_unit_ids"])) == 2
        for item in blueprints
        if item["slice"] == "multi-source"
    )


def test_preflight_is_explicitly_blocked_without_calls(
    assets: dict, tmp_path: Path
) -> None:
    preflight = build_preflight(assets, output_path=tmp_path / "unused.json")

    assert preflight["status"] == "blocked-not-authorized"
    assert preflight["provider_execution_authorized"] is False
    assert preflight["external_call_enabled"] is False
    assert preflight["checkpoint_1000_authorized"] is False
    assert preflight["scale_10000_authorized"] is False


def test_repository_freeze_does_not_allow_the_pilot() -> None:
    with pytest.raises(RepositoryFreezeError):
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)


def test_qwen_cannot_be_bound_without_a_registered_passing_result(
    tmp_path: Path,
) -> None:
    instrument = deepcopy(validate_instrument())
    reviewer = instrument["model_roles"]["independent_reviewer"]
    reviewer.update(
        {
            "provider_model": "qwen/qwen3.7-plus",
            "litellm_model": "openrouter/qwen/qwen3.7-plus",
            "qualification": "factual-qa-v3-reviewer-qualification-007",
        }
    )
    reviewer["provider_routing"] = {
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }
    path = tmp_path / "qwen-unqualified.json"
    path.write_text(json.dumps(instrument), encoding="utf-8")

    with pytest.raises(ScalePilotError, match="registered passing qualification"):
        validate_instrument(path)


def test_network_free_simulation_exercises_all_non_dispute_stages(
    assets: dict, tmp_path: Path
) -> None:
    output = tmp_path / "simulation.json"
    state = asyncio.run(
        execute(
            assets,
            transports=_simulation_transports(assets["instrument"]),
            output_path=output,
            simulation=True,
        )
    )

    assert state["status"] == "completed-keep"
    assert state["summary"]["failed_gates"] == []
    assert state["accounting"]["calls_attempted"] == 222
    assert len(state["results"]) == 100
    assert len(state["mutations"]) == 20
    assert len(state["human_priority_packet"]) == 12
    assert state["checkpoint_1000_authorized"] is False
    assert state["scale_10000_authorized"] is False


def test_failed_canary_records_invalid_result_and_zero_bulk_calls(
    assets: dict, tmp_path: Path
) -> None:
    instrument = assets["instrument"]
    transports = _simulation_transports(instrument)
    transports["author"] = SimulatedTransport(
        role="author",
        model=instrument["model_roles"]["author"]["provider_model"],
        fail_tasks={"factual_qa_v3_pilot_100_author_health"},
    )
    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=tmp_path / "canary.json",
            simulation=True,
        )
    )

    assert state["status"] == "invalid-execution"
    assert state["invalid_reason"] == "provider-canary-failed"
    assert state["accounting"]["calls_attempted"] == 1
    assert state["results"] == []
    assert transports["independent_reviewer"].calls == 0


def test_malformed_author_outputs_are_accounted_and_refine(
    assets: dict, tmp_path: Path
) -> None:
    instrument = assets["instrument"]
    transports = _simulation_transports(instrument)
    transports["author"] = SimulatedTransport(
        role="author",
        model=instrument["model_roles"]["author"]["provider_model"],
        malformed_tasks={"factual_qa_v3_pilot_100_author"},
    )
    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=tmp_path / "malformed.json",
            simulation=True,
        )
    )

    assert state["status"] == "completed-refine"
    assert len(state["results"]) == 100
    assert all(
        item["author_outcome"]["status"] == "malformed-response"
        for item in state["results"]
    )
    assert state["summary"]["metrics"]["malformed_response_rate"] > 0
    assert state["accounting"]["calls_attempted"] <= 246


def test_disputes_are_bounded_to_24_and_total_calls_to_246(
    assets: dict, tmp_path: Path
) -> None:
    instrument = assets["instrument"]
    transports = _simulation_transports(instrument)
    transports["independent_reviewer"] = SimulatedTransport(
        role="independent_reviewer",
        model=instrument["model_roles"]["independent_reviewer"]["provider_model"],
        invert_review_tasks={"factual_qa_v3_pilot_100_independent_review"},
    )
    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=tmp_path / "disputes.json",
            simulation=True,
        )
    )

    assert state["status"] == "completed-refine"
    assert sum(item["dispute_outcome"] is not None for item in state["results"]) == 24
    assert state["accounting"]["calls_attempted"] == 246
    assert state["summary"]["metrics"]["unresolved_dispute_rate"] == 0.76


def test_model_identity_drift_stops_at_canary(assets: dict, tmp_path: Path) -> None:
    instrument = assets["instrument"]
    transports = _simulation_transports(instrument)
    transports["author"] = SimulatedTransport(
        role="author",
        model="unexpected-model",
    )
    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=tmp_path / "identity.json",
            simulation=True,
        )
    )

    assert state["status"] == "invalid-execution"
    assert state["accounting"]["calls_attempted"] == 1
    assert state["results"] == []


def test_cost_stop_is_fail_closed(assets: dict, tmp_path: Path) -> None:
    instrument = assets["instrument"]
    transports = _simulation_transports(instrument)
    transports["author"] = SimulatedTransport(
        role="author",
        model=instrument["model_roles"]["author"]["provider_model"],
        cost_per_call=0.51,
    )
    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=tmp_path / "cost.json",
            simulation=True,
        )
    )

    assert state["status"] == "invalid-execution"
    assert state["accounting"]["calls_attempted"] == 1
    assert state["accounting"]["external_cost_usd"] == pytest.approx(0.51)


def test_running_checkpoint_resumes_without_repeating_accounting(
    assets: dict, tmp_path: Path
) -> None:
    output = tmp_path / "resume.json"
    with pytest.raises(PlannedInterruption):
        asyncio.run(
            execute(
                assets,
                transports=_simulation_transports(assets["instrument"]),
                output_path=output,
                simulation=True,
                stop_after_calls=10,
            )
        )
    checkpoint = json.loads(output.read_text(encoding="utf-8"))
    assert checkpoint["status"] == "running"
    assert checkpoint["accounting"]["calls_attempted"] == 10

    resumed = asyncio.run(
        execute(
            assets,
            transports=_simulation_transports(assets["instrument"]),
            output_path=output,
            simulation=True,
            resume=True,
        )
    )
    assert resumed["status"] == "completed-keep"
    assert resumed["accounting"]["calls_attempted"] == 222


def test_existing_output_and_invalid_resume_fail_closed(
    assets: dict, tmp_path: Path
) -> None:
    output = tmp_path / "existing.json"
    output.write_text("{}", encoding="utf-8")
    with pytest.raises(ScalePilotError, match="overwrite"):
        asyncio.run(
            execute(
                assets,
                transports=_simulation_transports(assets["instrument"]),
                output_path=output,
                simulation=True,
            )
        )

    invalid = tmp_path / "invalid-resume.json"
    invalid.write_text(
        json.dumps(
            {
                "run_type": INSTRUMENT_ID,
                "status": "running",
                "simulation": True,
                "bindings": {"tampered": True},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ScalePilotError, match="bindings drifted"):
        asyncio.run(
            execute(
                assets,
                transports=_simulation_transports(assets["instrument"]),
                output_path=invalid,
                simulation=True,
                resume=True,
            )
        )
