#!/usr/bin/env python3
"""Run the product-only mixed-wording 500+100 T0 development checkpoint."""

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
from scripts import build_academic_factual_qa_open_mixed_wording_005 as materializer
from scripts import run_academic_factual_qa_open_10000 as product
from scripts import run_academic_factual_qa_open_advisory_audit_004 as advisory
from scripts import score_academic_factual_qa_open_10000 as scorer
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonResponse,
    canonical_sha256,
)
from src.digital_twin.repository_freeze import (
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-product-checkpoint-005"
BINDING_ID = "academic-factual-qa-open-10000-openai-binding-006"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_product_checkpoint_005.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_006.json"
)
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
GENERATED = ROOT / "reports/generated"
CANDIDATE_CASES = materializer.CANDIDATE_CASES
CONTROL_CASES = materializer.CONTROL_CASES
WORDING_PROVENANCE = materializer.PROVENANCE
CANDIDATE_GOLD = DATASET_ROOT / (
    "academic_factual_qa_open_10000_v1_development_gold_002.json"
)
CONTROL_GOLD = DATASET_ROOT / (
    "academic_factual_qa_open_10000_v1_development_control_gold_002.json"
)
CANDIDATE_MANIFEST = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_candidate_manifest_005.json"
)
CONTROL_MANIFEST = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_control_manifest_005.json"
)
CANDIDATE_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-candidate-responses.sqlite3"
)
CANDIDATE_PROVIDER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-candidate-provider.sqlite3"
)
CANDIDATE_STATE = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-candidate-state.sqlite3"
)
CONTROL_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-control-responses.sqlite3"
)
CONTROL_PROVIDER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-control-provider.sqlite3"
)
CONTROL_STATE = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-control-state.sqlite3"
)
CANDIDATE_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-candidate-result.json"
)
PAIRED_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-paired-result.json"
)
ADVISORY_LEDGER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-advisory-audit.sqlite3"
)
ADVISORY_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-advisory-audit-result.json"
)
CRITICAL_REVIEW_LEDGER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-critical-review.sqlite3"
)
CRITICAL_REVIEW_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-005-critical-review-result.json"
)
CHECKPOINT_STATE = GENERATED / (
    "academic-factual-qa-open-10000-development-product-checkpoint-005-state.json"
)
PRODUCT_CONFIG = {
    "candidate": (
        CANDIDATE_CASES,
        CANDIDATE_MANIFEST,
        CANDIDATE_RESPONSES,
        CANDIDATE_PROVIDER,
        CANDIDATE_STATE,
        500,
    ),
    "control": (
        CONTROL_CASES,
        CONTROL_MANIFEST,
        CONTROL_RESPONSES,
        CONTROL_PROVIDER,
        CONTROL_STATE,
        100,
    ),
}
PROVIDER_LEDGERS = (
    CANDIDATE_PROVIDER,
    CONTROL_PROVIDER,
    ADVISORY_LEDGER,
    CRITICAL_REVIEW_LEDGER,
)
ALL_OUTPUTS = (
    CHECKPOINT_STATE,
    CANDIDATE_RESPONSES,
    CANDIDATE_PROVIDER,
    CANDIDATE_STATE,
    CONTROL_RESPONSES,
    CONTROL_PROVIDER,
    CONTROL_STATE,
    CANDIDATE_RESULT,
    PAIRED_RESULT,
    ADVISORY_LEDGER,
    ADVISORY_RESULT,
    CRITICAL_REVIEW_LEDGER,
    CRITICAL_REVIEW_RESULT,
)


