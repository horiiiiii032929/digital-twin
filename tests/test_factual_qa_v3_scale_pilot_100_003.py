from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from scripts.run_factual_qa_v3_scale_pilot_100 import (
    PlannedInterruption,
    SimulatedTransport,
)
from scripts.run_factual_qa_v3_scale_pilot_100_003 import (
    INSTRUMENT_ID,
    QuestionVariantSimulatedTransport,
    _simulation_transports,
    assemble_case,
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


def _live_metadata(instrument: dict) -> dict:
    roles = instrument["model_roles"]
    return {
        "deepseek": {
            "context_length": instrument["freshness"]["deepseek_context_length"],
            "maximum_output_tokens": instrument["freshness"][
                "deepseek_maximum_output_tokens"
            ],
            "models": {
                role["provider_model"]: {
                    "documented_revision": role["documented_revision"],
                    "peak_cache_miss_input_per_million_usd": role[
                        "pricing_usd_per_million_input_tokens"
                    ],
                    "peak_output_per_million_usd": role[
                        "pricing_usd_per_million_output_tokens"
                    ],
                }
                for role in (roles["author"], roles["dispute_reviewer"])
            },
        },
        "openrouter": {
            "model": roles["independent_reviewer"]["provider_model"],
            "context_length": instrument["freshness"][
                "openrouter_mistral_context_length"
            ],
            "input_per_million_usd": roles["independent_reviewer"][
                "pricing_usd_per_million_input_tokens"
            ],
            "output_per_million_usd": roles["independent_reviewer"][
                "pricing_usd_per_million_output_tokens"
            ],
        },
    }


def test_successor_is_reviewed_provider_unauthorized_and_frozen_out(
    assets: dict,
) -> None:
    instrument = validate_instrument()

    assert instrument["instrument_id"] == INSTRUMENT_ID
    assert instrument["status"] == "draft-reviewed-provider-execution-unauthorized"
    assert instrument["execution"]["provider_execution_authorized"] is False
    assert instrument["execution"]["automatic_stage_promotion"] is False
    assert assets["truth_artifact_sha256"] == instrument["truth_design"]["content_sha256"]

    with pytest.raises(RepositoryFreezeError):
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)


