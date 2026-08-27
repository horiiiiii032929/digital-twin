#!/usr/bin/env python3
"""Score checkpoint 003 only after candidate and control responses complete."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from scripts import score_academic_factual_qa_open_10000 as scorer
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-checkpoint-003"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_checkpoint_003.json"
)
GENERATED = ROOT / "reports/generated"
CANDIDATE_CASES = GENERATED / "academic-factual-qa-open-10000-v1-development-003-cases.json"
CANDIDATE_GOLD = GENERATED / "academic-factual-qa-open-10000-v1-development-003-gold.json"
CANDIDATE_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-003-candidate-responses.sqlite3"
)
CONTROL_CASES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-control-003-cases.json"
)
CONTROL_GOLD = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-control-003-gold.json"
)
CONTROL_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-003-control-responses.sqlite3"
)
CANDIDATE_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-003-candidate-result.json"
)
PAIRED_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-003-paired-result.json"
)


@contextmanager
def configured_scorer() -> Iterator[None]:
    previous_id = scorer.INSTRUMENT_ID
    previous_path = scorer.INSTRUMENT_PATH
    try:
        scorer.INSTRUMENT_ID = INSTRUMENT_ID
        scorer.INSTRUMENT_PATH = INSTRUMENT_PATH
        yield
    finally:
        scorer.INSTRUMENT_ID = previous_id
        scorer.INSTRUMENT_PATH = previous_path


def _require_complete(path: Path, count: int) -> None:
    if not path.is_file():
        raise RuntimeError(f"response ledger is missing: {path.name}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    finally:
        connection.close()
    if metadata.get("status") != "completed" or int(
        metadata.get("response_count", "-1")
    ) != count:
        raise RuntimeError(f"response ledger is incomplete: {path.name}")


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"exclusive result path is used: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT_PATH.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise RuntimeError("development scoring instrument drifted")
    if len(instrument.get("hard_gates", {})) != 22:
        raise RuntimeError("development hard-gate count drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "hard_gate_count": len(instrument["hard_gates"]),
        "gold_join_requires_both_response_ledgers": True,
        "provider_calls": 0,
    }


def simulate() -> dict[str, Any]:
    with configured_scorer():
        result = scorer.simulate()
    return {**result, "instrument_id": INSTRUMENT_ID}


def score() -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    # Check both ledgers before importing either hidden-gold package below.
    _require_complete(CANDIDATE_RESPONSES, 500)
    _require_complete(CONTROL_RESPONSES, 100)
    with configured_scorer():
        candidate = scorer.score_packages(
            cases_path=CANDIDATE_CASES,
            gold_path=CANDIDATE_GOLD,
            responses_path=CANDIDATE_RESPONSES,
        )
        control = scorer.score_packages(
            cases_path=CONTROL_CASES,
            gold_path=CONTROL_GOLD,
            responses_path=CONTROL_RESPONSES,
        )
        gates = json.loads(INSTRUMENT_PATH.read_text(encoding="utf-8"))["hard_gates"]
        paired = scorer.paired_comparison(
            candidate,
            control,
            lower_delta_gate=gates[
                "paired_supported_retention_delta_lower_95_min"
            ],
            boundary_not_worse=gates["paired_boundary_safety_not_worse"],
        )
    _write_exclusive(CANDIDATE_RESULT, candidate)
    _write_exclusive(PAIRED_RESULT, paired)
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": paired["status"],
        "decision": paired["decision"],
        "candidate_status": candidate["status"],
        "failed_gates": paired["failed_gates"],
        "paired_case_count": paired["paired_case_count"],
        "hidden_gold_opened_after_all_responses_completed": True,
        "provider_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--score", action="store_true")
    arguments = parser.parse_args()
    if arguments.score:
        result = score()
    elif arguments.simulate:
        result = simulate()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
