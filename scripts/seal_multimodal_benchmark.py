#!/usr/bin/env python3
"""Seal the reviewed multimodal benchmark without running retrieval candidates."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.validate_multimodal_retrieval_dataset import (
    ROOT,
    load_json,
    validate_dataset,
)
from src.digital_twin.evaluation.multimodal_benchmark import (
    DEVELOPMENT_CASES,
    DEVELOPMENT_SLICE_TARGETS,
    HELDOUT_CASES,
    SEAL_ID,
    SPLIT_SEED,
    canonical_bytes,
    choose_development_assets,
    partition_dataset,
    sha256_bytes,
    sha256_file,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


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
    development = partition_dataset(
        dataset, development_assets=development_assets, development=True
    )
    heldout = partition_dataset(
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

    ledger = {
        "schema_version": 1,
        "ledger_id": "multimodal-retrieval-v1-heldout-once",
        "seal_id": SEAL_ID,
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
        "seal_id": SEAL_ID,
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
