#!/usr/bin/env python3
"""Author, review, and materialize the AFQC-101 source-aligned questions."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any, Iterable

from dotenv import load_dotenv
import httpx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_reference_questions import (  # noqa: E402
    ReferenceQuestionAuthorResponseV1,
    ReferenceQuestionReviewerResponseV1,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    SourceClusterV2,
)
from src.digital_twin.evaluation.provider_json import (  # noqa: E402
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
)
from src.digital_twin.evaluation.source_aligned_wording import (  # noqa: E402
    assemble_source_aligned_wording,
    context_complete_fallback,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


PROGRAM_ID = "course-digital-twin-nonhuman-evaluation-program-002"
ATTEMPT_SUFFIXES = ("001", "002")
STAGE_ID = "academic-factual-qa-source-aligned-wording-001"
BINDING_ID = "academic-factual-qa-source-aligned-wording-binding-001"
AUTHOR_ROLE = "source-visible-question-author"
REVIEWER_ROLE = "target-blind-answer-reviewer"
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
INSTRUMENT_ROOT = ROOT / "research/05_evaluation/instruments"
RECORD_ROOT = ROOT / "research/05_evaluation/records"
GENERATED_ROOT = ROOT / "reports/generated"
PROGRAM_PATH = INSTRUMENT_ROOT / "course_digital_twin_nonhuman_evaluation_program_002.json"
BINDING_PATH = INSTRUMENT_ROOT / "academic_factual_qa_source_aligned_wording_binding_001.json"
SOURCE_PATH = DATASET_ROOT / "academic-factual-qa-source-aligned-confirmation-001-sources.json"
BASE_CASES_PATH = DATASET_ROOT / "academic-factual-qa-source-aligned-confirmation-001-cases.json"
GOLD_PATH = DATASET_ROOT / "academic-factual-qa-source-aligned-confirmation-001-gold.json"
OUTPUT_CASES_PATH = DATASET_ROOT / f"{STAGE_ID}-cases.json"
RESULT_PATH = RECORD_ROOT / f"{STAGE_ID}.json"
LEDGER_PATH = GENERATED_ROOT / f"{STAGE_ID}.sqlite3"
EXPECTED_MODELS = {
    AUTHOR_ROLE: "gpt-5.4-nano-2026-03-17",
    REVIEWER_ROLE: "gpt-5.6-terra",
}


class SourceAlignedWordingError(RuntimeError):
    """Raised when the bounded wording stage is not reproducible."""


def _select_attempt(suffix: str) -> None:
    """Bind one immutable attempt without changing its cases, prompts, or gates."""

    if suffix not in ATTEMPT_SUFFIXES:
        raise SourceAlignedWordingError(f"unknown source-aligned wording attempt: {suffix}")
    global STAGE_ID, BINDING_ID, BINDING_PATH, OUTPUT_CASES_PATH, RESULT_PATH, LEDGER_PATH
    STAGE_ID = f"academic-factual-qa-source-aligned-wording-{suffix}"
    BINDING_ID = f"academic-factual-qa-source-aligned-wording-binding-{suffix}"
    BINDING_PATH = INSTRUMENT_ROOT / (
        f"academic_factual_qa_source_aligned_wording_binding_{suffix}.json"
    )
    OUTPUT_CASES_PATH = DATASET_ROOT / f"{STAGE_ID}-cases.json"
    RESULT_PATH = RECORD_ROOT / f"{STAGE_ID}.json"
    LEDGER_PATH = GENERATED_ROOT / f"{STAGE_ID}.sqlite3"


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourceAlignedWordingError(f"required JSON is unavailable: {path.name}") from error
    if not isinstance(value, dict):
        raise SourceAlignedWordingError(f"JSON root is not an object: {path.name}")
    return value


def _load_hashed(path: Path) -> dict[str, Any]:
    value = _load_object(path)
    observed = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise SourceAlignedWordingError(f"content hash drifted: {path.name}")
    return value


def _load_rows(path: Path, key: str, count: int) -> tuple[dict[str, Any], list[Any]]:
    payload = _load_hashed(path)
    rows = payload.get(key)
    if not isinstance(rows, list) or len(rows) != count:
        raise SourceAlignedWordingError(f"{path.name} must contain {count} {key}")
    return payload, rows


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


def _batches(rows: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _author_schema(count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["case_id", "question"],
                    "properties": {
                        "case_id": {"type": "string", "minLength": 1},
                        "question": {
                            "type": "string",
                            "minLength": 12,
                            "maxLength": 500,
                            "pattern": "\\?$",
                        },
                    },
                },
            }
        },
    }


def _review_schema(count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "case_id",
                        "predicted_action",
                        "recovered_answer_spans",
                        "unambiguous",
                        "natural_student_question",
                        "gold_hint_leak",
                        "rationale",
                    ],
                    "properties": {
                        "case_id": {"type": "string", "minLength": 1},
                        "predicted_action": {
                            "type": "string",
                            "enum": ["answer", "abstain", "clarify", "refuse"],
                        },
                        "recovered_answer_spans": {
                            "type": "array",
                            "maxItems": 2,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "unambiguous": {"type": "boolean"},
                        "natural_student_question": {"type": "boolean"},
                        "gold_hint_leak": {"type": "boolean"},
                        "rationale": {"type": "string", "minLength": 1, "maxLength": 400},
                    },
                },
            }
        },
    }


def _parse_by_id(
    *, content: dict[str, Any], expected_ids: list[str], model: type[Any]
) -> tuple[list[Any], str | None]:
    try:
        rows = [model.model_validate(row) for row in content.get("items", [])]
    except Exception as error:  # noqa: BLE001
        return [], f"semantic-parse-failure:{type(error).__name__}"
    observed = [row.case_id for row in rows]
    if len(observed) != len(set(observed)):
        return [], "semantic-duplicate-case-id"
    if set(observed) != set(expected_ids):
        return [], "semantic-case-id-set-mismatch"
    by_id = {row.case_id: row for row in rows}
    return [by_id[case_id] for case_id in expected_ids], None


def _source_payload(clusters: list[SourceClusterV2]) -> list[dict[str, Any]]:
    return [
        {
            "cluster_id": row.cluster_id,
            "course_id": row.course_id,
            "section_heading": row.section_heading,
            "source_path": row.source_path,
            "source_text": row.text,
        }
        for row in clusters
    ]


def _author_prompt(
    *,
    clusters: list[SourceClusterV2],
    cases: list[EvaluationCaseV1],
    gold_by_id: dict[str, EvaluationGoldV1],
) -> tuple[str, str]:
    system = (
        "Rewrite each supplied canonical question as a clear, context-complete "
        "student question using only the matching public source. Preserve the case "
        "ID and intended action. Answer questions must uniquely require every "
        "listed exact span without copying the complete answer into the question. "
        "Boundary questions must clearly instantiate abstain, clarify, or refuse. "
        "Output only the requested schema."
    )
    items = []
    for case in cases:
        reference = gold_by_id[case.case_id]
        items.append(
            {
                "case_id": case.case_id,
                "cluster_id": case.cluster_id,
                "course_id": case.course_id,
                "slice": case.slice,
                "canonical_question": case.question,
                "expected_action": reference.expected_action.value,
                "required_answer_spans": [row.answer_span for row in reference.claims],
                "boundary_reason": reference.boundary_reason,
            }
        )
    return system, json.dumps(
        {"sources": _source_payload(clusters), "construction_items": items},
        sort_keys=True,
    )


def _review_prompt(
    *, clusters: list[SourceClusterV2], items: list[dict[str, Any]]
) -> tuple[str, str]:
    system = (
        "Independently inspect each candidate question using only its matching "
        "public source. You are not given the intended action or answer. Predict "
        "answer, abstain, clarify, or refuse. For answer, recover every exact source "
        "span needed; for a boundary action return no spans. Mark ambiguity, "
        "naturalness, and answer leakage honestly. Output only the requested schema."
    )
    return system, json.dumps(
        {"sources": _source_payload(clusters), "blind_review_items": items},
        sort_keys=True,
    )


def _loaded_domain() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[EvaluationCaseV1],
    list[EvaluationGoldV1],
    list[SourceClusterV2],
]:
    source_payload, source_rows = _load_rows(SOURCE_PATH, "clusters", 100)
    cases_payload, case_rows = _load_rows(BASE_CASES_PATH, "cases", 500)
    gold_payload, gold_rows = _load_rows(GOLD_PATH, "gold", 500)
    if not (
        cases_payload["source_plan_sha256"]
        == gold_payload["source_plan_sha256"]
        == source_payload["content_sha256"]
    ):
        raise SourceAlignedWordingError("source-aligned package bindings differ")
    cases = [EvaluationCaseV1.model_validate(row) for row in case_rows]
    gold = [EvaluationGoldV1.model_validate(row) for row in gold_rows]
    clusters = [SourceClusterV2.model_validate(row) for row in source_rows]
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise SourceAlignedWordingError("source-aligned public/gold IDs differ")
    return source_payload, cases_payload, gold_payload, cases, gold, clusters


def validate() -> dict[str, Any]:
    program = _load_hashed(PROGRAM_PATH)
    binding = _load_hashed(BINDING_PATH)
    source, cases, gold, case_rows, gold_rows, clusters = _loaded_domain()
    if program.get("program_id") != PROGRAM_ID or not all(
        (
            program.get("provider_execution_authorized") is True,
            program.get("paid_execution_authorized") is True,
            program.get("automatic_stage_progression") is True,
            program.get("stage_by_stage_user_approval_required") is False,
            program.get("private_data_authorized") is False,
            program.get("human_participant_execution_authorized") is False,
        )
    ):
        raise SourceAlignedWordingError("non-human program authority drifted")
    if binding.get("binding_id") != BINDING_ID or binding.get("program_id") != PROGRAM_ID:
        raise SourceAlignedWordingError("source-aligned wording binding identity drifted")
    providers = binding.get("providers", {})
    for role, model in EXPECTED_MODELS.items():
        provider = providers.get(role)
        if (
            not isinstance(provider, dict)
            or provider.get("provider") != "openai"
            or provider.get("first_party_endpoint") is not True
            or provider.get("provider_model") != model
            or provider.get("request_store") is not False
        ):
            raise SourceAlignedWordingError(f"provider binding drifted: {role}")
        payload = DirectProviderJsonTransport(provider)._payload(  # noqa: SLF001
            system="validation",
            prompt="validation",
            task="source-aligned-wording-validation",
            schema=_author_schema(1) if role == AUTHOR_ROLE else _review_schema(1),
        )
        if payload.get("store") is not False or payload.get("model") != model:
            raise SourceAlignedWordingError(f"provider payload drifted: {role}")
    bounds = binding["operational_bounds"]
    if bounds != {
        "clusters_per_batch": 4,
        "logical_call_count": 50,
        "maximum_transport_retries_total": 2,
        "maximum_cost_usd": 4.0,
        "product_calls": 0,
        "final_split_opened": False,
    }:
        raise SourceAlignedWordingError("source-aligned wording bounds drifted")
    return {
        "stage_id": STAGE_ID,
        "program_id": PROGRAM_ID,
        "status": "passed-build-only",
        "case_count": len(case_rows),
        "cluster_count": len(clusters),
        "required_reference_count": sum(len(row.claims) for row in gold_rows),
        "source_sha256": source["content_sha256"],
        "cases_sha256": cases["content_sha256"],
        "gold_sha256": gold["content_sha256"],
        "maximum_calls": bounds["logical_call_count"],
        "maximum_cost_usd": bounds["maximum_cost_usd"],
        "provider_calls": 0,
        "private_data_used": False,
        "human_participants": 0,
        "final_split_opened": False,
    }


def simulate() -> dict[str, Any]:
    _, _, _, cases, gold, clusters = _loaded_domain()
    cluster_by_id = {row.cluster_id: row for row in clusters}
    gold_by_id = {row.case_id: row for row in gold}
    authors = [
        ReferenceQuestionAuthorResponseV1(
            case_id=row.case_id,
            question=context_complete_fallback(
                case=row,
                cluster=cluster_by_id[row.cluster_id],
                forbidden_answer=gold_by_id[row.case_id].canonical_answer,
            ),
        )
        for row in cases
    ]
    reviewers = [
        ReferenceQuestionReviewerResponseV1(
            case_id=row.case_id,
            predicted_action=row.expected_action,
            recovered_answer_spans=[claim.answer_span for claim in row.claims],
            unambiguous=True,
            natural_student_question=True,
            gold_hint_leak=False,
            rationale="Network-free exact semantic recovery.",
        )
        for row in gold
    ]
    result = assemble_source_aligned_wording(
        cases=cases,
        gold=gold,
        clusters=clusters,
        authors=authors,
        reviewers=reviewers,
    )
    return {
        "stage_id": STAGE_ID,
        "status": "simulated-network-free",
        "decision": result["status"],
        "case_count": result["case_count"],
        "model_wording_count": result["model_wording_count"],
        "fallback_wording_count": result["fallback_wording_count"],
        "normalized_duplicate_count": result["normalized_duplicate_count"],
        "provider_calls": 0,
        "network_accessed": False,
    }


def preflight(*, resume: bool) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate()
    except Exception as error:  # noqa: BLE001
        blockers.append(f"validation-failed:{type(error).__name__}")
    binding = _load_hashed(BINDING_PATH)
    verified = datetime.fromisoformat(binding["verified_at"])
    age = (datetime.now(UTC) - verified.astimezone(UTC)).total_seconds() / 3600
    if age < 0 or age > binding["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if _repo_dirty():
        blockers.append("repository-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    if resume and not LEDGER_PATH.is_file():
        blockers.append("resume-ledger-missing")
    if not resume and LEDGER_PATH.exists():
        blockers.append("exclusive-ledger-path-used")
    if OUTPUT_CASES_PATH.exists() or RESULT_PATH.exists():
        blockers.append("exclusive-sanitized-output-path-used")
    return {
        "stage_id": STAGE_ID,
        "status": "ready" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "maximum_calls": 50,
        "maximum_cost_usd": 4.0,
        "provider_calls": 0,
        "credential_value_emitted": False,
    }


async def preflight_live(*, resume: bool) -> dict[str, Any]:
    result = preflight(resume=resume)
    blockers = list(result["blockers"])
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    checked: list[str] = []
    if api_key:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            for model in EXPECTED_MODELS.values():
                try:
                    response = await client.get(
                        f"https://api.openai.com/v1/models/{model}",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    value = response.json()
                except (httpx.HTTPError, ValueError) as error:
                    blockers.append(f"model-metadata-check-failed:{model}:{type(error).__name__}")
                    continue
                if response.is_error or not isinstance(value, dict) or value.get("id") != model:
                    blockers.append(f"model-unavailable-or-identity-drifted:{model}")
                    continue
                checked.append(model)
    result.update(
        {
            "status": "ready" if not blockers else "blocked",
            "blockers": sorted(set(blockers)),
            "live_model_metadata_checked": sorted(checked),
            "provider_inference_calls": 0,
        }
    )
    return result


def _exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise SourceAlignedWordingError(f"exclusive output already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


async def execute(*, resume: bool) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
    require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
    readiness = await preflight_live(resume=resume)
    if readiness["status"] != "ready":
        raise SourceAlignedWordingError(
            "source-aligned wording preflight blocked: " + ", ".join(readiness["blockers"])
        )
    program = _load_hashed(PROGRAM_PATH)
    binding = _load_hashed(BINDING_PATH)
    source_payload, cases_payload, gold_payload, cases, gold, clusters = _loaded_domain()
    gold_by_id = {row.case_id: row for row in gold}
    cases_by_cluster: dict[str, list[EvaluationCaseV1]] = {}
    for case in cases:
        cases_by_cluster.setdefault(case.cluster_id, []).append(case)
    run_binding = {
        "program_id": PROGRAM_ID,
        "program_sha256": program["content_sha256"],
        "stage_id": STAGE_ID,
        "binding_id": BINDING_ID,
        "binding_sha256": binding["content_sha256"],
        "source_sha256": source_payload["content_sha256"],
        "cases_sha256": cases_payload["content_sha256"],
        "gold_sha256": gold_payload["content_sha256"],
        "code_revision": _repo_revision(),
    }
    bounds = binding["operational_bounds"]
    ledger = ProviderCallLedgerV1(
        LEDGER_PATH,
        run_binding=run_binding,
        maximum_calls=bounds["logical_call_count"],
        maximum_cost_usd=bounds["maximum_cost_usd"],
        resume=resume,
        maximum_transport_retries_total=bounds["maximum_transport_retries_total"],
    )
    authors: list[ReferenceQuestionAuthorResponseV1] = []
    reviewers: list[ReferenceQuestionReviewerResponseV1] = []
    semantic_failures: list[dict[str, Any]] = []
    try:
        for batch_number, cluster_batch in enumerate(
            _batches(clusters, bounds["clusters_per_batch"]), start=1
        ):
            batch_cases = [
                case
                for cluster in cluster_batch
                for case in sorted(cases_by_cluster[cluster.cluster_id], key=lambda row: row.case_id)
            ]
            expected_ids = [row.case_id for row in batch_cases]
            author_system, author_prompt = _author_prompt(
                clusters=cluster_batch,
                cases=batch_cases,
                gold_by_id=gold_by_id,
            )
            author_response = await DirectProviderJsonTransport(
                binding["providers"][AUTHOR_ROLE]
            ).call_with_ledger(
                ledger=ledger,
                request_key=f"author-{batch_number:03d}",
                provider_role=AUTHOR_ROLE,
                system=author_system,
                prompt=author_prompt,
                task="source-aligned-question-authoring",
                schema=_author_schema(len(expected_ids)),
            )
            author_rows, author_error = _parse_by_id(
                content=author_response.content,
                expected_ids=expected_ids,
                model=ReferenceQuestionAuthorResponseV1,
            )
            if author_error:
                semantic_failures.append(
                    {"batch": batch_number, "role": AUTHOR_ROLE, "failure": author_error}
                )
                author_rows = []
            author_by_id = {row.case_id: row for row in author_rows}
            review_items = []
            for case in batch_cases:
                authored = author_by_id.get(case.case_id)
                question = (
                    authored.question
                    if authored is not None
                    else context_complete_fallback(
                        case=case,
                        cluster=next(row for row in cluster_batch if row.cluster_id == case.cluster_id),
                        forbidden_answer=gold_by_id[case.case_id].canonical_answer,
                    )
                )
                review_items.append(
                    {
                        "case_id": case.case_id,
                        "cluster_id": case.cluster_id,
                        "course_id": case.course_id,
                        "candidate_question": question,
                    }
                )
            review_system, review_prompt = _review_prompt(
                clusters=cluster_batch,
                items=review_items,
            )
            review_response = await DirectProviderJsonTransport(
                binding["providers"][REVIEWER_ROLE]
            ).call_with_ledger(
                ledger=ledger,
                request_key=f"review-{batch_number:03d}",
                provider_role=REVIEWER_ROLE,
                system=review_system,
                prompt=review_prompt,
                task="source-aligned-question-blind-review",
                schema=_review_schema(len(expected_ids)),
            )
            review_rows, review_error = _parse_by_id(
                content=review_response.content,
                expected_ids=expected_ids,
                model=ReferenceQuestionReviewerResponseV1,
            )
            if review_error:
                semantic_failures.append(
                    {"batch": batch_number, "role": REVIEWER_ROLE, "failure": review_error}
                )
                review_rows = []
            authors.extend(author_rows)
            reviewers.extend(review_rows)
        if ledger.snapshot()["provider_calls"] != bounds["logical_call_count"]:
            ledger.mark_invalid_execution()
            raise SourceAlignedWordingError("source-aligned wording call count drifted")
        assembled = assemble_source_aligned_wording(
            cases=cases,
            gold=gold,
            clusters=clusters,
            authors=authors,
            reviewers=reviewers,
        )
        ledger.mark_complete()
        snapshot = ledger.snapshot()
    except KeyboardInterrupt:
        ledger.mark_interrupted()
        raise
    except Exception:
        if ledger.snapshot().get("status") == "running":
            ledger.mark_invalid_execution()
        raise
    finally:
        ledger.close()

    cases_package: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": STAGE_ID,
        "source_plan_sha256": source_payload["content_sha256"],
        "base_cases_sha256": cases_payload["content_sha256"],
        "wording_binding_sha256": binding["content_sha256"],
        "case_count": 500,
        "cases": assembled["cases"],
        "provider_calls": snapshot["provider_calls"],
        "private_data_used": False,
        "known_benchmark": False,
        "final_split_opened": False,
    }
    cases_package["content_sha256"] = canonical_json_sha256(cases_package)
    rejection_counts = Counter(
        reason
        for row in assembled["decisions"]
        for reason in row["advisory_rejection_reasons"]
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": STAGE_ID,
        "program_id": PROGRAM_ID,
        "decision": assembled["status"],
        "code_revision": run_binding["code_revision"],
        "source_sha256": source_payload["content_sha256"],
        "base_cases_sha256": cases_payload["content_sha256"],
        "gold_sha256": gold_payload["content_sha256"],
        "output_cases_sha256": cases_package["content_sha256"],
        "binding_sha256": binding["content_sha256"],
        "case_count": assembled["case_count"],
        "model_wording_count": assembled["model_wording_count"],
        "fallback_wording_count": assembled["fallback_wording_count"],
        "normalized_duplicate_count": assembled["normalized_duplicate_count"],
        "semantic_batch_failures": semantic_failures,
        "advisory_rejection_counts": dict(sorted(rejection_counts.items())),
        "provider_accounting": {
            key: snapshot[key]
            for key in (
                "provider_calls",
                "provider_attempts",
                "recovered_transport_failures",
                "failed_calls",
                "input_tokens",
                "output_tokens",
                "maximum_latency_ms",
                "reported_cost_usd",
            )
        },
        "deterministic_truth_authoritative": True,
        "agent_reviews_authoritative": False,
        "review_independence_limitation": binding["review_independence_disclosure"],
        "private_data_used": False,
        "human_participants": 0,
        "final_split_opened": False,
    }
    result["content_sha256"] = canonical_json_sha256(result)
    _exclusive_json(OUTPUT_CASES_PATH, cases_package)
    _exclusive_json(RESULT_PATH, result)
    return result


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--preflight-live", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--attempt", choices=ATTEMPT_SUFFIXES, default="001")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    _select_attempt(arguments.attempt)
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate()
    elif arguments.simulate:
        result = simulate()
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.preflight_live:
        result = asyncio.run(preflight_live(resume=arguments.resume))
    else:
        result = asyncio.run(execute(resume=arguments.resume))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
