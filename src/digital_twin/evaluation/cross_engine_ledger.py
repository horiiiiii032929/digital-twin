"""Atomic finite-state ledger for cross-engine product evaluation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Literal


CROSS_ENGINE_STAGES = (
    "development-500-plus-100",
    "autonomy-820",
    "sealed-confirmation-1000",
    "known-regression-10000-plus-1000",
    "supplementary-proxies",
    "local-release-qualification",
)

StageResult = Literal["passed", "quality-failed", "invalid-execution"]


class CrossEngineLedgerError(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class CrossEngineProgramLedgerV1:
    def __init__(
        self,
        path: Path,
        *,
        program_id: str,
        binding: dict[str, Any],
        maximum_cost_usd: float,
        resume: bool,
    ) -> None:
        if maximum_cost_usd <= 0:
            raise ValueError("cross-engine budget must be positive")
        if resume and not path.is_file():
            raise CrossEngineLedgerError("resume ledger is missing")
        if not resume and path.exists():
            raise CrossEngineLedgerError("exclusive cross-engine ledger exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not resume:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS stages(
                   stage_index INTEGER PRIMARY KEY,
                   stage_id TEXT NOT NULL UNIQUE,
                   status TEXT NOT NULL,
                   result_sha256 TEXT,
                   decision TEXT
               )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS cases(
                   sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                   stage_id TEXT NOT NULL,
                   engine_id TEXT NOT NULL,
                   condition_id TEXT NOT NULL,
                   case_id TEXT NOT NULL,
                   payload_sha256 TEXT NOT NULL,
                   score_sha256 TEXT NOT NULL,
                   cost_usd REAL NOT NULL,
                   UNIQUE(stage_id,engine_id,condition_id,case_id)
               )"""
        )
        expected = {
            "schema_version": "1",
            "program_id": program_id,
            "binding_sha256": canonical_sha256(binding),
            "maximum_cost_usd": f"{maximum_cost_usd:.8f}",
        }
        existing = dict(self.connection.execute("SELECT key,value FROM metadata"))
        if resume:
            if any(existing.get(key) != value for key, value in expected.items()):
                raise CrossEngineLedgerError("resume binding or budget drifted")
        else:
            with self.connection:
                for key, value in {**expected, "program_status": "running"}.items():
                    self.connection.execute(
                        "INSERT INTO metadata(key,value) VALUES (?,?)", (key, value)
                    )
                for index, stage in enumerate(CROSS_ENGINE_STAGES):
                    self.connection.execute(
                        "INSERT INTO stages(stage_index,stage_id,status) VALUES (?,?,?)",
                        (index, stage, "pending"),
                    )
        self.maximum_cost_usd = maximum_cost_usd

    def _metadata(self, key: str) -> str | None:
        row = self.connection.execute(
            "SELECT value FROM metadata WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else str(row[0])

    def _set_metadata(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO metadata(key,value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def begin_stage(self, stage_id: str) -> None:
        if self._metadata("program_status") != "running":
            raise CrossEngineLedgerError("terminal program cannot begin a stage")
        if stage_id not in CROSS_ENGINE_STAGES:
            raise CrossEngineLedgerError("unknown cross-engine stage")
        index = CROSS_ENGINE_STAGES.index(stage_id)
        statuses = dict(
            self.connection.execute("SELECT stage_id,status FROM stages")
        )
        if any(statuses[CROSS_ENGINE_STAGES[prior]] != "passed" for prior in range(index)):
            raise CrossEngineLedgerError("cross-engine stage order was bypassed")
        if statuses[stage_id] not in {"pending", "running"}:
            raise CrossEngineLedgerError("completed stage cannot restart")
        with self.connection:
            self.connection.execute(
                "UPDATE stages SET status = 'running' WHERE stage_id = ?", (stage_id,)
            )

    def record_case(
        self,
        *,
        stage_id: str,
        engine_id: str,
        condition_id: str,
        case_id: str,
        response: dict[str, Any],
        score: dict[str, Any],
        cost_usd: float,
    ) -> None:
        if cost_usd < 0:
            raise ValueError("case cost cannot be negative")
        status = self.connection.execute(
            "SELECT status FROM stages WHERE stage_id = ?", (stage_id,)
        ).fetchone()
        if status is None or status[0] != "running":
            raise CrossEngineLedgerError("case cannot be recorded outside running stage")
        projected = self.total_cost_usd() + cost_usd
        if projected > self.maximum_cost_usd:
            raise CrossEngineLedgerError("cross-engine emergency cost stop reached")
        with self.connection:
            self.connection.execute(
                """INSERT INTO cases(
                       stage_id,engine_id,condition_id,case_id,payload_sha256,
                       score_sha256,cost_usd
                   ) VALUES (?,?,?,?,?,?,?)""",
                (
                    stage_id,
                    engine_id,
                    condition_id,
                    case_id,
                    canonical_sha256(response),
                    canonical_sha256(score),
                    cost_usd,
                ),
            )

    def has_case(
        self,
        *,
        stage_id: str,
        engine_id: str,
        condition_id: str,
        case_id: str,
    ) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM cases WHERE stage_id=? AND engine_id=? "
            "AND condition_id=? AND case_id=?",
            (stage_id, engine_id, condition_id, case_id),
        ).fetchone()
        return row is not None

    def complete_stage(
        self,
        stage_id: str,
        *,
        result: dict[str, Any],
        decision: StageResult,
    ) -> None:
        status = self.connection.execute(
            "SELECT status FROM stages WHERE stage_id = ?", (stage_id,)
        ).fetchone()
        if status is None or status[0] != "running":
            raise CrossEngineLedgerError("only a running stage can complete")
        stage_status = "passed" if decision == "passed" else decision
        with self.connection:
            self.connection.execute(
                "UPDATE stages SET status=?,result_sha256=?,decision=? WHERE stage_id=?",
                (stage_status, canonical_sha256(result), decision, stage_id),
            )
        if decision != "passed":
            self._set_metadata("program_status", decision)

    def finish(self) -> None:
        statuses = [
            row[0]
            for row in self.connection.execute(
                "SELECT status FROM stages ORDER BY stage_index"
            )
        ]
        if statuses != ["passed"] * len(CROSS_ENGINE_STAGES):
            raise CrossEngineLedgerError("program cannot finish before every stage passes")
        self._set_metadata("program_status", "completed-keep")

    def total_cost_usd(self) -> float:
        row = self.connection.execute("SELECT COALESCE(SUM(cost_usd),0) FROM cases").fetchone()
        return float(row[0])

    def snapshot(self) -> dict[str, Any]:
        return {
            "program_status": self._metadata("program_status"),
            "stages": [
                {"stage_id": row[0], "status": row[1], "decision": row[2]}
                for row in self.connection.execute(
                    "SELECT stage_id,status,decision FROM stages ORDER BY stage_index"
                )
            ],
            "case_count": int(
                self.connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
            ),
            "cost_usd": self.total_cost_usd(),
            "maximum_cost_usd": self.maximum_cost_usd,
        }

    def close(self) -> None:
        self.connection.close()
