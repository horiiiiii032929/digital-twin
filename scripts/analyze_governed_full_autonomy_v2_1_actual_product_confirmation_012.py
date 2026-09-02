#!/usr/bin/env python3
"""Apply the one scorer-only correction to immutable confirmation 012 outputs."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_012 as runner,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.evaluation import AutonomyEvaluationResponseV1


ANALYSIS_CORRECTION_ID = (
    "governed-full-autonomy-v2-1-actual-product-confirmation-012-"
    "analysis-correction-001"
)
CORRECTION_RESULT = runner.CONTEXT.output_root / "analysis-correction-001.json"
ORIGINAL_RUN_BINDING_SHA256 = (
    "b0c60d4173c2105f2c1303ecf87a5fdcbd4a771d77cabcc420ca663aa246a460"
)


def _load_immutable_responses() -> list[tuple[str, AutonomyEvaluationResponseV1]]:
    connection = sqlite3.connect(
        f"file:{runner.CONTEXT.response_ledger}?mode=ro", uri=True
    )
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata != {
            "schema_version": "1",
            "run_binding_sha256": ORIGINAL_RUN_BINDING_SHA256,
            "expected_count": "820",
            "public_sha256": (
                "23693a4c27b01603147f301bb9d91fe5c6f86be81b432bf601800d689849c9bc"
            ),
            "status": "completed",
            "response_count": "820",
            "clock_origin": "2026-09-01T12:00:00+00:00",
            "clock_timezone": "UTC",
        }:
            raise ValueError("immutable confirmation-012 ledger metadata drifted")
        persisted = list(
            connection.execute(
                "SELECT condition_id,payload_json,payload_sha256 "
                "FROM responses ORDER BY sequence"
            )
        )
    finally:
        connection.close()
    if len(persisted) != 820:
        raise ValueError("immutable confirmation-012 response count drifted")
    rows: list[tuple[str, AutonomyEvaluationResponseV1]] = []
    for condition, serialized, expected_hash in persisted:
        if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != expected_hash:
            raise ValueError("immutable confirmation-012 response hash drifted")
        rows.append(
            (condition, AutonomyEvaluationResponseV1.model_validate_json(serialized))
        )
    return rows


def validate_contract() -> dict[str, Any]:
    runner.validate()
    proactive_case_count = sum(
        runner.shared._is_proactive_evaluation_case(case)
        for _condition, case, _gold in runner.CONTEXT.builder.build_contract()
    )
    if proactive_case_count != 220:
        raise ValueError("corrected proactive event classification drifted")
    return {
        "analysis_correction_id": ANALYSIS_CORRECTION_ID,
        "proactive_case_count": proactive_case_count,
        "provider_calls_added": 0,
    }


def validate() -> dict[str, Any]:
    contract = validate_contract()
    invalid = json.loads(runner.CONTEXT.result_path.read_text(encoding="utf-8"))
    if invalid.get("status") != "invalid-execution":
        raise ValueError("confirmation 012 terminal result is not immutable invalid evidence")
    if invalid.get("failure_type") != "ZeroDivisionError":
        raise ValueError("confirmation 012 failure classification drifted")
    connection = sqlite3.connect(
        f"file:{runner.CONTEXT.response_ledger}?mode=ro", uri=True
    )
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
    finally:
        connection.close()
    if metadata.get("status") != "completed" or metadata.get("response_count") != "820":
        raise ValueError("confirmation 012 response ledger is not complete")
    return {
        **contract,
        "status": "passed-analysis-ready",
        "immutable_response_count": 820,
    }


def execute() -> dict[str, Any]:
    validate()
    require_bounded_pilot_operation_allowed(
        runner.CONTEXT.instrument_id, "method_evaluation_execution"
    )
    if CORRECTION_RESULT.exists():
        raise ValueError("analysis-correction output already exists")
    rows = _load_immutable_responses()
    result = runner.shared._score(rows, runner.CONTEXT)
    result.update(
        {
            "analysis_correction_id": ANALYSIS_CORRECTION_ID,
            "predecessor_result_id": (
                "governed-full-autonomy-v2-1-actual-product-confirmation-012-invalid"
            ),
            "correction_scope": "proactive-case-classification-only",
            "provider_calls_added": 0,
            "responses_reused_unchanged": True,
        }
    )
    runner.shared._atomic_write(CORRECTION_RESULT, result, exclusive=True)
    return result


def main() -> int:
    require_bounded_pilot_operation_allowed(
        runner.CONTEXT.instrument_id, "method_evaluation_execution"
    )
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    result = execute() if arguments.execute else validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
