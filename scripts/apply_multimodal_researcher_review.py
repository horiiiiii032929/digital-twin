#!/usr/bin/env python3
"""Apply a completed private multimodal researcher-review export locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.build_multimodal_private_draft import (
    AUTO_ADJUDICATIONS,
    CONFIRMED_SECOND_REVIEW_FIXES,
)
from scripts.validate_multimodal_retrieval_dataset import validate_dataset


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = (
    ROOT / "data/processed/multimodal_retrieval_v1/multimodal_retrieval_v1_draft.json"
)
REVIEW_ID = "multimodal-retrieval-v1-researcher-review-v2"
REQUIRED_ACTIVE_CHECKS = ("source", "claims", "region")
VALID_DECISIONS = {"accept", "reject", "revise"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATASET)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _review_note(decision: str, notes: Any) -> str:
    note = " ".join(str(notes or "").split())
    prefix = {
        "accept": "Researcher accepted this case via the local review export.",
        "reject": "Researcher rejected this case via the local review export.",
        "revise": "Researcher requested revision via the local review export.",
    }[decision]
    if note:
        prefix = f"{prefix} Note: {note}"
    return prefix[:500]


def apply_review(dataset: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    require(review.get("review_id") == REVIEW_ID, "unexpected researcher review ID")
    require(review.get("policy_confirmed") is True, "taxonomy policy was not confirmed")

    fix_confirmations = review.get("fix_confirmations")
    require(isinstance(fix_confirmations, dict), "fix confirmations must be an object")
    missing_fixes = [
        case_id
        for case_id in CONFIRMED_SECOND_REVIEW_FIXES
        if fix_confirmations.get(case_id) is not True
    ]
    require(not missing_fixes, f"missing direct-fix confirmations: {sorted(missing_fixes)}")

    decisions = review.get("decisions")
    require(isinstance(decisions, dict), "review decisions must be an object")
    cases_by_id = {case["case_id"]: case for case in dataset["cases"]}
    expected_ids = set(cases_by_id)
    actual_ids = set(decisions)
    require(actual_ids == expected_ids, "review decisions do not match the dataset cases")

    for case_id, case in cases_by_id.items():
        record = decisions[case_id]
        require(isinstance(record, dict), f"{case_id} review record must be an object")
        require(record.get("confirmed") is True, f"{case_id} is not confirmed")
        checks = record.get("checks")
        require(isinstance(checks, dict), f"{case_id} checks must be an object")
        missing_checks = [name for name in REQUIRED_ACTIVE_CHECKS if checks.get(name) is not True]
        if case_id not in AUTO_ADJUDICATIONS and checks.get("taxonomy") is not True:
            missing_checks.append("taxonomy")
        require(not missing_checks, f"{case_id} missing checks: {missing_checks}")
        decision = record.get("decision")
        require(decision in VALID_DECISIONS, f"{case_id} has invalid disposition")

        case["review"] = {
            "status": "researcher_verified" if decision == "accept" else "rejected" if decision == "reject" else "pending",
            "researcher_verified": decision == "accept",
            "notes": _review_note(decision, record.get("notes")),
        }
    return dataset


def main() -> int:
    args = parse_args()
    try:
        dataset = apply_review(load_json(args.dataset), load_json(args.review))
        summary = validate_dataset(dataset)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(dataset, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"multimodal researcher review application failed: {error}")
        return 1

    researcher_verified = sum(case["review"]["researcher_verified"] for case in dataset["cases"])
    statuses = {}
    for case in dataset["cases"]:
        status = case["review"]["status"]
        statuses[status] = statuses.get(status, 0) + 1
    print(
        json.dumps(
            {
                "status": summary["status"],
                "cases": summary["cases"],
                "researcher_verified": researcher_verified,
                "review_statuses": dict(sorted(statuses.items())),
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
