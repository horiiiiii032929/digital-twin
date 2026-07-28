#!/usr/bin/env python3
"""Validate the cross-course retrieval benchmark schema and private evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema

from scripts.draft_cross_course_benchmark import (
    MANIFEST_PATH,
    ROOT,
    artifact_id,
    load_corpus,
    sha256_file,
    sha256_text,
)


SCHEMA_PATH = (
    ROOT / "research/05_evaluation/cross_course_retrieval_v1.schema.json"
)
SYNTHETIC_EXAMPLE = (
    ROOT
    / "research/05_evaluation/"
    "cross_course_retrieval_v1_synthetic_example.json"
)
DEFAULT_DATASET = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft.json"
)
EXPECTED_ALLOCATION = {
    ("development", "answerable", "IT5002"): 8,
    ("heldout_draft", "answerable", "IT5002"): 7,
    ("development", "answerable", "CS5421"): 8,
    ("heldout_draft", "answerable", "CS5421"): 7,
    ("development", "answerable", "IT5100B"): 8,
    ("heldout_draft", "answerable", "IT5100B"): 7,
    ("development", "answerable", "IT5100E"): 8,
    ("heldout_draft", "answerable", "IT5100E"): 7,
    ("development", "no_evidence", None): 3,
    ("heldout_draft", "no_evidence", None): 12,
    ("development", "cross_course_confusion", "target"): 3,
    ("heldout_draft", "cross_course_confusion", "target"): 12,
    ("development", "adversarial_integrity", None): 2,
    ("heldout_draft", "adversarial_integrity", None): 8,
}
EXPECTED_CONFUSION_TARGETS = {
    "IT5002": 4,
    "CS5421": 4,
    "IT5100B": 4,
    "IT5100E": 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
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
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--expected-cases", type=int, default=100)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(dataset: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(dataset),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"schema error at {location}: {error.message}")


def normalized_query(query: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", query.casefold()))


def allocation_key(case: dict[str, Any]) -> tuple[str, str, str | None]:
    course: str | None = case["target_course_id"]
    if case["slice"] == "cross_course_confusion":
        course = "target"
    return (case["split"], case["slice"], course)


def validate_structure(dataset: dict[str, Any], expected_cases: int) -> None:
    cases = dataset["cases"]
    require(len(cases) == expected_cases, f"expected {expected_cases} cases")
    ids = [case["case_id"] for case in cases]
    require(len(ids) == len(set(ids)), "case IDs are not unique")
    queries = [normalized_query(case["query"]) for case in cases]
    require(len(queries) == len(set(queries)), "queries are not unique")
    allocation = Counter(allocation_key(case) for case in cases)
    require(allocation == Counter(EXPECTED_ALLOCATION), "allocation mismatch")
    confusion_targets = Counter(
        case["target_course_id"]
        for case in cases
        if case["slice"] == "cross_course_confusion"
    )
    require(
        confusion_targets == Counter(EXPECTED_CONFUSION_TARGETS),
        "cross-course confusion target allocation mismatch",
    )

    for case in cases:
        evidence = case["gold_evidence"]
        if case["slice"] in {"answerable", "cross_course_confusion"}:
            require(case["expected_action"] == "retrieve", "positive action mismatch")
            require(bool(case["required_claims"]), "positive case has no claim")
            require(bool(evidence), "positive case has no evidence")
            require(
                case["target_course_id"] is not None,
                "positive case has no target course",
            )
        else:
            require(not evidence, "boundary case unexpectedly has gold evidence")
            require(
                not case["required_claims"],
                "boundary case unexpectedly has required claims",
            )
            require(
                case["target_course_id"] is None,
                "boundary case unexpectedly targets a course",
            )
        if case["slice"] == "no_evidence":
            require(case["expected_action"] == "abstain", "no-evidence action mismatch")
        if case["slice"] == "adversarial_integrity":
            require(case["expected_action"] == "refuse", "adversarial action mismatch")

    reviews = [case["review"] for case in cases]
    researcher_count = sum(review["researcher_verified"] for review in reviews)
    second_count = sum(review["second_reviewed"] for review in reviews)
    if dataset["dataset_status"] in {"approved", "sealed", "opened"}:
        require(researcher_count == len(cases), "not all cases researcher verified")
        require(second_count >= 20, "fewer than 20 cases second reviewed")
    if dataset["dataset_status"] == "machine_draft":
        require(researcher_count == 0, "machine draft contains researcher approval")


def validate_evidence(dataset: dict[str, Any], source_root: Path) -> None:
    manifest = load_json(MANIFEST_PATH)
    manifest_documents: dict[str, tuple[str, dict[str, Any]]] = {}
    for course in manifest["courses"]:
        for document in course["documents"]:
            relative_path = str(
                Path(course["relative_root"]) / document["filename"]
            )
            manifest_documents[relative_path] = (course["course_id"], document)

    _, records = load_corpus(source_root)
    chunks = {record["chunk"].id: record for record in records}
    for case in dataset["cases"]:
        for evidence in case["gold_evidence"]:
            relative_path = evidence["relative_path"]
            require(relative_path in manifest_documents, "evidence path not in manifest")
            course_id, document = manifest_documents[relative_path]
            require(
                course_id == case["target_course_id"],
                f"{case['case_id']} evidence course mismatch",
            )
            path = source_root / relative_path
            require(
                sha256_file(path) == evidence["document_sha256"],
                f"{case['case_id']} document hash mismatch",
            )
            require(
                document["sha256"] == evidence["document_sha256"],
                f"{case['case_id']} manifest hash mismatch",
            )
            require(
                artifact_id(course_id, relative_path)
                == evidence["source_artifact_id"],
                f"{case['case_id']} source artifact mismatch",
            )
            require(
                evidence["chunk_id"] in chunks,
                f"{case['case_id']} chunk is absent",
            )
            record = chunks[evidence["chunk_id"]]
            chunk = record["chunk"]
            require(
                chunk.content_hash == evidence["chunk_sha256"],
                f"{case['case_id']} chunk hash mismatch",
            )
            require(
                chunk.page_start == evidence["page"] == chunk.page_end,
                f"{case['case_id']} page mismatch",
            )
            quote = evidence["supporting_quote"]
            require(
                quote in chunk.text,
                f"{case['case_id']} quote is not an exact chunk substring",
            )
            require(
                sha256_text(quote) == evidence["quote_sha256"],
                f"{case['case_id']} quote hash mismatch",
            )
            require(
                evidence["visual_dependency"] == "text_sufficient",
                f"{case['case_id']} visual-only evidence cannot be gold",
            )


def main() -> int:
    args = parse_args()
    dataset_path = SYNTHETIC_EXAMPLE if args.synthetic else args.dataset
    try:
        dataset = load_json(dataset_path)
        validate_schema(dataset)
        if not args.synthetic:
            validate_structure(dataset, args.expected_cases)
            if not args.schema_only:
                validate_evidence(dataset, args.source_root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"cross-course benchmark validation failed: {error}")
        return 1
    print(
        json.dumps(
            {
                "status": "passed",
                "dataset": str(dataset_path),
                "cases": len(dataset["cases"]),
                "schema_only": args.schema_only or args.synthetic,
                "researcher_verified": sum(
                    case["review"]["researcher_verified"]
                    for case in dataset["cases"]
                ),
                "second_reviewed": sum(
                    case["review"]["second_reviewed"]
                    for case in dataset["cases"]
                ),
                "difficulty_distribution": dict(
                    sorted(
                        Counter(
                            case["difficulty"] for case in dataset["cases"]
                        ).items()
                    )
                ),
                "ready_to_freeze": (
                    dataset["dataset_status"] in {"approved", "sealed", "opened"}
                    and all(
                        case["review"]["researcher_verified"]
                        for case in dataset["cases"]
                    )
                    and sum(
                        case["review"]["second_reviewed"]
                        for case in dataset["cases"]
                    )
                    >= 20
                ),
                "validated_at": datetime.now().astimezone().isoformat(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
