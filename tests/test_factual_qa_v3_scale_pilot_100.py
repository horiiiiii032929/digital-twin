from __future__ import annotations

import asyncio
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.run_factual_qa_v3_scale_pilot_100 import (
    AUTHOR_SCHEMA,
    INSTRUMENT_ID,
    REVIEW_SCHEMA,
    PlannedInterruption,
    ScalePilotError,
    SimulatedTransport,
    _author_prompt,
    _maximum_reserved_cost,
    _review_prompt,
    _simulation_transports,
    build_mutations,
    build_preflight,
    canonical_authored_case,
    deterministic_record,
    execute,
    load_assets,
    validate_authored,
    validate_instrument,
)
from scripts.run_factual_qa_quality_pilot import (
    AUTHOR_SCHEMA as QUALIFIED_AUTHOR_SCHEMA,
    REVIEW_SCHEMA as QUALIFIED_REVIEW_SCHEMA,
)
from scripts.run_factual_qa_v3_scale_rehearsal import _strict_review_prompt
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


@pytest.fixture(scope="module")
def assets() -> dict:
    return load_assets()


def test_successor_instrument_is_frozen_and_price_bounded(assets: dict) -> None:
    instrument = assets["instrument"]

    assert instrument["instrument_id"] == INSTRUMENT_ID
    assert instrument["status"] == "frozen-pending-execution"
    assert instrument["execution"]["provider_execution_authorized"] is True
    assert instrument["execution"]["dataset_write_authorized"] is False
    assert instrument["execution"]["automatic_stage_promotion"] is False
    assert instrument["execution"]["total_provider_call_limit"] == 246
    assert instrument["execution"]["cost_stop_usd"] == 3.0
    assert _maximum_reserved_cost(instrument) < instrument["execution"]["cost_stop_usd"]
    assert instrument["contract_design"] == {
        "version": "factual-qa-v3-contract-v2",
        "author_schema": "shared-full-json-schema",
        "reviewer_contract": "qualification-006-strict-contract",
        "mutation_basis": "deterministic-canonical-cases",
    }


def test_author_and_reviewer_use_shared_full_contracts(assets: dict) -> None:
    blueprint = assets["blueprints"][0]
    source_map = assets["source_map"]
    authored = canonical_authored_case(blueprint, source_map=source_map)

    assert AUTHOR_SCHEMA is QUALIFIED_AUTHOR_SCHEMA
    assert REVIEW_SCHEMA is QUALIFIED_REVIEW_SCHEMA
    assert _review_prompt(blueprint, authored, source_map=source_map) == (
        _strict_review_prompt(
            blueprint,
            authored=authored,
            source_context={
                "approved_sources": [
                    source_map[source_id]
                    for source_id in blueprint["evidence_unit_ids"]
                ],
                "distractors": [
                    source_map[source_id]
                    for source_id in blueprint["distractor_unit_ids"]
                ],
            },
        )
    )
    prompt = json.loads(_author_prompt(blueprint, source_map=source_map))
    assert prompt["requirements"]["output_contract"][
        "citation_object_exact_keys"
    ] == ["source_unit_id", "quote"]


@pytest.mark.parametrize(
    "invalid_citations",
    [
        ["source as a string"],
        [{"claim_id": "claim", "evidence_quote": "quote"}],
        [{"source_unit_id": "source"}],
        [{"source_unit_id": "source", "quote": "quote", "extra": True}],
    ],
)
def test_author_validator_rejects_every_observed_bad_citation_shape(
    invalid_citations: list,
) -> None:
    value = {
        "question": "Question?",
        "answer": "Answer.",
        "action": "answer",
        "selected_claim_ids": ["claim"],
        "citations": invalid_citations,
    }

    with pytest.raises(ScalePilotError, match="citation"):
        validate_authored(value)


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


def test_authorized_preflight_is_ready_without_calls(
    assets: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(
        "scripts.run_factual_qa_v3_scale_pilot_100._working_tree_dirty",
        lambda: False,
    )
    preflight = build_preflight(assets, output_path=tmp_path / "unused.json")

    assert preflight["status"] == "ready"
    assert preflight["provider_execution_authorized"] is True
    assert preflight["external_call_enabled"] is False
    assert preflight["checkpoint_1000_authorized"] is False
    assert preflight["scale_10000_authorized"] is False


def test_repository_freeze_authorizes_only_the_frozen_successor() -> None:
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
    assert len(state["mutations"]) == 20
    assert all(
        mutation["deterministic"]["passed"] is False
        and mutation["review_outcome"]["status"] == "complete"
        for mutation in state["mutations"]
    )
    assert state["accounting"]["calls_attempted"] <= 246


def test_mutations_are_built_from_deterministic_controls_not_author_results(
    assets: dict,
) -> None:
    blueprints = assets["blueprints"]
    source_map = assets["source_map"]
    mutations = build_mutations(
        blueprints,
        blueprints_by_id={item["blueprint_id"]: item for item in blueprints},
        source_map=source_map,
    )

    assert len(mutations) == 20
    for mutation in mutations:
        blueprint = next(
            item
            for item in blueprints
            if item["blueprint_id"] == mutation["blueprint_id"]
        )
        assert deterministic_record(
            blueprint, mutation["control_case"], source_map=source_map
        )["passed"]
        assert mutation["deterministic"]["passed"] is False


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
        cost_per_call=3.0,
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
    assert state["accounting"]["external_cost_usd"] == pytest.approx(3.0)


def test_pre_call_cost_guard_stops_resume_without_another_call(
    assets: dict, tmp_path: Path
) -> None:
    output = tmp_path / "pre-call-cost.json"
    with pytest.raises(PlannedInterruption):
        asyncio.run(
            execute(
                assets,
                transports=_simulation_transports(assets["instrument"]),
                output_path=output,
                simulation=True,
                stop_after_calls=1,
            )
        )
    checkpoint = json.loads(output.read_text(encoding="utf-8"))
    checkpoint["accounting"]["external_cost_usd"] = 3.0
    checkpoint["status"] = "running"
    output.write_text(json.dumps(checkpoint), encoding="utf-8")
    transports = _simulation_transports(assets["instrument"])

    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=output,
            simulation=True,
            resume=True,
        )
    )

    assert state["status"] == "invalid-execution"
    assert state["invalid_reason"] == "cost-stop-reached-before-call"
    assert sum(transport.calls for transport in transports.values()) == 0


def test_reported_token_limit_violations_are_recorded(
    assets: dict, tmp_path: Path
) -> None:
    instrument = assets["instrument"]
    transports = _simulation_transports(instrument)
    transports["author"] = SimulatedTransport(
        role="author",
        model=instrument["model_roles"]["author"]["provider_model"],
        output_tokens=701,
    )
    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=tmp_path / "token-limit.json",
            simulation=True,
        )
    )

    assert state["accounting"]["output_token_limit_exceeded_count"] == 101
    assert state["accounting"]["token_limit_exceeded_call_count"] == 101
    call = state["canaries"]["author"]["call"]
    assert call["requested_max_output_tokens"] == 700
    assert call["output_tokens"] == 701
    assert call["output_token_limit_exceeded"] is True


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
