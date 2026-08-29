#!/usr/bin/env python3
"""Run the finite evaluation-v2 four-model R1 development cascade."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import statistics
import subprocess
import tempfile
from typing import Any

from dotenv import load_dotenv

from scripts import run_academic_factual_qa_open_advisory_audit_004 as advisory
from scripts.academic_factual_qa_open_10000_t0_adapter import build_live_t0_adapter
from src.digital_twin.evaluation import (
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    ModelCandidateManifestV2,
    SystemUnderTestManifestV1,
    score_case,
    summarize_scores,
    reconcile_case_batch,
)
from src.digital_twin.evaluation.retrieval_materialization import (
    materialize_retrieval_indexes,
)
from src.digital_twin.evaluation.factual_qa_scoring import FactualQaCaseScoreV1
from src.digital_twin.evaluation.factual_qa_execution import (
    ResponseLedgerV1,
    canonical_json_sha256,
    execute_cases,
)
from src.digital_twin.model_policy import OPENAI_PRODUCT_CANDIDATE_MODELS
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonResponse,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-r1-model-cascade-001"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_r1_model_cascade_001.json"
)
PROFILE_PATH = ROOT / (
    "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)
GENERATED = ROOT / "reports/generated/r1-model-cascade-001"
STATE_PATH = GENERATED / "cascade-state.json"
ADVISORY_LEDGER_PATH = GENERATED / "selected-advisory-provider.sqlite3"
ADVISORY_RESULT_PATH = GENERATED / "selected-advisory-result.json"


class CascadeError(RuntimeError):
    """Raised when the finite cascade cannot preserve its frozen boundary."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CascadeError(f"JSON root is not an object: {path.name}")
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
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _package(path: Path, key: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _load(path)
    expected = canonical_json_sha256(
        {name: value for name, value in payload.items() if name != "content_sha256"}
    )
    rows = payload.get(key)
    if payload.get("content_sha256") != expected or not isinstance(rows, list):
        raise CascadeError(f"package hash or rows drifted: {path.name}")
    if payload.get("case_count") != len(rows):
        raise CascadeError(f"package count drifted: {path.name}")
    return payload, rows


def _instrument_paths() -> tuple[Path, Path, Path, Path]:
    instrument = _load(INSTRUMENT_PATH)
    return tuple(ROOT / instrument[name] for name in (
        "public_cases",
        "hidden_gold",
        "paired_control_cases",
        "paired_control_gold",
    ))  # type: ignore[return-value]


def _development_cases() -> list[EvaluationCaseV1]:
    public_path, _, _, _ = _instrument_paths()
    _, rows = _package(public_path, "cases")
    return [EvaluationCaseV1.model_validate(row) for row in rows]


def _screening_cases(cases: list[EvaluationCaseV1]) -> list[EvaluationCaseV1]:
    targets = _load(INSTRUMENT_PATH)["screening"]["slice_targets"]
    grouped: dict[str, list[EvaluationCaseV1]] = defaultdict(list)
    for case in cases:
        grouped[case.slice].append(case)
    selected: list[EvaluationCaseV1] = []
    for slice_name, target in targets.items():
        available = sorted(
            grouped.get(slice_name, []),
            key=lambda row: (row.course_id, row.cluster_id, row.case_id),
        )
        by_course: dict[str, list[EvaluationCaseV1]] = defaultdict(list)
        for row in available:
            by_course[row.course_id].append(row)
        course_ids = sorted(by_course)
        while len(selected) < sum(
            targets[name]
            for name in list(targets)[: list(targets).index(slice_name)]
        ) + target:
            progressed = False
            for course_id in course_ids:
                if by_course[course_id]:
                    selected.append(by_course[course_id].pop(0))
                    progressed = True
                    if sum(row.slice == slice_name for row in selected) == target:
                        break
            if not progressed:
                raise CascadeError(f"screening slice cannot meet target: {slice_name}")
    if len(selected) != 200 or len({row.case_id for row in selected}) != 200:
        raise CascadeError("screening set is not exactly 200 unique cases")
    return selected


def _candidate_manifests() -> list[ModelCandidateManifestV2]:
    instrument = _load(INSTRUMENT_PATH)
    revision = _repo_revision()
    shared = {
        "reasoning_effort": instrument["execution"]["reasoning_effort"],
        "max_output_tokens": instrument["execution"]["maximum_output_tokens"],
        "request_store": False,
        "prompt_id": "strict-evidence-grounded-prompt-v3",
        "retriever_id": "qwen3-hybrid-v1",
        "evidence_gate_id": "structured-lexical-coverage-evidence-gate-v1",
        "policy_id": "structured-professor-policy-v1",
        "code_revision": revision,
        "pricing_verified_at": instrument["metadata"]["verified_at"],
    }
    return [
        ModelCandidateManifestV2.model_validate(
            {
                **shared,
                **row,
                "expected_returned_model": row["provider_model"],
            }
        )
        for row in instrument["candidates"]
    ]


def validate() -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise CascadeError("instrument identity drifted")
    if tuple(row.provider_model for row in _candidate_manifests()) != (
        OPENAI_PRODUCT_CANDIDATE_MODELS
    ):
        raise CascadeError("four-model candidate order drifted")
    cases = _development_cases()
    screening = _screening_cases(cases)
    authorization = tuple(
        bool(instrument["execution"][name])
        for name in (
            "local_index_materialization_authorized",
            "provider_execution_authorized",
            "paid_execution_authorized",
        )
    )
    if len(set(authorization)) != 1:
        raise CascadeError("cascade execution authority is only partially enabled")
    if instrument["execution"]["sealed_final_execution_authorized"]:
        raise CascadeError("cascade cannot authorize the sealed final evaluation")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-authorized" if all(authorization) else "passed-build-only",
        "candidate_models": [row.provider_model for row in _candidate_manifests()],
        "development_case_count": len(cases),
        "screening_case_count": len(screening),
        "screening_case_ids_sha256": canonical_json_sha256(
            [row.case_id for row in screening]
        ),
        "provider_calls": 0,
        "paid_execution_authorized": all(authorization),
        "sealed_final_execution_authorized": False,
    }


