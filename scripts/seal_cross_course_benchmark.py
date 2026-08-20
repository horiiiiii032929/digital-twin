#!/usr/bin/env python3
"""Seal the approved private cross-course benchmark without opening held-out data."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed

from scripts.draft_cross_course_benchmark import MANIFEST_PATH, ROOT, sha256_file
from scripts.validate_cross_course_benchmark import (
    load_json,
    validate_evidence,
    validate_schema,
    validate_structure,
)


DEFAULT_DATASET = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft_6.json"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "data/processed/cross_course_retrieval_v1/sealed_v1"
)
DEVELOPMENT_FILENAME = "development.json"
HELDOUT_FILENAME = "heldout.json"
LEDGER_FILENAME = "heldout_once_ledger.json"
SEAL_FILENAME = "seal.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "ACADEMIA_VAULT_ROOT",
                Path.home() / "Documents" / "academia_vault",
            )
        ),
    )
    return parser.parse_args()


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def build_seal_artifacts(
    dataset: dict[str, Any],
    *,
    source_dataset_sha256: str,
    corpus_manifest_sha256: str,
    output_dir: Path,
    sealed_at: str,
) -> dict[str, tuple[Path, bytes]]:
    if dataset["dataset_status"] != "approved":
        raise ValueError("only an approved benchmark may be sealed")
    if len(dataset["cases"]) != 100:
        raise ValueError("the sealed benchmark must contain exactly 100 cases")
    if not all(
        case["review"]["researcher_verified"] for case in dataset["cases"]
    ):
        raise ValueError("all cases must be researcher verified")
    if (
        sum(case["review"]["second_reviewed"] for case in dataset["cases"])
        < 20
    ):
        raise ValueError("at least 20 cases must be second reviewed")

    split_counts = Counter(case["split"] for case in dataset["cases"])
    if split_counts != {"development": 40, "heldout_draft": 60}:
        raise ValueError("expected 40 development and 60 held-out cases")

    development = copy.deepcopy(dataset)
    development["dataset_status"] = "sealed"
    development["cases"] = [
        case for case in development["cases"] if case["split"] == "development"
    ]
    heldout = copy.deepcopy(dataset)
    heldout["dataset_status"] = "sealed"
    heldout["cases"] = [
        case for case in heldout["cases"] if case["split"] == "heldout_draft"
    ]

    development_path = output_dir / DEVELOPMENT_FILENAME
    heldout_path = output_dir / HELDOUT_FILENAME
    ledger_path = output_dir / LEDGER_FILENAME
    seal_path = output_dir / SEAL_FILENAME
    development_bytes = canonical_bytes(development)
    heldout_bytes = canonical_bytes(heldout)
    development_sha256 = sha256_bytes(development_bytes)
    heldout_sha256 = sha256_bytes(heldout_bytes)
    seal_id = "cross-course-retrieval-v1-draft-6-seal"

    ledger = {
        "schema_version": 1,
        "ledger_id": "cross-course-retrieval-v1-heldout-once",
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
            "Only the frozen one-time held-out runner may change this ledger; "
            "any other access invalidates the final evaluation."
        ),
    }
    ledger_bytes = canonical_bytes(ledger)
    seal = {
        "schema_version": 1,
        "seal_id": seal_id,
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "corpus_id": dataset["corpus_id"],
        "sealed_at": sealed_at,
        "source_dataset_sha256": source_dataset_sha256,
        "corpus_manifest_path": display_path(MANIFEST_PATH),
        "corpus_manifest_sha256": corpus_manifest_sha256,
        "development_path": display_path(development_path),
        "development_sha256": development_sha256,
        "development_cases": 40,
        "heldout_path": display_path(heldout_path),
        "heldout_sha256": heldout_sha256,
        "heldout_cases": 60,
        "heldout_access_ledger_path": display_path(ledger_path),
        "initial_heldout_access_ledger_sha256": sha256_bytes(ledger_bytes),
        "heldout_status": "unopened",
        "heldout_access_allowed": False,
        "runtime_candidate_freeze_required": True,
        "researcher_verified_cases": 100,
        "second_reviewed_cases": sum(
            case["review"]["second_reviewed"] for case in dataset["cases"]
        ),
        "quality_gates": {
            "schema_and_allocation": "passed",
            "source_quote_and_hash_integrity": "passed",
            "researcher_review": "passed",
            "second_review_quota": "passed",
            "whole_corpus_no_evidence_review": "passed",
            "pre_seal_candidate_access": 0,
        },
    }
    seal_bytes = canonical_bytes(seal)
    return {
        DEVELOPMENT_FILENAME: (development_path, development_bytes),
        HELDOUT_FILENAME: (heldout_path, heldout_bytes),
        LEDGER_FILENAME: (ledger_path, ledger_bytes),
        SEAL_FILENAME: (seal_path, seal_bytes),
    }


def write_exclusive(artifacts: dict[str, tuple[Path, bytes]]) -> None:
    paths = [path for path, _content in artifacts.values()]
    existing = [path for path in paths if path.exists()]
    if existing:
        raise FileExistsError(
            "seal artifacts already exist: "
            + ", ".join(str(path) for path in existing)
        )
    created: list[Path] = []
    try:
        for path, content in artifacts.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
            created.append(path)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def main() -> int:
    args = parse_args()
    require_pre_evaluation_operation_allowed("dataset_generation")
    dataset = load_json(args.dataset)
    validate_schema(dataset)
    validate_structure(dataset, expected_cases=100)
    validate_evidence(dataset, args.source_root)
    artifacts = build_seal_artifacts(
        dataset,
        source_dataset_sha256=sha256_file(args.dataset),
        corpus_manifest_sha256=sha256_file(MANIFEST_PATH),
        output_dir=args.output_dir,
        sealed_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
    )
    write_exclusive(artifacts)
    seal = json.loads(artifacts[SEAL_FILENAME][1])
    print(
        json.dumps(
            {
                "status": "sealed",
                "seal_id": seal["seal_id"],
                "development_cases": seal["development_cases"],
                "heldout_cases": seal["heldout_cases"],
                "heldout_status": seal["heldout_status"],
                "heldout_access_allowed": seal["heldout_access_allowed"],
                "development_sha256": seal["development_sha256"],
                "heldout_sha256": seal["heldout_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
