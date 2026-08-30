#!/usr/bin/env python3
"""Run one finite actual-product 500+100 checkpoint over atomic M2 retrieval."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from typing import Any, Iterator

from dotenv import load_dotenv

from scripts import academic_factual_qa_open_10000_t0_adapter as product_adapter
from scripts import build_academic_factual_qa_atomic_m2_product_checkpoint as builder
from scripts import run_academic_factual_qa_open_10000 as product
from scripts import score_academic_factual_qa_open_10000 as scorer
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = builder.PROGRAM_ID
INSTRUMENT_ID = builder.INSTRUMENT_ID
ADAPTER_FACTORY = (
    "scripts.academic_factual_qa_atomic_m2_t0_adapter:build_atomic_m2_t0_adapter"
)
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
CANDIDATE_RESPONSES = OUTPUT_ROOT / "candidate-responses.sqlite3"
CANDIDATE_PROVIDER = OUTPUT_ROOT / "candidate-provider.sqlite3"
CANDIDATE_STATE = OUTPUT_ROOT / "candidate-product-state.sqlite3"
CONTROL_RESPONSES = OUTPUT_ROOT / "control-responses.sqlite3"
CONTROL_PROVIDER = OUTPUT_ROOT / "control-provider.sqlite3"
CONTROL_STATE = OUTPUT_ROOT / "control-product-state.sqlite3"
CANDIDATE_RESULT = OUTPUT_ROOT / "candidate-result.json"
CONTROL_RESULT = OUTPUT_ROOT / "control-result.json"
PAIRED_RESULT = OUTPUT_ROOT / "paired-result.json"
CHECKPOINT_STATE = OUTPUT_ROOT / "checkpoint-state.json"
ALL_OUTPUTS = (
    CANDIDATE_RESPONSES,
    CANDIDATE_PROVIDER,
    CANDIDATE_STATE,
    CONTROL_RESPONSES,
    CONTROL_PROVIDER,
    CONTROL_STATE,
    CANDIDATE_RESULT,
    CONTROL_RESULT,
    PAIRED_RESULT,
    CHECKPOINT_STATE,
)


class AtomicProductCheckpointError(RuntimeError):
    """Raised when the finite product checkpoint violates its frozen contract."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AtomicProductCheckpointError(f"JSON root is not an object: {path.name}")
    return value


def _load_hashed(path: Path) -> dict[str, Any]:
    value = _load(path)
    observed = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise AtomicProductCheckpointError(f"content hash drifted: {path.name}")
    return value


def _revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _atomic_write(path: Path, value: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and path.exists():
        raise AtomicProductCheckpointError(f"exclusive output is used: {path.name}")
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _ledger_complete(path: Path, expected: int) -> bool:
    if not path.is_file():
        return False
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
    finally:
        connection.close()
    return (
        metadata.get("status") == "completed"
        and metadata.get("response_count") == str(expected)
    )


def _provider_totals() -> dict[str, Any]:
    totals = {
        "provider_calls": 0,
        "provider_attempts": 0,
        "failed_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reported_cost_usd": 0.0,
        "maximum_latency_ms": 0.0,
    }
    for path in (CANDIDATE_PROVIDER, CONTROL_PROVIDER):
        if not path.is_file():
            continue
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT COUNT(*),COALESCE(SUM(attempt_count),0),"
                "SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END),"
                "COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0),"
                "COALESCE(SUM(cost_usd),0),COALESCE(MAX(latency_ms),0) FROM calls"
            ).fetchone()
        finally:
            connection.close()
        totals["provider_calls"] += int(row[0])
        totals["provider_attempts"] += int(row[1])
        totals["failed_calls"] += int(row[2])
        totals["input_tokens"] += int(row[3])
        totals["output_tokens"] += int(row[4])
        totals["reported_cost_usd"] += float(row[5])
        totals["maximum_latency_ms"] = max(
            float(totals["maximum_latency_ms"]), float(row[6])
        )
    return totals


@contextmanager
def _configured_modules() -> Iterator[None]:
    product_values = {
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "INSTRUMENT_PATH": builder.INSTRUMENT,
        "PROVIDER_BINDING_PATH": builder.BINDING,
        "ACTIVE_GENERATOR": "openai-gpt-5.4-mini-live-extractive-boundary",
        "ACTIVE_GENERATOR_MODEL": "gpt-5.4-mini-2026-03-17",
    }
    scorer_values = {
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "INSTRUMENT_PATH": builder.INSTRUMENT,
    }
    old_product = {key: getattr(product, key) for key in product_values}
    old_scorer = {key: getattr(scorer, key) for key in scorer_values}
    old_adapter_binding = product_adapter.OPENAI_BINDING_PATH
    try:
        for key, value in product_values.items():
            setattr(product, key, value)
        for key, value in scorer_values.items():
            setattr(scorer, key, value)
        product_adapter.OPENAI_BINDING_PATH = builder.BINDING
        yield
    finally:
        for key, value in old_product.items():
            setattr(product, key, value)
        for key, value in old_scorer.items():
            setattr(scorer, key, value)
        product_adapter.OPENAI_BINDING_PATH = old_adapter_binding