def preflight(*, require_authorized: bool) -> dict[str, Any]:
    validated = validate()
    instrument = _load(INSTRUMENT_PATH)
    blockers: list[str] = []
    technical: list[str] = []
    verified = datetime.fromisoformat(instrument["metadata"]["verified_at"])
    if (datetime.now(UTC) - verified.astimezone(UTC)).total_seconds() > 86_400:
        technical.append("provider-metadata-older-than-24-hours")
    if _repo_dirty():
        technical.append("working-tree-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        technical.append("openai-credential-missing")
    index_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_INDEX_ROOT",
            str(
                ROOT
                / "reports/generated/academic-factual-qa-open-10000-v1-retrieval-indexes-001"
            ),
        )
    )
    model_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_QWEN_MODEL_ROOT",
            str(
                ROOT
                / "data/external/huggingface/hub/"
                "models--Qwen--Qwen3-Embedding-0.6B/snapshots"
            ),
        )
    )
    if not model_root.is_dir():
        technical.append("local-qwen-query-model-missing")
    source_plan = Path(
        os.getenv(
            "ACADEMIC_EVAL_SOURCE_PLAN_PATH",
            str(
                ROOT
                / "data/processed/academic_factual_qa_open_10000_v1_sources.json"
            ),
        )
    )
    if not source_plan.is_file():
        technical.append("public-source-plan-missing")
    if STATE_PATH.exists():
        technical.append("exclusive-cascade-output-used")
    for field in ("provider_execution_authorized", "paid_execution_authorized"):
        if not instrument["execution"][field]:
            blockers.append(f"{field.replace('_', '-')}-false")
    if not instrument["execution"]["local_index_materialization_authorized"]:
        blockers.append("local-index-materialization-authorized-false")
    if require_authorized:
        try:
            require_bounded_pilot_operation_allowed(
                INSTRUMENT_ID, "external_model_evaluation"
            )
            require_bounded_pilot_operation_allowed(
                INSTRUMENT_ID, "local_model_evaluation"
            )
            require_bounded_pilot_operation_allowed(
                INSTRUMENT_ID, "method_evaluation_execution"
            )
        except ValueError as error:
            blockers.append(type(error).__name__)
    return {
        **validated,
        "status": (
            "ready"
            if not technical and not blockers
            else "ready-pending-authorization"
            if not technical and not require_authorized
            else "blocked-not-ready"
        ),
        "technical_blockers": sorted(set(technical)),
        "authorization_blockers": sorted(set(blockers)),
        "credential_value_emitted": False,
        "retrieval_index_state": (
            "ready" if index_root.is_dir() else "build-on-authorized-execution"
        ),
        "provider_calls": 0,
    }


