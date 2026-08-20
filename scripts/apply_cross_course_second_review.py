#!/usr/bin/env python3
"""Apply a completed model second review and explicit adjudication."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed

from scripts.draft_cross_course_benchmark import ROOT, write_review


DEFAULT_DATASET = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft_6.json"
)
DEFAULT_RESULT = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/review/"
    "model_second_review_draft_6.json"
)
DEFAULT_ADJUDICATION = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/review/"
    "model_second_review_draft_6_adjudication.json"
)
DEFAULT_REVIEW = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/review/"
    "researcher_review_draft_6.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument(
        "--adjudication",
        type=Path,
        default=DEFAULT_ADJUDICATION,
    )
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def apply_second_review(
    dataset: dict[str, Any],
    result: dict[str, Any],
    adjudication: dict[str, Any],
) -> None:
    decisions = result["decisions"]
    if len(decisions) != 20:
        raise ValueError("second review must contain exactly 20 decisions")
    if len({item["case_id"] for item in decisions}) != 20:
        raise ValueError("second-review case IDs must be unique")

    rejected = [
        item for item in decisions if item["decision"]["decision"] == "reject"
    ]
    if len(rejected) != 1:
        raise ValueError("expected exactly one preserved reviewer rejection")
    rejected_case_id = rejected[0]["case_id"]
    if adjudication["review_id"] != result["review_id"]:
        raise ValueError("adjudication review ID mismatch")
    if adjudication["case_id"] != rejected_case_id:
        raise ValueError("adjudication case ID mismatch")
    if adjudication["original_decision"] != "reject":
        raise ValueError("adjudication must preserve the original rejection")
    if adjudication["adjudication"] != "retain":
        raise ValueError("rejected case was not approved for retention")
    if not adjudication["rationale"].strip():
        raise ValueError("adjudication rationale is required")

    cases = {case["case_id"]: case for case in dataset["cases"]}
    missing = sorted({item["case_id"] for item in decisions} - set(cases))
    if missing:
        raise ValueError(f"unknown second-review cases: {', '.join(missing)}")

    for item in decisions:
        case = cases[item["case_id"]]
        if not case["review"]["researcher_verified"]:
            raise ValueError(f"{item['case_id']} is not researcher verified")
        decision = item["decision"]["decision"]
        note = (
            f" Blinded local-model second review "
            f"{result['review_id']} ({result['model']} at "
            f"{result['model_digest']}) returned {decision}."
        )
        if decision == "reject":
            note += (
                " The rejection is preserved in the private result and was "
                f"adjudicated as retain by {adjudication['adjudicator']}: "
                f"{adjudication['rationale']}"
            )
        case["review"].update(
            {
                "status": "second_reviewed",
                "second_reviewed": True,
                "notes": f"{case['review']['notes']}{note}",
            }
        )
    dataset["dataset_status"] = "approved"


def main() -> int:
    args = parse_args()
    require_pre_evaluation_operation_allowed("dataset_generation")
    dataset_hash = sha256_file(args.dataset)
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    adjudication = json.loads(args.adjudication.read_text(encoding="utf-8"))
    if result["dataset_sha256"] != dataset_hash:
        raise ValueError("second-review dataset hash mismatch")
    apply_second_review(dataset, result, adjudication)
    args.dataset.write_text(
        f"{json.dumps(dataset, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    write_review(args.review_output, dataset)
    print(
        json.dumps(
            {
                "status": "applied",
                "researcher_verified": sum(
                    case["review"]["researcher_verified"]
                    for case in dataset["cases"]
                ),
                "second_reviewed": sum(
                    case["review"]["second_reviewed"]
                    for case in dataset["cases"]
                ),
                "adjudicated_case_id": adjudication["case_id"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
