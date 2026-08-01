from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from scripts.seal_multimodal_benchmark import (
    choose_development_assets,
    write_exclusive,
)


def split_fixture() -> dict:
    assets = [
        {"asset_id": f"mm-asset-{name}", "course_id": course}
        for name, course in (
            ("alpha", "IT5001"),
            ("bravo", "IT5002"),
            ("charlie", "IT5003"),
            ("delta", "IT5004"),
            ("echo", "IT5007"),
            ("foxtrot", "IT5008"),
        )
    ]
    cases = [
        {"asset_id": "mm-asset-alpha", "slice": "visual_answerable", "modality": "diagram"},
        {"asset_id": "mm-asset-alpha", "slice": "text_control", "modality": "mixed"},
        {"asset_id": "mm-asset-bravo", "slice": "visual_answerable", "modality": "table"},
        {"asset_id": "mm-asset-bravo", "slice": "adversarial_integrity", "modality": "mixed"},
        {"asset_id": "mm-asset-charlie", "slice": "visual_answerable", "modality": "screenshot"},
        {"asset_id": "mm-asset-delta", "slice": "text_control", "modality": "mixed"},
        {"asset_id": "mm-asset-echo", "slice": "no_evidence", "modality": "mixed"},
        {"asset_id": "mm-asset-foxtrot", "slice": "adversarial_integrity", "modality": "mixed"},
    ]
    return {"source_assets": assets, "cases": cases}


def test_split_is_deterministic_and_keeps_page_cases_together() -> None:
    dataset = split_fixture()
    targets = {
        "visual_answerable": 2,
        "text_control": 1,
        "no_evidence": 0,
        "adversarial_integrity": 1,
    }

    first = choose_development_assets(
        dataset, development_cases=4, slice_targets=targets, seed="test-seed"
    )
    second = choose_development_assets(
        dataset, development_cases=4, slice_targets=targets, seed="test-seed"
    )

    assert first == second
    selected = [case for case in dataset["cases"] if case["asset_id"] in first]
    assert len(selected) == 4
    assert Counter(case["slice"] for case in selected) == Counter(targets)
    for asset in dataset["source_assets"]:
        memberships = {
            case["asset_id"] in first
            for case in dataset["cases"]
            if case["asset_id"] == asset["asset_id"]
        }
        assert len(memberships) == 1


def test_split_rejects_impossible_asset_grouping() -> None:
    with pytest.raises(ValueError, match="no asset-grouped split"):
        choose_development_assets(
            split_fixture(),
            development_cases=1,
            slice_targets={"visual_answerable": 1, "text_control": 1},
        )


def test_seal_write_is_exclusive(tmp_path: Path) -> None:
    target = tmp_path / "seal.json"
    artifacts = {"seal.json": (target, b"{}\n")}

    write_exclusive(artifacts)
    assert target.read_bytes() == b"{}\n"

    with pytest.raises(FileExistsError, match="already exist"):
        write_exclusive(artifacts)
