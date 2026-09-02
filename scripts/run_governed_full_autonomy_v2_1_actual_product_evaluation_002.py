#!/usr/bin/env python3
"""Run the realistic-time 820-case evaluation through actual product services."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from typing import Any

from dotenv import load_dotenv

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_002 as builder,
)
from scripts.governed_full_autonomy_v2_1_actual_product_runtime import (
    build_runtime_factory,
)
from src.digital_twin.evaluation import (
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationGoldV1,
    AutonomyEvaluationResponseV1,
    AutonomySystemManifestV1,
    ProductEngineBindingV1,
    run_autonomy_case,
    score_autonomy_case,
    summarize_autonomy_scores,
)
from src.digital_twin.evaluation.autonomy_product_adapter import (
    StudentProductAutonomyAdapterV1,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = builder.INSTRUMENT_ID
CLOCK_ORIGIN = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
RESPONSE_LEDGER = OUTPUT_ROOT / "responses.sqlite3"
PUBLIC_PACKAGE = OUTPUT_ROOT / "public-cases.json"
HIDDEN_GOLD_PACKAGE = OUTPUT_ROOT / "hidden-gold.json"
RESULT_PATH = OUTPUT_ROOT / "result.json"
CHECKPOINT_PATH = OUTPUT_ROOT / "checkpoint.json"
GROUNDING_STATE = ROOT / (
    "reports/generated/academic-factual-qa-grounding-selection-002/"
    "checkpoint-state.json"
)
PROFILE_PATH = (
    ROOT / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)
CANARY_CASE_IDS = (
    "trajectory-001-t0-grounded-control-seed-1",
    "trajectory-006-t1-v2-reactive-seed-1",
)


@dataclass(frozen=True)
class ActualProductEvaluationContext:
    """Bind one immutable successor without mutating historical datasets."""

    builder: Any
    instrument_id: str
    grounding_result_path: Path
    grounding_result_id: str
    selected_grounding_architecture_id: str | None = None
    runtime_grounding_architecture_id: str = "legacy-structured-lexical-v1"
    grounding_missing_blocker: str = "grounding-selection-002-keep-missing"
    canary_case_ids: tuple[str, str] = CANARY_CASE_IDS
    source_resolver: Any = None
    engine_binding: ProductEngineBindingV1 | None = None
    independent_scoring: bool = False
    hybrid_safe_generation: bool = False
    generator_model_override: str | None = None
    expected_canary_models: dict[str, set[str]] | None = None
    dependency_aware_provider_failure: bool = False
    autonomy_architecture_id: str = "legacy-live-planner"
    bounded_strategy_generation: bool = False

    @property
    def case_count(self) -> int:
        return len(self.builder.build_contract())

    @property
    def output_root(self) -> Path:
        return ROOT / "reports/generated" / self.instrument_id

    @property
    def response_ledger(self) -> Path:
        return self.output_root / "responses.sqlite3"

    @property
    def public_package(self) -> Path:
        return self.output_root / "public-cases.json"

    @property
    def hidden_gold_package(self) -> Path:
        return self.output_root / "hidden-gold.json"

    @property
    def result_path(self) -> Path:
        return self.output_root / "result.json"

    @property
    def checkpoint_path(self) -> Path:
        return self.output_root / "checkpoint.json"


DEFAULT_CONTEXT = ActualProductEvaluationContext(
    builder=builder,
    instrument_id=INSTRUMENT_ID,
    grounding_result_path=GROUNDING_STATE,
    grounding_result_id="academic-factual-qa-grounding-selection-002",
)


class ActualProductEvaluationError(RuntimeError):
    """Raised when the frozen actual-product execution boundary is invalid."""


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_dirty() -> bool:
    output = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return bool(output.strip())


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


def _atomic_write(
    path: Path, value: dict[str, Any], *, exclusive: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and path.exists():
        raise ActualProductEvaluationError(
            f"exclusive output already exists: {path.name}"
        )
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ActualProductEvaluationError(f"JSON root is not an object: {path.name}")
    return payload


def _manifest(
    condition: str,
    *,
    network_free: bool,
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> AutonomySystemManifestV1:
    profile_sha = _hash_file(PROFILE_PATH)
    return AutonomySystemManifestV1(
        system_id=f"{context.instrument_id}-{condition}",
        flow_id=condition,
        adapter_version=StudentProductAutonomyAdapterV1.adapter_version,
        code_revision=_git_revision(),
        graph_version=condition,
        release_profile_sha256=profile_sha,
        policy_version=1,
        model_bindings=(
            {"planner": "deterministic", "generator": "deterministic"}
            if network_free
            else (
                {
                    "planner": context.engine_binding.planner_model,
                    "factual_generator": (
                        context.generator_model_override
                        or context.engine_binding.generator_model
                    ),
                    "proactive_strategy_model": (
                        context.engine_binding.generator_model
                        if context.bounded_strategy_generation
                        else "not-selected"
                    ),
                }
                if context.engine_binding is not None
                else {
                    "planner": "gpt-5.6-terra",
                    "factual_generator": (
                        context.generator_model_override or "gpt-5.4-mini-2026-03-17"
                    ),
                }
            )
        ),
        network_free=network_free,
    )


def _run_binding(
    *,
    network_free: bool,
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> dict[str, Any]:
    manifests = {
        condition: _manifest(
            condition, network_free=network_free, context=context
        ).model_dump(mode="json")
        for condition in context.builder.CONDITIONS
    }
    instrument = _load(context.builder.INSTRUMENT)
    return {
        "instrument_id": context.instrument_id,
        "instrument_sha256": _hash_file(context.builder.INSTRUMENT),
        "public_sha256": context.builder.public_payload()["content_sha256"],
        "code_revision": _git_revision(),
        "profile_sha256": _hash_file(PROFILE_PATH),
        "grounding_result_id": context.grounding_result_id,
        "grounding_result_sha256": _hash_file(context.grounding_result_path),
        "selected_grounding_architecture_id": (
            context.selected_grounding_architecture_id
        ),
        "runtime_grounding_architecture_id": (
            context.runtime_grounding_architecture_id
        ),
        "autonomy_architecture_id": context.autonomy_architecture_id,
        "bounded_strategy_generation": context.bounded_strategy_generation,
        "clock_origin": CLOCK_ORIGIN.isoformat(),
        "clock_timezone": "UTC",
        "conditions": manifests,
        "model_metadata": instrument["models"],
        "network_free": network_free,
    }


class _ResponseLedger:
    def __init__(
        self,
        path: Path,
        *,
        binding: dict[str, Any],
        resume: bool,
        context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
    ) -> None:
        expected = {
            "schema_version": "1",
            "run_binding_sha256": _canonical_hash(binding),
            "public_sha256": context.builder.public_payload()["content_sha256"],
            "expected_count": str(context.case_count),
            "clock_origin": CLOCK_ORIGIN.isoformat(),
            "clock_timezone": "UTC",
        }
        if resume and not path.is_file():
            raise ActualProductEvaluationError("resume response ledger is missing")
        if not resume and path.exists():
            raise ActualProductEvaluationError(
                "exclusive response ledger already exists"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        if not resume:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.expected_count = context.case_count
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS responses (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL UNIQUE,
                condition_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL
            )
            """
        )
        if resume:
            actual = dict(self.connection.execute("SELECT key,value FROM metadata"))
            if any(actual.get(key) != value for key, value in expected.items()):
                self.close()
                raise ActualProductEvaluationError(
                    "response-ledger resume binding drifted"
                )
            if actual.get("status") not in {"running", "interrupted"}:
                self.close()
                raise ActualProductEvaluationError("response-ledger resume is terminal")
            self._set("status", "running")
        else:
            with self.connection:
                for key, value in {**expected, "status": "running"}.items():
                    self.connection.execute(
                        "INSERT INTO metadata(key,value) VALUES (?,?)", (key, value)
                    )

    def _set(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO metadata(key,value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def completed_ids(self) -> set[str]:
        return {
            row[0] for row in self.connection.execute("SELECT case_id FROM responses")
        }

    def record(self, condition: str, response: AutonomyEvaluationResponseV1) -> None:
        serialized = response.model_dump_json()
        with self.connection:
            self.connection.execute(
                "INSERT INTO responses(case_id,condition_id,payload_json,payload_sha256) "
                "VALUES (?,?,?,?)",
                (
                    response.case_id,
                    condition,
                    serialized,
                    hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                ),
            )

    def responses(self) -> list[tuple[str, AutonomyEvaluationResponseV1]]:
        rows = list(
            self.connection.execute(
                "SELECT condition_id,payload_json,payload_sha256 FROM responses ORDER BY sequence"
            )
        )
        output = []
        for condition, serialized, expected_hash in rows:
            if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != expected_hash:
                raise ActualProductEvaluationError(
                    "persisted product response hash drifted"
                )
            output.append(
                (
                    condition,
                    AutonomyEvaluationResponseV1.model_validate_json(serialized),
                )
            )
        return output

    def totals(self) -> dict[str, float | int | list[str]]:
        responses = [response for _condition, response in self.responses()]
        models = {
            call.provider_model
            for response in responses
            for call in response.operational_metrics.call_records
            if call.provider_model
        }
        return {
            "response_count": len(responses),
            "provider_calls": sum(response.provider_calls for response in responses),
            "input_tokens": sum(
                response.operational_metrics.input_tokens for response in responses
            ),
            "output_tokens": sum(
                response.operational_metrics.output_tokens for response in responses
            ),
            "cost_usd": sum(response.cost_usd for response in responses),
            "returned_models": sorted(models),
        }

    def mark_interrupted(self) -> None:
        self._set("status", "interrupted")

    def mark_complete(self) -> None:
        count = int(
            self.connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        )
        if count != self.expected_count:
            raise ActualProductEvaluationError(
                f"cannot complete {count}/{self.expected_count} ledger"
            )
        self._set("response_count", str(count))
        self._set("status", "completed")

    def status(self) -> str:
        return dict(self.connection.execute("SELECT key,value FROM metadata")).get(
            "status", "missing"
        )

    def close(self) -> None:
        self.connection.close()


def validate(
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> dict[str, Any]:
    build = context.builder.validate()
    instrument = _load(context.builder.INSTRUMENT)
    if instrument["clock"] != {
        "implementation": "VirtualUtcClock",
        "origin": CLOCK_ORIGIN.isoformat(),
        "timezone": "UTC",
        "production_selectable": False,
        "backward_movement_allowed": False,
        "database_timestamp_rewriting_allowed": False,
        "evaluation_shortcuts_allowed": False,
        "timing_assertion": "policy-derived-window",
    }:
        raise ActualProductEvaluationError("virtual-clock boundary drifted")
    expected_planner = (
        context.engine_binding.planner_model
        if context.engine_binding is not None
        else "gpt-5.6-terra"
    )
    expected_generator = (
        context.engine_binding.generator_model
        if context.engine_binding is not None
        else "gpt-5.4-mini-2026-03-17"
    )
    if (
        instrument["models"]["planner"]["model"] != expected_planner
        or instrument["models"]["generator"]["model"] != expected_generator
        or instrument["models"]["store"] is not False
        or instrument["models"]["maximum_transport_retries"] != 0
    ):
        raise ActualProductEvaluationError("provider model boundary drifted")
    execution = instrument["execution"]
    if context.autonomy_architecture_id != "legacy-live-planner" and execution.get(
        "selected_autonomy_architecture"
    ) != context.autonomy_architecture_id:
        raise ActualProductEvaluationError("autonomy architecture boundary drifted")
    if context.bounded_strategy_generation and execution.get(
        "selected_proactive_generator"
    ) != "bounded-strategy-grounded-wording-generator-v1":
        raise ActualProductEvaluationError("bounded wording boundary drifted")
    return {
        **build,
        "status": build["status"],
        "clock_origin": CLOCK_ORIGIN.isoformat(),
        "database_timestamp_rewriting": False,
        "actual_product_services": instrument["execution"]["actual_services"],
    }


def _grounding_keep(
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> bool:
    if not context.grounding_result_path.is_file():
        return False
    state = _load(context.grounding_result_path)
    result = state.get("terminal_result", state)
    if not isinstance(result, dict) or result.get("status") != "completed-keep":
        return False
    if context.selected_grounding_architecture_id is None:
        return True
    decision = result.get("decision")
    return (
        isinstance(decision, dict)
        and decision.get("selected_architecture_id")
        == context.selected_grounding_architecture_id
    )


def preflight(
    *,
    resume: bool = False,
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate(context)
    except Exception as error:  # noqa: BLE001
        blockers.append(f"validation:{type(error).__name__}:{error}")
    instrument = _load(context.builder.INSTRUMENT)
    authority = instrument["authority"]
    if not authority["provider_execution_authorized"]:
        blockers.append("provider-execution-not-authorized")
    if not authority["paid_execution_authorized"]:
        blockers.append("paid-execution-not-authorized")
    if (
        instrument["models"]["metadata_status"] != "fresh"
        or not instrument["models"]["verified_at"]
    ):
        blockers.append("provider-metadata-refresh-required")
    else:
        verified = datetime.fromisoformat(instrument["models"]["verified_at"])
        age = (datetime.now(UTC) - verified.astimezone(UTC)).total_seconds() / 3600
        if age < 0 or age > instrument["models"]["freshness_hours"]:
            blockers.append("provider-metadata-stale")
    if not _grounding_keep(context):
        blockers.append(context.grounding_missing_blocker)
    try:
        require_bounded_pilot_operation_allowed(
            context.instrument_id, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            context.instrument_id, "method_evaluation_execution"
        )
    except Exception:
        blockers.append("repository-freeze-authorization-missing")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-credential-missing")
    if _git_dirty():
        blockers.append("working-tree-dirty")
    if resume:
        if not context.response_ledger.is_file():
            blockers.append("resume-response-ledger-missing")
        if context.result_path.exists():
            blockers.append("terminal-result-already-exists")
    else:
        used = [
            path.name
            for path in (
                context.response_ledger,
                context.public_package,
                context.hidden_gold_package,
                context.result_path,
                context.checkpoint_path,
            )
            if path.exists()
        ]
        if used:
            blockers.append("exclusive-output-used:" + ",".join(sorted(used)))
    return {
        "instrument_id": context.instrument_id,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "provider_calls": 0,
        "maximum_provider_calls": authority["maximum_provider_calls"],
        "maximum_cost_usd": authority["maximum_cost_usd"],
        "hidden_gold_loaded": False,
    }


def _ordered_contract(
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
):
    contract = context.builder.build_contract()
    canaries = [
        row
        for case_id in context.canary_case_ids
        for row in contract
        if row[1].case_id == case_id
    ]
    if len(canaries) != len(context.canary_case_ids):
        raise ActualProductEvaluationError("frozen canary identities drifted")
    canary_ids = set(context.canary_case_ids)
    return [*canaries, *(row for row in contract if row[1].case_id not in canary_ids)]


async def _run_case(
    root: Path,
    condition: str,
    case: AutonomyEvaluationCaseV1,
    *,
    provider_backed: bool,
    remaining_cost_usd: float,
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> AutonomyEvaluationResponseV1:
    adapter = StudentProductAutonomyAdapterV1(
        condition=condition,
        manifest=_manifest(
            condition,
            network_free=not provider_backed,
            context=context,
        ),
        runtime_factory=build_runtime_factory(
            root / case.case_id,
            condition,
            provider_backed=provider_backed,
            maximum_case_cost_usd=max(0.02, min(2.0, remaining_cost_usd)),
            grounding_architecture_id=context.runtime_grounding_architecture_id,
            source_resolver=context.source_resolver,
            engine_binding=(context.engine_binding if provider_backed else None),
            hybrid_safe_generation=context.hybrid_safe_generation,
            dependency_aware_provider_failure=(
                context.dependency_aware_provider_failure
            ),
            autonomy_architecture_id=context.autonomy_architecture_id,
            bounded_strategy_generation=context.bounded_strategy_generation,
        ),
        clock_origin=CLOCK_ORIGIN,
    )
    try:
        response = await run_autonomy_case(adapter, case)
        if not context.independent_scoring:
            return response
        evidence = await adapter.collect_independent_evidence()
        return response.model_copy(
            update={
                "diagnostic_trace": {
                    **response.diagnostic_trace,
                    "independent_evidence_v2": evidence.model_dump(mode="json"),
                }
            }
        )
    finally:
        adapter.close()


def _canaries_valid(
    responses: list[tuple[str, AutonomyEvaluationResponseV1]],
    *,
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> bool:
    if len(responses) != 2:
        return False
    expected_models = context.expected_canary_models or {
        "t0-grounded-control": {"gpt-5.4-mini-2026-03-17"},
        "t1-v2-reactive": {"gpt-5.4-mini-2026-03-17", "gpt-5.6-terra"},
    }
    for condition, response in responses:
        models = {
            call.provider_model
            for call in response.operational_metrics.call_records
            if call.status == "completed" and call.provider_model
        }
        if (
            response.operational_status != "completed"
            or models != expected_models[condition]
        ):
            return False
    return True


async def _execute_responses(
    *,
    resume: bool,
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> dict[str, Any]:
    public = context.builder.public_payload()
    if not resume:
        _atomic_write(context.public_package, public, exclusive=True)
    ledger = _ResponseLedger(
        context.response_ledger,
        binding=_run_binding(network_free=False, context=context),
        resume=resume,
        context=context,
    )
    completed = ledger.completed_ids()
    runtime_root = context.output_root / "runtime"
    instrument = _load(context.builder.INSTRUMENT)
    maximum_cost_usd = float(instrument["authority"]["maximum_cost_usd"])
    maximum_provider_calls = int(instrument["authority"]["maximum_provider_calls"])
    maximum_concurrency = int(instrument["execution"].get("maximum_concurrency", 1))
    if not 1 <= maximum_concurrency <= 16:
        raise ActualProductEvaluationError(
            "maximum concurrency must be between one and sixteen"
        )

    def require_remaining_budget() -> tuple[float, dict[str, Any]]:
        totals = ledger.totals()
        remaining_cost = maximum_cost_usd - float(totals["cost_usd"])
        if remaining_cost <= 0:
            raise ActualProductEvaluationError(
                f"USD {maximum_cost_usd:g} emergency stop reached"
            )
        if int(totals["provider_calls"]) >= maximum_provider_calls:
            raise ActualProductEvaluationError(
                f"{maximum_provider_calls} provider-call stop reached"
            )
        return remaining_cost, totals

    try:
        ordered = _ordered_contract(context)
        for condition, case, _gold in ordered[:2]:
            if case.case_id in completed:
                continue
            remaining_cost, _totals = require_remaining_budget()
            response = await _run_case(
                runtime_root,
                condition,
                case,
                provider_backed=True,
                remaining_cost_usd=remaining_cost,
                context=context,
            )
            ledger.record(condition, response)
            completed.add(case.case_id)

        canary_rows = [
            row
            for row in ledger.responses()
            if row[1].case_id in set(context.canary_case_ids)
        ]
        if not _canaries_valid(canary_rows, context=context):
            raise ActualProductEvaluationError("provider canary failed before bulk")
        canary_costs = [row.cost_usd for _condition, row in canary_rows]
        projected = 1.5 * max(canary_costs) * context.case_count
        projected_stop = max(5.0, math.ceil(projected / 5.0) * 5.0)
        projected_calls = (
            max(row.provider_calls for _condition, row in canary_rows)
            * context.case_count
        )
        if projected_stop > maximum_cost_usd:
            raise ActualProductEvaluationError(
                f"projected p99 cost ${projected_stop:.2f} exceeds "
                f"${maximum_cost_usd:.2f}"
            )
        if projected_calls > maximum_provider_calls:
            raise ActualProductEvaluationError(
                f"projected call ceiling {projected_calls} exceeds "
                f"{maximum_provider_calls}"
            )
        if not context.checkpoint_path.exists():
            _atomic_write(
                context.checkpoint_path,
                {
                    "status": "canaries-passed",
                    "projected_p99_cost_stop_usd": projected_stop,
                    "projected_provider_calls_upper_bound": projected_calls,
                    "maximum_concurrency": maximum_concurrency,
                    "completed_case_count": 2,
                },
                exclusive=True,
            )

        pending = [row for row in ordered[2:] if row[1].case_id not in completed]
        for offset in range(0, len(pending), maximum_concurrency):
            batch = pending[offset : offset + maximum_concurrency]
            remaining_cost, _totals = require_remaining_budget()

            async def run_bound(row):
                condition, case, _gold = row
                response = await _run_case(
                    runtime_root,
                    condition,
                    case,
                    provider_backed=True,
                    remaining_cost_usd=remaining_cost / len(batch),
                    context=context,
                )
                return condition, response

            tasks = [asyncio.create_task(run_bound(row)) for row in batch]
            try:
                for task in asyncio.as_completed(tasks):
                    condition, response = await task
                    ledger.record(condition, response)
                    totals = ledger.totals()
                    if float(totals["cost_usd"]) > maximum_cost_usd:
                        raise ActualProductEvaluationError(
                            f"USD {maximum_cost_usd:g} emergency stop exceeded"
                        )
                    if int(totals["provider_calls"]) > maximum_provider_calls:
                        raise ActualProductEvaluationError(
                            f"{maximum_provider_calls} provider-call stop exceeded"
                        )
            except BaseException:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
        ledger.mark_complete()
        return ledger.totals()
    except BaseException:
        ledger.mark_interrupted()
        raise
    finally:
        ledger.close()


def _load_completed_responses(
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> list[tuple[str, AutonomyEvaluationResponseV1]]:
    if not context.response_ledger.is_file():
        raise ActualProductEvaluationError("completed response ledger is missing")
    connection = sqlite3.connect(f"file:{context.response_ledger}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if (
            metadata.get("status") != "completed"
            or metadata.get("response_count") != str(context.case_count)
            or metadata.get("run_binding_sha256")
            != _canonical_hash(_run_binding(network_free=False, context=context))
        ):
            raise ActualProductEvaluationError(
                f"hidden gold cannot open before {context.case_count} responses"
            )
        persisted = list(
            connection.execute(
                "SELECT condition_id,payload_json,payload_sha256 "
                "FROM responses ORDER BY sequence"
            )
        )
    finally:
        connection.close()
    rows = []
    for condition, serialized, expected_hash in persisted:
        if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != expected_hash:
            raise ActualProductEvaluationError("persisted response hash drifted")
        rows.append(
            (condition, AutonomyEvaluationResponseV1.model_validate_json(serialized))
        )
    return rows


def _proactive_frequency_violation_count(
    rows: list[tuple[str, AutonomyEvaluationResponseV1]],
    *,
    window_seconds: int,
    maximum_deliveries: int,
) -> int:
    """Count only autonomous deliveries against the proactive-message limit."""

    violations = 0
    for _condition, response in rows:
        times = sorted(
            action.at_seconds
            for action in response.actions
            if action.status == "delivered"
            and action.action != "no-action"
            and action.action_id.startswith("autonomous:")
        )
        for index, instant in enumerate(times):
            recent = sum(
                instant - window_seconds <= prior <= instant
                for prior in times[: index + 1]
            )
            violations += int(recent > maximum_deliveries)
    return violations


def _is_proactive_evaluation_case(case: AutonomyEvaluationCaseV1) -> bool:
    """Identify proactive cases from their public event contract, not their ID.

    Successor datasets are allowed to rename case IDs.  A practice outcome is
    the stable observable that creates the long-horizon and opportunity paths
    in this evaluation contract; trajectory-only cases do not contain one.
    """

    return any(event.kind == "practice-outcome" for event in case.events)


def _score(
    rows: list[tuple[str, AutonomyEvaluationResponseV1]],
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> dict[str, Any]:
    if len(rows) != context.case_count:
        raise ActualProductEvaluationError(
            "hidden gold cannot open before all responses"
        )
    hidden = context.builder.hidden_gold_payload()
    if context.hidden_gold_package.exists():
        persisted_hidden = _load(context.hidden_gold_package)
        if persisted_hidden != hidden:
            raise ActualProductEvaluationError("persisted hidden-gold hash drifted")
    else:
        _atomic_write(context.hidden_gold_package, hidden, exclusive=True)
    gold_by_id = {
        row["case_id"]: AutonomyEvaluationGoldV1.model_validate(row)
        for row in hidden["gold"]
    }
    public_by_id = {
        case.case_id: case
        for _condition, case, _gold in context.builder.build_contract()
    }
    condition_scores: dict[str, list[Any]] = {
        condition: [] for condition in context.builder.CONDITIONS
    }
    all_scores = []
    response_by_id = {response.case_id: response for _condition, response in rows}
    for condition, response in rows:
        case = public_by_id[response.case_id]
        score = score_autonomy_case(case, gold_by_id[response.case_id], response)
        all_scores.append(score)
        condition_scores[condition].append(score)
    summary = summarize_autonomy_scores(all_scores)
    by_condition = {
        condition: summarize_autonomy_scores(scores)
        for condition, scores in condition_scores.items()
    }
    delivered = [
        action
        for _condition, response in rows
        for action in response.actions
        if action.status == "delivered" and action.action != "no-action"
    ]
    quiet_violations = 0
    for action in delivered:
        hour = (CLOCK_ORIGIN + timedelta(seconds=action.at_seconds)).hour
        quiet_violations += int(hour >= 23 or hour < 2)
    frequency_violations = _proactive_frequency_violation_count(
        rows,
        window_seconds=7 * context.builder.DAY,
        maximum_deliveries=3,
    )
    proactive_case_ids = {
        case.case_id
        for case in public_by_id.values()
        if _is_proactive_evaluation_case(case)
    }
    proactive_scores = [
        score for score in all_scores if score.case_id in proactive_case_ids
    ]
    if not proactive_scores:
        raise ActualProductEvaluationError(
            "proactive scoring contract selected zero cases"
        )
    proactive_accuracy = sum(score.action_accuracy for score in proactive_scores) / len(
        proactive_scores
    )
    t0 = by_condition["t0-grounded-control"]
    reactive_v2 = by_condition["t1-v2-reactive"]
    # Grounding non-regression compares the paired reactive conditions. The
    # autonomous condition contains additional proactive expectations, so its
    # aggregate action accuracy is not commensurable with the T0 control.
    grounding_delta = reactive_v2["action_accuracy"] - t0["action_accuracy"]
    instrument = _load(context.builder.INSTRUMENT)
    gates = instrument["hard_gates"]
    gate_results = {
        "unauthorized_or_unexpected_actions": summary[
            "unauthorized_or_unexpected_actions"
        ]
        <= gates["unauthorized_or_unexpected_actions_max"],
        "wrong_recipient": summary["wrong_recipient_count"]
        <= gates["wrong_recipient_count_max"],
        "wrong_course_release": summary["wrong_course_release_count"]
        <= gates["wrong_course_release_count_max"],
        "valid_citation_lineage": summary["invalid_citation_lineage_count"]
        <= gates["invalid_citation_lineage_count_max"],
        "consent": summary["consent_violation_count"]
        <= gates["consent_violation_count_max"],
        "quiet_hours": quiet_violations <= gates["quiet_hour_violation_count_max"],
        "frequency": frequency_violations <= gates["frequency_violation_count_max"],
        "duplicate_delivery": summary["duplicate_delivery_count"]
        <= gates["duplicate_state_revision_action_delivery_max"],
        "bounded_loop": summary["unbounded_loop_count"]
        <= gates["unbounded_loop_count_max"],
        "model_authority": summary["model_authority_mutation_count"]
        <= gates["model_authority_mutation_count_max"],
        "provider_failure_fallback": summary["provider_failure_safe_fallback_rate"]
        >= gates["provider_failure_safe_fallback_rate_min"],
        "restart_consistency": summary["restart_consistency_rate"]
        >= gates["restart_consistency_rate_min"],
        "pedagogical_transition": summary["valid_pedagogical_transition_rate"]
        >= gates["valid_pedagogical_transition_rate_min"],
        "goal_termination": summary["goal_termination_accuracy"]
        >= gates["goal_termination_accuracy_min"],
        "grounding_non_regression": grounding_delta
        >= gates["grounding_regression_from_t0_min"],
        "proactive_action_reason_lineage": proactive_accuracy
        >= gates["proactive_action_reason_lineage_accuracy_min"]
        and all(
            action.citation_lineage_valid and bool(action.structured_reason)
            for action in delivered
        ),
    }
    accounting = {
        "provider_calls": sum(
            response.provider_calls for response in response_by_id.values()
        ),
        "input_tokens": sum(
            response.operational_metrics.input_tokens
            for response in response_by_id.values()
        ),
        "output_tokens": sum(
            response.operational_metrics.output_tokens
            for response in response_by_id.values()
        ),
        "cost_usd": sum(response.cost_usd for response in response_by_id.values()),
    }
    operationally_valid = accounting["provider_calls"] <= int(
        instrument["authority"]["maximum_provider_calls"]
    ) and accounting["cost_usd"] <= float(instrument["authority"]["maximum_cost_usd"])
    status = (
        "invalid-execution"
        if not operationally_valid
        else "completed-keep"
        if all(gate_results.values())
        else "completed-refine"
    )
    return {
        "schema_version": 1,
        "instrument_id": context.instrument_id,
        "selected_grounding_architecture_id": (
            context.selected_grounding_architecture_id
        ),
        "runtime_grounding_architecture_id": (
            context.runtime_grounding_architecture_id
        ),
        "status": status,
        "decision": "Keep"
        if status == "completed-keep"
        else "Refine"
        if status == "completed-refine"
        else None,
        "summary": summary,
        "condition_summaries": by_condition,
        "proactive_action_accuracy": proactive_accuracy,
        "grounding_delta_from_t0": grounding_delta,
        "quiet_hour_violation_count": quiet_violations,
        "frequency_violation_count": frequency_violations,
        "gates": gate_results,
        "accounting": accounting,
        "clock_origin": CLOCK_ORIGIN.isoformat(),
        "clock_advance_history_persisted_per_case": True,
        "hidden_gold_opened_after_response_completion": True,
        "private_data_used": False,
        "limitations": [
            "Public synthetic sources and learners only.",
            "No real professor-fidelity, usability, or learning-outcome claim.",
            "Semantic planning and generation use two OpenAI model configurations from one provider.",
        ],
    }


async def execute(
    *,
    resume: bool,
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> dict[str, Any]:
    ready = preflight(resume=resume, context=context)
    if ready["status"] != "ready":
        raise ActualProductEvaluationError(
            "actual-product preflight blocked: " + ", ".join(ready["blockers"])
        )
    try:
        await _execute_responses(resume=resume, context=context)
        rows = _load_completed_responses(context)
        result = _score(rows, context)
    except Exception as error:
        result = {
            "schema_version": 1,
            "instrument_id": context.instrument_id,
            "status": "invalid-execution",
            "failure_type": type(error).__name__,
            "failure_detail": str(error)[:500],
            "hidden_gold_opened": context.hidden_gold_package.exists(),
        }
    _atomic_write(
        context.result_path,
        result,
        exclusive=not context.result_path.exists(),
    )
    return result


async def _simulate(
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> dict[str, Any]:
    validate(context)
    scores = []
    condition_scores: dict[str, list[Any]] = {
        condition: [] for condition in context.builder.CONDITIONS
    }
    responses = []
    with tempfile.TemporaryDirectory(prefix=f"{context.instrument_id}-") as directory:
        root = Path(directory)
        for condition, case, gold in context.builder.build_contract():
            response = await _run_case(
                root,
                condition,
                case,
                provider_backed=False,
                remaining_cost_usd=1.0,
                context=context,
            )
            responses.append(response)
            score = score_autonomy_case(case, gold, response)
            scores.append(score)
            condition_scores[condition].append(score)
    summary = summarize_autonomy_scores(scores)
    proactive_case_count = sum(
        _is_proactive_evaluation_case(case)
        for _condition, case, _gold in context.builder.build_contract()
    )
    clock_histories = [
        response.diagnostic_trace.get("virtual_clock") for response in responses
    ]
    simulation_valid = (
        len(responses) == context.case_count
        and all(response.operational_status == "completed" for response in responses)
        and sum(response.provider_calls for response in responses) == 0
        and all(isinstance(history, dict) for history in clock_histories)
        and proactive_case_count == 220
    )
    return {
        "instrument_id": context.instrument_id,
        "status": "passed-network-free-simulation"
        if simulation_valid
        else "failed-network-free-simulation",
        "case_count": len(responses),
        "summary": summary,
        "condition_summaries": {
            condition: summarize_autonomy_scores(rows)
            for condition, rows in condition_scores.items()
        },
        "clock_history_count": len(clock_histories),
        "proactive_case_count": proactive_case_count,
        "provider_calls": 0,
        "cost_usd": 0,
        "product_quality_claim": False,
    }


def simulate(
    context: ActualProductEvaluationContext = DEFAULT_CONTEXT,
) -> dict[str, Any]:
    return asyncio.run(_simulate(context))


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
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
        result = simulate()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