def _ensure_retrieval_indexes() -> dict[str, Any]:
    index_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_INDEX_ROOT",
            str(
                ROOT
                / "reports/generated/academic-factual-qa-open-10000-v1-retrieval-indexes-001"
            ),
        )
    )
    if index_root.is_dir():
        return {
            "status": "already-present",
            "provider_calls": 0,
            "cost_usd": 0.0,
        }
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "local_model_evaluation"
    )
    from scripts.academic_factual_qa_open_10000_t0_adapter import _chunks_by_course

    chunks_by_course, _ = _chunks_by_course()
    model_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_QWEN_MODEL_ROOT",
            str(
                ROOT
                / "data/external/huggingface/hub/"
                "models--Qwen--Qwen3-Embedding-0.6B/snapshots"
            ),
        )
    )
    return materialize_retrieval_indexes(
        chunks_by_course=chunks_by_course,
        profile=_load(PROFILE_PATH),
        model_root=model_root,
        output_root=index_root,
    )


def _manifest(candidate: ModelCandidateManifestV2, *, stage: str, control: bool):
    profile_hash = hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()
    return SystemUnderTestManifestV1(
        flow_id=(
            f"t0-any-hit-control-{candidate.candidate_id}"
            if control
            else f"t0-structured-candidate-{stage}-{candidate.candidate_id}"
        ),
        adapter_version="v1",
        code_revision=candidate.code_revision,
        profile_sha256=profile_hash,
        retriever=candidate.retriever_id,
        generator="openai-responses-live-atomic-v2",
        policy=candidate.policy_id,
        evidence_gate=(
            "any-hit-evidence-gate-v1" if control else candidate.evidence_gate_id
        ),
        model_bindings={"product-generator": candidate.provider_model},
        known_benchmark=True,
    )


def _paths(stage: str, candidate_id: str) -> dict[str, Path]:
    prefix = GENERATED / f"{stage}-{candidate_id}"
    return {
        "responses": prefix.with_name(prefix.name + "-responses.sqlite3"),
        "provider": prefix.with_name(prefix.name + "-provider.sqlite3"),
        "state": prefix.with_name(prefix.name + "-state.sqlite3"),
        "result": prefix.with_name(prefix.name + "-result.json"),
    }


def _gold_by_id(control: bool = False) -> dict[str, EvaluationGoldV1]:
    _, gold_path, _, control_gold_path = _instrument_paths()
    _, rows = _package(control_gold_path if control else gold_path, "gold")
    values = [EvaluationGoldV1.model_validate(row) for row in rows]
    return {row.case_id: row for row in values}


def _completed_responses(path: Path) -> list[EvaluationResponseV1] | None:
    if not path.is_file():
        return None
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        if metadata.get("status") != "completed":
            return None
        values = [
            EvaluationResponseV1.model_validate_json(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM responses ORDER BY sequence"
            )
        ]
    finally:
        connection.close()
    return values


