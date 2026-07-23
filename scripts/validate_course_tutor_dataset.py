#!/usr/bin/env python3
"""Validate course-tutor-v1 cases, conditions, evidence, and corpus identity."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate course-tutor-v1 JSON Schemas plus cross-file claim, "
            "evidence, condition, source, and hash invariants."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT
        / "data/processed/course_tutor_v1/anchor/course_tutor_v1_anchor_draft.json",
    )
    parser.add_argument(
        "--conditions",
        type=Path,
        default=ROOT
        / "data/processed/course_tutor_v1/anchor/"
        "course_tutor_v1_anchor_conditions_draft.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "research/05_evaluation/it5002_lectures_v1.manifest.json",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=ROOT / "data/interim/course_tutor_v1/evidence",
    )
    parser.add_argument(
        "--case-schema",
        type=Path,
        default=ROOT / "research/05_evaluation/course_tutor_v1.schema.json",
    )
    parser.add_argument(
        "--condition-schema",
        type=Path,
        default=ROOT
        / "research/05_evaluation/course_tutor_v1_condition.schema.json",
    )
    parser.add_argument(
        "--expected-cases",
        type=int,
        default=None,
        help="Fail unless the dataset and condition set contain this many cases.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as error:
        raise ValueError(f"missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unique_by_id(
    records: list[dict[str, Any]], key: str, label: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        record_id = record[key]
        require(record_id not in result, f"duplicate {label} ID: {record_id}")
        result[record_id] = record
    return result


def validate_schema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"schema validation failed at {location}: {error.message}")


def validate_dataset(
    dataset: dict[str, Any],
    conditions: dict[str, Any],
    manifest: dict[str, Any],
    evidence_root: Path,
    expected_cases: int | None,
) -> dict[str, int]:
    cases = unique_by_id(dataset["cases"], "case_id", "case")
    condition_records = unique_by_id(
        conditions["records"], "condition_id", "condition"
    )
    condition_by_case = unique_by_id(
        conditions["records"], "case_id", "condition case"
    )
    require(
        set(condition_by_case) == set(cases),
        "condition case IDs must match dataset case IDs exactly",
    )
    require(
        conditions["dataset_version"] == dataset["dataset_version"],
        "condition dataset_version does not match the case dataset",
    )
    require(
        conditions["split"] == dataset["split"],
        "condition split does not match the case dataset",
    )
    if expected_cases is not None:
        require(
            len(cases) == expected_cases,
            f"expected {expected_cases} cases, found {len(cases)}",
        )
        require(
            len(condition_records) == expected_cases,
            f"expected {expected_cases} conditions, found {len(condition_records)}",
        )

    documents = {item["document_id"]: item for item in manifest["documents"]}
    strata = {
        item["id"]: set(item["documents"]) for item in manifest["topic_strata"]
    }
    passage_count = 0
    claim_count = 0

    for case_id, case in cases.items():
        ground_truth = case["ground_truth"]
        claims = ground_truth["required_claims"] + ground_truth["optional_claims"]
        claims_by_id = unique_by_id(claims, "claim_id", f"{case_id} claim")
        required_ids = {
            claim["claim_id"] for claim in ground_truth["required_claims"]
        }
        evidence = unique_by_id(
            ground_truth["evidence_units"],
            "evidence_unit_id",
            f"{case_id} evidence",
        )
        claim_count += len(claims)

        for claim in claims:
            evidence_ids = set(claim["evidence_unit_ids"])
            require(
                evidence_ids <= set(evidence),
                f"{case_id} {claim['claim_id']} references unknown evidence",
            )
            for evidence_id in evidence_ids:
                item = evidence[evidence_id]
                require(
                    claim["claim_id"] in item["supports_claim_ids"],
                    f"{case_id} {claim['claim_id']} is not linked back by "
                    f"{evidence_id}",
                )
                if claim["claim_id"] in required_ids:
                    require(
                        item["role"] == "essential",
                        f"{case_id} required claim {claim['claim_id']} is not "
                        "supported by essential evidence",
                    )
                    require(
                        item["permission_status"]
                        not in {"prohibited", "superseded"},
                        f"{case_id} required claim {claim['claim_id']} uses "
                        "prohibited or superseded evidence",
                    )
                    if dataset["dataset_status"] in {"approved", "sealed", "opened"}:
                        require(
                            item["permission_status"] == "approved",
                            f"{case_id} approved dataset uses evidence that is "
                            "not approved",
                        )

        for evidence_id, item in evidence.items():
            require(
                set(item["supports_claim_ids"]) <= set(claims_by_id),
                f"{case_id} {evidence_id} supports an unknown claim",
            )
            if item["role"] in {"prohibited", "superseded"}:
                require(
                    not item["supports_claim_ids"],
                    f"{case_id} {evidence_id} is negative evidence but supports "
                    "a claim",
                )

            source_id = item["source_artifact_id"]
            if source_id in documents:
                require(
                    case["topic_stratum"] in strata,
                    f"{case_id} has unknown corpus topic stratum "
                    f"{case['topic_stratum']}",
                )
                require(
                    source_id in strata[case["topic_stratum"]],
                    f"{case_id} source {source_id} is outside topic stratum "
                    f"{case['topic_stratum']}",
                )
            else:
                require(
                    item["role"] in {"distractor", "prohibited", "superseded"},
                    f"{case_id} positive source {source_id} is absent from the "
                    "corpus manifest",
                )

            passage_path = evidence_root / f"{item['passage_id']}.txt"
            require(
                passage_path.exists(),
                f"{case_id} evidence passage is missing: {passage_path}",
            )
            actual_hash = hashlib.sha256(passage_path.read_bytes()).hexdigest()
            require(
                actual_hash == item["content_sha256"],
                f"{case_id} {evidence_id} passage hash mismatch: "
                f"{actual_hash} != {item['content_sha256']}",
            )
            passage_count += 1

        condition = condition_by_case[case_id]
        assignment = condition["context_assignment"]
        candidate = set(assignment["candidate_evidence_unit_ids"])
        presented = set(assignment["presented_evidence_unit_ids"])
        excluded_records = assignment["excluded_evidence"]
        excluded = {item["evidence_unit_id"] for item in excluded_records}
        require(
            candidate | excluded <= set(evidence),
            f"{case_id} condition references unknown evidence",
        )
        require(
            presented <= candidate,
            f"{case_id} presented evidence is not a subset of candidates",
        )
        require(
            not presented & excluded,
            f"{case_id} excluded evidence is also presented",
        )

        essential = {
            evidence_id
            for evidence_id, item in evidence.items()
            if item["role"] == "essential"
        }
        sufficiency = assignment["expected_sufficiency"]
        if sufficiency == "complete":
            require(
                essential <= presented,
                f"{case_id} complete condition omits essential evidence",
            )
        elif sufficiency == "partial":
            require(
                bool(essential & presented) and bool(essential - presented),
                f"{case_id} partial condition must present and omit essential "
                "evidence",
            )
        elif sufficiency == "none":
            require(
                not presented,
                f"{case_id} none condition presents evidence",
            )
        elif sufficiency == "not_applicable":
            require(
                not evidence and not presented,
                f"{case_id} not_applicable context has evidence",
            )

        for excluded_item in excluded_records:
            evidence_id = excluded_item["evidence_unit_id"]
            if excluded_item["reason"] == "permission_filter":
                require(
                    evidence_id in candidate,
                    f"{case_id} permission-filtered evidence was not a candidate",
                )
                require(
                    evidence[evidence_id]["permission_status"] == "prohibited",
                    f"{case_id} permission filter targets non-prohibited evidence",
                )

        expected = condition["expected_behavior"]
        expected_claim_ids = set(expected["required_claim_ids"])
        require(
            expected_claim_ids <= required_ids,
            f"{case_id} condition requires a non-required case claim",
        )
        if expected["mode"] == "case_default":
            require(
                expected_claim_ids == required_ids,
                f"{case_id} case_default condition changes required claims",
            )

        fault = condition["fault_injection"]
        if fault["fault"] == "none":
            require(
                fault["stage"] == "none"
                and fault["trigger"] == "none"
                and fault["expected_output_state"] == "normal",
                f"{case_id} no-fault condition has an inconsistent fault contract",
            )
        else:
            require(
                fault["stage"] != "none"
                and fault["trigger"] != "none"
                and fault["expected_output_state"] == "bounded_failure",
                f"{case_id} injected fault lacks a bounded failure contract",
            )

    return {
        "cases": len(cases),
        "conditions": len(condition_records),
        "claims": claim_count,
        "passages": passage_count,
    }


def main() -> int:
    args = parse_args()
    try:
        case_schema = load_json(args.case_schema)
        condition_schema = load_json(args.condition_schema)
        dataset = load_json(args.dataset)
        conditions = load_json(args.conditions)
        manifest = load_json(args.manifest)
        validate_schema(dataset, case_schema)
        validate_schema(conditions, condition_schema)
        counts = validate_dataset(
            dataset,
            conditions,
            manifest,
            args.evidence_root,
            args.expected_cases,
        )
    except (ValueError, jsonschema.SchemaError) as error:
        print(f"course-tutor-v1 validation failed: {error}")
        return 1

    print(
        "course-tutor-v1 validation passed: "
        f"{counts['cases']} cases, {counts['conditions']} conditions, "
        f"{counts['claims']} claims, {counts['passages']} hashed passages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