def validate() -> dict[str, Any]:
    builder.check()
    instrument = _load_hashed(builder.INSTRUMENT)
    binding = _load_hashed(builder.BINDING)
    runtime = _load_hashed(builder.RETRIEVAL_RUNTIME)
    if (
        instrument.get("program_id") != PROGRAM_ID
        or instrument.get("status") != "frozen-authorized-by-program"
        or instrument["execution"]["maximum_product_calls"] != 600
        or instrument["execution"]["maximum_transport_retries"] != 0
        or instrument["execution"]["maximum_cost_usd"] != 7.0
        or instrument["execution"]["final_execution_authorized"]
    ):
        raise AtomicProductCheckpointError("instrument execution boundary drifted")
    provider = binding["providers"]["high-volume-generator"]
    if (
        provider["provider"] != "openai"
        or provider["provider_model"] != "gpt-5.4-mini-2026-03-17"
        or provider["request_store"] is not False
        or provider["maximum_transport_retries"] != 0
    ):
        raise AtomicProductCheckpointError("direct OpenAI binding drifted")
    if runtime.get("hidden_gold_path_present") is not False:
        raise AtomicProductCheckpointError("retrieval runtime exposes hidden gold")
    source_code = (ROOT / "scripts/academic_factual_qa_atomic_m2_t0_adapter.py").read_text(
        encoding="utf-8"
    )
    forbidden = ("UPSTREAM_GOLD", "CONTROL_GOLD", "candidate_gold_path", "scorer")
    if any(token in source_code for token in forbidden):
        raise AtomicProductCheckpointError("response adapter exposes a gold code path")
    return {
        "instrument_id": INSTRUMENT_ID,
        "program_id": PROGRAM_ID,
        "status": "passed",
        "candidate_case_count": 500,
        "control_case_count": 100,
        "hidden_gold_available_to_response_process": False,
        "provider_calls": 0,
        "final_10000_opened": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate()
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
    except Exception as error:  # noqa: BLE001 - return all no-call blockers
        blockers.append(f"validation:{type(error).__name__}:{error}")
    if _dirty():
        blockers.append("working-tree-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-credential-missing")
    try:
        verified_at = datetime.fromisoformat(_load_hashed(builder.BINDING)["verified_at"])
        age = (datetime.now(UTC) - verified_at.astimezone(UTC)).total_seconds() / 3600
        if age < 0 or age > 24:
            blockers.append("provider-metadata-stale")
    except Exception as error:  # noqa: BLE001
        blockers.append(f"provider-metadata-invalid:{type(error).__name__}")
    if resume:
        if not CHECKPOINT_STATE.is_file():
            blockers.append("resume-checkpoint-missing")
    else:
        used = [path.name for path in ALL_OUTPUTS if path.exists()]
        if used:
            blockers.append("exclusive-output-used:" + ",".join(sorted(used)))
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "provider_calls": 0,
        "maximum_product_calls": 600,
        "maximum_cost_usd": 7.0,
        "reference_answers_loaded": False,
    }


def simulate(*, scenario: str) -> dict[str, Any]:
    if scenario not in {"pass", "product-failure", "provider-failure", "resume"}:
        raise AtomicProductCheckpointError("unknown simulation scenario")
    status = {
        "pass": "completed-keep",
        "product-failure": "completed-refine",
        "provider-failure": "invalid-execution",
        "resume": "completed-keep",
    }[scenario]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "scenario": scenario,
        "stage_order": [
            "candidate-500",
            "control-100",
            "hidden-gold-score",
            "paired-decision",
        ],
        "gold_opened_before_responses": False,
        "provider_calls": 0,
        "network_calls": 0,
    }


async def _execute_condition(condition: str, *, resume: bool) -> None:
    if condition == "candidate":
        paths = (
            builder.CASES,
            builder.CANDIDATE_MANIFEST,
            CANDIDATE_RESPONSES,
            CANDIDATE_PROVIDER,
            CANDIDATE_STATE,
        )
    else:
        paths = (
            builder.CONTROL_CASES,
            builder.CONTROL_MANIFEST,
            CONTROL_RESPONSES,
            CONTROL_PROVIDER,
            CONTROL_STATE,
        )
    cases, manifest, responses, provider_ledger, state = paths
    with _configured_modules():
        await product.execute(
            cases_path=cases,
            manifest_path=manifest,
            output=responses,
            adapter_factory=ADAPTER_FACTORY,
            provider_ledger=provider_ledger,
            state_path=state,
            resume=resume,
        )


