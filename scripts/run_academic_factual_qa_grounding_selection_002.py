#!/usr/bin/env python3
"""Run the one-shot 500+100 grounding selection with hidden gold."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
from typing import Any, Iterator

from dotenv import load_dotenv

from scripts import academic_factual_qa_open_10000_t0_adapter as product_adapter
from scripts import build_academic_factual_qa_grounding_selection_002 as builder
from scripts import run_academic_factual_qa_open_10000 as product
from scripts import score_academic_factual_qa_open_10000 as scorer
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = builder.INSTRUMENT_ID
PROGRAM_ID = builder.PROGRAM_ID
ADAPTER_FACTORY = (
    "scripts.academic_factual_qa_atomic_m2_t0_adapter:build_atomic_m2_t0_adapter"
)
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
CHECKPOINT_STATE = OUTPUT_ROOT / "checkpoint-state.json"
CANDIDATE_RESPONSES = OUTPUT_ROOT / "candidate-responses.sqlite3"
CANDIDATE_PROVIDER = OUTPUT_ROOT / "candidate-provider.sqlite3"
CANDIDATE_STATE = OUTPUT_ROOT / "candidate-product-state.sqlite3"
CONTROL_RESPONSES = OUTPUT_ROOT / "control-responses.sqlite3"
CONTROL_PROVIDER = OUTPUT_ROOT / "control-provider.sqlite3"
CONTROL_STATE = OUTPUT_ROOT / "control-product-state.sqlite3"
CANDIDATE_RESULT = OUTPUT_ROOT / "candidate-result.json"
CONTROL_RESULT = OUTPUT_ROOT / "control-result.json"
PAIRED_RESULT = OUTPUT_ROOT / "paired-result.json"
CANARY_ROOT = OUTPUT_ROOT / "canaries"


class GroundingSelectionExecutionError(RuntimeError):
    """Raised when the finite grounding-selection boundary is violated."""


def _condition_paths(condition: str) -> tuple[Path, Path, Path, Path, Path]:
    if condition == "candidate":
        return (
            builder.CASES,
            builder.CANDIDATE_MANIFEST,
            CANDIDATE_RESPONSES,
            CANDIDATE_PROVIDER,
            CANDIDATE_STATE,
        )
    if condition == "control":
        return (
            builder.CONTROL_CASES,
            builder.CONTROL_MANIFEST,
            CONTROL_RESPONSES,
            CONTROL_PROVIDER,
            CONTROL_STATE,
        )
    raise ValueError(f"unknown comparison condition: {condition}")


def _all_outputs() -> tuple[Path, ...]:
    return (
        CHECKPOINT_STATE,
        CANDIDATE_RESPONSES,
        CANDIDATE_PROVIDER,
        CANDIDATE_STATE,
        CONTROL_RESPONSES,
        CONTROL_PROVIDER,
        CONTROL_STATE,
        CANDIDATE_RESULT,
        CONTROL_RESULT,
        PAIRED_RESULT,
        CANARY_ROOT,
    )


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GroundingSelectionExecutionError(
            f"JSON root is not an object: {path.name}"
        )
    return value


def _load_hashed(path: Path) -> dict[str, Any]:
    value = _load(path)
    observed = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise GroundingSelectionExecutionError(f"content hash drifted: {path.name}")
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


def _atomic_write(
    path: Path, value: dict[str, Any], *, exclusive: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and path.exists():
        raise GroundingSelectionExecutionError(f"exclusive output is used: {path.name}")
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
    return metadata.get("status") == "completed" and metadata.get(
        "response_count"
    ) == str(expected)


def _provider_summary(paths: tuple[Path, ...]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "provider_calls": 0,
        "provider_attempts": 0,
        "failed_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reported_cost_usd": 0.0,
        "maximum_latency_ms": 0.0,
        "returned_models": [],
    }
    models: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = list(
                connection.execute(
                    "SELECT status,response_json,input_tokens,output_tokens,cost_usd,"
                    "latency_ms,attempt_count FROM calls ORDER BY sequence"
                )
            )
        finally:
            connection.close()
        for (
            status,
            response_json,
            input_tokens,
            output_tokens,
            cost,
            latency,
            attempts,
        ) in rows:
            summary["provider_calls"] += 1
            summary["provider_attempts"] += int(attempts)
            summary["failed_calls"] += int(status == "failed")
            summary["input_tokens"] += int(input_tokens)
            summary["output_tokens"] += int(output_tokens)
            summary["reported_cost_usd"] += float(cost)
            summary["maximum_latency_ms"] = max(
                float(summary["maximum_latency_ms"]), float(latency)
            )
            if response_json:
                model = json.loads(response_json).get("provider_model")
                if model:
                    models.add(str(model))
    summary["returned_models"] = sorted(models)
    return summary


@contextmanager
def _configured_modules() -> Iterator[None]:
    product_values = {
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "INSTRUMENT_PATH": builder.INSTRUMENT,
        "PROVIDER_BINDING_PATH": builder.BINDING,
        "ACTIVE_GENERATOR": "openai-gpt-5.4-mini-question-targeted-atomic-v1",
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
    build = builder.validate()
    instrument = _load_hashed(builder.INSTRUMENT)
    binding = _load_hashed(builder.BINDING)
    execution = instrument["execution"]
    if (
        execution["maximum_product_calls"] != 600
        or execution["maximum_canary_calls"] != 2
        or execution["maximum_total_calls"] != 602
        or execution["maximum_transport_retries"] != 0
        or execution["absolute_emergency_cost_usd"] != 50.0
        or execution["hidden_gold_after_both_response_ledgers"] is not True
    ):
        raise GroundingSelectionExecutionError("finite execution boundary drifted")
    provider = binding["providers"]["high-volume-generator"]
    if (
        provider["binding_id"] != "grounding-selection-openai-gpt-5.4-mini-002"
        or provider["provider_model"] != "gpt-5.4-mini-2026-03-17"
        or provider["request_store"] is not False
        or provider["maximum_transport_retries"] != 0
    ):
        raise GroundingSelectionExecutionError("exact OpenAI binding drifted")
    return {
        **build,
        "status": build["status"],
        "maximum_canary_calls": 2,
        "maximum_product_calls": 600,
        "maximum_total_calls": 602,
        "hidden_gold_loaded": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate()
    except Exception as error:  # noqa: BLE001 - expose every no-call blocker
        blockers.append(f"validation:{type(error).__name__}:{error}")
    try:
        binding = _load_hashed(builder.BINDING)
        authorization = binding["authorization"]
        if not authorization["provider_execution_authorized"]:
            blockers.append("provider-execution-not-authorized")
        if not authorization["paid_execution_authorized"]:
            blockers.append("paid-execution-not-authorized")
        if binding["metadata_status"] != "fresh" or not binding["verified_at"]:
            blockers.append("provider-metadata-refresh-required")
        else:
            verified_at = datetime.fromisoformat(binding["verified_at"])
            age = (
                datetime.now(UTC) - verified_at.astimezone(UTC)
            ).total_seconds() / 3600
            if age < 0 or age > binding["freshness_hours"]:
                blockers.append("provider-metadata-stale")
    except Exception as error:  # noqa: BLE001
        blockers.append(f"provider-binding:{type(error).__name__}:{error}")
    try:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    except Exception:
        blockers.append("repository-freeze-authorization-missing")
    if _dirty():
        blockers.append("working-tree-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-credential-missing")
    if resume:
        if not CHECKPOINT_STATE.is_file():
            blockers.append("resume-checkpoint-missing")
    else:
        used = [path.name for path in _all_outputs() if path.exists()]
        if used:
            blockers.append("exclusive-output-used:" + ",".join(sorted(used)))
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "provider_calls": 0,
        "maximum_total_calls": 602,
        "absolute_emergency_cost_usd": 50.0,
        "hidden_gold_loaded": False,
    }


def simulate(*, scenario: str) -> dict[str, Any]:
    if scenario not in {
        "pass",
        "quality-failure",
        "canary-failure",
        "provider-failure",
        "resume",
    }:
        raise GroundingSelectionExecutionError("unknown simulation scenario")
    validate()
    status = {
        "pass": "completed-keep",
        "quality-failure": "completed-refine",
        "canary-failure": "invalid-execution",
        "provider-failure": "invalid-execution",
        "resume": "completed-keep",
    }[scenario]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "scenario": scenario,
        "stage_order": [
            "candidate-canary",
            "control-canary",
            "candidate-500",
            "control-100",
            "hidden-gold-score",
            "paired-decision",
        ],
        "bulk_calls_after_canary_failure": 0,
        "gold_opened_before_responses": False,
        "provider_calls": 0,
        "network_calls": 0,
    }


def _canary_paths(condition: str) -> tuple[Path, Path, Path, Path]:
    root = CANARY_ROOT / condition
    return (
        root / "cases.json",
        root / "responses.sqlite3",
        root / "provider.sqlite3",
        root / "product-state.sqlite3",
    )


def _prepare_canary_package(condition: str) -> Path:
    cases_path, _, _, _ = _canary_paths(condition)
    if cases_path.is_file():
        return cases_path
    source_path = builder.CASES if condition == "candidate" else builder.CONTROL_CASES
    source = _load_hashed(source_path)
    expected_id = _load_hashed(builder.INSTRUMENT)["execution"]["canary_case_ids"][
        0 if condition == "candidate" else 1
    ]
    rows = [row for row in source["cases"] if row["case_id"] == expected_id]
    if len(rows) != 1:
        raise GroundingSelectionExecutionError("frozen canary identity is unavailable")
    payload = {
        "schema_version": 1,
        "dataset_id": f"{source['dataset_id']}-{condition}-canary",
        "split": source["split"],
        "case_count": 1,
        "cases": rows,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    _atomic_write(cases_path, payload, exclusive=True)
    return cases_path


async def _execute_canary(condition: str) -> float:
    cases_path, responses, provider_ledger, state = _canary_paths(condition)
    manifest = (
        builder.CANDIDATE_MANIFEST
        if condition == "candidate"
        else builder.CONTROL_MANIFEST
    )
    if _ledger_complete(responses, 1):
        summary = _provider_summary((provider_ledger,))
    else:
        cases_path = _prepare_canary_package(condition)
        with _configured_modules():
            await product.execute(
                cases_path=cases_path,
                manifest_path=manifest,
                output=responses,
                adapter_factory=ADAPTER_FACTORY,
                provider_ledger=provider_ledger,
                state_path=state,
                resume=False,
            )
        summary = _provider_summary((provider_ledger,))
    if (
        not _ledger_complete(responses, 1)
        or summary["provider_calls"] != 1
        or summary["provider_attempts"] != 1
        or summary["failed_calls"] != 0
        or summary["returned_models"] != ["gpt-5.4-mini-2026-03-17"]
    ):
        raise GroundingSelectionExecutionError(f"{condition} canary failed")
    return float(summary["reported_cost_usd"])


async def _execute_condition(condition: str, *, resume: bool) -> None:
    cases, manifest, responses, provider_ledger, state = _condition_paths(condition)
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
        raise GroundingSelectionExecutionError(
            "hidden gold cannot open before both ledgers"
        )
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


def _checkpoint(*, resume: bool) -> dict[str, Any]:
    instrument_hash = _load_hashed(builder.INSTRUMENT)["content_sha256"]
    binding_hash = _load_hashed(builder.BINDING)["content_sha256"]
    if resume:
        state = _load(CHECKPOINT_STATE)
        if (
            state.get("instrument_sha256") != instrument_hash
            or state.get("binding_sha256") != binding_hash
            or state.get("code_revision") != _revision()
            or state.get("status") not in {"running", "interrupted"}
        ):
            raise GroundingSelectionExecutionError("checkpoint resume binding drifted")
        return state
    state = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument_hash,
        "binding_sha256": binding_hash,
        "code_revision": _revision(),
        "status": "running",
        "completed_stages": [],
        "current_stage": "candidate-canary",
    }
    _atomic_write(CHECKPOINT_STATE, state, exclusive=True)
    return state


async def execute(*, resume: bool = False) -> dict[str, Any]:
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise GroundingSelectionExecutionError(
            "checkpoint preflight blocked: " + ", ".join(readiness["blockers"])
        )
    state = _checkpoint(resume=resume)
    try:
        canary_costs: dict[str, float] = {}
        for condition in ("candidate", "control"):
            stage = f"{condition}-canary"
            state["current_stage"] = stage
            if stage not in state["completed_stages"]:
                canary_costs[condition] = await _execute_canary(condition)
                state["completed_stages"].append(stage)
                _atomic_write(CHECKPOINT_STATE, state)
            else:
                canary_costs[condition] = _provider_summary(
                    (_canary_paths(condition)[2],)
                )["reported_cost_usd"]
        projected = 1.5 * (
            canary_costs["candidate"] * 500 + canary_costs["control"] * 100
        )
        projected_stop = max(5.0, math.ceil(projected / 5.0) * 5.0)
        if projected_stop > 50.0:
            raise GroundingSelectionExecutionError(
                f"projected p99 cost ${projected_stop:.2f} exceeds $50.00"
            )
        state["projected_p99_cost_stop_usd"] = projected_stop
        for condition, expected in (("candidate", 500), ("control", 100)):
            stage = f"{condition}-{expected}"
            state["current_stage"] = stage
            if stage in state["completed_stages"]:
                continue
            _, _, responses, provider_ledger, product_state = _condition_paths(
                condition
            )
            if not _ledger_complete(responses, expected):
                await _execute_condition(
                    condition,
                    resume=responses.exists()
                    or provider_ledger.exists()
                    or product_state.exists(),
                )
            if not _ledger_complete(responses, expected):
                raise GroundingSelectionExecutionError(
                    f"{condition} response ledger incomplete"
                )
            state["completed_stages"].append(stage)
            _atomic_write(CHECKPOINT_STATE, state)
        state["current_stage"] = "hidden-gold-score"
        candidate, control, paired = _score()
        state["completed_stages"].extend(
            stage
            for stage in ("hidden-gold-score", "paired-decision")
            if stage not in state["completed_stages"]
        )
        accounting = _provider_summary(
            (
                _canary_paths("candidate")[2],
                _canary_paths("control")[2],
                CANDIDATE_PROVIDER,
                CONTROL_PROVIDER,
            )
        )
        operationally_valid = (
            accounting["provider_calls"] <= 602
            and accounting["provider_attempts"] == accounting["provider_calls"]
            and accounting["reported_cost_usd"] <= 50.0
            and accounting["returned_models"] == ["gpt-5.4-mini-2026-03-17"]
        )
        status = paired["status"] if operationally_valid else "invalid-execution"
        result = {
            "schema_version": 1,
            "instrument_id": INSTRUMENT_ID,
            "status": status,
            "decision": paired.get("decision") if operationally_valid else None,
            "candidate_status": candidate["status"],
            "control_status": control["status"],
            "failed_gates": paired["failed_gates"],
            "accounting": accounting,
            "projected_p99_cost_stop_usd": projected_stop,
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
    except Exception as error:  # preserve every bounded invalid execution
        result = {
            "schema_version": 1,
            "instrument_id": INSTRUMENT_ID,
            "status": "invalid-execution",
            "failure_stage": state.get("current_stage"),
            "failure_type": type(error).__name__,
            "failure_detail": str(error)[:400],
            "accounting": _provider_summary(
                (
                    _canary_paths("candidate")[2],
                    _canary_paths("control")[2],
                    CANDIDATE_PROVIDER,
                    CONTROL_PROVIDER,
                )
            ),
            "hidden_gold_opened": False,
            "final_10000_opened": False,
        }
        state.update(
            status="invalid-execution", current_stage=None, terminal_result=result
        )
        _atomic_write(CHECKPOINT_STATE, state)
        return result


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument(
        "--simulate",
        choices=(
            "pass",
            "quality-failure",
            "canary-failure",
            "provider-failure",
            "resume",
        ),
    )
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
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
