#!/usr/bin/env python3
"""Materialize the immutable 452-model/48-canonical public case package."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.digital_twin.evaluation.factual_qa_contract import EvaluationCaseV1
from src.digital_twin.evaluation.provider_json import canonical_sha256
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
MATERIALIZATION_ID = "academic-factual-qa-open-10000-mixed-wording-package-005"
SOURCE_RESULT = ROOT / (
    "reports/generated/"
    "academic-factual-qa-open-10000-wording-development-004-result.json"
)
SOURCE_RESULT_SHA256 = "864664af671bdb0881cb0ea60f72f7821d1b9488a112307dcc41191df323c436"
SOURCE_CASES = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_cases_002.json"
)
SOURCE_CONTROL_CASES = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_control_cases_002.json"
)
CANDIDATE_CASES = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_mixed_wording_005_cases.json"
)
CONTROL_CASES = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_control_mixed_wording_005_cases.json"
)
PROVENANCE = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_mixed_wording_005_provenance.json"
)


class MixedWordingPackageError(RuntimeError):
    """Raised when immutable wording evidence or its public extraction drifts."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MixedWordingPackageError(f"JSON root is not an object: {path.name}")
    return value


def _load_package(path: Path, *, rows_key: str) -> dict[str, Any]:
    value = _load(path)
    expected = canonical_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise MixedWordingPackageError(f"package hash drifted: {path.name}")
    rows = value.get(rows_key)
    if not isinstance(rows, list) or value.get("case_count") != len(rows):
        raise MixedWordingPackageError(f"package count drifted: {path.name}")
    return value


