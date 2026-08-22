from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path

import pytest

import scripts.run_evidence_sufficiency_v2_independent_review as runner
from scripts.run_factual_qa_v3_scale_pilot_100 import PlannedInterruption


@pytest.fixture
def assets() -> dict:
    return runner.load_assets()


def _verdicts(assets: dict) -> dict[str, str]:
    return {
        item_id: expected["expected_verdict"]
        for item_id, expected in assets["packet"]["sensitivity_scoring_key"].items()
    }


def _transport(assets: dict, **kwargs) -> runner.SimulatedReviewTransport:
    return runner.SimulatedReviewTransport(
        model=assets["instrument"]["execution_safety"]["reviewer_model"],
        verdicts=_verdicts(assets),
        **kwargs,
    )


def _live_metadata(assets: dict) -> dict:
    safety = assets["instrument"]["execution_safety"]
    return {
        "verified_at": "2026-08-22T06:30:00+00:00",
        "registry": {
            "data": [
                {
                    "id": safety["reviewer_model"],
                    "context_length": 262_144,
                    "pricing": {
                        "prompt": "0.00000015",
                        "completion": "0.0000006",
                    },
                    "supported_parameters": [
                        "max_tokens",
                        "response_format",
                        "structured_outputs",
                        "temperature",
                    ],
                }
            ]
        },
        "endpoints": {
            "data": {
                "endpoints": [
                    {
                        "provider_name": "Mistral",
                        "status": 0,
                        "context_length": 262_144,
                        "pricing": {
                            "prompt": "0.00000015",
                            "completion": "0.0000006",
                        },
                        "supported_parameters": [
                            "max_tokens",
                            "response_format",
                            "structured_outputs",
                            "temperature",
                        ],
                    }
                ]
            }
        },
    }


def test_runner_contract_binds_exact_packet_and_limits(assets: dict) -> None:
    instrument = assets["instrument"]
    safety = instrument["execution_safety"]

    assert assets["packet"]["content_sha256"] == (
        "90c177ae9dc158396af0e7be6bc393cc894b8f1b6cc278648682a86c9906215b"
    )
    assert len(assets["packet"]["review_batches"]) == 12
    assert len(assets["packet"]["sensitivity_items"]) == 12
    assert safety["maximum_calls"] == 13
    assert safety["maximum_reserved_cost_usd"] == 0.0702
    assert safety["maximum_cost_usd"] == 0.5
    assert instrument["status"] == "frozen-pending-execution"
    assert safety["provider_execution_authorized"] is True
    assert instrument["decision_rule"]["authorize_provider_execution"] is True


