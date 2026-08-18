#!/usr/bin/env python3
"""Resolve a completed blinded review against its hidden condition mapping."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "research/05_evaluation/instruments/professor_fidelity_blinded_review_v1.schema.json"
VALID_LABELS = {"fail", "partial", "pass"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finalize_review(
    template: dict[str, Any],
    mapping: dict[str, Any],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    if template.get("status") != "complete":
        raise ValueError("review template must be marked complete")
    if template.get("source_run_id") != mapping.get("source_run_id"):
        raise ValueError("review and mapping source runs differ")
    if template.get("dataset_sha256") != mapping.get("dataset_sha256"):
        raise ValueError("review and mapping dataset hashes differ")
    reviewer = template.get("reviewer", {})
    if not all(
        (
            reviewer.get("reviewer_id"),
            reviewer.get("role") in {"researcher", "professor"},
            reviewer.get("blinded_to_conditions") is True,
            isinstance(reviewer.get("independent_human_review"), bool),
            template.get("reviewed_at"),
        )
    ):
        raise ValueError("reviewer metadata is incomplete")
    assignment_rows = mapping.get("assignments", [])
    judgment_rows = template.get("judgments", [])
    assignments = {
        item["task_id"]: item for item in mapping.get("assignments", [])
    }
    judgments = {
        item["task_id"]: item for item in template.get("judgments", [])
    }
    if len(assignments) != len(assignment_rows) or len(judgments) != len(
        judgment_rows
    ):
        raise ValueError("review tasks must be unique")
    if set(assignments) != set(judgments):
        raise ValueError("completed review must cover every blinded task exactly once")
    cases = {case["case_id"]: case for case in dataset.get("cases", [])}
    if len(cases) != len(dataset.get("cases", [])):
        raise ValueError("review dataset case identities are not unique")
    if {item["case_id"] for item in assignment_rows} - set(cases):
        raise ValueError("review mapping contains a case outside the dataset")
    normalized = []
    for task_id in sorted(assignments):
        assignment = assignments[task_id]
        judgment = judgments[task_id]
        if judgment.get("case_id") != assignment["case_id"]:
            raise ValueError(f"case identity drifted for {task_id}")
        if not all(
            isinstance(judgment.get(field), bool)
            for field in (
                "required_claim_expression",
                "supported_claim_precision",
                "citation_semantic_alignment",
                "citation_completeness",
                "presented_evidence_completeness",
            )
        ):
            raise ValueError(f"semantic labels are incomplete for {task_id}")
        dimensions = judgment.get("pedagogy_dimensions", [])
        if not dimensions or any(
            item.get("label") not in VALID_LABELS for item in dimensions
        ):
            raise ValueError(f"pedagogy labels are incomplete for {task_id}")
        expected_dimensions = cases[assignment["case_id"]]["rubric"][
            "required_pedagogy_dimensions"
        ]
        observed_dimensions = [item.get("dimension") for item in dimensions]
        if (
            len(observed_dimensions) != len(expected_dimensions)
            or len(set(observed_dimensions)) != len(observed_dimensions)
            or set(observed_dimensions) != set(expected_dimensions)
        ):
            raise ValueError(f"pedagogy dimensions drifted for {task_id}")
        normalized.append(
            {
                "case_id": assignment["case_id"],
                "condition": assignment["condition"],
                "required_claim_expression": judgment["required_claim_expression"],
                "supported_claim_precision": judgment["supported_claim_precision"],
                "citation_semantic_alignment": judgment["citation_semantic_alignment"],
                "citation_completeness": judgment["citation_completeness"],
                "presented_evidence_completeness": judgment[
                    "presented_evidence_completeness"
                ],
                "pedagogy_dimensions": dimensions,
            }
        )
    result = {
        "schema_version": "1.0.0",
        "review_id": template["review_id"],
        "source_run_id": template["source_run_id"],
        "dataset_sha256": template["dataset_sha256"],
        "status": "complete",
        "reviewed_at": template["reviewed_at"],
        "reviewer": reviewer,
        "judgments": normalized,
    }
    schema = load_json(SCHEMA)
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-historical-reproduction", action="store_true")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if not arguments.confirm_historical_reproduction:
        raise ValueError(
            "anchor review finalization is historical reproduction and requires "
            "--confirm-historical-reproduction"
        )
    mapping = load_json(arguments.mapping)
    dataset_sha256 = hashlib.sha256(arguments.dataset.read_bytes()).hexdigest()
    if mapping.get("dataset_sha256") != dataset_sha256:
        raise ValueError("review dataset hash does not match the blinded mapping")
    result = finalize_review(
        load_json(arguments.template),
        mapping,
        load_json(arguments.dataset),
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with arguments.output.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(result, indent=2, ensure_ascii=False)}\n")
    except FileExistsError as error:
        raise ValueError(
            f"refusing to overwrite finalized review: {arguments.output}"
        ) from error
    print(arguments.output)


if __name__ == "__main__":
    main()