def _provider_totals() -> tuple[int, float]:
    calls = 0
    cost = 0.0
    if not GENERATED.is_dir():
        return calls, cost
    for path in sorted(GENERATED.glob("*provider.sqlite3")):
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM calls"
            ).fetchone()
        except sqlite3.Error:
            continue
        finally:
            connection.close()
        calls += int(row[0])
        cost += float(row[1])
    return calls, cost


def _score(
    cases: list[EvaluationCaseV1], responses: list[EvaluationResponseV1], *, control: bool
) -> dict[str, Any]:
    gold = _gold_by_id(control)
    by_id = {row.case_id: row for row in responses}
    if set(by_id) != {row.case_id for row in cases}:
        raise CascadeError("response IDs do not exactly match the evaluated cases")
    scores = [score_case(row, gold[row.case_id], by_id[row.case_id]) for row in cases]
    summary = summarize_scores(scores)
    return {
        "summary": summary,
        "case_scores": [row.model_dump(mode="json") for row in scores],
    }


def _screen_pass(result: dict[str, Any]) -> bool:
    gates = _load(INSTRUMENT_PATH)["screening"]["gates"]
    summary = result["summary"]
    metrics = summary["metrics"]
    malformed_rate = summary["operational_failure_count"] / summary["case_count"]
    return (
        summary["severe_unsupported_release_count"]
        <= gates["severe_unsupported_release_count_max"]
        and metrics["source_version_validity"]
        >= gates["source_version_validity_min"]
        and metrics["boundary_action_accuracy"]
        >= gates["boundary_action_accuracy_min"]
        and metrics["provider_completion"] >= gates["provider_completion_min"]
        and malformed_rate <= gates["malformed_output_max"]
    )


def _full_pass(result: dict[str, Any]) -> bool:
    gates = _load(INSTRUMENT_PATH)["full_development"]["gates"]
    summary = result["summary"]
    metrics = summary["metrics"]
    return all(
        (
            metrics["fully_grounded_factual_success"]
            >= gates["fully_grounded_factual_success_min"],
            metrics["action_accuracy_answerable"]
            >= gates["action_accuracy_answerable_min"],
            metrics["boundary_action_accuracy"]
            >= gates["boundary_action_accuracy_min"],
            metrics["atomic_claim_precision"] >= gates["atomic_claim_precision_min"],
            metrics["atomic_claim_recall"] >= gates["atomic_claim_recall_min"],
            metrics["citation_precision"] >= gates["citation_precision_min"],
            metrics["citation_recall"] >= gates["citation_recall_min"],
            metrics["source_version_validity"]
            >= gates["source_version_validity_min"],
            summary["severe_unsupported_release_count"]
            <= gates["severe_unsupported_release_count_max"],
        )
    )


