#!/usr/bin/env python3
"""Run the finite OpenAI calibration, wording, and 500+100 checkpoint."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any

from dotenv import load_dotenv

from src.digital_twin.evaluation.provider_json import canonical_sha256
from src.digital_twin.repository_freeze import (
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-checkpoint-003"
BINDING_ID = "academic-factual-qa-open-10000-openai-binding-003"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_checkpoint_003.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_003.json"
)
GENERATED = ROOT / "reports/generated"
STATE_PATH = GENERATED / (
    "academic-factual-qa-open-10000-development-checkpoint-003-state.json"
)
CALIBRATION_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-openai-reviewer-calibration-001-result.json"
)
WORDING_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-wording-development-003-result.json"
)
PAIRED_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-003-paired-result.json"
)
PROVIDER_LEDGERS = (
    GENERATED / "academic-factual-qa-open-10000-openai-reviewer-calibration-001.sqlite3",
    GENERATED / "academic-factual-qa-open-10000-wording-development-003.sqlite3",
    GENERATED
    / "academic-factual-qa-open-10000-v1-development-003-candidate-provider.sqlite3",
    GENERATED
    / "academic-factual-qa-open-10000-v1-development-003-control-provider.sqlite3",
)
RUNTIME_PACKAGES = (
    GENERATED / "academic-factual-qa-open-10000-v1-development-003-cases.json",
    GENERATED / "academic-factual-qa-open-10000-v1-development-003-gold.json",
    GENERATED
    / "academic-factual-qa-open-10000-v1-development-control-003-cases.json",
    GENERATED
    / "academic-factual-qa-open-10000-v1-development-control-003-gold.json",
)
PRODUCT_ARTIFACTS: dict[str, tuple[Path, Path, Path]] = {
    "candidate": (
        GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-candidate-responses.sqlite3",
        PROVIDER_LEDGERS[2],
        GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-candidate-state.sqlite3",
    ),
    "control": (
        GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-control-responses.sqlite3",
        PROVIDER_LEDGERS[3],
        GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-control-state.sqlite3",
    ),
}
ALL_OUTPUTS = (
    STATE_PATH,
    *PROVIDER_LEDGERS,
    CALIBRATION_RESULT,
    WORDING_RESULT,
    *RUNTIME_PACKAGES,
    *(path for paths in PRODUCT_ARTIFACTS.values() for path in paths),
    GENERATED / "academic-factual-qa-open-10000-v1-development-003-candidate-result.json",
    PAIRED_RESULT,
)


class DevelopmentCheckpointError(RuntimeError):
    """Raised when the finite development checkpoint violates its contract."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DevelopmentCheckpointError(f"JSON root is not an object: {path.name}")
    return value