def _score() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not _ledger_complete(CANDIDATE_RESPONSES, 500) or not _ledger_complete(
        CONTROL_RESPONSES, 100
    ):
        raise AtomicProductCheckpointError("hidden gold cannot open before both ledgers")
    with _configured_modules():
        candidate = scorer.score_packages(
            cases_path=builder.CASES,
            gold_path=builder.GOLD,
            responses_path=CANDIDATE_RESPONSES,
        )
        control = scorer.score_packages(
            cases_path=builder.CONTROL_CASES,
            gold_path=builder.CONTROL_GOLD,
            responses_path=CONTROL_RESPONSES,
        )
        gates = _load_hashed(builder.INSTRUMENT)["hard_gates"]
        paired = scorer.paired_comparison(
            candidate,
            control,
            lower_delta_gate=gates["paired_supported_retention_delta_lower_95_min"],
            boundary_not_worse=gates["paired_boundary_safety_not_worse"],
        )
    for path, value in (
        (CANDIDATE_RESULT, candidate),
        (CONTROL_RESULT, control),
        (PAIRED_RESULT, paired),
    ):
        if not path.exists():
            _atomic_write(path, value, exclusive=True)
    return candidate, control, paired


async def execute(*, resume: bool = False) -> dict[str, Any]:
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise AtomicProductCheckpointError(
            "checkpoint preflight blocked: " + ", ".join(readiness["blockers"])
        )
    state = (
        _load(CHECKPOINT_STATE)
        if resume
        else {
            "schema_version": 1,
            "program_id": PROGRAM_ID,
            "instrument_id": INSTRUMENT_ID,
            "instrument_sha256": _load_hashed(builder.INSTRUMENT)["content_sha256"],
            "code_revision": _revision(),
            "status": "running",
            "completed_stages": [],
            "current_stage": "candidate-500",
        }
    )
    if resume and (
        state.get("instrument_sha256")
        != _load_hashed(builder.INSTRUMENT)["content_sha256"]
        or state.get("code_revision") != _revision()
        or state.get("status") not in {"running", "interrupted"}
    ):
        raise AtomicProductCheckpointError("checkpoint resume binding drifted")
    if not resume:
        _atomic_write(CHECKPOINT_STATE, state, exclusive=True)
    try:
        for condition, stage, expected in (
            ("candidate", "candidate-500", 500),
            ("control", "control-100", 100),
        ):
            response_path = (
                CANDIDATE_RESPONSES if condition == "candidate" else CONTROL_RESPONSES
            )
            if stage not in state["completed_stages"]:
                paths = (
                    (CANDIDATE_PROVIDER, CANDIDATE_STATE)
                    if condition == "candidate"
                    else (CONTROL_PROVIDER, CONTROL_STATE)
                )
                if not _ledger_complete(response_path, expected):
                    await _execute_condition(
                        condition,
                        resume=response_path.exists() or any(path.exists() for path in paths),
                    )
                if not _ledger_complete(response_path, expected):
                    raise AtomicProductCheckpointError(f"{condition} ledger incomplete")
                state["completed_stages"].append(stage)
                state["current_stage"] = (
                    "control-100" if condition == "candidate" else "hidden-gold-score"
                )
                _atomic_write(CHECKPOINT_STATE, state)
        candidate, control, paired = _score()
        if "hidden-gold-score" not in state["completed_stages"]:
            state["completed_stages"].extend(["hidden-gold-score", "paired-decision"])
        accounting = _provider_totals()
        if (
            accounting["provider_calls"] > 600
            or accounting["provider_attempts"] != accounting["provider_calls"]
            or accounting["reported_cost_usd"] > 7.0
        ):
            status = "invalid-execution"
        else:
            status = paired["status"]
        result = {
            "schema_version": 1,
            "program_id": PROGRAM_ID,
            "instrument_id": INSTRUMENT_ID,
            "status": status,
            "decision": paired["decision"] if status != "invalid-execution" else None,
            "candidate_status": candidate["status"],
            "control_status": control["status"],
            "failed_gates": paired["failed_gates"],
            "accounting": accounting,
            "hidden_gold_opened_after_response_ledgers": True,
            "private_data_used": False,
            "final_10000_opened": False,
        }
        state.update(status=status, current_stage=None, terminal_result=result)
        _atomic_write(CHECKPOINT_STATE, state)
        return result
    except KeyboardInterrupt:
        state.update(status="interrupted")
        _atomic_write(CHECKPOINT_STATE, state)
        raise
    except Exception as error:  # preserve bounded invalid execution evidence
        result = {
            "schema_version": 1,
            "program_id": PROGRAM_ID,
            "instrument_id": INSTRUMENT_ID,
            "status": "invalid-execution",
            "failure_stage": state.get("current_stage"),
            "failure_type": type(error).__name__,
            "failure_detail": str(error)[:400],
            "accounting": _provider_totals(),
            "final_10000_opened": False,
        }
        state.update(status="invalid-execution", current_stage=None, terminal_result=result)
        _atomic_write(CHECKPOINT_STATE, state)
        return result


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument(
        "--simulate", choices=("pass", "product-failure", "provider-failure", "resume")
    )
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
        result = asyncio.run(execute(resume=arguments.resume))
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.simulate:
        result = simulate(scenario=arguments.simulate)
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
