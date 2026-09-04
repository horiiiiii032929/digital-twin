from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_true_visual_colpali_confirmation as builder
from scripts import run_true_visual_colpali_confirmation as runner


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


def test_preflight_is_blocked_when_credential_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_git_clean", lambda: True)
    monkeypatch.setattr(runner, "_git_revision", lambda: "a" * 40)
    monkeypatch.delenv("JINA_API_KEY", raising=False)

    result = runner.preflight()

    assert result["network_calls_made"] == 0
    assert result["status"] == "blocked"
    assert "JINA_API_KEY is missing" in result["reasons"]
    assert result["reasons"] == ["JINA_API_KEY is missing"]


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