def _load_hashed(path: Path, *, key: str, identity: str) -> dict[str, Any]:
    value = _load(path)
    if value.get(key) != identity:
        raise DevelopmentCheckpointError(f"identity drifted: {path.name}")
    expected = canonical_sha256(
        {field: row for field, row in value.items() if field != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise DevelopmentCheckpointError(f"content hash drifted: {path.name}")
    return value


def _repo_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _run_module(module: str, *arguments: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-m", module, *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DevelopmentCheckpointError(
            f"stage command failed: {module} returncode={result.returncode}"
        )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise DevelopmentCheckpointError(
            f"stage command returned malformed status: {module}"
        ) from error
    if not isinstance(value, dict):
        raise DevelopmentCheckpointError(f"stage status is not an object: {module}")
    return value


def _write_state(state: dict[str, Any], *, exclusive: bool = False) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and STATE_PATH.exists():
        raise DevelopmentCheckpointError("exclusive combined state path is used")
    temporary = STATE_PATH.with_name(f"{STATE_PATH.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, STATE_PATH)


def _initial_state(instrument: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "binding_id": BINDING_ID,
        "binding_sha256": binding["content_sha256"],
        "code_revision": _repo_revision(),
        "status": "running",
        "current_stage": "reviewer-calibration",
        "completed_stages": [],
        "terminal_result": None,
    }


def _resume_state(instrument: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    if not STATE_PATH.is_file():
        raise DevelopmentCheckpointError("resume combined state is missing")
    state = _load(STATE_PATH)
    expected = {
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "binding_id": BINDING_ID,
        "binding_sha256": binding["content_sha256"],
        "code_revision": _repo_revision(),
    }
    if any(state.get(key) != value for key, value in expected.items()):
        raise DevelopmentCheckpointError("combined resume binding drifted")
    if state.get("status") not in {"running", "interrupted"}:
        raise DevelopmentCheckpointError("combined resume state is terminal")
    state["status"] = "running"
    return state


def _complete_stage(state: dict[str, Any], stage: str, next_stage: str) -> None:
    if stage not in state["completed_stages"]:
        state["completed_stages"].append(stage)
    state["current_stage"] = next_stage
    _write_state(state)


def _terminal(state: dict[str, Any], status: str, result: dict[str, Any]) -> dict[str, Any]:
    state["status"] = status
    state["terminal_result"] = result
    state["current_stage"] = None
    _write_state(state)
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "completed_stages": state["completed_stages"],
        "terminal_result": result,
    }


def _sqlite_complete(path: Path, *, expected_count: int) -> bool:
    if not path.is_file():
        return False
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    finally:
        connection.close()
    return metadata.get("status") == "completed" and int(
        metadata.get("response_count", "-1")
    ) == expected_count


def _provider_totals() -> tuple[int, float]:
    calls = 0
    cost = 0.0
    for path in PROVIDER_LEDGERS:
        if not path.is_file():
            continue
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM calls"
            ).fetchone()
        finally:
            connection.close()
        calls += int(row[0])
        cost += float(row[1])
    return calls, cost


def validate(*, require_unauthorized: bool = True) -> dict[str, Any]:
    instrument = _load_hashed(
        INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID
    )
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    stages = instrument["combined_checkpoint"]["stage_order"]
    if stages != [
        "reviewer-calibration",
        "question-wording",
        "candidate-500",
        "control-100",
        "deterministic-score-and-compare",
    ]:
        raise DevelopmentCheckpointError("combined stage order drifted")
    if instrument["combined_checkpoint"]["maximum_calls"] != 660:
        raise DevelopmentCheckpointError("combined call ceiling drifted")
    if instrument["combined_checkpoint"]["maximum_cost_usd"] != 18.0:
        raise DevelopmentCheckpointError("combined cost ceiling drifted")
    calibration = _run_module(
        "scripts.run_academic_factual_qa_openai_reviewer_calibration",
        "--validate" if require_unauthorized else "--validate-live",
    )
    wording = _run_module(
        "scripts.run_academic_factual_qa_open_wording_v3",
        "--validate" if require_unauthorized else "--validate-live",
    )
    packages = _run_module(
        "scripts.prepare_academic_factual_qa_open_development_003", "--validate"
    )
    product = _run_module(
        "scripts.run_academic_factual_qa_open_product_003", "--validate"
    )
    scoring = _run_module(
        "scripts.score_academic_factual_qa_open_development_003", "--validate"
    )
    return {
        "instrument_id": INSTRUMENT_ID,
        "binding_id": BINDING_ID,
        "status": "passed-build-only",
        "stage_statuses": {
            "calibration": calibration["status"],
            "wording": wording["status"],
            "packages": packages["status"],
            "product": product["status"],
            "scoring": scoring["status"],
        },
        "maximum_calls": instrument["combined_checkpoint"]["maximum_calls"],
        "maximum_cost_usd": instrument["combined_checkpoint"]["maximum_cost_usd"],
        "provider_calls": 0,
        "final_execution_authorized": False,
        "binding_hash": binding["content_sha256"],
    }


def simulate(*, scenario: str) -> dict[str, Any]:
    calibration_status = (
        "completed-refine" if scenario == "calibration-failure" else "completed-go-deeper"
    )
    completed = ["reviewer-calibration"]
    if calibration_status != "completed-go-deeper":
        return {
            "instrument_id": INSTRUMENT_ID,
            "status": calibration_status,
            "completed_stages": completed,
            "wording_executed": False,
            "product_executed": False,
            "provider_calls": 0,
        }
    wording_status = (
        "completed-refine" if scenario == "wording-failure" else "completed-go-deeper"
    )
    completed.append("question-wording")
    if wording_status != "completed-go-deeper":
        return {
            "instrument_id": INSTRUMENT_ID,
            "status": wording_status,
            "completed_stages": completed,
            "product_executed": False,
            "provider_calls": 0,
        }
    completed.extend(["candidate-500", "control-100", "deterministic-score-and-compare"])
    status = "completed-refine" if scenario == "product-failure" else "completed-keep"
    if scenario not in {"pass", "calibration-failure", "wording-failure", "product-failure"}:
        raise ValueError(f"unknown simulation scenario: {scenario}")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "completed_stages": completed,
        "provider_calls": 0,
        "network_accessed": False,
        "final_execution_authorized": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _load_hashed(
        INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID
    )
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    blockers: list[str] = []
    try:
        validate(require_unauthorized=False)
    except Exception as error:  # noqa: BLE001 - aggregate fail-closed blockers
        blockers.append(f"build-validation-failed:{type(error).__name__}")
    if _repo_dirty():
        blockers.append("repository-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    operations = set(BOUNDED_PILOT_AUTHORIZATIONS.get(INSTRUMENT_ID, ()))
    for operation in ("external_model_evaluation", "method_evaluation_execution"):
        if operation not in operations:
            blockers.append(f"freeze-{operation}-authorization-missing")
    required = (
        "provider_execution_authorized",
        "paid_execution_authorized",
        "calibration_execution_authorized",
        "wording_development_execution_authorized",
        "product_development_execution_authorized",
        "semantic_review_execution_authorized",
    )
    for key in required:
        if not instrument["authorization"][key]:
            blockers.append(f"instrument-{key.replace('_', '-')}-false")
        if not binding["authorization"][key]:
            blockers.append(f"binding-{key.replace('_', '-')}-false")
    for key in (
        "provider_execution_authorized",
        "paid_execution_authorized",
        "development_execution_authorized",
    ):
        if not instrument["execution"][key]:
            blockers.append(f"execution-{key.replace('_', '-')}-false")
    if instrument["authorization"]["final_execution_authorized"] or instrument[
        "execution"
    ]["final_execution_authorized"]:
        blockers.append("final-execution-must-remain-unauthorized")
    verified_at = datetime.fromisoformat(binding["verified_at"])
    age = (
        datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)
    ).total_seconds() / 3600
    if age < 0 or age > binding["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if resume:
        if not STATE_PATH.is_file():
            blockers.append("resume-state-missing")
    else:
        used = sorted(path.name for path in set(ALL_OUTPUTS) if path.exists())
        if used:
            blockers.append("exclusive-output-path-used:" + ",".join(used))
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
        "credential_values_emitted": False,
        "maximum_calls": instrument["combined_checkpoint"]["maximum_calls"],
        "maximum_cost_usd": instrument["combined_checkpoint"]["maximum_cost_usd"],
        "final_execution_authorized": False,
    }


def _execute_stage(
    state: dict[str, Any],
    *,
    stage: str,
    module: str,
    execute_arguments: tuple[str, ...],
    result_path: Path | None = None,
) -> dict[str, Any]:
    try:
        _run_module(module, *execute_arguments)
        return _load(result_path) if result_path is not None else {"status": "completed"}
    except KeyboardInterrupt:
        state["status"] = "interrupted"
        _write_state(state)
        raise
    except Exception as error:  # noqa: BLE001 - preserve invalid stage evidence
        return _terminal(
            state,
            "invalid-execution",
            {"stage": stage, "failure_type": type(error).__name__},
        )


def execute(*, resume: bool = False) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise DevelopmentCheckpointError(
            "combined preflight is blocked: " + ", ".join(readiness["blockers"])
        )
    instrument = _load_hashed(
        INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID
    )
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    state = _resume_state(instrument, binding) if resume else _initial_state(instrument, binding)
    if not resume:
        _write_state(state, exclusive=True)

    if "reviewer-calibration" not in state["completed_stages"]:
        if not CALIBRATION_RESULT.exists():
            ledger_exists = PROVIDER_LEDGERS[0].exists()
            result = _execute_stage(
                state,
                stage="reviewer-calibration",
                module="scripts.run_academic_factual_qa_openai_reviewer_calibration",
                execute_arguments=("--execute", "--resume") if ledger_exists else ("--execute",),
            )
            if result.get("status") == "invalid-execution":
                return result
            result = _execute_stage(
                state,
                stage="reviewer-calibration",
                module="scripts.run_academic_factual_qa_openai_reviewer_calibration",
                execute_arguments=("--score",),
                result_path=CALIBRATION_RESULT,
            )
        else:
            result = _load(CALIBRATION_RESULT)
        _complete_stage(state, "reviewer-calibration", "question-wording")
        if result.get("status") != "completed-go-deeper":
            return _terminal(state, str(result.get("status")), result)

    if "question-wording" not in state["completed_stages"]:
        if not WORDING_RESULT.exists():
            ledger_exists = PROVIDER_LEDGERS[1].exists()
            result = _execute_stage(
                state,
                stage="question-wording",
                module="scripts.run_academic_factual_qa_open_wording_v3",
                execute_arguments=("--execute", "--resume") if ledger_exists else ("--execute",),
            )
            if result.get("status") == "invalid-execution":
                return result
            result = _execute_stage(
                state,
                stage="question-wording",
                module="scripts.run_academic_factual_qa_open_wording_v3",
                execute_arguments=("--score",),
                result_path=WORDING_RESULT,
            )
        else:
            result = _load(WORDING_RESULT)
        _complete_stage(state, "question-wording", "runtime-package-materialization")
        if result.get("status") != "completed-go-deeper":
            return _terminal(state, str(result.get("status")), result)

    if "runtime-package-materialization" not in state["completed_stages"]:
        if all(path.exists() for path in RUNTIME_PACKAGES):
            package_result = {"status": "runtime-packages-completed"}
        elif any(path.exists() for path in RUNTIME_PACKAGES):
            return _terminal(
                state,
                "invalid-execution",
                {"stage": "runtime-package-materialization", "failure_type": "PartialOutput"},
            )
        else:
            package_result = _execute_stage(
                state,
                stage="runtime-package-materialization",
                module="scripts.prepare_academic_factual_qa_open_development_003",
                execute_arguments=("--write",),
            )
        if package_result.get("status") == "invalid-execution":
            return package_result
        _complete_stage(state, "runtime-package-materialization", "candidate-500")

    for condition, stage, count, next_stage in (
        ("candidate", "candidate-500", 500, "control-100"),
        ("control", "control-100", 100, "deterministic-score-and-compare"),
    ):
        if stage in state["completed_stages"]:
            continue
        response_path, _, _ = PRODUCT_ARTIFACTS[condition]
        if not _sqlite_complete(response_path, expected_count=count):
            resume_product = any(path.exists() for path in PRODUCT_ARTIFACTS[condition])
            result = _execute_stage(
                state,
                stage=stage,
                module="scripts.run_academic_factual_qa_open_product_003",
                execute_arguments=(
                    "--execute",
                    "--condition",
                    condition,
                    *(('--resume',) if resume_product else ()),
                ),
            )
            if result.get("status") == "invalid-execution":
                return result
        if not _sqlite_complete(response_path, expected_count=count):
            return _terminal(
                state,
                "invalid-execution",
                {"stage": stage, "failure_type": "IncompleteResponseLedger"},
            )
        _complete_stage(state, stage, next_stage)

    if "deterministic-score-and-compare" not in state["completed_stages"]:
        if not PAIRED_RESULT.exists():
            result = _execute_stage(
                state,
                stage="deterministic-score-and-compare",
                module="scripts.score_academic_factual_qa_open_development_003",
                execute_arguments=("--score",),
                result_path=PAIRED_RESULT,
            )
        else:
            result = _load(PAIRED_RESULT)
        if result.get("status") == "invalid-execution":
            return result
        _complete_stage(state, "deterministic-score-and-compare", "accounting-check")

    calls, cost = _provider_totals()
    if calls > instrument["combined_checkpoint"]["maximum_calls"] or cost > instrument[
        "combined_checkpoint"
    ]["maximum_cost_usd"]:
        return _terminal(
            state,
            "invalid-execution",
            {"stage": "accounting-check", "provider_calls": calls, "cost_usd": cost},
        )
    result = _load(PAIRED_RESULT)
    result = {
        "status": result["status"],
        "decision": result["decision"],
        "failed_gates": result["failed_gates"],
        "provider_calls": calls,
        "reported_cost_usd": cost,
    }
    return _terminal(state, result["status"], result)


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument(
        "--simulate",
        choices=("pass", "calibration-failure", "wording-failure", "product-failure"),
    )
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.validate:
        result = validate()
    elif arguments.simulate:
        result = simulate(scenario=arguments.simulate)
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    else:
        result = execute(resume=arguments.resume)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
