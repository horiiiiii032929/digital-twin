from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest

from scripts.seal_multimodal_benchmark import write_exclusive
from src.digital_twin.evaluation.multimodal_benchmark import (
    DEVELOPMENT_CASES,
    SEAL_ID,
    MultimodalSealError,
    canonical_bytes,
    choose_development_assets,
    load_sealed_development,
    sha256_bytes,
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


def write_loader_fixture(tmp_path: Path) -> tuple[Path, Path]:
    sealed = tmp_path / "sealed"
    sealed.mkdir()
    development = {
        "dataset_status": "sealed",
        "cases": [
            {
                "case_id": f"mmr1-test-case-{index:02d}",
                "split": "development",
                "review": {"researcher_verified": True},
            }
            for index in range(DEVELOPMENT_CASES)
        ],
    }
    development_bytes = canonical_bytes(development)
    (sealed / "development.json").write_bytes(development_bytes)
    (sealed / "heldout.json").write_text("must not be read", encoding="utf-8")
    heldout_hash = "a" * 64
    ledger = {
        "seal_id": SEAL_ID,
        "heldout_sha256": heldout_hash,
        "status": "unopened",
        "attempts": [],
    }
    ledger_bytes = canonical_bytes(ledger)
    ledger_path = sealed / "heldout_once_ledger.json"
    ledger_path.write_bytes(ledger_bytes)
    seal = {
        "seal_id": SEAL_ID,
        "development_path": "sealed/development.json",
        "development_sha256": sha256_bytes(development_bytes),
        "heldout_path": "sealed/heldout.json",
        "heldout_sha256": heldout_hash,
        "heldout_status": "unopened",
        "heldout_access_allowed": False,
        "initial_heldout_access_ledger_sha256": sha256_bytes(ledger_bytes),
    }
    seal_path = sealed / "seal.json"
    seal_path.write_text(json.dumps(seal), encoding="utf-8")
    return seal_path, ledger_path


def test_development_loader_keeps_heldout_unopened(tmp_path: Path) -> None:
    seal_path, ledger_path = write_loader_fixture(tmp_path)

    dataset, seal = load_sealed_development(
        root=tmp_path, seal_path=seal_path, ledger_path=ledger_path
    )

    assert len(dataset["cases"]) == DEVELOPMENT_CASES
    assert seal["heldout_status"] == "unopened"


def test_development_loader_rejects_modified_ledger(tmp_path: Path) -> None:
    seal_path, ledger_path = write_loader_fixture(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["attempts"] = [{"attempt": 1}]
    ledger_path.write_bytes(canonical_bytes(ledger))

    with pytest.raises(MultimodalSealError, match="not pristine"):
        load_sealed_development(
            root=tmp_path, seal_path=seal_path, ledger_path=ledger_path
        )