def test_preflight_is_blocked_before_live_or_paid_authorization(
    assets: dict, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(
        "scripts.run_factual_qa_v3_scale_pilot_100_003._working_tree_dirty",
        lambda: False,
    )

    preflight = build_preflight(assets, output_path=tmp_path / "unused.json")

    assert preflight["status"] == "blocked-not-authorized"
    assert preflight["provider_execution_authorized"] is False
    assert preflight["live_provider_match_checked"] is False
    assert preflight["external_call_enabled"] is False
    assert preflight["checkpoint_1000_authorized"] is False
    assert preflight["scale_10000_authorized"] is False


def test_expired_snapshot_blocks_an_otherwise_ready_preflight(
    assets: dict, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorized_assets = deepcopy(assets)
    instrument = authorized_assets["instrument"]
    instrument["status"] = "frozen-pending-execution"
    instrument["execution"]["provider_execution_authorized"] = True
    verified = datetime.fromisoformat(instrument["freshness"]["verified_at"])
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(
        "scripts.run_factual_qa_v3_scale_pilot_100_003._working_tree_dirty",
        lambda: False,
    )

    preflight = build_preflight(
        authorized_assets,
        output_path=tmp_path / "unused.json",
        live_metadata=_live_metadata(instrument),
        now=verified + timedelta(hours=25),
    )

    assert preflight["status"] == "blocked-provider-freshness"
    assert preflight["freshness_snapshot_current"] is False
    assert preflight["live_provider_match"] is True


def test_model_wording_cannot_mutate_authoritative_truth(assets: dict) -> None:
    truth = assets["truth_packages"][0]

    case, provenance = assemble_case(
        truth,
        question_variant="A completely new natural-language wording?",
    )

    assert case["question"] == "A completely new natural-language wording?"
    assert case["answer"] == truth["canonical_answer"]
    assert case["action"] == truth["expected_action"]
    assert case["selected_claim_ids"] == truth["selected_claim_ids"]
    assert case["citations"] == truth["citations"]
    assert provenance["truth_package_sha256"] == truth["truth_package_sha256"]


def test_normal_network_free_simulation_passes_all_successor_gates(
    assets: dict, tmp_path
) -> None:
    state = asyncio.run(
        execute(
            assets,
            transports=_simulation_transports(assets["instrument"]),
            output_path=tmp_path / "normal.json",
            simulation=True,
        )
    )

    assert state["status"] == "completed-keep"
    assert state["summary"]["failed_gates"] == []
    assert state["accounting"]["calls_attempted"] == 222
    assert state["summary"]["metrics"]["deterministic_acceptance_rate"] == 1.0
    assert state["summary"]["metrics"]["model_question_variant_acceptance_rate"] == 1.0
    assert state["summary"]["metrics"]["exact_duplicate_question_rate"] == 0.0
    assert len(state["mutations"]) == 20
    assert len(state["human_priority_packet"]) == 12


def test_malformed_authors_fall_back_without_mutating_truth(
    assets: dict, tmp_path
) -> None:
    transports = _simulation_transports(assets["instrument"])
    transports["author"] = QuestionVariantSimulatedTransport(
        model=assets["instrument"]["model_roles"]["author"]["provider_model"],
        malformed_tasks={"factual_qa_v3_pilot_100_003_author"},
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
    assert state["summary"]["metrics"]["deterministic_acceptance_rate"] == 1.0
    assert state["summary"]["metrics"]["deterministic_fallback_count"] == 100
    assert state["summary"]["metrics"]["model_question_variant_acceptance_rate"] == 0.0
    assert all(
        result["wording_provenance"]["wording_source"]
        == "deterministic-canonical-fallback"
        for result in state["results"]
    )
    assert len(state["mutations"]) == 20


def test_duplicate_model_questions_are_rejected_before_acceptance(
    assets: dict, tmp_path
) -> None:
    transports = _simulation_transports(assets["instrument"])
    transports["author"] = QuestionVariantSimulatedTransport(
        model=assets["instrument"]["model_roles"]["author"]["provider_model"],
        forced_question="What is the same repeated question?",
    )

    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=tmp_path / "duplicates.json",
            simulation=True,
        )
    )

    assert state["status"] == "completed-refine"
    assert state["summary"]["metrics"]["model_question_variant_acceptance_rate"] == 0.01
    assert state["summary"]["metrics"]["deterministic_fallback_count"] == 99
    assert state["summary"]["metrics"]["exact_duplicate_question_rate"] == 0.0
    assert sum(
        result["wording_provenance"]["variant_rejection_reason"]
        == "duplicate-normalized-question"
        for result in state["results"]
    ) == 99


def test_canary_identity_drift_stops_before_bulk_calls(assets: dict, tmp_path) -> None:
    transports = _simulation_transports(assets["instrument"])
    transports["author"] = QuestionVariantSimulatedTransport(model="unexpected-model")

    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=tmp_path / "identity.json",
            simulation=True,
        )
    )

    assert state["status"] == "invalid-execution"
    assert state["invalid_reason"] == "provider-model-identity-drift"
    assert state["accounting"]["calls_attempted"] == 1
    assert state["results"] == []


def test_maximum_dispute_path_is_bounded_to_246_calls(assets: dict, tmp_path) -> None:
    transports = _simulation_transports(assets["instrument"])
    transports["independent_reviewer"] = SimulatedTransport(
        role="independent_reviewer",
        model=assets["instrument"]["model_roles"]["independent_reviewer"][
            "provider_model"
        ],
        invert_review_tasks={"factual_qa_v3_pilot_100_003_independent_review"},
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
    assert state["accounting"]["calls_attempted"] == 246
    assert sum(result["dispute_outcome"] is not None for result in state["results"]) == 24
    assert state["summary"]["metrics"]["unresolved_dispute_rate"] == 0.76


def test_successor_resume_preserves_exact_truth_and_accounting(
    assets: dict, tmp_path
) -> None:
    output = tmp_path / "resume.json"
    with pytest.raises(PlannedInterruption):
        asyncio.run(
            execute(
                assets,
                transports=_simulation_transports(assets["instrument"]),
                output_path=output,
                simulation=True,
                stop_after_calls=3,
            )
        )

    state = asyncio.run(
        execute(
            assets,
            transports=_simulation_transports(assets["instrument"]),
            output_path=output,
            simulation=True,
            resume=True,
        )
    )

    assert state["status"] == "completed-keep"
    assert state["accounting"]["calls_attempted"] == 222
    assert len(state["results"]) == 100
    assert all(result["truth_package_sha256"] for result in state["results"])
