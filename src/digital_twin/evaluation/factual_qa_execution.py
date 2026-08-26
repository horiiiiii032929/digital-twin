"""Atomic response persistence for flow-independent factual-QA runs.

This module deliberately has no dependency on the hidden-gold contract or the
scorer.  A response process can therefore be imported and executed without a
code path capable of loading reference answers.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Iterable

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationResponseV1,
    EvaluationUsageV1,
    SystemUnderTestManifestV1,
    TutorEvaluationAdapterV1,
)


class FactualQaExecutionError(RuntimeError):
    """Raised when an execution or resume binding is unsafe."""


def canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ResponseLedgerV1:
    """Exclusive SQLite ledger bound to cases, SUT manifest, and run config."""

    def __init__(
        self,
        path: Path,
        *,
        cases_sha256: str,
        system_manifest_sha256: str,
        run_configuration_sha256: str,
        resume: bool,
    ) -> None:
        self.path = path
        expected = {
            "schema_version": "1",
            "cases_sha256": cases_sha256,
            "system_manifest_sha256": system_manifest_sha256,
            "run_configuration_sha256": run_configuration_sha256,
        }
        if resume and not path.is_file():
            raise FactualQaExecutionError("resume ledger does not exist")
        if not resume and path.exists():
            raise FactualQaExecutionError("response ledger already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not resume:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS responses (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL
            )
            """
        )
        if resume:
            actual = dict(self.connection.execute("SELECT key, value FROM metadata"))
            if any(actual.get(key) != value for key, value in expected.items()):
                self.connection.close()
                raise FactualQaExecutionError("response resume binding drifted")
            if actual.get("status") not in {"running", "interrupted"}:
                self.connection.close()
                raise FactualQaExecutionError("response ledger is terminal")
            self._set_metadata("status", "running")
        else:
            with self.connection:
                for key, value in {**expected, "status": "running"}.items():
                    self.connection.execute(
                        "INSERT INTO metadata(key, value) VALUES (?, ?)", (key, value)
                    )

    def _set_metadata(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO metadata(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def completed_case_ids(self) -> set[str]:
        return {row[0] for row in self.connection.execute("SELECT case_id FROM responses")}

    def record(self, response: EvaluationResponseV1) -> None:
        payload = response.model_dump(mode="json")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self.connection:
            self.connection.execute(
                "INSERT INTO responses(case_id, payload_json, payload_sha256) VALUES (?, ?, ?)",
                (
                    response.case_id,
                    serialized,
                    hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                ),
            )

    def mark_interrupted(self) -> None:
        self._set_metadata("status", "interrupted")

    def mark_complete(self, *, expected_count: int) -> None:
        actual = self.connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        if actual != expected_count:
            raise FactualQaExecutionError(
                f"cannot complete response ledger with {actual}/{expected_count} rows"
            )
        self._set_metadata("status", "completed")
        self._set_metadata("response_count", str(actual))

    def snapshot(self) -> dict[str, str | int]:
        metadata = dict(self.connection.execute("SELECT key, value FROM metadata"))
        return {
            **metadata,
            "response_count": self.connection.execute(
                "SELECT COUNT(*) FROM responses"
            ).fetchone()[0],
        }

    def close(self) -> None:
        self.connection.close()


async def execute_cases(
    *,
    cases: Iterable[EvaluationCaseV1],
    adapter: TutorEvaluationAdapterV1,
    manifest: SystemUnderTestManifestV1,
    ledger: ResponseLedgerV1,
) -> dict[str, str | int]:
    rows = list(cases)
    identifiers = [row.case_id for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise FactualQaExecutionError("public input contains duplicate case IDs")
    completed = ledger.completed_case_ids()
    if not completed <= set(identifiers):
        raise FactualQaExecutionError("ledger contains a case outside the input package")
    try:
        for case in rows:
            if case.case_id in completed:
                continue
            try:
                response = await adapter.evaluate(case)
                if response.flow_id != manifest.flow_id:
                    raise FactualQaExecutionError("adapter flow identity drifted")
            except (asyncio.TimeoutError, RuntimeError, ValueError) as error:
                response = EvaluationResponseV1(
                    case_id=case.case_id,
                    flow_id=manifest.flow_id,
                    action=EvaluationAction.OPERATIONAL_FAILURE,
                    answer=f"Operational failure: {type(error).__name__}",
                    operational_status="failed",
                    usage=EvaluationUsageV1(),
                    trace={"failure_type": type(error).__name__},
                )
            ledger.record(response)
        validate_completion = getattr(adapter, "validate_completion", None)
        if callable(validate_completion):
            validate_completion()
        ledger.mark_complete(expected_count=len(rows))
        finalize = getattr(adapter, "finalize", None)
        if callable(finalize):
            finalize()
        return ledger.snapshot()
    except BaseException:
        ledger.mark_interrupted()
        interrupt = getattr(adapter, "interrupt", None)
        if callable(interrupt):
            interrupt()
        raise
