#!/usr/bin/env python3
"""Seal course-tutor v1.2 splits only after explicit human authoring review."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.validate_course_tutor_dataset import (
    load_json,
    validate_dataset,
    validate_schema,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/processed/course_tutor_v1/review_v1_2_3"
DEFAULT_OUTPUT = ROOT / "data/processed/course_tutor_v1/sealed_v2"
MANIFEST_PATH = ROOT / "research/05_evaluation/it5002_lectures_v1.manifest.json"
EVIDENCE_ROOT = ROOT / "data/interim/course_tutor_v1/evidence"
CASE_SCHEMA_PATH = ROOT / "research/05_evaluation/course_tutor_v1.schema.json"
CONDITION_SCHEMA_PATH = ROOT / "research/05_evaluation/course_tutor_v1_condition.schema.json"
REQUIRED_REVIEW_CHECKS = (
    "question_authentic_and_synthetic",
    "expected_behavior_correct",
    "claims_atomic_and_correct",
    "evidence_supports_claims",
    "permission_and_version_correct",
    "split_assignment_acceptable",
)
EXPECTED_REVIEW_ID = "course-tutor-v1.2-authoring-review-004"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")
    except FileExistsError as error:
        raise ValueError(f"refusing to overwrite sealed artifact: {path}") from error


def _review_decisions(
    review: dict[str, Any],
    split: str,
    expected_case_ids: set[str],
) -> dict[str, dict[str, Any]]:
    reviewer = review.get("reviewer", {})
    reviewed_at = review.get("reviewed_at")
    try:
        parsed_reviewed_at = datetime.fromisoformat(reviewed_at)
    except (TypeError, ValueError):
        parsed_reviewed_at = None
    if not all(
        (
            review.get("review_id") == EXPECTED_REVIEW_ID,
            review.get("status") == "complete",
            parsed_reviewed_at is not None
            and parsed_reviewed_at.tzinfo is not None,
            reviewer.get("human_review") is True,
            reviewer.get("codex_assisted") is False,
            reviewer.get("role") in {"researcher", "professor"},
            isinstance(reviewer.get("reviewer_id"), str),
            bool(reviewer.get("reviewer_id", "").strip()),
        )
    ):
        raise ValueError(
            "the exact completed, timestamped, non-Codex human review is required"
        )
    decision_rows = (
        review.get("splits", {}).get(split, {}).get("case_decisions", [])
    )
    decisions = {item["case_id"]: item for item in decision_rows}
    if len(decisions) != len(decision_rows):
        raise ValueError(f"{split} review contains duplicate case decisions")
    if set(decisions) != expected_case_ids:
        raise ValueError(f"{split} review must cover every case exactly once")
    if any(
        item.get("decision") != "approve"
        or any(item.get(check) is not True for check in REQUIRED_REVIEW_CHECKS)
        or not isinstance(item.get("notes"), str)
        for item in decisions.values()
    ):
        raise ValueError(f"{split} contains unapproved review decisions")
    return decisions


def seal_splits(
    input_root: Path,
    output_root: Path,
    review_path: Path,
) -> dict[str, Any]:
    review_manifest = load_json(input_root / "review_manifest.json")
    review = load_json(review_path)
    if review.get("draft_hashes") != review_manifest.get("splits"):
        raise ValueError("authoring review is not bound to the exact review draft")
    manifest = load_json(MANIFEST_PATH)
    case_schema = load_json(CASE_SCHEMA_PATH)
    condition_schema = load_json(CONDITION_SCHEMA_PATH)
    reviewer = review["reviewer"]
    reviewed_at = review["reviewed_at"]

    planned_paths = [
        output_root / name
        for name in (
            "development.json",
            "development_conditions.json",
            "heldout.json",
            "heldout_conditions.json",
            "seal.json",
            "heldout_once_ledger.json",
            "authoring_review.json",
        )
    ]
    existing = [path for path in planned_paths if path.exists()]
    if existing:
        raise ValueError(f"sealed target already exists: {existing[0]}")

    prepared: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for split, expected in (("development", 48), ("heldout", 104)):
        dataset_path = input_root / f"{split}.json"
        conditions_path = input_root / f"{split}_conditions.json"
        recorded = review_manifest["splits"][split]
        if sha256(dataset_path) != recorded["dataset_sha256"]:
            raise ValueError(f"{split} review draft hash drifted")
        if sha256(conditions_path) != recorded["conditions_sha256"]:
            raise ValueError(f"{split} condition hash drifted")
        dataset = copy.deepcopy(load_json(dataset_path))
        conditions = copy.deepcopy(load_json(conditions_path))
        case_ids = {case["case_id"] for case in dataset["cases"]}
        _review_decisions(review, split, case_ids)
        for case in dataset["cases"]:
            annotation = case["annotation"]
            annotation.update(
                {
                    "status": (
                        "professor_approved"
                        if reviewer["role"] == "professor"
                        else "single_review"
                    ),
                    "reviewer_ids": [reviewer["reviewer_id"]],
                    "professor_decision": (
                        "approved" if reviewer["role"] == "professor" else "pending"
                    ),
                    "revision": annotation["revision"] + 1,
                    "updated_at": reviewed_at,
                    "change_summary": (
                        "Human authoring review approved the case, claim-evidence "
                        "links, expected action, policy boundary, and split assignment."
                    ),
                }
            )
        dataset["dataset_status"] = "approved" if split == "development" else "sealed"
        dataset["sealed_at"] = reviewed_at
        validate_schema(dataset, case_schema)
        validate_schema(conditions, condition_schema)
        validate_dataset(dataset, conditions, manifest, EVIDENCE_ROOT, expected)
        prepared[split] = dataset, conditions

    output_hashes = {}
    for split, (dataset, conditions) in prepared.items():
        dataset_path = output_root / f"{split}.json"
        conditions_path = output_root / f"{split}_conditions.json"
        write_json_exclusive(dataset_path, dataset)
        write_json_exclusive(conditions_path, conditions)
        output_hashes[split] = {
            "dataset_sha256": sha256(dataset_path),
            "conditions_sha256": sha256(conditions_path),
        }
    seal = {
        "seal_id": "course-tutor-v1.2-seal-001",
        "created_at": reviewed_at,
        "authoring_review_id": review["review_id"],
        "splits": output_hashes,
        "development_cases": 48,
        "heldout_cases": 104,
    }
    write_json_exclusive(output_root / "seal.json", seal)
    write_json_exclusive(
        output_root / "heldout_once_ledger.json",
        {
            "ledger_id": "course-tutor-v1.2-heldout-once-001",
            "status": "unopened",
            "dataset_sha256": output_hashes["heldout"]["dataset_sha256"],
            "conditions_sha256": output_hashes["heldout"]["conditions_sha256"],
            "opened_at": None,
            "run_id": None,
            "rerun_allowed": False,
        },
    )
    write_json_exclusive(output_root / "authoring_review.json", review)
    return seal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review", type=Path, required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            seal_splits(arguments.input_root, arguments.output_root, arguments.review),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