def test_provider_transport_disables_retries_and_fallbacks(assets: dict) -> None:
    transport = runner.ProviderReviewTransport(
        runner._provider_binding(assets["instrument"])
    )

    assert transport.client.provider_options["num_retries"] == 0
    assert transport.client.provider_options["extra_body"]["provider"] == {
        "order": ["Mistral"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }
    assert transport.client.response_format is None


def test_strict_response_format_is_bound_to_each_batch_schema(assets: dict) -> None:
    binding = runner._provider_binding(assets["instrument"])
    schema = runner._response_schema(12)

    response_format = runner._response_format_for_call(binding, schema)

    assert response_format == {
        "type": "json_schema",
        "json_schema": {
            "name": "evidence_sufficiency_review_12",
            "strict": True,
            "schema": schema,
        },
    }


def test_historical_review_002_remains_loadable() -> None:
    historical_path = (
        Path(__file__).resolve().parents[1] / "research/05_evaluation/instruments/"
        "evidence_sufficiency_v2_independent_review_002.json"
    )

    historical = runner.load_assets(historical_path)

    assert historical["instrument"]["instrument_id"].endswith("-002")
    assert historical["packet"]["content_sha256"] == (
        "3bac86bede6b03d3d9963ff477d2c9dd4a6c4b06a58393ad77469be8c3bd4a67"
    )
    assert (
        runner._provider_binding(historical["instrument"])["response_format_mode"]
        == "json-object-prompt-schema"
    )


def test_network_free_simulation_completes_all_13_calls(
    assets: dict, tmp_path: Path
) -> None:
    output = tmp_path / "simulation.json"
    state = asyncio.run(
        runner.execute(
            assets,
            transport=_transport(assets),
            output_path=output,
            simulation=True,
        )
    )

    assert state["status"] == "simulation-completed"
    assert state["accounting"]["calls_attempted"] == 13
    assert len(state["judgments"]) == 132
    assert state["summary"]["provider_or_model_calls"] == 0
    assert state["summary"]["gates"] == {
        "response_contract_valid": True,
        "clean_specificity": True,
        "defect_detection": True,
        "review_coverage": True,
        "unresolved_clear": True,
    }
    assert state["summary"]["freeze_eligible"] is False


def test_sensitivity_failure_stops_before_bulk_calls(
    assets: dict, tmp_path: Path
) -> None:
    verdicts = _verdicts(assets)
    clean_id = next(
        item_id
        for item_id, expected in assets["packet"]["sensitivity_scoring_key"].items()
        if expected["expected_verdict"] == "approve"
    )
    verdicts[clean_id] = "revise"
    transport = runner.SimulatedReviewTransport(
        model=assets["instrument"]["execution_safety"]["reviewer_model"],
        verdicts=verdicts,
    )

    state = asyncio.run(
        runner.execute(
            assets,
            transport=transport,
            output_path=tmp_path / "sensitivity-fail.json",
            simulation=True,
        )
    )

    assert state["status"] == "completed-reviewer-unreliable"
    assert state["accounting"]["calls_attempted"] == 1
    assert state["batch_outcomes"] == []


@pytest.mark.parametrize(
    ("transport_kwargs", "expected_reason"),
    [
        ({"malformed_call": 1}, "malformed-review-response"),
        ({"provider_error_call": 1}, "provider-error"),
        ({"identity_drift_call": 1}, "provider-model-identity-drift"),
    ],
)
def test_sensitivity_operational_failure_stops_bulk(
    assets: dict,
    tmp_path: Path,
    transport_kwargs: dict,
    expected_reason: str,
) -> None:
    state = asyncio.run(
        runner.execute(
            assets,
            transport=_transport(assets, **transport_kwargs),
            output_path=tmp_path / f"{expected_reason}.json",
            simulation=True,
        )
    )

    assert state["status"] == "invalid-execution"
    assert state["invalid_reason"] == expected_reason
    assert state["accounting"]["calls_attempted"] == 1
    assert state["batch_outcomes"] == []
    if expected_reason == "malformed-review-response":
        assert state["sensitivity_outcome"]["raw_response_content"] == "not-json"
        assert state["sensitivity_outcome"]["error_detail"]


def test_malformed_bulk_response_preserves_prior_accounting(
    assets: dict, tmp_path: Path
) -> None:
    state = asyncio.run(
        runner.execute(
            assets,
            transport=_transport(assets, malformed_call=2),
            output_path=tmp_path / "malformed-bulk.json",
            simulation=True,
        )
    )

    assert state["status"] == "invalid-execution"
    assert state["invalid_reason"] == "malformed-review-response"
    assert state["accounting"]["calls_attempted"] == 2
    assert state["accounting"]["calls_with_provider_response"] == 2
    assert len(state["judgments"]) == 12
    assert state["batch_outcomes"][0]["raw_response_content"] == "not-json"
    assert state["batch_outcomes"][0]["error_detail"]


def test_cost_overshoot_is_recorded_and_stops(assets: dict, tmp_path: Path) -> None:
    state = asyncio.run(
        runner.execute(
            assets,
            transport=_transport(assets, cost_per_call=0.6),
            output_path=tmp_path / "cost-stop.json",
            simulation=True,
        )
    )

    assert state["status"] == "invalid-execution"
    assert state["invalid_reason"] == "cost-ceiling-exceeded"
    assert state["accounting"]["external_cost_usd"] == pytest.approx(0.6)
    assert state["accounting"]["calls_attempted"] == 1


def test_interruption_resumes_from_exact_checkpoint(
    assets: dict, tmp_path: Path
) -> None:
    output = tmp_path / "resume.json"
    with pytest.raises(PlannedInterruption):
        asyncio.run(
            runner.execute(
                assets,
                transport=_transport(assets),
                output_path=output,
                simulation=True,
                stop_after_calls=2,
            )
        )

    checkpoint = json.loads(output.read_text(encoding="utf-8"))
    assert checkpoint["status"] == "running"
    assert checkpoint["accounting"]["calls_attempted"] == 2

    resumed_transport = _transport(assets)
    state = asyncio.run(
        runner.execute(
            assets,
            transport=resumed_transport,
            output_path=output,
            simulation=True,
            resume=True,
        )
    )

    assert state["status"] == "simulation-completed"
    assert state["accounting"]["calls_attempted"] == 13
    assert resumed_transport.calls == 11


def test_resume_rejects_binding_drift(assets: dict, tmp_path: Path) -> None:
    output = tmp_path / "binding-drift.json"
    with pytest.raises(PlannedInterruption):
        asyncio.run(
            runner.execute(
                assets,
                transport=_transport(assets),
                output_path=output,
                simulation=True,
                stop_after_calls=1,
            )
        )
    state = json.loads(output.read_text(encoding="utf-8"))
    state["bindings"]["packet_sha256"] = "drifted"
    output.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(runner.ReviewRunnerError, match="bindings drifted"):
        asyncio.run(
            runner.execute(
                assets,
                transport=_transport(assets),
                output_path=output,
                simulation=True,
                resume=True,
            )
        )


def test_preflight_reports_authorization_boundaries(
    assets: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unauthorized = deepcopy(assets)
    unauthorized["instrument"]["status"] = "reviewer-bound-provider-unauthorized"
    unauthorized["instrument"]["execution_safety"]["provider_execution_authorized"] = (
        False
    )
    unauthorized["instrument"]["decision_rule"]["authorize_provider_execution"] = False
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(runner, "_working_tree_dirty", lambda: False)
    monkeypatch.setattr(runner, "BOUNDED_PILOT_AUTHORIZATIONS", {})
    verified = datetime.fromisoformat(
        unauthorized["instrument"]["execution_safety"]["reviewer_verified_at"]
    )

    result = runner.build_preflight(
        unauthorized,
        output_path=tmp_path / "unused.json",
        live_metadata=_live_metadata(assets),
        now=verified + timedelta(hours=1),
    )

    assert result["status"] == "blocked-not-authorized"
    assert result["blockers"] == [
        "provider-review-not-authorized",
        "instrument-not-frozen",
        "bounded-freeze-authorization-missing",
    ]
    assert result["credential_present"] is True
    assert result["credential_value_emitted"] is False
    assert result["provider_or_model_calls"] == 0


def test_authorized_preflight_is_ready_only_with_every_gate(
    assets: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorized = deepcopy(assets)
    authorized["instrument"]["status"] = "frozen-pending-execution"
    authorized["instrument"]["execution_safety"]["provider_execution_authorized"] = True
    authorized["instrument"]["decision_rule"]["authorize_provider_execution"] = True
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(runner, "_working_tree_dirty", lambda: False)
    monkeypatch.setattr(
        runner,
        "BOUNDED_PILOT_AUTHORIZATIONS",
        {runner.INSTRUMENT_ID: ("external_model_evaluation",)},
    )
    verified = datetime.fromisoformat(
        authorized["instrument"]["execution_safety"]["reviewer_verified_at"]
    )

    result = runner.build_preflight(
        authorized,
        output_path=tmp_path / "ready.json",
        live_metadata=_live_metadata(authorized),
        now=verified + timedelta(hours=1),
    )

    assert result["status"] == "ready"
    assert result["blockers"] == []
    assert result["planned_calls"] == 13
    assert result["maximum_reserved_cost_usd"] == 0.0702


def test_preflight_fails_closed_for_stale_metadata(
    assets: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(runner, "_working_tree_dirty", lambda: False)
    verified = datetime.fromisoformat(
        assets["instrument"]["execution_safety"]["reviewer_verified_at"]
    )

    result = runner.build_preflight(
        assets,
        output_path=tmp_path / "stale.json",
        live_metadata=_live_metadata(assets),
        now=verified + timedelta(hours=24, seconds=1),
    )

    assert result["metadata_fresh"] is False
    assert "provider-metadata-not-current" in result["blockers"]


def test_preflight_detects_live_price_drift(
    assets: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(runner, "_working_tree_dirty", lambda: False)
    live = _live_metadata(assets)
    live["registry"]["data"][0]["pricing"]["prompt"] = "0.00000016"
    verified = datetime.fromisoformat(
        assets["instrument"]["execution_safety"]["reviewer_verified_at"]
    )

    result = runner.build_preflight(
        assets,
        output_path=tmp_path / "price-drift.json",
        live_metadata=live,
        now=verified + timedelta(hours=1),
    )

    assert "reviewer-input-price-drift" in result["live_provider_failures"]
    assert "provider-metadata-not-current" in result["blockers"]


def test_preflight_detects_endpoint_context_drift(
    assets: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(runner, "_working_tree_dirty", lambda: False)
    live = _live_metadata(assets)
    live["endpoints"]["data"]["endpoints"][0]["context_length"] = 131_072
    verified = datetime.fromisoformat(
        assets["instrument"]["execution_safety"]["reviewer_verified_at"]
    )

    result = runner.build_preflight(
        assets,
        output_path=tmp_path / "context-drift.json",
        live_metadata=live,
        now=verified + timedelta(hours=1),
    )

    assert "mistral-endpoint-context-drift" in result["live_provider_failures"]
    assert "provider-metadata-not-current" in result["blockers"]


def test_preflight_detects_existing_output(
    assets: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "exists.json"
    output.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(runner, "_working_tree_dirty", lambda: False)
    verified = datetime.fromisoformat(
        assets["instrument"]["execution_safety"]["reviewer_verified_at"]
    )

    result = runner.build_preflight(
        assets,
        output_path=output,
        live_metadata=_live_metadata(assets),
        now=verified + timedelta(hours=1),
    )

    assert "output-path-already-exists" in result["blockers"]
