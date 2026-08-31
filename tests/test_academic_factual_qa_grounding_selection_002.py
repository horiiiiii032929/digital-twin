import json

import pytest

from scripts import academic_factual_qa_atomic_m2_t0_adapter as adapter
from scripts import build_academic_factual_qa_grounding_selection_002 as builder
from scripts import run_academic_factual_qa_grounding_selection_002 as runner
from src.digital_twin.evaluation.provider_json import DirectProviderJsonTransport


def test_grounding_selection_build_is_finite_and_gold_isolated() -> None:
    result = runner.validate()

    assert result["status"] == "passed-build-only"
    assert result["candidate_case_count"] == 500
    assert result["control_case_count"] == 100
    assert result["maximum_canary_calls"] == 2
    assert result["maximum_total_calls"] == 602
    assert result["hidden_gold_loaded"] is False
    assert result["adapter_version"] == adapter.ACTION_ROUTER_ADAPTER_VERSION
    binding = runner._load_hashed(runner.builder.BINDING)
    provider = binding["providers"]["high-volume-generator"]
    assert provider["first_party_endpoint"] is True
    DirectProviderJsonTransport(provider)
    assert runner.EXECUTION_ATTEMPT_ID.endswith("attempt-002")


def test_grounding_selection_rejects_adapter_manifest_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    manifest = json.loads(builder.CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    manifest["adapter_version"] = "v1"
    drifted = tmp_path / "manifest.json"
    drifted.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(builder, "CANDIDATE_MANIFEST", drifted)

    with pytest.raises(
        builder.GroundingSelectionBuildError,
        match="action-router adapter contract",
    ):
        builder.validate()


def test_action_router_factory_returns_the_versioned_successor_adapter() -> None:
    assert (
        adapter._adapter_type(successor=True).adapter_version  # noqa: SLF001
        == adapter.ACTION_ROUTER_ADAPTER_VERSION
    )
    assert adapter._adapter_type(successor=False).adapter_version == "v1"  # noqa: SLF001


def test_grounding_selection_simulations_stop_at_frozen_decisions() -> None:
    expected = {
        "pass": "completed-keep",
        "quality-failure": "completed-refine",
        "canary-failure": "invalid-execution",
        "provider-failure": "invalid-execution",
        "resume": "completed-keep",
    }

    for scenario, status in expected.items():
        result = runner.simulate(scenario=scenario)
        assert result["status"] == status
        assert result["gold_opened_before_responses"] is False
        assert result["provider_calls"] == 0
        assert result["network_calls"] == 0


def test_grounding_selection_preflight_makes_no_calls_before_live_execution() -> None:
    result = runner.preflight()

    assert result["status"] in {"ready", "blocked-not-authorized"}
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False
