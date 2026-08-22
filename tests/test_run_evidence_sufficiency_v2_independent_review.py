from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path

import httpx
import pytest

import scripts.run_evidence_sufficiency_v2_independent_review as runner
from scripts.run_factual_qa_v3_scale_pilot_100 import PlannedInterruption


INSTRUMENT_004_PATH = Path(
    "research/05_evaluation/instruments/"
    "evidence_sufficiency_v2_independent_review_004.json"
)
INSTRUMENT_005_PATH = Path(
    "research/05_evaluation/instruments/"
    "evidence_sufficiency_v2_independent_review_005.json"
)
INSTRUMENT_006_PATH = Path(
    "research/05_evaluation/instruments/"
    "evidence_sufficiency_v2_independent_review_006.json"
)
INSTRUMENT_007_PATH = Path(
    "research/05_evaluation/instruments/"
    "evidence_sufficiency_v2_independent_review_007.json"
)


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
    supported_parameters = [
        "max_tokens",
        "response_format",
        "structured_outputs",
    ]
    if safety.get("temperature") is not None:
        supported_parameters.append("temperature")
    if safety.get("reasoning_effort") is not None:
        supported_parameters.append("reasoning_effort")
    if safety.get("seed") is not None:
        supported_parameters.append("seed")
    return {
        "verified_at": "2026-08-22T06:30:00+00:00",
        "registry": {
            "data": [
                {
                    "id": safety["reviewer_model"],
                    "context_length": safety["provider_context_window_tokens"],
                    "pricing": {
                        "prompt": str(
                            safety["pricing_usd_per_million_input_tokens"] / 1_000_000
                        ),
                        "completion": str(
                            safety["pricing_usd_per_million_output_tokens"] / 1_000_000
                        ),
                    },
                    "supported_parameters": supported_parameters,
                }
            ]
        },
        "endpoints": {
            "data": {
                "endpoints": [
                    {
                        "provider_name": safety.get(
                            "reviewer_endpoint_provider_name", "Mistral"
                        ),
                        "tag": safety.get("reviewer_endpoint_tag"),
                        "name": (
                            f"{safety.get('reviewer_endpoint_provider_name', 'Mistral')}"
                            f" | {safety.get('reviewer_backend_model', safety['reviewer_model'])}"
                        ),
                        "status": 0,
                        "context_length": safety["provider_context_window_tokens"],
                        "pricing": {
                            "prompt": str(
                                safety["pricing_usd_per_million_input_tokens"]
                                / 1_000_000
                            ),
                            "completion": str(
                                safety["pricing_usd_per_million_output_tokens"]
                                / 1_000_000
                            ),
                        },
                        "supported_parameters": supported_parameters,
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
    assert instrument["status"] == "invalid-execution-authorization-revoked"
    assert safety["provider_execution_authorized"] is False
    assert instrument["decision_rule"]["authorize_provider_execution"] is False


def test_native_openrouter_attempt_is_invalid_and_revoked() -> None:
    assets = runner.load_assets(INSTRUMENT_004_PATH)
    instrument = assets["instrument"]
    safety = instrument["execution_safety"]

    assert instrument["instrument_id"].endswith("-004")
    assert instrument["status"] == "invalid-execution-authorization-revoked"
    assert safety["provider_execution_authorized"] is False
    assert instrument["decision_rule"]["authorize_provider_execution"] is False
    assert safety["reviewer_transport"] == runner.NATIVE_OPENROUTER_TRANSPORT
    assert safety["reviewer_api_url"] == runner.OPENROUTER_CHAT_URL
    assert assets["packet"]["content_sha256"] == (
        "75fc54d28a708df7a36150f0519db6eb7429b6e625ebbde7feceecfa817f8fbd"
    )


def test_review_005_binds_stable_gemini_to_exact_google_endpoint() -> None:
    assets = runner.load_assets(INSTRUMENT_005_PATH)
    safety = assets["instrument"]["execution_safety"]

    assert assets["instrument"]["status"] == "reviewer-bound-provider-unauthorized"
    assert safety["provider_execution_authorized"] is False
    assert safety["reviewer_model"] == "google/gemini-3.7-flash"
    assert safety["reviewer_backend_model"] == ("google/gemini-3.7-flash-20260813")
    assert safety["provider_routing"] == {
        "order": ["google-ai-studio"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }
    assert safety["maximum_reserved_cost_usd"] == 0.39
    assert assets["packet"]["content_sha256"] == (
        "94fad389cdddbb6c1e10f45a8e6d18f11e84d570195855010c293009ab146efb"
    )


def test_review_006_is_invalid_revoked_and_binds_snapshot_gpt_endpoint() -> None:
    assets = runner.load_assets(INSTRUMENT_006_PATH)
    safety = assets["instrument"]["execution_safety"]

    assert assets["instrument"]["status"] == "invalid-execution-authorization-revoked"
    assert safety["provider_execution_authorized"] is False
    assert (
        assets["instrument"]["decision_rule"]["authorize_provider_execution"] is False
    )
    assert safety["reviewer_model"] == "openai/gpt-5.4-mini"
    assert safety["reviewer_backend_model"] == "openai/gpt-5.4-mini-20260317"
    assert safety["temperature"] is None
    assert safety["reasoning_effort"] == "none"
    assert safety["seed"] == 0
    assert safety["provider_routing"] == {
        "order": ["openai"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }
    assert safety["maximum_reserved_cost_usd"] == 0.429
    assert assets["packet"]["content_sha256"] == (
        "40c8bea9f9316a12b1a55fba8aadaac82a6a8434c70499c8ee0aafd8eb94a64e"
    )


@pytest.mark.asyncio
async def test_review_006_native_request_omits_temperature_and_pins_reasoning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets = runner.load_assets(INSTRUMENT_006_PATH)
    binding = runner._provider_binding(assets["instrument"])
    captured = {}

    async def post(**kwargs):
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={
                "id": "gen-synthetic",
                "model": "openai/gpt-5.4-mini",
                "system_fingerprint": "fp-synthetic",
                "choices": [{"message": {"content": '{"judgments": []}'}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 3,
                    "cost": 0.0000225,
                },
            },
            request=httpx.Request("POST", runner.OPENROUTER_CHAT_URL),
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-key")
    transport = runner.NativeOpenRouterReviewTransport(binding, post=post)
    await transport.call(
        system="Synthetic system message.",
        prompt='{"items": []}',
        task="synthetic_review",
        schema=runner._response_schema(1),
    )

    assert "temperature" not in captured["json"]
    assert captured["json"]["reasoning"] == {"effort": "none", "exclude": True}
    assert captured["json"]["seed"] == 0
    assert captured["json"]["provider"]["order"] == ["openai"]


def test_review_007_is_invalid_revoked_with_resilient_same_model_contract() -> None:
    assets = runner.load_assets(INSTRUMENT_007_PATH)
    safety = assets["instrument"]["execution_safety"]

    assert assets["instrument"]["status"] == "invalid-execution-authorization-revoked"
    assert safety["provider_execution_authorized"] is False
    assert assets["instrument"]["decision_rule"]["authorize_provider_execution"] is False
    assert safety["reviewer_model"] == "openai/gpt-5.4-mini"
    assert safety["reviewer_backend_model"] == "openai/gpt-5.4-mini-20260317"
    assert safety["reasoning_effort"] is None
    assert safety["seed"] is None
    assert safety["provider_routing"] == {
        "order": ["openai", "azure"],
        "allow_fallbacks": True,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }
    assert safety["maximum_reserved_cost_usd"] == 0.858
    assert safety["maximum_cost_usd"] == 1.5
    assert assets["packet"]["content_sha256"] == (
        "a6cdda77cb824cc620577cc1fcab23ec17166fa78ba525faaf3ff811b062eed7"
    )


@pytest.mark.asyncio
async def test_review_007_request_omits_nonessential_sampling_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets = runner.load_assets(INSTRUMENT_007_PATH)
    binding = runner._provider_binding(assets["instrument"])
    captured = {}

    async def post(**kwargs):
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={
                "id": "gen-synthetic",
                "model": "openai/gpt-5.4-mini",
                "system_fingerprint": "fp-synthetic",
                "choices": [{"message": {"content": '{"judgments": []}'}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 3,
                    "cost": 0.0000225,
                },
            },
            request=httpx.Request("POST", runner.OPENROUTER_CHAT_URL),
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-key")
    transport = runner.NativeOpenRouterReviewTransport(binding, post=post)
    await transport.call(
        system="Synthetic system message.",
        prompt='{"items": []}',
        task="synthetic_review",
        schema=runner._response_schema(1),
    )

    assert "temperature" not in captured["json"]
    assert "reasoning" not in captured["json"]
    assert "seed" not in captured["json"]
    assert captured["json"]["provider"] == {
        "order": ["openai", "azure"],
        "allow_fallbacks": True,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }


@pytest.mark.asyncio
async def test_native_openrouter_transport_matches_official_request_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets = runner.load_assets(INSTRUMENT_004_PATH)
    binding = runner._provider_binding(assets["instrument"])
    captured = {}

    async def post(**kwargs):
        captured.update(kwargs)
        return httpx.Response(
            200,
            headers={
                "X-Request-Id": "req-synthetic",
                "X-Generation-Id": "gen-synthetic",
            },
            json={
                "id": "gen-synthetic",
                "model": "mistralai/mistral-small-2603",
                "system_fingerprint": "fp-synthetic",
                "choices": [{"message": {"content": '{"judgments": []}'}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 3,
                    "cost": 0.0000036,
                },
                "openrouter_metadata": {
                    "requested": "mistralai/mistral-small-2603",
                    "strategy": "direct",
                    "attempt": 1,
                    "endpoints": {
                        "available": [{"provider": "Mistral", "selected": True}]
                    },
                },
            },
            request=httpx.Request("POST", runner.OPENROUTER_CHAT_URL),
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-key")
    transport = runner.NativeOpenRouterReviewTransport(binding, post=post)
    schema = runner._response_schema(1)

    raw = await transport.call(
        system="Synthetic system message.",
        prompt='{"items": []}',
        task="synthetic_review",
        schema=schema,
    )

    assert captured["url"] == runner.OPENROUTER_CHAT_URL
    assert captured["headers"]["Authorization"] == "Bearer synthetic-test-key"
    assert captured["headers"]["X-OpenRouter-Metadata"] == "enabled"
    assert captured["json"]["model"] == "mistralai/mistral-small-2603"
    assert captured["json"]["provider"] == {
        "order": ["Mistral"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }
    assert captured["json"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "evidence_sufficiency_review_1",
            "strict": True,
            "schema": schema,
        },
    }
    assert raw.provider_model == "mistralai/mistral-small-2603"
    assert raw.approximate_cost_usd == 0.0000036
    assert raw.request_id == "req-synthetic"
    assert raw.generation_id == "gen-synthetic"
    assert raw.openrouter_metadata["attempt"] == 1


@pytest.mark.asyncio
async def test_native_openrouter_error_is_preserved_without_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assets = runner.load_assets(INSTRUMENT_004_PATH)
    binding = runner._provider_binding(assets["instrument"])

    async def post(**kwargs):
        assert kwargs["headers"]["Authorization"] == "Bearer synthetic-test-key"
        return httpx.Response(
            401,
            headers={
                "X-Request-Id": "req-error",
                "X-Generation-Id": "gen-error",
            },
            json={
                "error": {
                    "code": 401,
                    "message": "Upstream Mistral authentication failed",
                },
                "openrouter_metadata": {
                    "requested": "mistralai/mistral-small-2603",
                    "attempt": 1,
                    "attempts": [{"provider": "Mistral", "status": 401}],
                },
            },
            request=httpx.Request("POST", runner.OPENROUTER_CHAT_URL),
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-key")
    output = tmp_path / "native-error.json"
    result = await runner.execute(
        assets,
        transport=runner.NativeOpenRouterReviewTransport(binding, post=post),
        output_path=output,
        simulation=False,
    )

    assert result["status"] == "invalid-execution"
    assert result["accounting"]["calls_attempted"] == 1
    assert result["accounting"]["calls_with_provider_response"] == 0
    assert result["sensitivity_outcome"] == {
        "status": "provider-error",
        "error_type": "OpenRouterRequestError",
        "value": None,
        "call": None,
        "error_code": "401",
        "error_detail": "Upstream Mistral authentication failed",
        "http_status": 401,
        "request_id": "req-error",
        "generation_id": "gen-error",
        "openrouter_metadata": {
            "requested": "mistralai/mistral-small-2603",
            "attempt": 1,
            "attempts": [{"provider": "Mistral", "status": 401}],
        },
    }
    assert "synthetic-test-key" not in output.read_text(encoding="utf-8")


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

    assert "reviewer-endpoint-context-drift" in result["live_provider_failures"]
    assert "provider-metadata-not-current" in result["blockers"]


def test_preflight_detects_exact_backend_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assets = runner.load_assets(INSTRUMENT_006_PATH)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(runner, "_working_tree_dirty", lambda: False)
    live = _live_metadata(assets)
    live["endpoints"]["data"]["endpoints"][0]["name"] = (
        "OpenAI | openai/gpt-5.4-mini-unexpected"
    )
    verified = datetime.fromisoformat(
        assets["instrument"]["execution_safety"]["reviewer_verified_at"]
    )

    result = runner.build_preflight(
        assets,
        output_path=tmp_path / "backend-drift.json",
        live_metadata=live,
        now=verified + timedelta(hours=1),
    )

    assert "reviewer-backend-model-drift" in result["live_provider_failures"]
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
