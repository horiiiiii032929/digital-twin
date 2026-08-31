#!/usr/bin/env python3
"""Freeze three source-range-disjoint development folds for architecture work."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.digital_twin.evaluation.architecture_evolution import (
    ArchitectureDevelopmentFreezeV1,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
OUTPUT_ROOT = DATASET_ROOT / "architecture_evolution_001"
PROGRAM_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "course_digital_twin_whole_system_architecture_evolution_001.json"
)
FREEZE_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "course_digital_twin_whole_system_architecture_development_freeze_001.json"
)
PROGRAM_ID = "course-digital-twin-whole-system-architecture-evolution-001"
FREEZE_ID = "course-digital-twin-whole-system-architecture-development-freeze-001"

_INPUTS = (
    (1, "architecture-round-1-development", "source-aligned"),
    (2, "architecture-round-2-development", "atomic-m2"),
    (3, "architecture-round-3-development", "action-router"),
)


class ArchitectureTrancheBuildError(RuntimeError):
    """Raised when a development fold is not reproducible or independent."""


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _load_hashed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ArchitectureTrancheBuildError(f"JSON root is not an object: {path}")
    observed = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise ArchitectureTrancheBuildError(f"content hash drifted: {path.name}")
    return value


def _package(
    *,
    kind: str,
    tranche_id: str,
    rows: list[dict[str, Any]],
    source_sha256: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "tranche_id": tranche_id,
        "package_kind": kind,
        "case_count": len(rows),
        "source_package_sha256": source_sha256,
        "private_data_used": False,
        "provider_calls": 0,
        "product_inputs_exclude_gold": True,
        "rows": rows,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def _range_rows(source: dict[str, Any]) -> list[tuple[str, int, int, int]]:
    rows: list[tuple[str, int, int, int]] = []
    for chunk in source.get("chunks", []):
        metadata = chunk.get("metadata", {})
        try:
            rows.append(
                (
                    str(chunk["source_artifact_id"]),
                    int(chunk["source_version"]),
                    int(metadata["char_start"]),
                    int(metadata["char_end"]),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ArchitectureTrancheBuildError(
                "source chunk lacks canonical character lineage"
            ) from error
    if not rows:
        raise ArchitectureTrancheBuildError("source package has no canonical ranges")
    return rows


def _ranges_overlap(
    left: list[tuple[str, int, int, int]],
    right: list[tuple[str, int, int, int]],
) -> bool:
    for left_source, left_version, left_start, left_end in left:
        for right_source, right_version, right_start, right_end in right:
            if (
                left_source == right_source
                and left_version == right_version
                and max(left_start, right_start) < min(left_end, right_end)
            ):
                return True
    return False


def build() -> tuple[dict[str, Any], dict[Path, dict[str, Any]]]:
    if not PROGRAM_PATH.is_file():
        raise ArchitectureTrancheBuildError("architecture program is missing")
    program_sha256 = _raw_sha256(PROGRAM_PATH)
    seen_questions: set[str] = set()
    earlier_ranges: list[list[tuple[str, int, int, int]]] = []
    outputs: dict[Path, dict[str, Any]] = {}
    frozen_rows: list[dict[str, Any]] = []

    for round_number, tranche_id, stem in _INPUTS:
        prefix = DATASET_ROOT / f"academic-factual-qa-{stem}-confirmation-001"
        source_path = Path(f"{prefix}-sources.json")
        cases_path = Path(f"{prefix}-cases.json")
        gold_path = Path(f"{prefix}-gold.json")
        source = _load_hashed(source_path)
        cases = _load_hashed(cases_path)
        gold = _load_hashed(gold_path)

        case_rows = cases.get("cases")
        gold_rows = gold.get("gold")
        if not isinstance(case_rows, list) or not isinstance(gold_rows, list):
            raise ArchitectureTrancheBuildError("input package rows are malformed")
        validated_cases = [EvaluationCaseV1.model_validate(row) for row in case_rows]
        gold_by_id = {
            item.case_id: item
            for item in (EvaluationGoldV1.model_validate(row) for row in gold_rows)
        }
        if len(gold_by_id) != len(gold_rows):
            raise ArchitectureTrancheBuildError("input gold contains duplicate case IDs")

        kept_cases: list[dict[str, Any]] = []
        kept_gold: list[dict[str, Any]] = []
        removed: list[str] = []
        for case in validated_cases:
            normalized = normalize_question(case.question)
            if normalized in seen_questions:
                removed.append(case.case_id)
                continue
            reference = gold_by_id.get(case.case_id)
            if reference is None:
                raise ArchitectureTrancheBuildError(
                    f"public case lacks hidden gold: {case.case_id}"
                )
            seen_questions.add(normalized)
            kept_cases.append(case.model_dump(mode="json"))
            kept_gold.append(reference.model_dump(mode="json"))

        case_ids = {row["case_id"] for row in kept_cases}
        if case_ids != {row["case_id"] for row in kept_gold}:
            raise ArchitectureTrancheBuildError("public and gold case IDs differ")
        if len(kept_cases) < 400:
            raise ArchitectureTrancheBuildError("development fold is too small")

        ranges = _range_rows(source)
        if any(_ranges_overlap(ranges, previous) for previous in earlier_ranges):
            raise ArchitectureTrancheBuildError(
                f"{tranche_id} overlaps an earlier source range"
            )
        earlier_ranges.append(ranges)

        output_cases = OUTPUT_ROOT / f"round-{round_number}-cases.json"
        output_gold = OUTPUT_ROOT / f"round-{round_number}-gold.json"
        source_sha256 = _raw_sha256(source_path)
        case_package = _package(
            kind="public-cases",
            tranche_id=tranche_id,
            rows=kept_cases,
            source_sha256=source_sha256,
        )
        gold_package = _package(
            kind="hidden-gold",
            tranche_id=tranche_id,
            rows=kept_gold,
            source_sha256=source_sha256,
        )
        outputs[output_cases] = case_package
        outputs[output_gold] = gold_package
        frozen_rows.append(
            {
                "tranche_id": tranche_id,
                "round_number": round_number,
                "source": {
                    "path": _relative(source_path),
                    "sha256": source_sha256,
                    "role": "source-corpus",
                },
                "public_cases": {
                    "path": _relative(output_cases),
                    "sha256": hashlib.sha256(_json_bytes(case_package)).hexdigest(),
                    "role": "public-cases",
                },
                "hidden_gold": {
                    "path": _relative(output_gold),
                    "sha256": hashlib.sha256(_json_bytes(gold_package)).hexdigest(),
                    "role": "hidden-gold",
                },
                "case_count": len(kept_cases),
                "cluster_count": len({row["cluster_id"] for row in kept_cases}),
                "removed_duplicate_case_ids": removed,
                "source_range_overlap_with_earlier_folds": 0,
                "normalized_question_overlap_with_earlier_folds": 0,
            }
        )

    freeze = {
        "schema_version": 1,
        "freeze_id": FREEZE_ID,
        "program_id": PROGRAM_ID,
        "program_sha256": program_sha256,
        "status": "frozen-build-only",
        "deterministic_truth_authoritative": True,
        "product_inputs_exclude_gold": True,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "tranches": frozen_rows,
    }
    ArchitectureDevelopmentFreezeV1.model_validate(freeze)
    outputs[FREEZE_PATH] = freeze
    return freeze, outputs


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write() -> dict[str, Any]:
    freeze, outputs = build()
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = _json_bytes(payload)
        if path.exists() and path.read_bytes() != serialized:
            raise ArchitectureTrancheBuildError(f"frozen output drifted: {path}")
        path.write_bytes(serialized)
    return summary(freeze, status="written")


def check() -> dict[str, Any]:
    freeze, outputs = build()
    for path, payload in outputs.items():
        if not path.is_file() or path.read_bytes() != _json_bytes(payload):
            raise ArchitectureTrancheBuildError(f"frozen output is stale: {path}")
    return summary(freeze, status="passed")


def summary(value: dict[str, Any], *, status: str) -> dict[str, Any]:
    return {
        "freeze_id": value["freeze_id"],
        "status": status,
        "round_case_counts": {
            str(row["round_number"]): row["case_count"] for row in value["tranches"]
        },
        "removed_duplicate_count": sum(
            len(row["removed_duplicate_case_ids"]) for row in value["tranches"]
        ),
        "source_range_overlap_count": 0,
        "normalized_cross_fold_question_overlap_count": 0,
        "provider_calls": 0,
        "paid_cost_usd": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = write() if args.write else check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