class ProductCheckpointError(RuntimeError):
    """Raised when product checkpoint 005 violates its frozen contract."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProductCheckpointError(f"JSON root is not an object: {path.name}")
    return value


def _load_hashed(path: Path, *, key: str, identity: str) -> dict[str, Any]:
    value = _load(path)
    if value.get(key) != identity:
        raise ProductCheckpointError(f"identity drifted: {path.name}")
    expected = canonical_sha256(
        {field: row for field, row in value.items() if field != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise ProductCheckpointError(f"content hash drifted: {path.name}")
    return value


def _validated_package(
    path: Path, *, rows_key: str, expected_hash: str, expected_count: int
) -> dict[str, Any]:
    value = _load(path)
    actual = canonical_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != actual or actual != expected_hash:
        raise ProductCheckpointError(f"package hash drifted: {path.name}")
    rows = value.get(rows_key)
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise ProductCheckpointError(f"package count drifted: {path.name}")
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


def _write_state(state: dict[str, Any], *, exclusive: bool = False) -> None:
    CHECKPOINT_STATE.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and CHECKPOINT_STATE.exists():
        raise ProductCheckpointError("exclusive checkpoint state path is used")
    temporary = CHECKPOINT_STATE.with_name(f"{CHECKPOINT_STATE.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, CHECKPOINT_STATE)


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise ProductCheckpointError(f"exclusive output path is used: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def configured_product() -> Iterator[None]:
    previous = {
        "INSTRUMENT_ID": product.INSTRUMENT_ID,
        "INSTRUMENT_PATH": product.INSTRUMENT_PATH,
        "PROVIDER_BINDING_PATH": product.PROVIDER_BINDING_PATH,
    }
    adapter_previous = {
        "OPENAI_BINDING_PATH": adapter.OPENAI_BINDING_PATH,
        "PRODUCT_MAXIMUM_CALLS": adapter.PRODUCT_MAXIMUM_CALLS,
        "PRODUCT_MAXIMUM_COST_USD": adapter.PRODUCT_MAXIMUM_COST_USD,
    }
    try:
        product.INSTRUMENT_ID = INSTRUMENT_ID
        product.INSTRUMENT_PATH = INSTRUMENT_PATH
        product.PROVIDER_BINDING_PATH = BINDING_PATH
        adapter.OPENAI_BINDING_PATH = BINDING_PATH
        adapter.PRODUCT_MAXIMUM_CALLS = {"candidate": 500, "control": 100}
        adapter.PRODUCT_MAXIMUM_COST_USD = {"candidate": 5.0, "control": 1.0}
        yield
    finally:
        for name, value in previous.items():
            setattr(product, name, value)
        for name, value in adapter_previous.items():
            setattr(adapter, name, value)


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


@contextmanager
def configured_advisory() -> Iterator[None]:
    configuration = {
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "BINDING_ID": BINDING_ID,
        "INSTRUMENT_PATH": INSTRUMENT_PATH,
        "BINDING_PATH": BINDING_PATH,
        "CASES_PATH": CANDIDATE_CASES,
        "GOLD_PATH": CANDIDATE_GOLD,
        "RESPONSES_PATH": CANDIDATE_RESPONSES,
        "DETERMINISTIC_RESULT_PATH": CANDIDATE_RESULT,
        "LEDGER_PATH": ADVISORY_LEDGER,
        "RESULT_PATH": ADVISORY_RESULT,
        "REVIEWER_ROLE": "routine-advisory-reviewer",
    }
    previous = {name: getattr(advisory, name) for name in configuration}
    try:
        for name, value in configuration.items():
            setattr(advisory, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(advisory, name, value)


def validate(*, require_unauthorized: bool = True) -> dict[str, Any]:
    instrument = _load_hashed(INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID)
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    package_result = materializer.check()
    dataset = instrument["dataset"]
    candidate = _validated_package(
        CANDIDATE_CASES,
        rows_key="cases",
        expected_hash=dataset["public_cases_content_sha256"],
        expected_count=500,
    )
    control = _validated_package(
        CONTROL_CASES,
        rows_key="cases",
        expected_hash=dataset["control_cases_content_sha256"],
        expected_count=100,
    )
    candidate_gold = _validated_package(
        CANDIDATE_GOLD,
        rows_key="gold",
        expected_hash=dataset["hidden_gold_content_sha256"],
        expected_count=500,
    )
    control_gold = _validated_package(
        CONTROL_GOLD,
        rows_key="gold",
        expected_hash=dataset["control_gold_content_sha256"],
        expected_count=100,
    )
    candidate_ids = {row["case_id"] for row in candidate["cases"]}
    control_ids = {row["case_id"] for row in control["cases"]}
    if candidate_ids != {row["case_id"] for row in candidate_gold["gold"]}:
        raise ProductCheckpointError("candidate public/gold identities drifted")
    if control_ids != {row["case_id"] for row in control_gold["gold"]}:
        raise ProductCheckpointError("control public/gold identities drifted")
    if not control_ids < candidate_ids:
        raise ProductCheckpointError("control is not a strict candidate subset")
    if instrument["combined_checkpoint"]["stage_order"] != [
        "candidate-500",
        "control-100",
        "deterministic-score-and-compare",
        "routine-nano-advisory-audit",
        "bounded-critical-truth-escalation",
    ]:
        raise ProductCheckpointError("checkpoint stage order drifted")
    if instrument["combined_checkpoint"]["maximum_calls"] != 666:
        raise ProductCheckpointError("checkpoint call ceiling drifted")
    if instrument["combined_checkpoint"]["maximum_cost_usd"] != 8.0:
        raise ProductCheckpointError("checkpoint cost ceiling drifted")
    if instrument["method"]["wording_provider_calls"] != 0:
        raise ProductCheckpointError("successor attempted to reopen wording calls")
    with configured_product():
        product_result = product.validate_contract()
        manifests = [
            product._load_manifest(path)  # noqa: SLF001
            for path in (CANDIDATE_MANIFEST, CONTROL_MANIFEST)
        ]
    with configured_scorer():
        scoring_result = scorer.simulate()
    with configured_advisory():
        advisory_result = advisory.validate(require_unauthorized=require_unauthorized)
    providers = binding["providers"]
    expected_models = {
        "high-volume-generator": "gpt-5.4-mini-2026-03-17",
        "routine-advisory-reviewer": "gpt-5.4-nano-2026-03-17",
        "critical-truth-reviewer": "gpt-5.4-2026-03-05",
    }
    if {
        role: providers[role]["provider_model"] for role in expected_models
    } != expected_models:
        raise ProductCheckpointError("OpenAI model cascade drifted")
    critical_transport = DirectProviderJsonTransport(
        providers["critical-truth-reviewer"]
    )
    critical_payload = critical_transport._payload(  # noqa: SLF001
        system="Review one possible source-truth defect.",
        prompt="{}",
        task="network-free-critical-truth-review",
        schema=advisory._schema(1),  # noqa: SLF001
    )
    if critical_payload.get("store") is not False:
        raise ProductCheckpointError("critical reviewer store policy drifted")
    if not all(row.generator == "openai-gpt-5.4-mini-live-atomic" for row in manifests):
        raise ProductCheckpointError("product generator manifest drifted")
    if manifests[0].evidence_gate != "structured-lexical-coverage-evidence-gate-v1":
        raise ProductCheckpointError("candidate evidence gate drifted")
    if manifests[1].evidence_gate != "any-hit-evidence-gate-v1":
        raise ProductCheckpointError("control evidence gate drifted")
    if require_unauthorized:
        if any(instrument["authorization"].values()) or any(binding["authorization"].values()):
            raise ProductCheckpointError("build-only provider authority drifted")
        if any(
            instrument["execution"][key]
            for key in (
                "provider_execution_authorized",
                "paid_execution_authorized",
                "development_execution_authorized",
                "final_execution_authorized",
            )
        ):
            raise ProductCheckpointError("build-only execution authority drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "binding_id": BINDING_ID,
        "status": "passed-build-only",
        "case_count": package_result["case_count"],
        "control_case_count": package_result["control_case_count"],
        "accepted_model_wording_count": package_result["accepted_model_wording_count"],
        "canonical_fallback_count": package_result["canonical_fallback_count"],
        "stage_statuses": {
            "product": product_result["status"],
            "scoring": scoring_result["status"],
            "advisory": advisory_result["status"],
        },
        "maximum_calls": 666,
        "maximum_cost_usd": 8.0,
        "wording_provider_calls": 0,
        "provider_calls": 0,
        "deterministic_scoring_authoritative": True,
        "advisory_failure_invalidates_deterministic_measurement": False,
        "hidden_gold_visible_to_product": False,
        "final_execution_authorized": False,
        "binding_hash": binding["content_sha256"],
    }


def simulate(*, scenario: str) -> dict[str, Any]:
    if scenario not in {
        "pass",
        "product-failure",
        "provider-failure",
        "advisory-malformed",
        "truth-defect",
    }:
        raise ValueError(f"unknown simulation scenario: {scenario}")
    completed = [
        "candidate-500",
        "control-100",
        "deterministic-score-and-compare",
        "routine-nano-advisory-audit",
        "bounded-critical-truth-escalation",
    ]
    if scenario == "provider-failure":
        status = "invalid-execution"
        completed = []
    elif scenario == "product-failure":
        status = "completed-refine"
    elif scenario == "truth-defect":
        status = "needs-human-review"
    else:
        status = "completed-keep"
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "completed_stages": completed,
        "wording_provider_calls": 0,
        "advisory_limitation_count": 1 if scenario == "advisory-malformed" else 0,
        "critical_escalation_case_count": 1 if scenario == "truth-defect" else 0,
        "deterministic_result_changed_by_advisory": False,
        "provider_calls": 0,
        "network_accessed": False,
        "hidden_gold_visible_to_product": False,
        "final_execution_authorized": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _load_hashed(INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID)
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    blockers: list[str] = []
    try:
        validate(require_unauthorized=False)
    except Exception as error:  # noqa: BLE001 - report every preflight blocker
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
        "product_development_execution_authorized",
        "semantic_review_execution_authorized",
    )
    for label, record in (("instrument", instrument), ("binding", binding)):
        for key in required:
            if not record["authorization"][key]:
                blockers.append(f"{label}-{key.replace('_', '-')}-false")
    for key in (
        "provider_execution_authorized",
        "paid_execution_authorized",
        "development_execution_authorized",
    ):
        if not instrument["execution"][key]:
            blockers.append(f"execution-{key.replace('_', '-')}-false")
    if instrument["authorization"]["final_execution_authorized"] or instrument["execution"]["final_execution_authorized"]:
        blockers.append("final-execution-must-remain-unauthorized")
    verified_at = datetime.fromisoformat(binding["verified_at"])
    age = (
        datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)
    ).total_seconds() / 3600
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
        "wording_provider_calls": 0,
        "credential_values_emitted": False,
        "maximum_calls": 666,
        "maximum_cost_usd": 8.0,
        "final_execution_authorized": False,
    }


def _initial_state(instrument: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "binding_id": BINDING_ID,
        "binding_sha256": binding["content_sha256"],
        "candidate_cases_sha256": instrument["dataset"]["public_cases_content_sha256"],
        "control_cases_sha256": instrument["dataset"]["control_cases_content_sha256"],
        "wording_provenance_sha256": instrument["dataset"]["wording_provenance_content_sha256"],
        "code_revision": _repo_revision(),
        "status": "running",
        "current_stage": "candidate-500",
        "completed_stages": [],
        "terminal_result": None,
    }


def _resume_state(instrument: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    if not CHECKPOINT_STATE.is_file():
        raise ProductCheckpointError("checkpoint resume state is missing")
    state = _load(CHECKPOINT_STATE)
    expected = _initial_state(instrument, binding)
    for key in (
        "instrument_id",
        "instrument_sha256",
        "binding_id",
        "binding_sha256",
        "candidate_cases_sha256",
        "control_cases_sha256",
        "wording_provenance_sha256",
        "code_revision",
    ):
        if state.get(key) != expected[key]:
            raise ProductCheckpointError("checkpoint resume binding drifted")
    if state.get("status") not in {"running", "interrupted"}:
        raise ProductCheckpointError("checkpoint resume state is terminal")
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
        raise ProductCheckpointError(f"response ledger is incomplete: {path.name}")


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
            raise ProductCheckpointError(
                f"{condition} preflight blocked: {readiness['blockers']}"
            )
        await product.execute(
            cases_path=cases_path,
            manifest_path=manifest,
            output=responses,
            adapter_factory=(
                "scripts.academic_factual_qa_open_10000_t0_adapter:"
                "build_live_t0_adapter"
            ),
            provider_ledger=provider_ledger,
            state_path=state_path,
            resume=resume,
        )


def _score() -> dict[str, Any]:
    _require_response_complete(CANDIDATE_RESPONSES, 500)
    _require_response_complete(CONTROL_RESPONSES, 100)
    # Hidden gold is first opened here, after both public-response ledgers are durable.
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


def _critical_review_rows(case_ids: list[str]) -> list[dict[str, Any]]:
    rows, _, _ = advisory.build_audit_rows()
    rows_by_id = {row["case_id"]: row for row in rows}
    missing = sorted(set(case_ids) - set(rows_by_id))
    if missing:
        raise ProductCheckpointError(
            "critical review selection escaped the routine audit: " + ",".join(missing)
        )
    return [rows_by_id[case_id] for case_id in case_ids]


def _score_critical_review(
    *, selected_ids: list[str], overflow_ids: list[str], reviewer_model: str
) -> dict[str, Any]:
    reviews: list[dict[str, Any]] = []
    limitations: list[dict[str, str]] = []
    if CRITICAL_REVIEW_LEDGER.is_file():
        connection = sqlite3.connect(
            f"file:{CRITICAL_REVIEW_LEDGER}?mode=ro", uri=True
        )
        try:
            calls = connection.execute(
                "SELECT status,response_json,failure_type,failure_detail "
                "FROM calls ORDER BY sequence"
            ).fetchall()
        finally:
            connection.close()
        for status, response_json, failure_type, failure_detail in calls:
            if status == "completed" and response_json:
                response = ProviderJsonResponse.model_validate_json(response_json)
                reviews.extend(response.content["items"])
            elif status == "failed":
                limitations.append(
                    {
                        "failure_type": str(failure_type),
                        "failure_detail": str(failure_detail)[:240],
                    }
                )
    reviewed_ids = {row["case_id"] for row in reviews}
    missing_ids = sorted(set(selected_ids) - reviewed_ids)
    confirmed_ids = sorted(
        row["case_id"]
        for row in reviews
        if row["potential_authoritative_truth_defect"]
    )
    unresolved_ids = sorted(set(overflow_ids + missing_ids + confirmed_ids))
    payload = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": "needs-human-review" if unresolved_ids else "completed",
        "routine_flagged_case_count": len(selected_ids) + len(overflow_ids),
        "selected_case_count": len(selected_ids),
        "reviewed_case_count": len(reviewed_ids),
        "overflow_case_count": len(overflow_ids),
        "limitation_count": len(limitations) + len(missing_ids) + len(overflow_ids),
        "limitations": limitations,
        "confirmed_truth_defect_count": len(confirmed_ids),
        "confirmed_truth_defect_case_ids": confirmed_ids,
        "unresolved_case_ids": unresolved_ids,
        "reviewer_model": reviewer_model,
        "same_provider_model_review": True,
        "deterministic_result_changed": False,
    }
    if CRITICAL_REVIEW_RESULT.exists():
        return _load(CRITICAL_REVIEW_RESULT)
    _write_json_exclusive(CRITICAL_REVIEW_RESULT, payload)
    return payload


async def _execute_critical_review(
    routine_flagged_ids: list[str], *, resume: bool
) -> dict[str, Any]:
    if CRITICAL_REVIEW_RESULT.exists():
        return _load(CRITICAL_REVIEW_RESULT)
    instrument = _load_hashed(
        INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID
    )
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    configuration = instrument["critical_truth_escalation"]
    maximum_cases = int(configuration["maximum_cases"])
    ordered_ids = sorted(set(routine_flagged_ids))
    selected_ids = ordered_ids[:maximum_cases]
    overflow_ids = ordered_ids[maximum_cases:]
    reviewer = binding["providers"]["critical-truth-reviewer"]
    if not selected_ids:
        return _score_critical_review(
            selected_ids=[],
            overflow_ids=[],
            reviewer_model=reviewer["provider_model"],
        )
    rows = _critical_review_rows(selected_ids)
    run_binding = {
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "binding_id": BINDING_ID,
        "binding_sha256": binding["content_sha256"],
        "routine_advisory_result_sha256": hashlib.sha256(
            ADVISORY_RESULT.read_bytes()
        ).hexdigest(),
        "selection_sha256": canonical_sha256(rows),
        "code_revision": _repo_revision(),
        "reviewer_model": reviewer["provider_model"],
    }
    transport = DirectProviderJsonTransport(reviewer)
    if CRITICAL_REVIEW_LEDGER.exists():
        connection = sqlite3.connect(
            f"file:{CRITICAL_REVIEW_LEDGER}?mode=ro", uri=True
        )
        try:
            ledger_status = dict(
                connection.execute("SELECT key,value FROM metadata")
            ).get("status")
        finally:
            connection.close()
        if ledger_status not in {"running", "interrupted"}:
            return _score_critical_review(
                selected_ids=selected_ids,
                overflow_ids=overflow_ids,
                reviewer_model=reviewer["provider_model"],
            )
    ledger = ProviderCallLedgerV1(
        CRITICAL_REVIEW_LEDGER,
        run_binding=run_binding,
        maximum_calls=int(configuration["maximum_calls"]),
        maximum_cost_usd=float(configuration["maximum_cost_usd"]),
        resume=resume or CRITICAL_REVIEW_LEDGER.exists(),
    )
    try:
        for number, row in enumerate(rows, start=1):
            system, prompt = advisory._prompt([row])  # noqa: SLF001
            try:
                await transport.call_with_ledger(
                    ledger=ledger,
                    request_key=f"critical-truth-{number:03d}-{row['case_id']}",
                    provider_role="critical-truth-reviewer",
                    system=system,
                    prompt=prompt,
                    task="academic-factual-qa-critical-truth-escalation",
                    schema=advisory._schema(1),  # noqa: SLF001
                )
            except Exception:  # advisory escalation failure remains a limitation
                break
        if ledger.snapshot()["status"] == "running":
            ledger.mark_complete()
    except KeyboardInterrupt:
        ledger.mark_interrupted()
        raise
    finally:
        ledger.close()
    return _score_critical_review(
        selected_ids=selected_ids,
        overflow_ids=overflow_ids,
        reviewer_model=reviewer["provider_model"],
    )


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
        raise ProductCheckpointError(
            "checkpoint preflight is blocked: " + ", ".join(readiness["blockers"])
        )
    instrument = _load_hashed(INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID)
    binding = _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)
    state = _resume_state(instrument, binding) if resume else _initial_state(instrument, binding)
    if not resume:
        _write_state(state, exclusive=True)
    try:
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
            _complete_stage(
                state, "deterministic-score-and-compare", "routine-nano-advisory-audit"
            )
        else:
            paired = _load(PAIRED_RESULT)

        with configured_advisory():
            if "routine-nano-advisory-audit" not in state["completed_stages"]:
                audit_result = (
                    _load(ADVISORY_RESULT)
                    if ADVISORY_RESULT.exists()
                    else await advisory.execute(resume=ADVISORY_LEDGER.exists())
                )
                _complete_stage(
                    state,
                    "routine-nano-advisory-audit",
                    "bounded-critical-truth-escalation",
                )
            else:
                audit_result = _load(ADVISORY_RESULT)

            if "bounded-critical-truth-escalation" not in state["completed_stages"]:
                critical_result = await _execute_critical_review(
                    audit_result["potential_truth_defect_case_ids"],
                    resume=CRITICAL_REVIEW_LEDGER.exists(),
                )
                _complete_stage(
                    state, "bounded-critical-truth-escalation", "accounting-check"
                )
            else:
                critical_result = _load(CRITICAL_REVIEW_RESULT)

        calls, cost = _provider_totals()
        if calls > instrument["combined_checkpoint"]["maximum_calls"] or cost > instrument["combined_checkpoint"]["maximum_cost_usd"]:
            return _terminal(
                state,
                "invalid-execution",
                {
                    "stage": "accounting-check",
                    "provider_calls": calls,
                    "reported_cost_usd": cost,
                },
            )
        final_status = (
            "needs-human-review"
            if critical_result["unresolved_case_ids"]
            else paired["status"]
        )
        result = {
            "status": final_status,
            "deterministic_status": paired["status"],
            "decision": paired["decision"],
            "failed_gates": paired["failed_gates"],
            "advisory_status": audit_result["status"],
            "advisory_limitation_count": audit_result["limitation_count"],
            "potential_truth_defect_case_ids": audit_result[
                "potential_truth_defect_case_ids"
            ],
            "critical_review_status": critical_result["status"],
            "critical_reviewed_case_count": critical_result["reviewed_case_count"],
            "critical_review_limitation_count": critical_result["limitation_count"],
            "unresolved_truth_defect_case_ids": critical_result[
                "unresolved_case_ids"
            ],
            "deterministic_result_changed_by_advisory": False,
            "wording_provider_calls": 0,
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
            {
                "stage": state.get("current_stage"),
                "failure_type": type(error).__name__,
                "failure_detail": str(error)[:300],
            },
        )


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument(
        "--simulate",
        choices=(
            "pass",
            "product-failure",
            "provider-failure",
            "advisory-malformed",
            "truth-defect",
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
