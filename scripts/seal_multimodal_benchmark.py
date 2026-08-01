#!/usr/bin/env python3
"""Freeze the reviewed multimodal benchmark without running retrieval candidates."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.validate_multimodal_retrieval_dataset import (
    ROOT,
    load_json,
    validate_dataset,
)


DEFAULT_DATASET = (
    ROOT
    / "data/processed/multimodal_retrieval_v1/"
    "multimodal_retrieval_v1_draft.json"
)
DEFAULT_OUTPUT_DIR = ROOT / "data/processed/multimodal_retrieval_v1/sealed_v1"
DEVELOPMENT_FILENAME = "development.json"
HELDOUT_FILENAME = "heldout.json"
LEDGER_FILENAME = "heldout_once_ledger.json"
SEAL_FILENAME = "seal.json"
SPLIT_SEED = "multimodal-retrieval-v1-split-v1"
DEVELOPMENT_CASES = 16
HELDOUT_CASES = 24
DEVELOPMENT_SLICE_TARGETS = {
    "visual_answerable": 10,
    "text_control": 3,
    "no_evidence": 1,
    "adversarial_integrity": 2,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _group_order(asset_id: str, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{asset_id}".encode()).hexdigest()


def choose_development_assets(
    dataset: dict[str, Any],
    *,
    development_cases: int = DEVELOPMENT_CASES,
    slice_targets: dict[str, int] = DEVELOPMENT_SLICE_TARGETS,
    seed: str = SPLIT_SEED,
) -> frozenset[str]:
    """Choose a deterministic exact split while keeping each page asset together."""
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in dataset["cases"]:
        grouped[case["asset_id"]].append(case)
    groups = sorted(grouped.items(), key=lambda item: _group_order(item[0], seed))
    suffix_cases = [0] * (len(groups) + 1)
    for index in range(len(groups) - 1, -1, -1):
        suffix_cases[index] = suffix_cases[index + 1] + len(groups[index][1])

    target = Counter(slice_targets)
    best: tuple[tuple[Any, ...], frozenset[str]] | None = None

    def search(
        index: int,
        selected_assets: tuple[str, ...],
        selected_cases: tuple[dict[str, Any], ...],
        counts: Counter[str],
    ) -> None:
        nonlocal best
        total = len(selected_cases)
        if total > development_cases or total + suffix_cases[index] < development_cases:
            return
        if any(counts[name] > expected for name, expected in target.items()):
            return
        if index == len(groups):
            if total != development_cases or counts != target:
                return
            courses = Counter(
                assets[case["asset_id"]]["course_id"] for case in selected_cases
            )
            modalities = {
                case["modality"]
                for case in selected_cases
                if case["slice"] == "visual_answerable"
            }
            tie_break = hashlib.sha256("|".join(selected_assets).encode()).hexdigest()
            score = (
                len(courses),
                len(modalities),
                -max(courses.values()),
                tie_break,
            )
            candidate = (score, frozenset(selected_assets))
            if best is None or candidate[0] > best[0]:
                best = candidate
            return

        asset_id, cases = groups[index]
        delta = Counter(case["slice"] for case in cases)
        search(
            index + 1,
            selected_assets + (asset_id,),
            selected_cases + tuple(cases),
            counts + delta,
        )
        search(index + 1, selected_assets, selected_cases, counts)

    search(0, (), (), Counter())
    if best is None:
        raise ValueError("no asset-grouped split satisfies the development targets")
    return best[1]


def _partition_dataset(
    dataset: dict[str, Any],
    *,
    development_assets: frozenset[str],
    development: bool,
) -> dict[str, Any]:
    partition = copy.deepcopy(dataset)
    partition["dataset_status"] = "sealed"
    expected_membership = development
    split = "development" if development else "heldout_draft"
    partition["cases"] = [
        case
        for case in partition["cases"]
        if (case["asset_id"] in development_assets) is expected_membership
    ]
    for case in partition["cases"]:
        case["split"] = split
    retained_assets = {case["asset_id"] for case in partition["cases"]}
    partition["source_assets"] = [
        asset
        for asset in partition["source_assets"]
        if asset["asset_id"] in retained_assets
    ]
    return partition


def build_seal_artifacts(
    dataset: dict[str, Any],
    *,
    source_dataset_sha256: str,
    output_dir: Path,
    sealed_at: str,
) -> dict[str, tuple[Path, bytes]]:
    if dataset["dataset_status"] not in {"researcher_review", "approved"}:
        raise ValueError("only a reviewed or approved multimodal draft may be sealed")
    if len(dataset["cases"]) != DEVELOPMENT_CASES + HELDOUT_CASES:
        raise ValueError("the multimodal benchmark must contain exactly 40 cases")
    if not all(case["review"]["researcher_verified"] for case in dataset["cases"]):
        raise ValueError("all multimodal cases must be researcher verified")

    development_assets = choose_development_assets(dataset)
    development = _partition_dataset(
        dataset, development_assets=development_assets, development=True
    )
    heldout = _partition_dataset(
        dataset, development_assets=development_assets, development=False
    )
    if len(development["cases"]) != DEVELOPMENT_CASES:
        raise ValueError("development split size mismatch")
    if len(heldout["cases"]) != HELDOUT_CASES:
        raise ValueError("held-out split size mismatch")
    if {case["asset_id"] for case in development["cases"]} & {
        case["asset_id"] for case in heldout["cases"]
    }:
        raise ValueError("a source page asset crosses the frozen split")
    validate_dataset(development)
    validate_dataset(heldout)

    development_path = output_dir / DEVELOPMENT_FILENAME
    heldout_path = output_dir / HELDOUT_FILENAME
    ledger_path = output_dir / LEDGER_FILENAME
    seal_path = output_dir / SEAL_FILENAME
    development_bytes = canonical_bytes(development)
    heldout_bytes = canonical_bytes(heldout)
    development_sha256 = sha256_bytes(development_bytes)
    heldout_sha256 = sha256_bytes(heldout_bytes)
    seal_id = "multimodal-retrieval-v1-seal"

    ledger = {
        "schema_version": 1,
        "ledger_id": "multimodal-retrieval-v1-heldout-once",
        "seal_id": seal_id,
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "heldout_sha256": heldout_sha256,
        "status": "unopened",
        "created_at": sealed_at,
        "opened_at": None,
        "completed_at": None,
        "attempts": [],
        "access_rule": (
            "Only the frozen one-time multimodal held-out runner may read cases "
            "or change this ledger; any other semantic access invalidates the run."
        ),
    }
    ledger_bytes = canonical_bytes(ledger)
    seal = {
        "schema_version": 1,
        "seal_id": seal_id,
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "sealed_at": sealed_at,
        "source_dataset_sha256": source_dataset_sha256,
        "split_seed": SPLIT_SEED,
        "split_strategy": (
            "asset-grouped exact 40/60 split; maximize course and visual-modality "
            "coverage, then minimize maximum development course count"
        ),
        "development_slice_targets": DEVELOPMENT_SLICE_TARGETS,
        "development_path": display_path(development_path),
        "development_sha256": development_sha256,
        "development_cases": DEVELOPMENT_CASES,
        "development_assets": len(development["source_assets"]),
        "heldout_path": display_path(heldout_path),
        "heldout_sha256": heldout_sha256,
        "heldout_cases": HELDOUT_CASES,
        "heldout_assets": len(heldout["source_assets"]),
        "heldout_access_ledger_path": display_path(ledger_path),
        "initial_heldout_access_ledger_sha256": sha256_bytes(ledger_bytes),
        "heldout_status": "unopened",
        "heldout_access_allowed": False,
        "researcher_verified_cases": len(dataset["cases"]),
        "quality_gates": {
            "schema_and_allocation": "passed",
            "asset_hash_and_region_integrity": "passed",
            "researcher_review": "passed",
            "asset_group_split_isolation": "passed",
            "pre_seal_candidate_access": 0,
        },
    }
    return {
        DEVELOPMENT_FILENAME: (development_path, development_bytes),
        HELDOUT_FILENAME: (heldout_path, heldout_bytes),
        LEDGER_FILENAME: (ledger_path, ledger_bytes),
        SEAL_FILENAME: (seal_path, canonical_bytes(seal)),
    }


def write_exclusive(artifacts: dict[str, tuple[Path, bytes]]) -> None:
    existing = [path for path, _content in artifacts.values() if path.exists()]
    if existing:
        raise FileExistsError(
            "multimodal seal artifacts already exist: "
            + ", ".join(str(path) for path in existing)
        )
    created: list[Path] = []
    try:
        for path, content in artifacts.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
            created.append(path)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def main() -> int:
    args = parse_args()
    try:
        dataset = load_json(args.dataset)
        validate_dataset(dataset)
        artifacts = build_seal_artifacts(
            dataset,
            source_dataset_sha256=sha256_file(args.dataset),
            output_dir=args.output_dir,
            sealed_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        )
        write_exclusive(artifacts)
        seal = json.loads(artifacts[SEAL_FILENAME][1])
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"multimodal benchmark seal failed: {error}")
        return 1
    print(
        json.dumps(
            {
                "status": "sealed",
                "seal_id": seal["seal_id"],
                "development_cases": seal["development_cases"],
                "heldout_cases": seal["heldout_cases"],
                "heldout_status": seal["heldout_status"],
                "heldout_access_allowed": seal["heldout_access_allowed"],
                "model_called": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
