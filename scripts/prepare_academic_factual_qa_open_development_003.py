#!/usr/bin/env python3
"""Materialize paired runtime packages after wording checkpoint 003 passes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.provider_json import canonical_sha256
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-checkpoint-003"
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
WORDING_RESULT = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-wording-development-003-result.json"
)
SOURCE_GOLD = DATASET_ROOT / "academic_factual_qa_open_10000_v1_development_gold_002.json"
SOURCE_CONTROL_CASES = DATASET_ROOT / (
    "academic_factual_qa_open_10000_v1_development_control_cases_002.json"
)
SOURCE_CONTROL_GOLD = DATASET_ROOT / (
    "academic_factual_qa_open_10000_v1_development_control_gold_002.json"
)
CANDIDATE_CASES = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-v1-development-003-cases.json"
)
CANDIDATE_GOLD = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-v1-development-003-gold.json"
)
CONTROL_CASES = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-v1-development-control-003-cases.json"
)
CONTROL_GOLD = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-v1-development-control-003-gold.json"
)


class DevelopmentPackageError(RuntimeError):
    """Raised when paired development packages cannot be materialized safely."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DevelopmentPackageError(f"JSON root is not an object: {path.name}")
    return value


def _validate_package(path: Path, *, rows_key: str) -> dict[str, Any]:
    value = _load(path)
    expected = canonical_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise DevelopmentPackageError(f"package hash drifted: {path.name}")
    if value.get("case_count") != len(value.get(rows_key, [])):
        raise DevelopmentPackageError(f"package row count drifted: {path.name}")
    return value


def _package(*, dataset_id: str, split: str, key: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "split": split,
        "case_count": len(rows),
        key: rows,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    return payload


def build_packages(wording_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if wording_result.get("instrument_id") != INSTRUMENT_ID:
        raise DevelopmentPackageError("wording result instrument drifted")
    if wording_result.get("status") != "completed-go-deeper":
        raise DevelopmentPackageError("wording result did not pass")
    cases = [EvaluationCaseV1.model_validate(row) for row in wording_result.get("cases", [])]
    if len(cases) != 500 or len({row.case_id for row in cases}) != 500:
        raise DevelopmentPackageError("wording result case coverage drifted")
    gold_source = _validate_package(SOURCE_GOLD, rows_key="gold")
    gold = [EvaluationGoldV1.model_validate(row) for row in gold_source["gold"]]
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise DevelopmentPackageError("wording and hidden-gold identities drifted")
    control_source = _validate_package(SOURCE_CONTROL_CASES, rows_key="cases")
    control_gold_source = _validate_package(SOURCE_CONTROL_GOLD, rows_key="gold")
    control_ids = [row["case_id"] for row in control_source["cases"]]
    if len(control_ids) != 100 or len(set(control_ids)) != 100:
        raise DevelopmentPackageError("control subset identities drifted")
    case_by_id = {row.case_id: row for row in cases}
    gold_by_id = {row.case_id: row for row in gold}
    if set(control_ids) != {row["case_id"] for row in control_gold_source["gold"]}:
        raise DevelopmentPackageError("control cases and hidden gold are not paired")
    candidate_id = "academic-factual-qa-open-10000-v1-development-003"
    control_id = "academic-factual-qa-open-10000-v1-development-control-003"
    return {
        "candidate_cases": _package(
            dataset_id=candidate_id,
            split="development",
            key="cases",
            rows=[row.model_dump(mode="json") for row in cases],
        ),
        "candidate_gold": _package(
            dataset_id=candidate_id,
            split="development",
            key="gold",
            rows=[row.model_dump(mode="json") for row in gold],
        ),
        "control_cases": _package(
            dataset_id=control_id,
            split="development-control",
            key="cases",
            rows=[case_by_id[case_id].model_dump(mode="json") for case_id in control_ids],
        ),
        "control_gold": _package(
            dataset_id=control_id,
            split="development-control",
            key="gold",
            rows=[gold_by_id[case_id].model_dump(mode="json") for case_id in control_ids],
        ),
    }


def validate() -> dict[str, Any]:
    gold = _validate_package(SOURCE_GOLD, rows_key="gold")
    control_cases = _validate_package(SOURCE_CONTROL_CASES, rows_key="cases")
    control_gold = _validate_package(SOURCE_CONTROL_GOLD, rows_key="gold")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "candidate_gold_count": gold["case_count"],
        "control_case_count": control_cases["case_count"],
        "control_gold_count": control_gold["case_count"],
        "provider_calls": 0,
    }


def simulate() -> dict[str, Any]:
    source_cases = _validate_package(
        DATASET_ROOT / "academic_factual_qa_open_10000_v1_development_cases_002.json",
        rows_key="cases",
    )
    simulated = {
        "instrument_id": INSTRUMENT_ID,
        "status": "completed-go-deeper",
        "cases": source_cases["cases"],
    }
    packages = build_packages(simulated)
    with tempfile.TemporaryDirectory(prefix="academic-open-development-003-") as directory:
        root = Path(directory)
        for name, payload in packages.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            _validate_package(
                path, rows_key="gold" if name.endswith("gold") else "cases"
            )
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "simulated-network-free",
        "candidate_case_count": packages["candidate_cases"]["case_count"],
        "control_case_count": packages["control_cases"]["case_count"],
        "provider_calls": 0,
    }


def write() -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    packages = build_packages(_load(WORDING_RESULT))
    outputs = {
        CANDIDATE_CASES: packages["candidate_cases"],
        CANDIDATE_GOLD: packages["candidate_gold"],
        CONTROL_CASES: packages["control_cases"],
        CONTROL_GOLD: packages["control_gold"],
    }
    for path in outputs:
        if path.exists():
            raise DevelopmentPackageError(f"exclusive output path is used: {path.name}")
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "runtime-packages-completed",
        "candidate_case_count": packages["candidate_cases"]["case_count"],
        "control_case_count": packages["control_cases"]["case_count"],
        "hidden_gold_loaded_after_wording_completion": True,
        "provider_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    if arguments.write:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
        result = write()
    elif arguments.simulate:
        result = simulate()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
