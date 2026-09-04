#!/usr/bin/env python3
"""Score a confirmation whose responses completed but whose scoring crashed.

An attempt is marked ``invalid-execution`` whenever anything after response
execution raises, including a defect in the harness itself. When the response
ledger nonetheless reports ``completed`` with the full expected count, the
product's answers are durable, hash-verified, and were produced before hidden
gold was opened. Scoring them is a pure function of (responses, gold): it runs
no product code, calls no provider, and cannot change a single response.

This entrypoint recovers that score. It deliberately does not clear the
terminal marker on the original attempt: that attempt stays invalid in the
record, and the score produced here is published as a correction to it, with
the original failure named.

Guards, all of them the harness's own:

* ``_load_completed_responses`` refuses unless the ledger status is
  ``completed``, the response count equals the case count, and the run binding
  hash matches; it also re-verifies every persisted response hash.
* ``_score`` refuses unless the persisted hidden gold matches the gold the
  builder computes.

Nothing here can execute a case. If the ledger is short, the run is genuinely
invalid and the successor must be a fresh package.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_governed_full_autonomy_v2_1_actual_product_evaluation_002 as shared  # noqa: E402
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


CONTEXTS = {
    "governed-full-autonomy-v2-1-corpus-confirmation-025": (
        "scripts.run_governed_full_autonomy_v2_1_corpus_confirmation_025"
    ),
}


class ScoreRecoveryError(RuntimeError):
    """Raised when a score cannot be recovered from durable responses."""


def _context(instrument_id: str):
    module_name = CONTEXTS.get(instrument_id)
    if module_name is None:
        raise ScoreRecoveryError(f"no registered recovery context: {instrument_id}")
    import importlib

    return importlib.import_module(module_name).CONTEXT


def _ledger_state(context) -> dict[str, Any]:
    path = context.response_ledger
    if not path.is_file():
        raise ScoreRecoveryError(f"response ledger is missing: {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        rows = connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
    finally:
        connection.close()
    return {
        "status": metadata.get("status"),
        "response_count": int(rows),
        "expected_count": int(metadata.get("expected_count", 0)),
        "public_sha256": metadata.get("public_sha256"),
    }


def _original_failure(context) -> dict[str, Any]:
    path = context.output_root / "result.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") == "invalid-execution":
        return {
            "original_status": payload["status"],
            "original_failure_type": payload.get("failure_type"),
            "original_failure_detail": payload.get("failure_detail"),
            "original_accounting": payload.get("accounting"),
        }
    return {"original_status": payload.get("status")}


def recover(instrument_id: str) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(
        instrument_id, "method_evaluation_execution"
    )
    context = _context(instrument_id)
    state = _ledger_state(context)
    if state["status"] != "completed":
        raise ScoreRecoveryError(
            f"ledger status is {state['status']!r}; only a completed response "
            "ledger can be scored, and a short ledger requires a fresh package"
        )
    if state["response_count"] != context.case_count:
        raise ScoreRecoveryError(
            f"ledger holds {state['response_count']} of {context.case_count} "
            "responses; a fresh package is required"
        )

    # Both calls are the ones execute() itself makes after execution.
    rows = shared._load_completed_responses(context)  # noqa: SLF001
    result = shared._score(rows, context)  # noqa: SLF001
    return {
        **result,
        "score_recovered_from_durable_responses": True,
        "responses_re_executed": False,
        "provider_calls_during_recovery": 0,
        "original_attempt": _original_failure(context),
        "recovery_note": (
            "The original attempt is recorded invalid. Its responses completed "
            "and hash-verified before hidden gold opened, so this score is a "
            "correction to that attempt, not a new execution."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instrument-id", required=True, choices=sorted(CONTEXTS))
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()
    require_bounded_pilot_operation_allowed(
        arguments.instrument_id, "method_evaluation_execution"
    )
    result = recover(arguments.instrument_id)
    serialized = json.dumps(result, indent=2, sort_keys=True)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