def _package(*, dataset_id: str, split: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "split": split,
        "case_count": len(rows),
        "cases": rows,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    return payload


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise MixedWordingPackageError(f"exclusive output path is used: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def build_from_result(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if result.get("instrument_id") != (
        "academic-factual-qa-open-10000-development-checkpoint-004"
    ):
        raise MixedWordingPackageError("source wording instrument identity drifted")
    if result.get("status") != "completed-refine":
        raise MixedWordingPackageError("source wording result is not immutable Refine evidence")
    expected_hash = canonical_sha256(
        {key: row for key, row in result.items() if key != "content_sha256"}
    )
    if result.get("content_sha256") != expected_hash:
        raise MixedWordingPackageError("source wording content hash drifted")

    cases = [EvaluationCaseV1.model_validate(row) for row in result.get("cases", [])]
    decisions = result.get("decisions", [])
    if len(cases) != 500 or len(decisions) != 500:
        raise MixedWordingPackageError("source wording coverage drifted")
    if len({row.case_id for row in cases}) != 500:
        raise MixedWordingPackageError("source wording case IDs are not unique")
    decision_by_id = {str(row["case_id"]): row for row in decisions}
    if len(decision_by_id) != 500 or set(decision_by_id) != {row.case_id for row in cases}:
        raise MixedWordingPackageError("source wording decision identities drifted")

    status_counts = Counter(str(row["status"]) for row in decisions)
    if status_counts != {"accepted-model-wording": 452, "canonical-fallback": 48}:
        raise MixedWordingPackageError("mixed wording composition drifted")
    if result.get("accepted_wording_count") != 452 or result.get("canonical_fallback_count") != 48:
        raise MixedWordingPackageError("source wording aggregate drifted")

    source_cases = {
        row.case_id: row
        for row in (
            EvaluationCaseV1.model_validate(value)
            for value in _load_package(SOURCE_CASES, rows_key="cases")["cases"]
        )
    }
    if set(source_cases) != {row.case_id for row in cases}:
        raise MixedWordingPackageError("source canonical case identities drifted")
    for row in cases:
        if decision_by_id[row.case_id]["status"] == "canonical-fallback":
            if row.question != source_cases[row.case_id].question:
                raise MixedWordingPackageError(
                    f"canonical fallback wording drifted: {row.case_id}"
                )

    candidate_rows = [row.model_dump(mode="json") for row in cases]
    candidate = _package(
        dataset_id="academic-factual-qa-open-10000-v1-development-mixed-wording-005",
        split="development",
        rows=candidate_rows,
    )
    control_source = _load_package(SOURCE_CONTROL_CASES, rows_key="cases")
    control_ids = [str(row["case_id"]) for row in control_source["cases"]]
    if len(control_ids) != 100 or len(set(control_ids)) != 100:
        raise MixedWordingPackageError("control identity allocation drifted")
    case_by_id = {row["case_id"]: row for row in candidate_rows}
    control = _package(
        dataset_id=(
            "academic-factual-qa-open-10000-v1-development-control-"
            "mixed-wording-005"
        ),
        split="development-control",
        rows=[case_by_id[case_id] for case_id in control_ids],
    )
    provenance: dict[str, Any] = {
        "schema_version": 1,
        "provenance_id": (
            "academic-factual-qa-open-10000-v1-development-mixed-wording-005"
        ),
        "source_instrument_id": result["instrument_id"],
        "source_result_sha256": SOURCE_RESULT_SHA256,
        "source_result_content_sha256": result["content_sha256"],
        "case_count": 500,
        "accepted_model_wording_count": 452,
        "canonical_fallback_count": 48,
        "candidate_cases_content_sha256": candidate["content_sha256"],
        "control_case_count": 100,
        "control_cases_content_sha256": control["content_sha256"],
        "wording_by_case": [
            {
                "case_id": row.case_id,
                "wording_source": decision_by_id[row.case_id]["status"],
                "decision_reason": decision_by_id[row.case_id]["reason"],
            }
            for row in cases
        ],
        "provider_calls_required_to_materialize": 0,
        "hidden_gold_loaded": False,
        "private_data_used": False,
        "final_split_opened": False,
    }
    provenance["content_sha256"] = canonical_sha256(provenance)
    return {"candidate": candidate, "control": control, "provenance": provenance}


def build() -> dict[str, dict[str, Any]]:
    if not SOURCE_RESULT.is_file():
        raise MixedWordingPackageError("immutable source wording result is unavailable")
    if hashlib.sha256(SOURCE_RESULT.read_bytes()).hexdigest() != SOURCE_RESULT_SHA256:
        raise MixedWordingPackageError("source wording result file hash drifted")
    return build_from_result(_load(SOURCE_RESULT))


def write() -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(MATERIALIZATION_ID, "dataset_generation")
    packages = build()
    for path, key in (
        (CANDIDATE_CASES, "candidate"),
        (CONTROL_CASES, "control"),
        (PROVENANCE, "provenance"),
    ):
        _write_exclusive(path, packages[key])
    return summary(packages)


def check() -> dict[str, Any]:
    candidate = _load_package(CANDIDATE_CASES, rows_key="cases")
    control = _load_package(CONTROL_CASES, rows_key="cases")
    provenance = _load(PROVENANCE)
    expected = canonical_sha256(
        {key: row for key, row in provenance.items() if key != "content_sha256"}
    )
    if provenance.get("content_sha256") != expected:
        raise MixedWordingPackageError("wording provenance hash drifted")
    packages = {"candidate": candidate, "control": control, "provenance": provenance}
    if SOURCE_RESULT.is_file():
        rebuilt = build()
        if packages != rebuilt:
            raise MixedWordingPackageError("committed mixed wording package drifted")
    return summary(packages)


def summary(packages: dict[str, dict[str, Any]]) -> dict[str, Any]:
    provenance = packages["provenance"]
    return {
        "materialization_id": MATERIALIZATION_ID,
        "status": "passed",
        "case_count": packages["candidate"]["case_count"],
        "control_case_count": packages["control"]["case_count"],
        "accepted_model_wording_count": provenance["accepted_model_wording_count"],
        "canonical_fallback_count": provenance["canonical_fallback_count"],
        "candidate_cases_content_sha256": packages["candidate"]["content_sha256"],
        "control_cases_content_sha256": packages["control"]["content_sha256"],
        "provider_calls": 0,
        "hidden_gold_loaded": False,
        "final_split_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.write:
        require_bounded_pilot_operation_allowed(MATERIALIZATION_ID, "dataset_generation")
    result = write() if arguments.write else check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
