#!/usr/bin/env python3
"""Apply the one scorer-only correction to immutable confirmation 012 outputs."""

from __future__ import annotations

import argparse
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


ANALYSIS_CORRECTION_ID = (
    "governed-full-autonomy-v2-1-actual-product-confirmation-012-"
    "analysis-correction-001"
)
CORRECTION_RESULT = runner.CONTEXT.output_root / "analysis-correction-001.json"


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
    rows = runner.shared._load_completed_responses(runner.CONTEXT)
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
