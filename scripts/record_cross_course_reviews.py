#!/usr/bin/env python3
"""Record explicit researcher decisions in the private benchmark draft."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.draft_cross_course_benchmark import ROOT, write_review


DEFAULT_DATASET = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft.json"
)
DEFAULT_REVIEW = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "review/researcher_review.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--case-id", action="append", required=True)
    parser.add_argument("--decision", choices=("accept", "reject"), required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--note", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset: dict[str, Any] = json.loads(
        args.dataset.read_text(encoding="utf-8")
    )
    requested = set(args.case_id)
    cases = {
        case["case_id"]: case
        for case in dataset["cases"]
        if case["case_id"] in requested
    }
    missing = sorted(requested - set(cases))
    if missing:
        raise ValueError(f"unknown case IDs: {', '.join(missing)}")

    reviewed_at = datetime.now().astimezone().isoformat()
    for case_id in args.case_id:
        review = cases[case_id]["review"]
        if review["second_reviewed"]:
            raise ValueError(f"{case_id} is already independently reviewed")
        review.update(
            {
                "status": (
                    "researcher_verified"
                    if args.decision == "accept"
                    else "rejected"
                ),
                "researcher_verified": args.decision == "accept",
                "second_reviewed": False,
                "reviewer": args.reviewer,
                "reviewed_at": reviewed_at,
                "notes": args.note,
            }
        )

    dataset["dataset_status"] = "researcher_review"
    args.dataset.write_text(
        f"{json.dumps(dataset, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    write_review(args.review_output, dataset)
    print(
        json.dumps(
            {
                "status": "recorded",
                "decision": args.decision,
                "case_ids": args.case_id,
                "reviewer": args.reviewer,
                "reviewed_at": reviewed_at,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
