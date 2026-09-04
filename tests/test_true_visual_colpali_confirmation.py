from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_true_visual_colpali_confirmation as builder
from scripts import run_true_visual_colpali_confirmation as runner

_load_published_instrument = runner._instrument


def _authorized_instrument() -> dict[str, object]:
    instrument = json.loads(json.dumps(_load_published_instrument()))
    instrument["status"] = "frozen-pending-execution"
    instrument["provider_execution_authorized"] = True
    instrument["paid_execution_authorized"] = True
    return instrument


def test_fresh_visual_dataset_reconstructs_and_balances_modalities() -> None:
    dataset = builder.build_dataset(write_assets=False)
    builder.validate_dataset(dataset)

    assert dataset["cluster_count"] == 30
    assert dataset["answerable_case_count"] == 30
    assert dataset["boundary_case_count"] == 30
    assert {
        modality: sum(asset["modality"] == modality for asset in dataset["assets"])
        for modality in ("table", "equation", "diagram")
    } == {"table": 10, "equation": 10, "diagram": 10}


def test_network_free_simulation_passes_without_provider_calls() -> None:
    result = runner.simulate()

    assert result["provider_calls"] == 0
    assert result["status"] == "completed-go-deeper"
    assert result["candidate"]["complete_visual_evidence_at_3"] == 1.0
    assert result["candidate_original_region_lineage"] == 1.0
    assert result["boundary_evaluation_status"] == "deferred-to-actual-product-checkpoint"


def test_preflight_is_blocked_when_credential_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(runner, "_instrument", _authorized_instrument)
    monkeypatch.setattr(runner, "_git_clean", lambda: True)
    monkeypatch.setattr(runner, "_git_revision", lambda: "a" * 40)
    monkeypatch.setattr(runner, "DEFAULT_OUTPUT_ROOT", tmp_path)
    monkeypatch.delenv("JINA_API_KEY", raising=False)

    result = runner.preflight()

    assert result["network_calls_made"] == 0
    assert result["status"] == "blocked"
    assert "JINA_API_KEY is missing" in result["reasons"]
    assert result["reasons"] == ["JINA_API_KEY is missing"]


def test_account_token_quota_bounds_the_complete_run() -> None:
    quota = runner._quota_status(runner._instrument())

    assert quota == {
        "account_total_token_limit": 10_000_000,
        "run_worst_case_token_reservation": 1_966_080,
        "account_token_headroom_after_reservation": 8_033_920,
        "reservation_within_account_limit": True,
    }


def test_preflight_blocks_when_worst_case_reservation_exceeds_account_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instrument = _authorized_instrument()
    instrument["provider_binding"]["maximum_calls"] = 400
    monkeypatch.setattr(runner, "_instrument", lambda: instrument)
    monkeypatch.setattr(runner, "_metadata_is_fresh", lambda _: True)
    monkeypatch.setattr(runner, "_git_clean", lambda: True)
    monkeypatch.setattr(runner, "_git_revision", lambda: "a" * 40)
    monkeypatch.setattr(runner, "DEFAULT_OUTPUT_ROOT", tmp_path)
    monkeypatch.setenv("JINA_API_KEY", "test-only")

    result = runner.preflight()

    assert result["status"] == "blocked"
    assert result["reasons"] == [
        "run worst-case token reservation exceeds the account limit"
    ]
    assert result["network_calls_made"] == 0


def test_published_instrument_revokes_provider_authority() -> None:
    instrument = runner._instrument()

    assert instrument["status"] == "completed-go-deeper-authorization-revoked"
    assert instrument["provider_execution_authorized"] is False
    assert instrument["paid_execution_authorized"] is False


def test_dataset_rejects_boundary_lineage() -> None:
    dataset = json.loads(json.dumps(builder.build_dataset(write_assets=False)))
    boundary = next(case for case in dataset["cases"] if case["expected_action"] != "answer")
    boundary["required_asset_ids"] = [dataset["assets"][0]["asset_id"]]
    dataset["content_sha256"] = builder.canonical_sha256(
        {key: value for key, value in dataset.items() if key != "content_sha256"}
    )

    with pytest.raises(builder.VisualConfirmationBuildError, match="boundary"):
        builder.validate_dataset(dataset)


def test_render_paths_stay_hash_bound() -> None:
    dataset = builder.build_dataset(write_assets=False)
    for asset in dataset["assets"]:
        path = runner._render_path(asset)
        assert path.is_file()
        assert path.resolve().is_relative_to(Path(runner.ROOT))
