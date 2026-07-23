#!/usr/bin/env python3
"""Validate the frozen retrieval-v3 plan and public open-set instrument."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS = ROOT / "research/05_evaluation/instruments"
FREEZE_PATH = INSTRUMENTS / "retrieval_v3_freeze.json"
OPEN_SET_SCHEMA_PATH = (
    ROOT / "research/05_evaluation/it5002_retrieval_open_set_v1.schema.json"
)
OPEN_SET_EXAMPLE_PATH = (
    ROOT
    / "research/05_evaluation/it5002_retrieval_open_set_v1_synthetic_example.json"
)


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


def validate_schema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"schema validation failed at {location}: {error.message}")


def unique_by_id(
    records: list[dict[str, Any]], key: str, label: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        identifier = record[key]
        require(identifier not in result, f"duplicate {label}: {identifier}")
        result[identifier] = record
    return result


def validate_open_set_example(example: dict[str, Any]) -> int:
    cases = unique_by_id(example["cases"], "case_id", "open-set case ID")
    families: set[str] = set()
    for case in cases.values():
        require(
            case["split"] == example["split"],
            f"open-set case {case['case_id']} split mismatch",
        )
        require(
            case["expected_action"] == "abstain",
            f"open-set case {case['case_id']} must abstain",
        )
        family = case["case_family_id"]
        require(family not in families, f"duplicate open-set family: {family}")
        families.add(family)
        tempting = unique_by_id(
            case["tempting_evidence"],
            "evidence_id",
            f"{case['case_id']} tempting evidence ID",
        )
        for item in tempting.values():
            require(
                item["status"]
                in {"approved_but_insufficient", "prohibited", "superseded"},
                f"{case['case_id']} has eligible positive evidence",
            )
    return len(cases)


def validate_freeze(freeze: dict[str, Any]) -> dict[str, int]:
    require(
        freeze["freeze_id"]
        == "it5002-retrieval-v3-candidate-freeze-2026-07-23",
        "unexpected retrieval-v3 freeze_id",
    )
    require(
        freeze["status"] == "candidate_set_frozen",
        "retrieval-v3 candidate set must be frozen",
    )
    require(
        freeze["heldout_access_allowed"] is False,
        "held-out access must remain disabled before runtime freeze",
    )
    rapid = freeze["rapid_checkpoint"]
    require(
        rapid["checkpoint_id"] == "it5002-retrieval-rapid-v1"
        and rapid["status"] == "prospectively_frozen",
        "unexpected retrieval rapid checkpoint",
    )
    require(
        rapid["deadline"] == "2026-07-24",
        "retrieval rapid checkpoint deadline must remain 2026-07-24",
    )
    require(
        rapid["conditions"] == ["R1", "R5"],
        "retrieval rapid checkpoint must compare only R1 and R5",
    )
    require(
        rapid["development"]
        == {
            "answerable_cases": 13,
            "no_evidence_cases": 13,
            "total_cases": 26,
        },
        "retrieval rapid development counts differ from the freeze",
    )
    require(
        rapid["heldout"]["access_allowed"] is False,
        "rapid held-out access must remain disabled",
    )
    require(
        rapid["heldout"]["answerable_cases"] == 39
        and rapid["heldout"]["no_evidence_cases"] == 20
        and rapid["heldout"]["total_cases"] == 59,
        "retrieval rapid held-out counts differ from the freeze",
    )
    require(
        rapid["heldout"]["answerable_cases_per_lecture"] == 3
        and sum(rapid["heldout"]["scenario_counts"].values()) == 39,
        "retrieval rapid answerable coverage differs from the freeze",
    )
    require(
        rapid["heldout"]["disjoint_from_full_v3"] is True,
        "rapid cases must remain disjoint from full retrieval-v3",
    )
    require(
        rapid["decision"]["keep_available"] is False
        and rapid["decision"]["rollback_condition"] == "R1",
        "rapid checkpoint cannot make a final selection",
    )
    require(
        rapid["decision"]["no_evidence_minimum_passes"] == 19
        and rapid["decision"]["no_evidence_denominator"] == 20,
        "rapid no-evidence decision gate differs from the freeze",
    )
    require(
        freeze["corpus"]["document_count"] == 13,
        "retrieval-v3 corpus must contain 13 documents",
    )
    require(
        freeze["corpus"]["page_count"] == 508,
        "retrieval-v3 corpus must contain 508 pages",
    )
    require(
        freeze["corpus"]["private_source_text_committed"] is False,
        "private source text cannot be committed",
    )

    datasets = unique_by_id(freeze["datasets"], "dataset_id", "dataset ID")
    require(
        set(datasets)
        == {"course-tutor-v1", "it5002-retrieval-open-set-v1"},
        "retrieval-v3 dataset set differs from the freeze",
    )
    require(
        datasets["course-tutor-v1"]["heldout_cases"] == 104,
        "course-tutor-v1 held-out count must be 104",
    )
    require(
        datasets["it5002-retrieval-open-set-v1"]["heldout_cases"] == 52,
        "open-set held-out count must be 52",
    )

    representations = unique_by_id(
        freeze["representations"], "representation_id", "representation ID"
    )
    conditions = unique_by_id(
        freeze["conditions"], "condition_id", "condition ID"
    )
    require(
        set(conditions) == {"R0", "R1", "R2", "R3", "R4", "R5", "R6", "O1"},
        "retrieval-v3 condition set differs from the freeze",
    )
    for condition in conditions.values():
        require(
            condition["representation_id"] in representations,
            f"{condition['condition_id']} has an unknown representation",
        )
        require(
            condition["final_limit"] == 5,
            f"{condition['condition_id']} final limit must be 5",
        )

    r5 = conditions["R5"]
    require(
        r5["selection_role"] == "confirmatory_candidate",
        "R5 must remain the confirmatory candidate",
    )
    first_stage_models = {item["model"] for item in r5["first_stage"]}
    require(
        first_stage_models == {"okapi-bm25", "Qwen/Qwen3-Embedding-0.6B"},
        "R5 first-stage model set differs from the freeze",
    )
    require(
        r5["reranker"]["model"] == "Qwen/Qwen3-Reranker-0.6B",
        "R5 reranker differs from the freeze",
    )
    require(
        r5["fusion"]
        == {"method": "rrf", "k": 60, "deduplicate_by": "passage_id"},
        "R5 fusion differs from the freeze",
    )

    r6 = conditions["R6"]
    require(
        r6["decomposition"]["eligible_scenario"] == "multi_evidence",
        "R6 decomposition must remain limited to multi_evidence",
    )
    require(
        r6["decomposition"]["maximum_rounds"] == 1,
        "R6 must allow exactly one decomposition round",
    )
    require(
        r6["decomposition"]["maximum_subqueries"] == 3,
        "R6 maximum subquery count must remain 3",
    )

    black_box = freeze["black_box_reference"]
    require(
        black_box["reference_id"] == "B1"
        and black_box["product"] == "NotebookLM",
        "unexpected black-box product reference",
    )
    require(
        black_box["selection_eligible"] is False,
        "NotebookLM cannot select an internal retriever",
    )
    require(
        {"recall_at_k", "ndcg_at_k", "candidate_rank"}
        <= set(black_box["prohibited_metrics"]),
        "NotebookLM hidden retrieval metrics must remain prohibited",
    )

    primary_metrics = unique_by_id(
        freeze["primary_metrics"], "metric_id", "primary metric ID"
    )
    require(
        set(primary_metrics)
        == {
            "complete_evidence_success_at_3",
            "gold_claim_context_coverage_at_3",
            "no_evidence_accuracy",
        },
        "retrieval-v3 primary metric set differs from the freeze",
    )
    require(
        primary_metrics["no_evidence_accuracy"]["eligibility_floor"] == 0.95,
        "no-evidence eligibility floor must remain 0.95",
    )

    hypotheses = unique_by_id(
        freeze["analysis"]["confirmatory_hypotheses"],
        "hypothesis_id",
        "hypothesis ID",
    )
    require(
        set(hypotheses) == {"H1", "H2", "H3"},
        "retrieval-v3 confirmatory hypothesis set differs",
    )
    require(
        freeze["analysis"]["multiple_testing"] == "holm_h1_h3",
        "retrieval-v3 must retain Holm correction for H1-H3",
    )
    require(
        freeze["analysis"]["random_seed"] == 5002,
        "retrieval-v3 analysis seed must remain 5002",
    )

    hard_gates = freeze["hard_gates"]
    require(len(hard_gates) == len(set(hard_gates)), "duplicate retrieval hard gate")
    require(
        freeze["runtime_bindings"]["status"] == "pending_feasibility_preflight",
        "runtime bindings must remain pending until the feasibility preflight",
    )

    for label, relative_path in freeze["artifact_paths"].items():
        path = ROOT / relative_path
        require(path.exists(), f"retrieval-v3 {label} artifact is missing: {path}")
    manifest = ROOT / freeze["corpus"]["manifest_path"]
    require(manifest.exists(), f"retrieval-v3 corpus manifest is missing: {manifest}")

    return {
        "conditions": len(conditions),
        "datasets": len(datasets),
        "primary_metrics": len(primary_metrics),
        "hard_gates": len(hard_gates),
        "rapid_heldout_cases": rapid["heldout"]["total_cases"],
    }


def validate_retrieval_v3_instruments() -> dict[str, int | str]:
    freeze = load_json(FREEZE_PATH)
    schema = load_json(OPEN_SET_SCHEMA_PATH)
    example = load_json(OPEN_SET_EXAMPLE_PATH)
    validate_schema(example, schema)
    example_cases = validate_open_set_example(example)
    counts = validate_freeze(freeze)
    return {"status": "passed", "example_cases": example_cases, **counts}


def main() -> int:
    try:
        result = validate_retrieval_v3_instruments()
    except (ValueError, jsonschema.SchemaError) as error:
        print(f"retrieval-v3 instrument validation failed: {error}")
        return 1
    print(
        "retrieval-v3 instrument validation passed: "
        f"{result['conditions']} conditions, {result['datasets']} datasets, "
        f"{result['primary_metrics']} primary metrics, "
        f"{result['hard_gates']} hard gates, "
        f"{result['rapid_heldout_cases']} rapid held-out cases, "
        f"{result['example_cases']} public example case"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
