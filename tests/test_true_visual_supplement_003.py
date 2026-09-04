from __future__ import annotations

from scripts import run_true_visual_supplement_003 as runner
from src.digital_twin.evaluation.provider_json import ProviderJsonResponse


def test_frozen_successor_validation_and_simulation_remain_network_free() -> None:
    validation = runner.validate()
    simulation = runner.simulate()

    assert validation["asset_count"] == 30
    assert validation["case_count"] == 60
    assert validation["paid_execution_authorized"] is True
    assert validation["provider_calls"] == 0
    assert simulation["status"] == "completed-go-deeper"
    assert simulation["provider_calls"] == 0
    assert simulation["metrics"]["original_region_lineage_rate"] == 1.0


def test_duplicate_semantic_values_are_canonicalized_and_accounted() -> None:
    values, removed = runner._canonicalize_list(
        [" Router ", "router", "packet   queue", "Packet queue"]
    )

    assert values == ["Router", "packet queue"]
    assert removed == 2


def test_description_preserves_original_region_lineage_after_deduplication() -> None:
    asset = runner._dataset()["assets"][0]
    response = ProviderJsonResponse(
        content={
            "transcription": "A visible fact",
            "entities": ["router", "Router"],
            "relationships": ["A points to B"],
            "uncertainty": [],
        },
        provider_model=runner.historical.VISUAL_MODEL,
        provider_revision=runner.historical.VISUAL_MODEL,
        input_tokens=10,
        output_tokens=10,
        cost_usd=0.001,
        latency_ms=1,
    )

    row = runner._description_record(asset, response, transmitted_image_sha256="a" * 64)

    assert row["region_ids"] == [value["region_id"] for value in asset["region_lineage"]]
    assert row["semantic_list_duplicate_removal_count"] == 1
    assert row["description_segments"] == ["A visible fact", "router", "A points to B"]


def test_preflight_is_ready_after_fresh_metadata_and_bounded_authority(monkeypatch) -> None:
    monkeypatch.setattr(runner, "_repo_dirty", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _name: "/usr/bin/rsvg-convert")
    monkeypatch.setenv("OPENAI_API_KEY", "configured")
    result = runner.preflight(output_root=runner.ROOT / "reports/generated/unused-visual-003")

    assert result["status"] == "ready"
    assert result["blockers"] == []
