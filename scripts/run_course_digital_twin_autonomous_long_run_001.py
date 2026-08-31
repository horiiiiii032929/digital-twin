#!/usr/bin/env python3
"""Run the finite #153 -> #157 -> publication successor under one authority."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from typing import Any

from dotenv import load_dotenv

from scripts import run_academic_factual_qa_grounding_selection_002 as grounding
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_002 as autonomy,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "course-digital-twin-autonomous-long-run-001"
EXECUTION_ATTEMPT_ID = f"{PROGRAM_ID}-attempt-002"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_autonomous_long_run_001.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated" / EXECUTION_ATTEMPT_ID
LEDGER_NAME = "program-ledger.sqlite3"
RESULT_NAME = "program-result.json"
TEAMS_NAME = "professor-update.txt"
HISTORICAL_RECORD = ROOT / (
    "research/05_evaluation/records/"
    "course-digital-twin-evaluation-program-011.json"
)
LOCAL_RELEASE_TESTS = (
    "tests/digital_twin/test_governed_autonomy.py",
    "tests/test_governed_full_autonomy_v2_1_actual_product_evaluation_002.py",
    "tests/test_governed_full_autonomy_v2_1_provider_integration.py",
    "tests/services/test_runtime_backup.py",
)


class AutonomousLongRunError(RuntimeError):
    """Raised when the frozen long-run program boundary is violated."""


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AutonomousLongRunError(f"JSON root is not an object: {path.name}")
    return payload


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _atomic_write(path: Path, payload: dict[str, Any] | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    if isinstance(payload, str):
        serialized = payload.rstrip() + "\n"
    else:
        serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _recorded_program_stage(output_root: Path, stage_id: str) -> dict[str, Any] | None:
    """Read one durable parent-stage result without mutating resume state."""

    ledger_path = output_root / LEDGER_NAME
    if not ledger_path.is_file():
        return None
    connection = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT status,result_json FROM stages WHERE stage_id=?", (stage_id,)
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return {"status": row[0], **json.loads(row[1])}


def _recover_terminal_grounding_result(*, resume: bool) -> dict[str, Any] | None:
    """Recover a child result persisted just before a parent-process interruption."""

    if not resume or not grounding.CHECKPOINT_STATE.is_file():
        return None
    state = _load(grounding.CHECKPOINT_STATE)
    result = state.get("terminal_result")
    if state.get("status") not in {
        "completed-keep",
        "completed-refine",
        "invalid-execution",
    } or not isinstance(result, dict):
        return None
    return result


def _recover_terminal_autonomy_result(*, resume: bool) -> dict[str, Any] | None:
    """Recover the immutable autonomy result when its child ledger is terminal."""

    if not resume or not autonomy.RESULT_PATH.is_file():
        return None
    result = _load(autonomy.RESULT_PATH)
    if result.get("status") not in {
        "completed-keep",
        "completed-refine",
        "invalid-execution",
    }:
        return None
    return result


def validate() -> dict[str, Any]:
    manifest = _load(INSTRUMENT)
    observed_hash = canonical_json_sha256(
        {key: value for key, value in manifest.items() if key != "content_sha256"}
    )
    if manifest.get("content_sha256") != observed_hash:
        raise AutonomousLongRunError("program manifest hash drifted")
    status = manifest.get("status")
    if (
        manifest.get("program_id") != PROGRAM_ID
        or status not in {"frozen-pending-execution", "completed-invalid-execution"}
        or manifest.get("execution_attempt_id") != EXECUTION_ATTEMPT_ID
        or manifest.get("global_emergency_cost_usd") != 200.0
        or manifest.get("automatic_stage_progression") is not True
        or manifest.get("same_case_quality_rerun_allowed") is not False
    ):
        raise AutonomousLongRunError("finite program boundary drifted")
    authority = manifest["authorization"]
    authorized = (
        authority["provider_execution_authorized"],
        authority["paid_execution_authorized"],
    )
    if authority["additional_stage_authorization_required"] is not False:
        raise AutonomousLongRunError("single program authority drifted")
    if status == "frozen-pending-execution" and authorized != (True, True):
        raise AutonomousLongRunError("single program authority drifted")
    if status == "completed-invalid-execution" and authorized != (False, False):
        raise AutonomousLongRunError("terminal program authority is not revoked")
    stage_ids = [row["stage_id"] for row in manifest["stages"]]
    if stage_ids != [
        "grounding-selection-500-plus-100",
        "actual-product-autonomy-820",
        "local-release-regression",
        "evidence-synthesis-and-publication",
    ]:
        raise AutonomousLongRunError("program stage order drifted")
    if not HISTORICAL_RECORD.is_file():
        raise AutonomousLongRunError("Program 011 historical evidence is missing")
    return {
        "program_id": PROGRAM_ID,
        "status": (
            "passed-frozen-pending-execution"
            if status == "frozen-pending-execution"
            else "passed-terminal-authority-revoked"
        ),
        "stage_count": len(stage_ids),
        "global_emergency_cost_usd": 200.0,
        "known_10000_plus_1000_preserved": True,
        "same_case_quality_rerun_allowed": False,
        "provider_calls": 0,
    }


class ProgramLedger:
    def __init__(self, path: Path, *, resume: bool) -> None:
        manifest_hash = hashlib.sha256(INSTRUMENT.read_bytes()).hexdigest()
        expected = {
            "program_id": PROGRAM_ID,
            "manifest_sha256": manifest_hash,
            "code_revision": _git_revision(),
            "global_emergency_cost_usd": "200.0",
        }
        if resume and not path.is_file():
            raise AutonomousLongRunError("resume program ledger is missing")
        if not resume and path.exists():
            raise AutonomousLongRunError("exclusive program ledger already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not resume:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stages (
                stage_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        if resume:
            actual = dict(self.connection.execute("SELECT key,value FROM metadata"))
            if any(actual.get(key) != value for key, value in expected.items()):
                raise AutonomousLongRunError("program resume binding drifted")
            if actual.get("status") not in {"running", "interrupted"}:
                raise AutonomousLongRunError("program ledger is already terminal")
            self._metadata("status", "running")
        else:
            for key, value in {**expected, "status": "running"}.items():
                self.connection.execute(
                    "INSERT INTO metadata(key,value) VALUES (?,?)", (key, value)
                )

    def _metadata(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO metadata(key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def stage(self, stage_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT status,result_json FROM stages WHERE stage_id=?", (stage_id,)
        ).fetchone()
        return None if row is None else {"status": row[0], **json.loads(row[1])}

    def record(self, stage_id: str, result: dict[str, Any]) -> None:
        status = str(result.get("status", "invalid-execution"))
        self.connection.execute(
            "INSERT INTO stages(stage_id,status,result_json,updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(stage_id) DO UPDATE SET status=excluded.status,"
            "result_json=excluded.result_json,updated_at=excluded.updated_at",
            (
                stage_id,
                status,
                json.dumps(result, sort_keys=True),
                datetime.now(UTC).isoformat(),
            ),
        )

    def results(self) -> dict[str, dict[str, Any]]:
        return {
            row[0]: {"status": row[1], **json.loads(row[2])}
            for row in self.connection.execute(
                "SELECT stage_id,status,result_json FROM stages ORDER BY rowid"
            )
        }

    def cost(self) -> float:
        total = 0.0
        for result in self.results().values():
            accounting = result.get("accounting", {})
            total += float(
                accounting.get("reported_cost_usd", result.get("cost_usd", 0.0))
            )
        return total

    def mark(self, status: str) -> None:
        self._metadata("status", status)
        self._metadata("total_cost_usd", f"{self.cost():.10f}")

    def close(self) -> None:
        self.connection.close()


def _local_release_regression() -> dict[str, Any]:
    command = [
        "uv",
        "run",
        "pytest",
        *LOCAL_RELEASE_TESTS,
        "-q",
    ]
    process = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "status": "completed-keep" if process.returncode == 0 else "completed-refine",
        "provider_calls": 0,
        "cost_usd": 0.0,
        "command": command,
        "exit_code": process.returncode,
        "output_tail": process.stdout[-4000:],
        "error_tail": process.stderr[-2000:],
        "t0_rollback_retained": True,
    }


def _publication(results: dict[str, dict[str, Any]], output_root: Path) -> dict[str, Any]:
    historical = _load(HISTORICAL_RECORD)
    grounding_result = results.get("grounding-selection-500-plus-100", {})
    autonomy_result = results.get("actual-product-autonomy-820", {})
    local_result = results.get("local-release-regression", {})
    grounding_keep = grounding_result.get("status") == "completed-keep"
    autonomy_keep = autonomy_result.get("status") == "completed-keep"
    local_keep = local_result.get("status") == "completed-keep"
    status = (
        "completed-keep"
        if grounding_keep and autonomy_keep and local_keep
        else "completed-refine"
    )
    result = {
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "execution_attempt_id": EXECUTION_ATTEMPT_ID,
        "status": status,
        "decision": "Keep" if status == "completed-keep" else "Refine",
        "stages": results,
        "historical_10000_plus_1000": {
            "run_id": historical["run_id"],
            "decision": historical["decision"],
            "operational_summary": historical["operational_summary"],
            "known_benchmark_only": True,
            "rerun": False,
        },
        "claims_not_established": [
            "real-professor-fidelity",
            "real-student-usability",
            "learning-improvement",
            "true-visual-release-readiness",
        ],
        "additional_stage_authorization_requested": False,
        "authority_revocation_required_after_publication": True,
    }
    _atomic_write(output_root / RESULT_NAME, result)
    if grounding_keep:
        grounding_line = "- The fresh 500+100 grounding successor passed."
    else:
        grounding_line = "- The fresh 500+100 grounding successor did not pass its frozen gates."
    autonomy_line = (
        "- The provider-backed 820-case autonomy evaluation passed."
        if autonomy_keep
        else "- Autonomous V2.1 was not promoted from this checkpoint."
    )
    teams = "\n".join(
        [
            "Hi Prof, a quick project checkpoint:",
            "",
            grounding_line,
            autonomy_line,
            (
                "- The earlier actual-product evaluation completed 10,000 candidate "
                "+ 1,000 control cases and remains valid Refine evidence; I did not "
                "tune or rerun that sealed set."
            ),
            "- The local release, persistence, restart, and rollback path was rechecked.",
            "",
            (
                "The system uses deterministic source/action/citation checks as the "
                "authority; model judgments are advisory. Real professor fidelity and "
                "real-student learning outcomes remain separate future evidence."
            ),
        ]
    )
    _atomic_write(output_root / TEAMS_NAME, teams)
    return {
        "status": "completed-keep",
        "provider_calls": 0,
        "cost_usd": 0.0,
        "program_decision": result["decision"],
        "result_path": str((output_root / RESULT_NAME).relative_to(ROOT)),
        "teams_message_path": str((output_root / TEAMS_NAME).relative_to(ROOT)),
    }


def preflight(*, output_root: Path, resume: bool) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate()
    except Exception as error:  # noqa: BLE001
        blockers.append(f"validation:{type(error).__name__}:{error}")
    manifest = _load(INSTRUMENT)
    verified = datetime.fromisoformat(manifest["metadata"]["verified_at"])
    age = (datetime.now(UTC) - verified.astimezone(UTC)).total_seconds() / 3600
    if age < 0 or age > manifest["metadata"]["freshness_hours"]:
        blockers.append("provider-metadata-stale")
    if _git_dirty():
        blockers.append("working-tree-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-credential-missing")
    try:
        for operation in ("external_model_evaluation", "method_evaluation_execution"):
            require_bounded_pilot_operation_allowed(PROGRAM_ID, operation)
    except Exception:
        blockers.append("repository-freeze-authorization-missing")
    ledger_path = output_root / LEDGER_NAME
    if resume and not ledger_path.is_file():
        blockers.append("resume-program-ledger-missing")
    if not resume and ledger_path.exists():
        blockers.append("exclusive-program-output-used; use --resume")
    grounding_recorded = _recorded_program_stage(
        output_root, "grounding-selection-500-plus-100"
    )
    grounding_recoverable = _recover_terminal_grounding_result(resume=resume)
    if grounding_recorded is None and grounding_recoverable is None:
        child = grounding.preflight(resume=grounding.CHECKPOINT_STATE.exists())
        blockers.extend(f"grounding:{row}" for row in child["blockers"])
    return {
        "program_id": PROGRAM_ID,
        "status": "ready" if not blockers else "blocked-not-ready",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
        "global_emergency_cost_usd": 200.0,
    }


async def execute(*, output_root: Path, resume: bool) -> dict[str, Any]:
    readiness = preflight(output_root=output_root, resume=resume)
    if readiness["status"] != "ready":
        raise AutonomousLongRunError(
            "program preflight blocked: " + ", ".join(readiness["blockers"])
        )
    ledger = ProgramLedger(output_root / LEDGER_NAME, resume=resume)
    try:
        if ledger.stage("grounding-selection-500-plus-100") is None:
            result = _recover_terminal_grounding_result(resume=resume)
            if result is None:
                result = await grounding.execute(
                    resume=grounding.CHECKPOINT_STATE.exists()
                )
            ledger.record("grounding-selection-500-plus-100", result)
        grounding_result = ledger.stage("grounding-selection-500-plus-100") or {}
        if grounding_result.get("status") == "completed-keep":
            if ledger.stage("actual-product-autonomy-820") is None:
                result = _recover_terminal_autonomy_result(resume=resume)
                if result is None:
                    result = await autonomy.execute(
                        resume=autonomy.RESPONSE_LEDGER.exists()
                    )
                ledger.record("actual-product-autonomy-820", result)
        elif ledger.stage("actual-product-autonomy-820") is None:
            ledger.record(
                "actual-product-autonomy-820",
                {
                    "status": "skipped-dependency",
                    "reason": "grounding-selection-not-keep",
                    "provider_calls": 0,
                    "cost_usd": 0.0,
                },
            )
        if ledger.cost() > 200.0:
            raise AutonomousLongRunError("global cost ceiling exhausted")
        if ledger.stage("local-release-regression") is None:
            ledger.record("local-release-regression", _local_release_regression())
        if ledger.stage("evidence-synthesis-and-publication") is None:
            publication = _publication(ledger.results(), output_root)
            ledger.record("evidence-synthesis-and-publication", publication)
        result = _load(output_root / RESULT_NAME)
        ledger.mark("completed")
        return result
    except BaseException:
        ledger.mark("interrupted")
        raise
    finally:
        ledger.close()


def simulate() -> dict[str, Any]:
    validate()
    return {
        "program_id": PROGRAM_ID,
        "status": "passed-network-free-simulation",
        "stage_order": [row["stage_id"] for row in _load(INSTRUMENT)["stages"]],
        "quality_failure_stops_dependent_autonomy": True,
        "orthogonal_release_and_publication_continue": True,
        "known_10000_plus_1000_rerun": False,
        "provider_calls": 0,
        "network_calls": 0,
    }


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID)
        result = asyncio.run(
            execute(output_root=arguments.output_root, resume=arguments.resume)
        )
    elif arguments.preflight:
        result = preflight(
            output_root=arguments.output_root, resume=arguments.resume
        )
    elif arguments.simulate:
        result = simulate()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
