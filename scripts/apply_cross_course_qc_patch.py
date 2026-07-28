#!/usr/bin/env python3
"""Apply a private, traceable semantic-QC patch to a benchmark draft."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from scripts.draft_cross_course_benchmark import (
    ROOT,
    blank_review,
    evidence_from,
    load_corpus,
    sha256_file,
    sha256_text,
    write_review,
)


DEFAULT_SOURCE = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft_2.json"
)
DEFAULT_PATCH = (
    ROOT
    / "data/interim/cross_course_retrieval_v1/"
    "qc_patch_draft_3.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft_3.json"
)
DEFAULT_REVIEW = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/review/"
    "researcher_review_draft_3.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW)
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resolve_patch_evidence(
    specifications: list[dict[str, str]],
    records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for specification in specifications:
        chunk_id = specification["chunk_id"]
        require(chunk_id in records, f"unknown patch chunk: {chunk_id}")
        record = records[chunk_id]
        quote = specification["supporting_quote"]
        require(
            quote in record["chunk"].text,
            f"patch quote is not exact for {chunk_id}",
        )
        resolved.append(evidence_from(record, quote))
    return resolved


def apply_case_fields(
    case: dict[str, Any],
    revision: dict[str, Any],
) -> None:
    for field in ("query", "difficulty", "topic", "required_claims"):
        if field in revision:
            case[field] = revision[field]
    if "supporting_quotes" in revision:
        quotes = revision["supporting_quotes"]
        require(
            len(quotes) == len(case["gold_evidence"]),
            f"{case['case_id']} quote count mismatch",
        )
        for evidence, quote in zip(
            case["gold_evidence"],
            quotes,
            strict=True,
        ):
            evidence["supporting_quote"] = quote
            evidence["quote_sha256"] = sha256_text(quote)
    case["review"] = blank_review()


def main() -> int:
    args = parse_args()
    dataset = json.loads(args.source.read_text(encoding="utf-8"))
    patch = json.loads(args.patch.read_text(encoding="utf-8"))
    source_sha256 = sha256_file(args.source)
    require(
        patch["source_dataset_sha256"] == source_sha256,
        "QC patch source hash mismatch",
    )
    target_version = patch["target_dataset_version"]
    require(
        target_version.startswith("draft-")
        and target_version.removeprefix("draft-").isdigit(),
        "QC patch target must be a draft version",
    )
    source_version = int(dataset["dataset_version"].removeprefix("draft-"))
    target_number = int(target_version.removeprefix("draft-"))
    require(
        target_number == source_version + 1,
        "QC patch target must be the next draft version",
    )

    records: dict[str, dict[str, Any]] = {}
    if patch["replacements"]:
        _, corpus_records = load_corpus(args.source_root)
        records = {
            record["chunk"].id: record
            for record in corpus_records
        }
    cases = {
        case["case_id"]: case
        for case in dataset["cases"]
    }
    changed: set[str] = set()

    for revision in patch["updates"]:
        case_id = revision["case_id"]
        require(case_id in cases, f"unknown update case: {case_id}")
        apply_case_fields(cases[case_id], revision)
        changed.add(case_id)

    for replacement in patch["replacements"]:
        case_id = replacement["case_id"]
        require(case_id in cases, f"unknown replacement case: {case_id}")
        original = cases[case_id]
        evidence = resolve_patch_evidence(
            replacement["evidence"],
            records,
        )
        distractor_records = [
            records[chunk_id]
            for chunk_id in replacement.get("distractor_chunk_ids", [])
        ]
        require(
            all(
                record["course_id"] == replacement["target_course_id"]
                for record in (
                    records[item["chunk_id"]]
                    for item in replacement["evidence"]
                )
            ),
            f"{case_id} replacement course mismatch",
        )
        require(
            all(
                record["course_id"] != replacement["target_course_id"]
                for record in distractor_records
            ),
            f"{case_id} distractor course mismatch",
        )
        original.update(
            {
                "target_course_id": replacement["target_course_id"],
                "query": replacement["query"],
                "difficulty": replacement["difficulty"],
                "topic": replacement["topic"],
                "required_claims": replacement["required_claims"],
                "gold_evidence": evidence,
                "distractor_source_ids": sorted(
                    {
                        record["source_artifact_id"]
                        for record in distractor_records
                    }
                ),
                "review": blank_review(),
            }
        )
        changed.add(case_id)

    require(
        changed == set(patch["flagged_case_ids"]),
        "not every flagged case was changed exactly once",
    )
    dataset["dataset_version"] = target_version
    dataset["dataset_status"] = "machine_draft"
    dataset["authoring"].update(
        {
            "method": "local-model-draft-with-local-assistant-qc",
            "qc_amendment_path": (
                "research/04_experiments/"
                "2026-07-28-cross-course-benchmark-v1-qc-amendment.md"
            ),
            "predecessor_dataset_sha256": source_sha256,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        f"{json.dumps(dataset, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    write_review(args.review_output, dataset)
    print(
        json.dumps(
            {
                "status": f"{target_version}-created",
                "changed_cases": len(changed),
                "source_dataset_sha256": source_sha256,
                "output": str(args.output),
                "review": str(args.review_output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
