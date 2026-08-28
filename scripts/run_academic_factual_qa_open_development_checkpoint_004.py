#!/usr/bin/env python3
"""Run the finite deterministic-primary OpenAI 500+100 checkpoint."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from typing import Any, Iterator

from dotenv import load_dotenv

from scripts import academic_factual_qa_open_10000_t0_adapter as adapter
from scripts import run_academic_factual_qa_open_10000 as product
from scripts import run_academic_factual_qa_open_advisory_audit_004 as advisory
from scripts import run_academic_factual_qa_open_wording as wording
from scripts import score_academic_factual_qa_open_10000 as scorer
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.provider_json import canonical_sha256
from src.digital_twin.repository_freeze import (
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-checkpoint-004"
BINDING_ID = "academic-factual-qa-open-10000-openai-binding-005"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_checkpoint_004.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_005.json"
)
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
GENERATED = ROOT / "reports/generated"
SOURCE_CASES = DATASET_ROOT / "academic_factual_qa_open_10000_v1_development_cases_002.json"
SOURCE_GOLD = DATASET_ROOT / "academic_factual_qa_open_10000_v1_development_gold_002.json"
SOURCE_CONTROL_CASES = DATASET_ROOT / (
    "academic_factual_qa_open_10000_v1_development_control_cases_002.json"
)
SOURCE_CONTROL_GOLD = DATASET_ROOT / (
    "academic_factual_qa_open_10000_v1_development_control_gold_002.json"
)
WORDING_LEDGER = GENERATED / "academic-factual-qa-open-10000-wording-development-004.sqlite3"
WORDING_RESULT = GENERATED / "academic-factual-qa-open-10000-wording-development-004-result.json"
CANDIDATE_CASES = GENERATED / "academic-factual-qa-open-10000-v1-development-004-cases.json"
CANDIDATE_GOLD = GENERATED / "academic-factual-qa-open-10000-v1-development-004-gold.json"
CONTROL_CASES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-control-004-cases.json"
)
CONTROL_GOLD = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-control-004-gold.json"
)
CANDIDATE_MANIFEST = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_candidate_manifest_004.json"
)
CONTROL_MANIFEST = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_control_manifest_004.json"
)
CANDIDATE_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-candidate-responses.sqlite3"
)
CANDIDATE_PROVIDER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-candidate-provider.sqlite3"
)
CANDIDATE_STATE = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-candidate-state.sqlite3"
)
CONTROL_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-control-responses.sqlite3"
)
CONTROL_PROVIDER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-control-provider.sqlite3"
)
CONTROL_STATE = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-control-state.sqlite3"
)
CANDIDATE_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-candidate-result.json"
)
PAIRED_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-paired-result.json"
)
CHECKPOINT_STATE = GENERATED / (
    "academic-factual-qa-open-10000-development-checkpoint-004-state.json"
)
RUNTIME_PACKAGES = (CANDIDATE_CASES, CANDIDATE_GOLD, CONTROL_CASES, CONTROL_GOLD)
PROVIDER_LEDGERS = (
    WORDING_LEDGER,
    CANDIDATE_PROVIDER,
    CONTROL_PROVIDER,
    advisory.LEDGER_PATH,
)
PRODUCT_CONFIG = {
    "candidate": (CANDIDATE_CASES, CANDIDATE_MANIFEST, CANDIDATE_RESPONSES, CANDIDATE_PROVIDER, CANDIDATE_STATE, 500),
    "control": (CONTROL_CASES, CONTROL_MANIFEST, CONTROL_RESPONSES, CONTROL_PROVIDER, CONTROL_STATE, 100),
}
ALL_OUTPUTS = (
    CHECKPOINT_STATE,
    WORDING_LEDGER,
    WORDING_RESULT,
    *RUNTIME_PACKAGES,
    CANDIDATE_RESPONSES,
    CANDIDATE_PROVIDER,
    CANDIDATE_STATE,
    CONTROL_RESPONSES,
    CONTROL_PROVIDER,
    CONTROL_STATE,
    CANDIDATE_RESULT,
    PAIRED_RESULT,
    advisory.LEDGER_PATH,
    advisory.RESULT_PATH,
)


class DevelopmentCheckpointError(RuntimeError):
    """Raised when the finite checkpoint violates its prospective contract."""


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


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise DevelopmentCheckpointError(f"exclusive output path is used: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_state(state: dict[str, Any], *, exclusive: bool = False) -> None:
    CHECKPOINT_STATE.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and CHECKPOINT_STATE.exists():
        raise DevelopmentCheckpointError("exclusive checkpoint state path is used")
    temporary = CHECKPOINT_STATE.with_name(f"{CHECKPOINT_STATE.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, CHECKPOINT_STATE)


@contextmanager
def configured_wording() -> Iterator[None]:
    configuration = {
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "BINDING_ID": BINDING_ID,
        "INSTRUMENT_PATH": INSTRUMENT_PATH,
        "BINDING_PATH": BINDING_PATH,
        "LEDGER_PATH": WORDING_LEDGER,
        "RESULT_PATH": WORDING_RESULT,
    }
    previous = {name: getattr(wording, name) for name in configuration}
    try:
        for name, value in configuration.items():
            setattr(wording, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(wording, name, value)


@contextmanager
def configured_product() -> Iterator[None]:
    previous = {
        "INSTRUMENT_ID": product.INSTRUMENT_ID,
        "INSTRUMENT_PATH": product.INSTRUMENT_PATH,
        "PROVIDER_BINDING_PATH": product.PROVIDER_BINDING_PATH,
    }
    adapter_previous = adapter.OPENAI_BINDING_PATH
    try:
        product.INSTRUMENT_ID = INSTRUMENT_ID
        product.INSTRUMENT_PATH = INSTRUMENT_PATH
        product.PROVIDER_BINDING_PATH = BINDING_PATH
        adapter.OPENAI_BINDING_PATH = BINDING_PATH
        yield
    finally:
        for name, value in previous.items():
            setattr(product, name, value)
        adapter.OPENAI_BINDING_PATH = adapter_previous


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


def _validate_package(path: Path, *, rows_key: str) -> dict[str, Any]:
    value = _load(path)
    expected = canonical_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise DevelopmentCheckpointError(f"package hash drifted: {path.name}")
    if value.get("case_count") != len(value.get(rows_key, [])):
        raise DevelopmentCheckpointError(f"package count drifted: {path.name}")
    return value


def _package(*, dataset_id: str, split: str, key: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "split": split,
        "case_count": len(rows),
        key: rows,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    return payload


def build_runtime_packages(wording_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if wording_result.get("instrument_id") != INSTRUMENT_ID:
        raise DevelopmentCheckpointError("wording result identity drifted")
    if wording_result.get("status") != "completed-go-deeper":
        raise DevelopmentCheckpointError("wording did not pass")
    cases = [EvaluationCaseV1.model_validate(row) for row in wording_result.get("cases", [])]
    if len(cases) != 500 or len({row.case_id for row in cases}) != 500:
        raise DevelopmentCheckpointError("wording case coverage drifted")
    source_gold = _validate_package(SOURCE_GOLD, rows_key="gold")
    gold = [EvaluationGoldV1.model_validate(row) for row in source_gold["gold"]]
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise DevelopmentCheckpointError("wording and hidden-gold identities drifted")
    control_cases = _validate_package(SOURCE_CONTROL_CASES, rows_key="cases")
    control_gold = _validate_package(SOURCE_CONTROL_GOLD, rows_key="gold")
    control_ids = [row["case_id"] for row in control_cases["cases"]]
    if len(control_ids) != 100 or len(set(control_ids)) != 100:
        raise DevelopmentCheckpointError("control identities drifted")
    if set(control_ids) != {row["case_id"] for row in control_gold["gold"]}:
        raise DevelopmentCheckpointError("control case/gold pairing drifted")
    case_by_id = {row.case_id: row for row in cases}
    gold_by_id = {row.case_id: row for row in gold}
    candidate_id = "academic-factual-qa-open-10000-v1-development-004"
    control_id = "academic-factual-qa-open-10000-v1-development-control-004"
    return {
        "candidate_cases": _package(
            dataset_id=candidate_id,
            split="development",
            key="cases",
            rows=[row.model_dump(mode="json") for row in cases],
        ),
        "candidate_gold": _package(
            dataset_id=candidate_id,
            split="development",
            key="gold",
            rows=[row.model_dump(mode="json") for row in gold],
        ),
        "control_cases": _package(
            dataset_id=control_id,
            split="development-control",
            key="cases",
            rows=[case_by_id[case_id].model_dump(mode="json") for case_id in control_ids],
        ),
        "control_gold": _package(
            dataset_id=control_id,
            split="development-control",
            key="gold",
            rows=[gold_by_id[case_id].model_dump(mode="json") for case_id in control_ids],
        ),
    }


def write_runtime_packages() -> dict[str, Any]:
    packages = build_runtime_packages(_load(WORDING_RESULT))
    outputs = {
        CANDIDATE_CASES: packages["candidate_cases"],
        CANDIDATE_GOLD: packages["candidate_gold"],
        CONTROL_CASES: packages["control_cases"],
        CONTROL_GOLD: packages["control_gold"],
    }
    if any(path.exists() for path in outputs):
        raise DevelopmentCheckpointError("one or more runtime package outputs already exist")
    for path, payload in outputs.items():
        _write_json_exclusive(path, payload)
    return {"status": "completed", "candidate_case_count": 500, "control_case_count": 100}


def _response_complete(path: Path, count: int) -> bool:
    if not path.is_file():
        return False
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    finally:
        connection.close()
    return metadata.get("status") == "completed" and metadata.get("response_count") == str(count)


def _require_response_complete(path: Path, count: int) -> None:
    if not _response_complete(path, count):
        raise DevelopmentCheckpointError(f"response ledger is incomplete: {path.name}")


def validate(*, require_unauthorized: bool = True) -> dict[str, Any]:
    instrument = _load_hashed(INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID)
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    expected_stages = [
        "question-wording",
        "candidate-500",
        "control-100",
        "deterministic-score-and-compare",
        "non-blocking-advisory-audit",
    ]
    if instrument["combined_checkpoint"]["stage_order"] != expected_stages:
        raise DevelopmentCheckpointError("checkpoint stage order drifted")
    if instrument["combined_checkpoint"]["maximum_calls"] != 704:
        raise DevelopmentCheckpointError("checkpoint call ceiling drifted")
    if instrument["combined_checkpoint"]["maximum_cost_usd"] != 23.0:
        raise DevelopmentCheckpointError("checkpoint cost ceiling drifted")
    with configured_wording():
        wording_result = wording.validate(require_unauthorized=require_unauthorized)
    with configured_product():
        product_result = product.validate_contract()
        manifests = [product._load_manifest(path) for path in (CANDIDATE_MANIFEST, CONTROL_MANIFEST)]  # noqa: SLF001
    with configured_scorer():
        scoring_result = scorer.simulate()
    advisory_result = advisory.validate(require_unauthorized=require_unauthorized)
    if not all(manifest.generator == "openai-gpt-5.4-mini-live-atomic" for manifest in manifests):
        raise DevelopmentCheckpointError("product generator manifest drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "binding_id": BINDING_ID,
        "status": "passed-build-only",
        "stage_statuses": {
            "wording": wording_result["status"],
            "product": product_result["status"],
            "scoring": scoring_result["status"],
            "advisory": advisory_result["status"],
        },
        "maximum_calls": 704,
        "maximum_cost_usd": 23.0,
        "provider_calls": 0,
        "deterministic_scoring_authoritative": True,
        "advisory_failure_invalidates_deterministic_measurement": False,
        "final_execution_authorized": False,
        "binding_hash": binding["content_sha256"],
    }


def simulate(*, scenario: str) -> dict[str, Any]:
    if scenario not in {"pass", "wording-failure", "product-failure", "advisory-malformed", "truth-defect"}:
        raise ValueError(f"unknown simulation scenario: {scenario}")
    if scenario == "wording-failure":
        completed = ["question-wording"]
        status = "completed-refine"
    else:
        completed = [
            "question-wording",
            "runtime-package-materialization",
            "candidate-500",
            "control-100",
            "deterministic-score-and-compare",
            "non-blocking-advisory-audit",
        ]
        if scenario == "product-failure":
            status = "completed-refine"
        elif scenario == "truth-defect":
            status = "needs-human-review"
        else:
            status = "completed-keep"
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "completed_stages": completed,
        "advisory_limitation_count": 1 if scenario == "advisory-malformed" else 0,
        "deterministic_result_changed_by_advisory": False,
        "provider_calls": 0,
        "network_accessed": False,
        "final_execution_authorized": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _load_hashed(INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID)
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    blockers: list[str] = []
    try:
        validate(require_unauthorized=False)
    except Exception as error:  # noqa: BLE001
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
        "wording_development_execution_authorized",
        "product_development_execution_authorized",
        "semantic_review_execution_authorized",
    )
    for label, record in (("instrument", instrument), ("binding", binding)):
        for key in required:
            if not record["authorization"][key]:
                blockers.append(f"{label}-{key.replace('_', '-')}-false")
    for key in ("provider_execution_authorized", "paid_execution_authorized", "development_execution_authorized"):
        if not instrument["execution"][key]:
            blockers.append(f"execution-{key.replace('_', '-')}-false")
    if instrument["authorization"]["final_execution_authorized"] or instrument["execution"]["final_execution_authorized"]:
        blockers.append("final-execution-must-remain-unauthorized")
    verified_at = datetime.fromisoformat(binding["verified_at"])
    age = (datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)).total_seconds() / 3600
    if age < 0 or age > binding["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if resume:
        if not CHECKPOINT_STATE.is_file():
            blockers.append("resume-state-missing")
    else:
        used = sorted(path.name for path in ALL_OUTPUTS if path.exists())
        if used:
            blockers.append("exclusive-output-path-used:" + ",".join(used))
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
        "credential_values_emitted": False,
        "maximum_calls": 704,
        "maximum_cost_usd": 23.0,
        "final_execution_authorized": False,
    }


def _initial_state(instrument: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "binding_id": BINDING_ID,
        "binding_sha256": binding["content_sha256"],
        "code_revision": _repo_revision(),
        "status": "running",
        "current_stage": "question-wording",
        "completed_stages": [],
        "terminal_result": None,
    }


def _resume_state(instrument: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    if not CHECKPOINT_STATE.is_file():
        raise DevelopmentCheckpointError("checkpoint resume state is missing")
    state = _load(CHECKPOINT_STATE)
    expected = {
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "binding_id": BINDING_ID,
        "binding_sha256": binding["content_sha256"],
        "code_revision": _repo_revision(),
    }
    if any(state.get(key) != value for key, value in expected.items()):
        raise DevelopmentCheckpointError("checkpoint resume binding drifted")
    if state.get("status") not in {"running", "interrupted"}:
        raise DevelopmentCheckpointError("checkpoint resume state is terminal")
    state["status"] = "running"
    return state


def _complete_stage(state: dict[str, Any], stage: str, next_stage: str | None) -> None:
    if stage not in state["completed_stages"]:
        state["completed_stages"].append(stage)
    state["current_stage"] = next_stage
    _write_state(state)


def _terminal(state: dict[str, Any], status: str, result: dict[str, Any]) -> dict[str, Any]:
    state["status"] = status
    state["current_stage"] = None
    state["terminal_result"] = result
    _write_state(state)
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "completed_stages": state["completed_stages"],
        "terminal_result": result,
    }


async def _execute_product(condition: str, *, resume: bool) -> None:
    cases_path, manifest, responses, provider_ledger, state_path, _ = PRODUCT_CONFIG[condition]
    with configured_product():
        readiness = product.preflight(
            stage="development",
            cases_path=cases_path,
            manifest_path=manifest,
            output=responses,
            provider_ledger=provider_ledger,
            state_path=state_path,
            resume=resume,
        )
        if readiness["status"] != "ready":
            raise DevelopmentCheckpointError(f"{condition} preflight blocked: {readiness['blockers']}")
        await product.execute(
            cases_path=cases_path,
            manifest_path=manifest,
            output=responses,
            adapter_factory="scripts.academic_factual_qa_open_10000_t0_adapter:build_live_t0_adapter",
            provider_ledger=provider_ledger,
            state_path=state_path,
            resume=resume,
        )


def _score() -> dict[str, Any]:
    _require_response_complete(CANDIDATE_RESPONSES, 500)
    _require_response_complete(CONTROL_RESPONSES, 100)
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
        gates = _load(INSTRUMENT_PATH)["hard_gates"]
        paired = scorer.paired_comparison(
            candidate,
            control,
            lower_delta_gate=gates["paired_supported_retention_delta_lower_95_min"],
            boundary_not_worse=gates["paired_boundary_safety_not_worse"],
        )
    _write_json_exclusive(CANDIDATE_RESULT, candidate)
    _write_json_exclusive(PAIRED_RESULT, paired)
    return paired


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


async def execute(*, resume: bool = False) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise DevelopmentCheckpointError("checkpoint preflight is blocked: " + ", ".join(readiness["blockers"]))
    instrument = _load_hashed(INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID)
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    state = _resume_state(instrument, binding) if resume else _initial_state(instrument, binding)
    if not resume:
        _write_state(state, exclusive=True)
    try:
        if "question-wording" not in state["completed_stages"]:
            with configured_wording():
                if not WORDING_RESULT.exists():
                    await wording.execute(resume=WORDING_LEDGER.exists())
                    wording_result = wording.score()
                else:
                    wording_result = _load(WORDING_RESULT)
            _complete_stage(state, "question-wording", "runtime-package-materialization")
            if wording_result.get("status") != "completed-go-deeper":
                return _terminal(state, "completed-refine", wording_result)

        if "runtime-package-materialization" not in state["completed_stages"]:
            if all(path.exists() for path in RUNTIME_PACKAGES):
                pass
            elif any(path.exists() for path in RUNTIME_PACKAGES):
                return _terminal(state, "invalid-execution", {"stage": "runtime-package-materialization", "failure_type": "PartialOutput"})
            else:
                write_runtime_packages()
            _complete_stage(state, "runtime-package-materialization", "candidate-500")

        for condition, stage, next_stage in (
            ("candidate", "candidate-500", "control-100"),
            ("control", "control-100", "deterministic-score-and-compare"),
        ):
            if stage in state["completed_stages"]:
                continue
            _, _, responses, provider_ledger, state_path, count = PRODUCT_CONFIG[condition]
            if not _response_complete(responses, count):
                await _execute_product(
                    condition,
                    resume=any(path.exists() for path in (responses, provider_ledger, state_path)),
                )
            _require_response_complete(responses, count)
            _complete_stage(state, stage, next_stage)

        if "deterministic-score-and-compare" not in state["completed_stages"]:
            paired = _load(PAIRED_RESULT) if PAIRED_RESULT.exists() else _score()
            _complete_stage(state, "deterministic-score-and-compare", "non-blocking-advisory-audit")
        else:
            paired = _load(PAIRED_RESULT)

        if "non-blocking-advisory-audit" not in state["completed_stages"]:
            audit_result = (
                _load(advisory.RESULT_PATH)
                if advisory.RESULT_PATH.exists()
                else await advisory.execute(resume=advisory.LEDGER_PATH.exists())
            )
            _complete_stage(state, "non-blocking-advisory-audit", "accounting-check")
        else:
            audit_result = _load(advisory.RESULT_PATH)

        calls, cost = _provider_totals()
        if calls > instrument["combined_checkpoint"]["maximum_calls"] or cost > instrument["combined_checkpoint"]["maximum_cost_usd"]:
            return _terminal(
                state,
                "invalid-execution",
                {"stage": "accounting-check", "provider_calls": calls, "reported_cost_usd": cost},
            )
        final_status = "needs-human-review" if audit_result["potential_truth_defect_count"] else paired["status"]
        result = {
            "status": final_status,
            "deterministic_status": paired["status"],
            "decision": paired["decision"],
            "failed_gates": paired["failed_gates"],
            "advisory_status": audit_result["status"],
            "advisory_limitation_count": audit_result["limitation_count"],
            "potential_truth_defect_case_ids": audit_result["potential_truth_defect_case_ids"],
            "deterministic_result_changed_by_advisory": False,
            "provider_calls": calls,
            "reported_cost_usd": cost,
            "final_execution_authorized": False,
        }
        return _terminal(state, final_status, result)
    except KeyboardInterrupt:
        state["status"] = "interrupted"
        _write_state(state)
        raise
    except Exception as error:  # noqa: BLE001 - preserve terminal harness evidence
        return _terminal(
            state,
            "invalid-execution",
            {"stage": state.get("current_stage"), "failure_type": type(error).__name__, "failure_detail": str(error)[:300]},
        )


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument(
        "--simulate",
        choices=("pass", "wording-failure", "product-failure", "advisory-malformed", "truth-defect"),
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
    if arguments.validate:
        result = validate()
    elif arguments.simulate:
        result = simulate(scenario=arguments.simulate)
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    else:
        result = asyncio.run(execute(resume=arguments.resume))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
