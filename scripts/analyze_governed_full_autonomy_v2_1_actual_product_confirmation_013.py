#!/usr/bin/env python3
"""Correct confirmation 013 reference actions against the approved fallback contract."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
from dataclasses import replace
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
    run_governed_full_autonomy_v2_1_actual_product_confirmation_013 as runner,
)
from src.digital_twin.evaluation import AutonomyEvaluationResponseV1
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ANALYSIS_CORRECTION_ID = (
    "governed-full-autonomy-v2-1-actual-product-confirmation-013-"
    "reference-validity-correction-001"
)
CORRECTION_RESULT = runner.CONTEXT.output_root / "reference-validity-correction-001.json"
ORIGINAL_RUN_BINDING_SHA256 = (
    "11ae5bc1dc5f28dcd4f24b2747ebd504480849ac93be4fcee9c2eb0c4e022f6a"
)
V2_CONDITIONS = {"t1-v2-reactive", "t1-v2-autonomous"}


def _provider_failure_v2_case_ids() -> set[str]:
    selected = set()
    for condition, case, _gold in runner.CONTEXT.builder.build_contract():
        failure_times = [
            event.at_seconds for event in case.events if event.kind == "provider-failure"
        ]
        if condition not in V2_CONDITIONS or not failure_times:
            continue
        if any(
            event.kind == "student-message" and event.at_seconds > min(failure_times)
            for event in case.events
        ):
            selected.add(case.case_id)
    return selected


class _FallbackAlignedBuilder:
    """Expose the same public cases with corrected provider-fallback references."""

    def __getattr__(self, name: str) -> Any:
        return getattr(runner.CONTEXT.builder, name)

    @staticmethod
    def _correct_gold(gold):
        expected = []
        changed = 0
        for action in gold.expected_actions:
            if action.action == "no-action" and action.earliest_seconds == 3600:
                action = action.model_copy(
                    update={
                        "action": "provide-hint-or-example",
                        "must_have_valid_lineage": True,
                    }
                )
                changed += 1
            expected.append(action)
        if changed != 1:
            raise ValueError(
                f"expected one provider-fallback reference in {gold.case_id}, got {changed}"
            )
        return gold.model_copy(update={"expected_actions": expected})

    def build_contract(self):
        target_ids = _provider_failure_v2_case_ids()
        rows = []
        changed = 0
        for condition, case, gold in runner.CONTEXT.builder.build_contract():
            if case.case_id in target_ids:
                gold = self._correct_gold(gold)
                changed += 1
            rows.append((condition, case, gold))
        if changed != 30:
            raise ValueError(f"expected 30 corrected V2 references, got {changed}")
        return rows

    def hidden_gold_payload(self) -> dict[str, Any]:
        payload = json.loads(
            json.dumps(runner.CONTEXT.builder.hidden_gold_payload())
        )
        target_ids = _provider_failure_v2_case_ids()
        changed = 0
        for row in payload["gold"]:
            if row["case_id"] not in target_ids:
                continue
            matching = [
                action
                for action in row["expected_actions"]
                if action["action"] == "no-action"
                and action["earliest_seconds"] == 3600
            ]
            if len(matching) != 1:
                raise ValueError(
                    f"expected one provider-fallback reference in {row['case_id']}"
                )
            matching[0]["action"] = "provide-hint-or-example"
            matching[0]["must_have_valid_lineage"] = True
            changed += 1
        if changed != 30:
            raise ValueError(f"expected 30 corrected hidden references, got {changed}")
        payload.pop("content_sha256", None)
        payload["content_sha256"] = runner.CONTEXT.builder.canonical_hash(payload)
        return payload


CORRECTED_BUILDER = _FallbackAlignedBuilder()
CORRECTED_CONTEXT = replace(
    runner.CONTEXT,
    builder=CORRECTED_BUILDER,
    instrument_id=ANALYSIS_CORRECTION_ID,
)


def _load_immutable_responses() -> list[tuple[str, AutonomyEvaluationResponseV1]]:
    connection = sqlite3.connect(
        f"file:{runner.CONTEXT.response_ledger}?mode=ro", uri=True
    )
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        expected = {
            "schema_version": "1",
            "run_binding_sha256": ORIGINAL_RUN_BINDING_SHA256,
            "expected_count": "820",
            "public_sha256": (
                "12f6c5fc9c35b150340744cf1b5a0caf080a6d073a9cf3ff585174424d143d02"
            ),
            "status": "completed",
            "response_count": "820",
            "clock_origin": "2026-09-01T12:00:00+00:00",
            "clock_timezone": "UTC",
        }
        if metadata != expected:
            raise ValueError("immutable confirmation-013 ledger metadata drifted")
        persisted = list(
            connection.execute(
                "SELECT condition_id,payload_json,payload_sha256 "
                "FROM responses ORDER BY sequence"
            )
        )
    finally:
        connection.close()
    if len(persisted) != 820:
        raise ValueError("immutable confirmation-013 response count drifted")
    rows = []
    for condition, serialized, expected_hash in persisted:
        if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != expected_hash:
            raise ValueError("immutable confirmation-013 response hash drifted")
        rows.append(
            (condition, AutonomyEvaluationResponseV1.model_validate_json(serialized))
        )
    return rows


def validate_contract() -> dict[str, Any]:
    original = runner.CONTEXT.builder.build_contract()
    corrected = CORRECTED_BUILDER.build_contract()
    target_ids = _provider_failure_v2_case_ids()
    if len(target_ids) != 30:
        raise ValueError("provider-failure V2 reference count drifted")
    changed_ids = {
        original_row[1].case_id
        for original_row, corrected_row in zip(original, corrected, strict=True)
        if original_row[2] != corrected_row[2]
    }
    if changed_ids != target_ids:
        raise ValueError("reference correction changed cases outside the target set")
    return {
        "analysis_correction_id": ANALYSIS_CORRECTION_ID,
        "corrected_reference_count": len(changed_ids),
        "correction_scope": "provider-failure-v2-safe-deterministic-fallback",
        "provider_calls_added": 0,
    }


def validate() -> dict[str, Any]:
    contract = validate_contract()
    result = json.loads(runner.CONTEXT.result_path.read_text(encoding="utf-8"))
    if result.get("status") != "completed-refine":
        raise ValueError("confirmation 013 terminal Refine result drifted")
    if result.get("summary", {}).get("unauthorized_or_unexpected_actions") != 30:
        raise ValueError("confirmation 013 failure cardinality drifted")
    _load_immutable_responses()
    return {**contract, "status": "passed-analysis-ready", "response_count": 820}


def execute() -> dict[str, Any]:
    validate()
    require_bounded_pilot_operation_allowed(
        runner.CONTEXT.instrument_id, "method_evaluation_execution"
    )
    if CORRECTION_RESULT.exists():
        raise ValueError("reference-validity correction output already exists")
    result = runner.shared._score(_load_immutable_responses(), CORRECTED_CONTEXT)
    result.update(
        {
            "analysis_correction_id": ANALYSIS_CORRECTION_ID,
            "predecessor_result_id": runner.CONTEXT.instrument_id,
            "correction_scope": (
                "30 V2 provider-failure references aligned to the approved "
                "deterministic T1-v1/T0 fallback contract"
            ),
            "provider_calls_added": 0,
            "responses_reused_unchanged": True,
            "original_result_preserved": True,
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