def _paired_comparison(
    candidate: dict[str, Any], control: dict[str, Any]
) -> dict[str, Any]:
    gates = _load(INSTRUMENT_PATH)["paired_control"]["gates"]
    candidate_scores = {
        row["case_id"]: FactualQaCaseScoreV1.model_validate(row)
        for row in candidate["case_scores"]
    }
    control_scores = {
        row["case_id"]: FactualQaCaseScoreV1.model_validate(row)
        for row in control["case_scores"]
    }
    if not control_scores or not set(control_scores).issubset(candidate_scores):
        raise CascadeError("paired control identities are not a candidate subset")
    pairs = [
        (candidate_scores[case_id], control_scores[case_id])
        for case_id in sorted(control_scores)
    ]
    answerable = [pair for pair in pairs if pair[0].answerable]
    boundary = [pair for pair in pairs if not pair[0].answerable]
    if not answerable or not boundary:
        raise CascadeError("paired comparison requires answerable and boundary cases")
    deltas: dict[str, list[float]] = defaultdict(list)
    for candidate_row, control_row in answerable:
        if (
            candidate_row.source_family_id != control_row.source_family_id
            or candidate_row.expected_action != control_row.expected_action
        ):
            raise CascadeError("paired control metadata drifted")
        deltas[candidate_row.source_family_id].append(
            float(candidate_row.fully_grounded_success)
            - float(control_row.fully_grounded_success)
        )
    family_means = [statistics.fmean(rows) for _, rows in sorted(deltas.items())]
    rng = random.Random(20260829)
    replicates = 10_000
    samples = sorted(
        statistics.fmean(rng.choice(family_means) for _ in family_means)
        for _ in range(replicates)
    )
    lower = samples[math.floor(0.025 * (replicates - 1))]
    upper = samples[math.ceil(0.975 * (replicates - 1))]
    candidate_boundary = statistics.fmean(
        float(candidate_row.boundary_safe) for candidate_row, _ in boundary
    )
    control_boundary = statistics.fmean(
        float(control_row.boundary_safe) for _, control_row in boundary
    )
    gate_results = {
        "supported_answer_retention_lower_95": (
            lower >= gates["supported_answer_retention_delta_lower_95_min"]
        ),
        "boundary_safety_not_worse": candidate_boundary >= control_boundary,
    }
    return {
        "paired_case_count": len(pairs),
        "supported_answer_retention": {
            "estimate": statistics.fmean(family_means),
            "lower_95": lower,
            "upper_95": upper,
            "source_family_count": len(family_means),
            "replicates": replicates,
            "seed": 20260829,
        },
        "boundary_safety": {
            "candidate": candidate_boundary,
            "control": control_boundary,
            "delta": candidate_boundary - control_boundary,
        },
        "gate_results": gate_results,
        "passed": all(gate_results.values()),
    }


async def _run_arm(
    *,
    stage: str,
    candidate: ModelCandidateManifestV2,
    cases: list[EvaluationCaseV1],
    control: bool = False,
    resume: bool,
) -> dict[str, Any]:
    paths = _paths(stage, candidate.candidate_id)
    existing = _completed_responses(paths["responses"])
    if existing is None:
        used_calls, used_cost = _provider_totals()
        limits = _load(INSTRUMENT_PATH)["execution"]
        remaining_calls = int(limits["maximum_logical_calls"]) - used_calls
        remaining_cost = float(limits["emergency_cost_stop_usd"]) - used_cost
        if remaining_calls < len(cases) or remaining_cost <= 0:
            raise CascadeError("cascade-wide call or cost ceiling reached before arm")
        manifest = _manifest(candidate, stage=stage, control=control)
        rows_hash = canonical_json_sha256(
            [row.model_dump(mode="json") for row in cases]
        )
        arm_resume = resume and paths["responses"].exists()
        adapter = build_live_t0_adapter(
            manifest=manifest,
            cases=cases,
            runtime={
                "instrument_id": INSTRUMENT_ID,
                "cases_sha256": rows_hash,
                "code_revision": candidate.code_revision,
                "provider_ledger_path": str(paths["provider"]),
                "state_path": str(paths["state"]),
                "resume": arm_resume,
                "maximum_calls": min(len(cases), remaining_calls),
                "maximum_cost_usd": remaining_cost,
                "model_candidate_manifest": candidate.model_dump(mode="json"),
            },
        )
        ledger = ResponseLedgerV1(
            paths["responses"],
            cases_sha256=rows_hash,
            system_manifest_sha256=canonical_json_sha256(
                manifest.model_dump(mode="json")
            ),
            run_configuration_sha256=canonical_json_sha256(
                {
                    "instrument_id": INSTRUMENT_ID,
                    "stage": stage,
                    "candidate": candidate.model_dump(mode="json"),
                    "control": control,
                }
            ),
            resume=arm_resume,
        )
        try:
            await execute_cases(cases=cases, adapter=adapter, manifest=manifest, ledger=ledger)
        finally:
            ledger.close()
        existing = _completed_responses(paths["responses"])
    if existing is None:
        raise CascadeError(f"arm did not produce a completed response ledger: {stage}")
    result = {
        "stage": stage,
        "candidate": candidate.model_dump(mode="json"),
        **_score(cases, existing, control=control),
    }
    paths["result"].parent.mkdir(parents=True, exist_ok=True)
    temporary = paths["result"].with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, paths["result"])
    return result


def _advisory_binding() -> dict[str, Any]:
    return {
        "binding_id": "r1-cascade-sol-advisory-v1",
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "first_party_endpoint": True,
        "api_url": "https://api.openai.com/v1/responses",
        "credential_environment_variable": "OPENAI_API_KEY",
        "provider_model": "gpt-5.6-sol",
        "documented_revision": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "max_output_tokens": 600,
        "timeout_seconds": 60,
        "maximum_transport_retries": 1,
        "pricing_usd_per_million_input_tokens": 4.0,
        "pricing_usd_per_million_output_tokens": 20.0,
    }


def _audit_selection(case_scores: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    failures = [
        row["case_id"]
        for row in case_scores
        if not (
            row["fully_grounded_success"]
            if row["answerable"]
            else row["boundary_safe"]
        )
    ]
    passing = [
        row["case_id"]
        for row in case_scores
        if row["case_id"] not in set(failures)
    ]
    sample_count = math.ceil(len(case_scores) * 0.10)
    sample = sorted(
        passing,
        key=lambda case_id: hashlib.sha256(
            f"20260829:{case_id}".encode("utf-8")
        ).hexdigest(),
    )[:sample_count]
    return failures, sample


def _audit_rows(
    *,
    cases: list[EvaluationCaseV1],
    responses: list[EvaluationResponseV1],
    deterministic_result: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    by_case = {row.case_id: row for row in cases}
    by_response = {row.case_id: row for row in responses}
    gold = _gold_by_id()
    failures, sample = _audit_selection(deterministic_result["case_scores"])
    selected = [*failures, *(case_id for case_id in sample if case_id not in failures)]
    scores = {row["case_id"]: row for row in deterministic_result["case_scores"]}
    rows = []
    for case_id in selected:
        case = by_case[case_id]
        reference = gold[case_id]
        response = by_response[case_id]
        score = scores[case_id]
        rows.append(
            {
                "case_id": case_id,
                "selection": (
                    "deterministic-failure" if case_id in failures else "seeded-pass"
                ),
                "course_id": case.course_id,
                "slice": case.slice,
                "question": case.question,
                "expected_action": reference.expected_action.value,
                "canonical_answer": reference.canonical_answer,
                "canonical_claim_spans": [claim.answer_span for claim in reference.claims],
                "boundary_reason": reference.boundary_reason,
                "actual_action": response.action.value,
                "answer": response.answer,
                "atomic_claims": [claim.text for claim in response.atomic_claims],
                "citation_count": len(response.citations),
                "deterministic_failure": case_id in failures,
                "deterministic_action_correct": score["action_correct"],
            }
        )
    return rows, failures, sample


async def _run_advisory_audit(
    *,
    selected_result: dict[str, Any],
    cases: list[EvaluationCaseV1],
    resume: bool,
) -> dict[str, Any]:
    if ADVISORY_RESULT_PATH.is_file():
        return _load(ADVISORY_RESULT_PATH)
    candidate_id = selected_result["candidate"]["candidate_id"]
    responses = _completed_responses(_paths("full", candidate_id)["responses"])
    if responses is None:
        raise CascadeError("selected response ledger is incomplete before advisory audit")
    rows, failures, sample = _audit_rows(
        cases=cases,
        responses=responses,
        deterministic_result=selected_result,
    )
    batches = [rows[index : index + 4] for index in range(0, len(rows), 4)]
    if not batches:
        return {
            "status": "completed",
            "reviewed_case_count": 0,
            "limitation_count": 0,
            "authoritative": False,
        }
    binding = _advisory_binding()
    used_calls, used_cost = _provider_totals()
    limits = _load(INSTRUMENT_PATH)["execution"]
    remaining_calls = int(limits["maximum_logical_calls"]) - used_calls
    remaining_cost = float(limits["emergency_cost_stop_usd"]) - used_cost
    if remaining_calls < len(batches) or remaining_cost <= 0:
        raise CascadeError("cascade-wide ceiling reached before advisory review")
    ledger = ProviderCallLedgerV1(
        ADVISORY_LEDGER_PATH,
        run_binding={
            "instrument_id": INSTRUMENT_ID,
            "selected_candidate": selected_result["candidate"],
            "selected_case_ids_sha256": canonical_json_sha256(
                [row["case_id"] for row in rows]
            ),
            "binding": binding,
            "code_revision": _repo_revision(),
        },
        maximum_calls=len(batches),
        maximum_cost_usd=remaining_cost,
        maximum_transport_retries_total=math.floor(len(batches) * 0.02),
        resume=resume and ADVISORY_LEDGER_PATH.exists(),
    )
    transport = DirectProviderJsonTransport(binding)
    limitations: list[str] = []
    accepted_votes: list[dict[str, Any]] = []
    try:
        for number, batch in enumerate(batches, start=1):
            system, prompt = advisory._prompt(batch)  # noqa: SLF001
            try:
                response = await transport.call_with_ledger(
                    ledger=ledger,
                    request_key=f"selected-advisory-{number:03d}",
                    provider_role="advisory-reviewer",
                    system=system,
                    prompt=prompt,
                    task="r1-model-cascade-advisory-review",
                    schema=advisory._schema(len(batch)),  # noqa: SLF001
                    quarantine_failures=True,
                )
            except Exception as error:
                limitations.extend(row["case_id"] for row in batch)
                continue
            reconciliation = reconcile_case_batch(
                expected_case_ids=[row["case_id"] for row in batch],
                provider_rows=response.content.get("items", []),
                validate_semantics=lambda value: value,
            )
            for reconciled in reconciliation.rows:
                if reconciled.payload is None:
                    limitations.append(reconciled.case_id)
                else:
                    accepted_votes.append(reconciled.payload)
        if ledger.snapshot()["status"] == "running":
            ledger.mark_complete()
        ledger_snapshot = ledger.snapshot()
    except KeyboardInterrupt:
        ledger.mark_interrupted()
        raise
    finally:
        ledger.close()
    result = {
        "status": "completed-with-limitations" if limitations else "completed",
        "reviewed_case_count": len(rows),
        "deterministic_failure_count": len(failures),
        "seeded_passing_sample_count": len(sample),
        "accepted_vote_count": len(accepted_votes),
        "limitation_count": len(set(limitations)),
        "limited_case_ids": sorted(set(limitations)),
        "potential_truth_defect_case_ids": sorted(
            vote["case_id"]
            for vote in accepted_votes
            if vote.get("potential_authoritative_truth_defect") is True
        ),
        "reviewer_model": binding["provider_model"],
        "same_provider_model_review": True,
        "selected_model_equals_reviewer": (
            selected_result["candidate"]["provider_model"]
            == binding["provider_model"]
        ),
        "authoritative": False,
        "deterministic_result_changed": False,
        "ledger": ledger_snapshot,
    }
    ADVISORY_RESULT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _rank(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        results,
        key=lambda row: (
            -row["summary"]["metrics"]["fully_grounded_factual_success"],
            row["summary"]["latency_ms_p95"],
            row["summary"]["cost_usd"],
            row["candidate"]["candidate_id"],
        ),
    )


def _select_passing(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Apply the frozen practical-equivalence, latency, then cost rule."""

    passing = _rank([row for row in results if _full_pass(row)])
    if not passing:
        return None
    best = passing[0]
    threshold = float(
        _load(INSTRUMENT_PATH)["selection"]["practical_equivalence_points"]
    )
    best_metric = best["summary"]["metrics"]["fully_grounded_factual_success"]
    best_interval = best["summary"]["fully_grounded_source_family_interval"]
    equivalent: list[dict[str, Any]] = []
    for row in passing:
        metric = row["summary"]["metrics"]["fully_grounded_factual_success"]
        interval = row["summary"]["fully_grounded_source_family_interval"]
        intervals_overlap = (
            interval["lower_95"] <= best_interval["upper_95"]
            and best_interval["lower_95"] <= interval["upper_95"]
        )
        if best_metric - metric <= threshold or intervals_overlap:
            equivalent.append(row)
    return min(
        equivalent,
        key=lambda row: (
            row["summary"]["latency_ms_p95"],
            row["summary"]["cost_usd"],
            row["candidate"]["candidate_id"],
        ),
    )


async def execute(*, resume: bool) -> dict[str, Any]:
    ready = preflight(require_authorized=True)
    if ready["status"] != "ready":
        raise CascadeError("live cascade preflight is not ready")
    retrieval_index = _ensure_retrieval_indexes()
    cases = _development_cases()
    screening = _screening_cases(cases)
    screening_results = [
        await _run_arm(
            stage="screening",
            candidate=candidate,
            cases=screening,
            resume=resume,
        )
        for candidate in _candidate_manifests()
    ]
    eligible = _rank([row for row in screening_results if _screen_pass(row)])[:2]
    full_results: list[dict[str, Any]] = []
    for screening_result in eligible:
        candidate = ModelCandidateManifestV2.model_validate(
            screening_result["candidate"]
        )
        full_results.append(
            await _run_arm(
                stage="full",
                candidate=candidate,
                cases=cases,
                resume=resume,
            )
        )
    selected = _select_passing(full_results)
    control_result = None
    paired_comparison = None
    advisory_result = None
    if selected is not None:
        _, _, control_cases_path, _ = _instrument_paths()
        _, control_rows = _package(control_cases_path, "cases")
        control_cases = [EvaluationCaseV1.model_validate(row) for row in control_rows]
        control_result = await _run_arm(
            stage="control",
            candidate=ModelCandidateManifestV2.model_validate(selected["candidate"]),
            cases=control_cases,
            control=True,
            resume=resume,
        )
        paired_comparison = _paired_comparison(selected, control_result)
        advisory_result = await _run_advisory_audit(
            selected_result=selected,
            cases=cases,
            resume=resume,
        )
    keep = selected is not None and bool(paired_comparison["passed"])
    result = {
        "instrument_id": INSTRUMENT_ID,
        "status": "completed-keep" if keep else "completed-refine",
        "decision": "Keep" if keep else "Refine",
        "selected_candidate": selected["candidate"] if selected else None,
        "fallback": None if selected else "deterministic-grounded-generator",
        "screening_results": screening_results,
        "full_results": full_results,
        "control_result": control_result,
        "paired_comparison": paired_comparison,
        "advisory_review": advisory_result,
        "retrieval_index_materialization": retrieval_index,
        "sealed_final_execution_authorized": False,
    }
    GENERATED.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def simulate(*, scenario: str) -> dict[str, Any]:
    validate()
    if scenario not in {"pass", "no-model-passes", "quarantine"}:
        raise CascadeError("unknown simulation scenario")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "completed-keep" if scenario == "pass" else "completed-refine"
        ),
        "scenario": scenario,
        "screened_models": list(OPENAI_PRODUCT_CANDIDATE_MODELS),
        "full_model_count": 2 if scenario == "pass" else 0,
        "control_case_count": 100 if scenario == "pass" else 0,
        "fallback": (
            None if scenario == "pass" else "deterministic-grounded-generator"
        ),
        "provider_calls": 0,
        "paid_execution_authorized": False,
        "sealed_final_execution_authorized": False,
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument(
        "--simulate", choices=("pass", "no-model-passes", "quarantine")
    )
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "local_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
        result = asyncio.run(execute(resume=arguments.resume))
    elif arguments.preflight:
        result = preflight(require_authorized=False)
    elif arguments.simulate:
        result = simulate(scenario=arguments.simulate)
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
