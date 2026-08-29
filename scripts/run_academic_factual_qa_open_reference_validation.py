#!/usr/bin/env python3
"""Run the finite source-visible author and target-blind reviewer checkpoint."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any, Iterable

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_open_reference_validation import (  # noqa: E402
    TARGET_ALLOCATION,
    author_requests,
    build_reference_pool,
)
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
    score_reference_questions,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    SourceClusterV2,
)
from src.digital_twin.evaluation.provider_json import (  # noqa: E402
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonResponse,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


AUTHOR_ROLE = "source-visible-question-author"
REVIEWER_ROLE = "target-blind-answer-reviewer"


@dataclass(frozen=True)
class ReferenceQuestionAttempt:
    instrument_id: str
    binding_id: str
    instrument_path: Path
    binding_path: Path
    ledger_path: Path
    result_path: Path
    cases_path: Path
    gold_path: Path
    author_question_pattern: str | None = None


def _attempt(*, suffix: str, question_pattern: str | None) -> ReferenceQuestionAttempt:
    return ReferenceQuestionAttempt(
        instrument_id=(
            "academic-factual-qa-open-10000-reference-question-validation-" + suffix
        ),
        binding_id=(
            "academic-factual-qa-open-10000-reference-question-binding-" + suffix
        ),
        instrument_path=ROOT
        / (
            "research/05_evaluation/instruments/"
            "academic_factual_qa_open_10000_reference_question_validation_"
            + suffix
            + ".json"
        ),
        binding_path=ROOT
        / (
            "research/05_evaluation/instruments/"
            "academic_factual_qa_open_10000_reference_question_binding_"
            + suffix
            + ".json"
        ),
        ledger_path=ROOT
        / (
            "reports/generated/academic-factual-qa-open-10000-reference-question-"
            "validation-" + suffix + ".sqlite3"
        ),
        result_path=ROOT
        / (
            "reports/generated/academic-factual-qa-open-10000-reference-question-"
            "validation-" + suffix + "-result.json"
        ),
        cases_path=ROOT
        / (
            "research/05_evaluation/datasets/"
            "academic_factual_qa_open_10000_v1_development_reference_validated_"
            + suffix
            + "_cases.json"
        ),
        gold_path=ROOT
        / (
            "research/05_evaluation/datasets/"
            "academic_factual_qa_open_10000_v1_development_reference_validated_"
            + suffix
            + "_gold.json"
        ),
        author_question_pattern=question_pattern,
    )


ATTEMPT_001 = _attempt(suffix="001", question_pattern=None)
ATTEMPT_002 = _attempt(suffix="002", question_pattern=r"\?$")
ATTEMPTS = {
    ATTEMPT_001.instrument_id: ATTEMPT_001,
    ATTEMPT_002.instrument_id: ATTEMPT_002,
}


class ReferenceQuestionCheckpointError(RuntimeError):
    """Raised when the frozen reference-question checkpoint drifts."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReferenceQuestionCheckpointError(
            f"JSON root is not an object: {path.name}"
        )
    return value


def _load_hashed(path: Path, *, key: str, identity: str) -> dict[str, Any]:
    value = _load(path)
    if value.get(key) != identity:
        raise ReferenceQuestionCheckpointError(f"identity drifted: {path.name}")
    observed = canonical_json_sha256(
        {field: row for field, row in value.items() if field != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise ReferenceQuestionCheckpointError(f"content hash drifted: {path.name}")
    return value


def _instrument(attempt: ReferenceQuestionAttempt = ATTEMPT_001) -> dict[str, Any]:
    return _load_hashed(
        attempt.instrument_path,
        key="instrument_id",
        identity=attempt.instrument_id,
    )


def _binding(attempt: ReferenceQuestionAttempt = ATTEMPT_001) -> dict[str, Any]:
    return _load_hashed(
        attempt.binding_path,
        key="binding_id",
        identity=attempt.binding_id,
    )


def _batches(rows: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _author_schema(
    count: int, *, attempt: ReferenceQuestionAttempt = ATTEMPT_001
) -> dict[str, Any]:
    schema: dict[str, Any] = {
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
                        },
                    },
                },
            }
        },
    }
    if attempt.author_question_pattern is not None:
        schema["properties"]["items"]["items"]["properties"]["question"]["pattern"] = (
            attempt.author_question_pattern
        )
    return schema


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
                            "minItems": 0,
                            "maxItems": 2,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "unambiguous": {"type": "boolean"},
                        "natural_student_question": {"type": "boolean"},
                        "gold_hint_leak": {"type": "boolean"},
                        "rationale": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 400,
                        },
                    },
                },
            }
        },
    }


def _source_rows(clusters: list[SourceClusterV2]) -> list[dict[str, Any]]:
    return [
        {
            "cluster_id": row.cluster_id,
            "source_course_id": row.course_id,
            "section_heading": row.section_heading,
            "source_text": row.text,
        }
        for row in clusters
    ]


def _author_prompt(
    *, clusters: list[SourceClusterV2], requests: list[dict[str, Any]]
) -> tuple[str, str]:
    system = (
        "Write one clear, natural student question per item using only its supplied "
        "public source. The question must uniquely require the expected action. For "
        "answer cases it must uniquely elicit every required answer span without "
        "copying the full canonical answer into the question. For abstain, clarify, "
        "and refuse cases it must clearly instantiate the stated boundary. Do not "
        "change case IDs and return only the requested schema."
    )
    prompt = json.dumps(
        {"sources": _source_rows(clusters), "construction_items": requests},
        sort_keys=True,
    )
    return system, prompt


def _review_prompt(
    *, clusters: list[SourceClusterV2], items: list[dict[str, Any]]
) -> tuple[str, str]:
    system = (
        "Independently validate each candidate question using only its supplied "
        "public source. You are not given the intended action or answer. Predict "
        "answer, abstain, clarify, or refuse. For answer, return every exact source "
        "span needed to answer, in question order. For other actions return no "
        "spans. Mark unambiguous only when one action and answer are uniquely "
        "determined. Mark gold_hint_leak when the question reveals its answer. "
        "Return only the requested schema."
    )
    prompt = json.dumps(
        {"sources": _source_rows(clusters), "blind_review_items": items},
        sort_keys=True,
    )
    return system, prompt


def _parse_authors(
    content: dict[str, Any], expected_ids: list[str]
) -> list[ReferenceQuestionAuthorResponseV1]:
    rows = [
        ReferenceQuestionAuthorResponseV1.model_validate(row)
        for row in content.get("items", [])
    ]
    if [row.case_id for row in rows] != expected_ids:
        raise ReferenceQuestionCheckpointError("author response IDs or order drifted")
    return rows


def _parse_reviews(
    content: dict[str, Any], expected_ids: list[str]
) -> list[ReferenceQuestionReviewerResponseV1]:
    rows = [
        ReferenceQuestionReviewerResponseV1.model_validate(row)
        for row in content.get("items", [])
    ]
    if [row.case_id for row in rows] != expected_ids:
        raise ReferenceQuestionCheckpointError("review response IDs or order drifted")
    return rows


def _git_revision() -> str:
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


def validate(
    *,
    require_unauthorized: bool = True,
    attempt: ReferenceQuestionAttempt = ATTEMPT_001,
) -> dict[str, Any]:
    instrument = _instrument(attempt)
    binding = _binding(attempt)
    pool = build_reference_pool()
    if pool["content_sha256"] != instrument["dataset"]["source_pool_sha256"]:
        raise ReferenceQuestionCheckpointError("fresh source-pool hash drifted")
    if set(binding["providers"]) != {AUTHOR_ROLE, REVIEWER_ROLE}:
        raise ReferenceQuestionCheckpointError("reference provider roles drifted")
    if any(row["provider"] != "openai" for row in binding["providers"].values()):
        raise ReferenceQuestionCheckpointError("non-OpenAI provider entered checkpoint")
    clusters = [SourceClusterV2.model_validate(row) for row in pool["clusters"][:4]]
    ids = {row.cluster_id for row in clusters}
    requests = [row for row in author_requests(pool) if row["cluster_id"] in ids]
    author_system, author_prompt = _author_prompt(clusters=clusters, requests=requests)
    authors = [
        ReferenceQuestionAuthorResponseV1(
            case_id=row["case_id"],
            question=f"What does the source establish for reference {row['case_id']}?",
        )
        for row in requests
    ]
    review_items = [
        {
            "case_id": row.case_id,
            "cluster_id": row.case_id.rsplit("-q", 1)[0],
            "course_id": next(
                request["course_id"]
                for request in requests
                if request["case_id"] == row.case_id
            ),
            "candidate_question": row.question,
        }
        for row in authors
    ]
    review_system, review_prompt = _review_prompt(clusters=clusters, items=review_items)
    author_transport = DirectProviderJsonTransport(binding["providers"][AUTHOR_ROLE])
    reviewer_transport = DirectProviderJsonTransport(
        binding["providers"][REVIEWER_ROLE]
    )
    author_payload = author_transport._payload(  # noqa: SLF001
        system=author_system,
        prompt=author_prompt,
        task="reference-question-author-contract",
        schema=_author_schema(len(requests), attempt=attempt),
    )
    review_payload = reviewer_transport._payload(  # noqa: SLF001
        system=review_system,
        prompt=review_prompt,
        task="reference-question-review-contract",
        schema=_review_schema(len(requests)),
    )
    if (
        author_payload.get("store") is not False
        or review_payload.get("store") is not False
    ):
        raise ReferenceQuestionCheckpointError("reference request store=false drifted")
    serialized = json.dumps(
        {"author": author_payload, "reviewer": review_payload}, sort_keys=True
    ).casefold()
    if any(
        name in serialized for name in ("openrouter", "deepseek", "gemini", "mistral")
    ):
        raise ReferenceQuestionCheckpointError(
            "retired provider leaked into checkpoint"
        )
    if any(
        key in review_items[0]
        for key in ("expected_action", "canonical_answer", "required_answer_spans")
    ):
        raise ReferenceQuestionCheckpointError("blind reviewer input exposes truth")
    question_schema = author_payload["text"]["format"]["schema"]["properties"]["items"][
        "items"
    ]["properties"]["question"]
    if (
        attempt.author_question_pattern is not None
        and question_schema.get("pattern") != attempt.author_question_pattern
    ):
        raise ReferenceQuestionCheckpointError("author question schema pattern drifted")
    if require_unauthorized and (
        any(instrument["authorization"].values())
        or any(binding["authorization"].values())
    ):
        raise ReferenceQuestionCheckpointError("build-only authority drifted")
    return {
        "instrument_id": attempt.instrument_id,
        "binding_id": attempt.binding_id,
        "status": "passed-build-only",
        "candidate_cluster_count": pool["candidate_cluster_count"],
        "candidate_case_count": pool["candidate_case_count"],
        "target_cluster_count": pool["target_cluster_count"],
        "target_case_count": pool["target_case_count"],
        "batch_count": instrument["dataset"]["batch_count"],
        "maximum_calls": instrument["operational_bounds"]["maximum_logical_calls"],
        "source_disjoint_from_checkpoint_007": True,
        "strict_schema_requested": True,
        "author_question_pattern": attempt.author_question_pattern,
        "openai_store": False,
        "provider_calls": 0,
        "product_calls": 0,
        "private_data_used": False,
        "final_split_opened": False,
    }


def _simulated_votes() -> tuple[
    dict[str, Any],
    list[ReferenceQuestionAuthorResponseV1],
    list[ReferenceQuestionReviewerResponseV1],
]:
    pool = build_reference_pool()
    cases = [EvaluationCaseV1.model_validate(row) for row in pool["base_cases"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in pool["gold"]]
    gold_by_id = {row.case_id: row for row in gold}
    authors = [
        ReferenceQuestionAuthorResponseV1(
            case_id=row.case_id,
            question=f"What should a student determine for source case {row.case_id}?",
        )
        for row in cases
    ]
    reviewers = [
        ReferenceQuestionReviewerResponseV1(
            case_id=row.case_id,
            predicted_action=gold_by_id[row.case_id].expected_action,
            recovered_answer_spans=[
                claim.answer_span for claim in gold_by_id[row.case_id].claims
            ],
            unambiguous=True,
            natural_student_question=True,
            gold_hint_leak=False,
            rationale="Network-free simulated independent recovery.",
        )
        for row in cases
    ]
    return pool, authors, reviewers


def simulate(*, attempt: ReferenceQuestionAttempt = ATTEMPT_001) -> dict[str, Any]:
    pool, authors, reviewers = _simulated_votes()
    score = score_reference_questions(
        base_cases=[EvaluationCaseV1.model_validate(row) for row in pool["base_cases"]],
        gold=[EvaluationGoldV1.model_validate(row) for row in pool["gold"]],
        cluster_modalities={
            row["cluster_id"]: row["source_modality"] for row in pool["clusters"]
        },
        authors=authors,
        reviewers=reviewers,
        target_allocation=TARGET_ALLOCATION,
    )
    return {
        "instrument_id": attempt.instrument_id,
        "status": "simulated-network-free",
        "decision": score["status"],
        "candidate_case_count": score["candidate_case_count"],
        "passed_case_count": score["passed_case_count"],
        "selected_cluster_count": score["selected_cluster_count"],
        "selected_case_count": score["selected_case_count"],
        "allocation_shortfalls": score["allocation_shortfalls"],
        "provider_calls": 0,
        "network_accessed": False,
        "product_calls": 0,
        "final_split_opened": False,
    }


def preflight(
    *,
    resume: bool = False,
    attempt: ReferenceQuestionAttempt = ATTEMPT_001,
) -> dict[str, Any]:
    instrument = _instrument(attempt)
    binding = _binding(attempt)
    blockers: list[str] = []
    try:
        validate(require_unauthorized=False, attempt=attempt)
    except Exception as error:  # noqa: BLE001
        blockers.append(f"build-validation-failed:{type(error).__name__}")
    if _repo_dirty():
        blockers.append("repository-dirty")
    if resume and not attempt.ledger_path.is_file():
        blockers.append("resume-ledger-missing")
    if not resume and attempt.ledger_path.exists():
        blockers.append("exclusive-ledger-path-used")
    if attempt.result_path.exists():
        blockers.append("exclusive-result-path-used")
    operations = set(BOUNDED_PILOT_AUTHORIZATIONS.get(attempt.instrument_id, ()))
    for operation in ("external_model_evaluation", "method_evaluation_execution"):
        if operation not in operations:
            blockers.append(f"freeze-{operation}-authorization-missing")
    for key in (
        "provider_execution_authorized",
        "paid_execution_authorized",
        "reference_question_validation_authorized",
    ):
        if not instrument["authorization"][key]:
            blockers.append(f"instrument-{key.replace('_', '-')}-false")
        if not binding["authorization"][key]:
            blockers.append(f"binding-{key.replace('_', '-')}-false")
    for provider in binding["providers"].values():
        variable = provider["credential_environment_variable"]
        if not os.getenv(variable, "").strip():
            blockers.append(f"{variable.casefold()}-missing")
    verified = datetime.fromisoformat(binding["verified_at"])
    age_hours = (
        datetime.now(timezone.utc) - verified.astimezone(timezone.utc)
    ).total_seconds() / 3600
    if age_hours < 0 or age_hours > binding["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if instrument["authorization"]["product_development_execution_authorized"]:
        blockers.append("product-development-must-remain-unauthorized")
    if instrument["authorization"]["final_execution_authorized"]:
        blockers.append("final-execution-must-remain-unauthorized")
    return {
        "instrument_id": attempt.instrument_id,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": sorted(set(blockers)),
        "maximum_calls": instrument["operational_bounds"]["maximum_logical_calls"],
        "maximum_cost_usd": instrument["operational_bounds"]["maximum_cost_usd"],
        "provider_calls": 0,
        "product_calls": 0,
        "credential_values_emitted": False,
        "final_split_opened": False,
    }


async def execute(
    *, resume: bool, attempt: ReferenceQuestionAttempt = ATTEMPT_001
) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(
        attempt.instrument_id, "external_model_evaluation"
    )
    instrument = _instrument(attempt)
    binding = _binding(attempt)
    for record in (instrument, binding):
        if not all(
            record["authorization"][key]
            for key in (
                "provider_execution_authorized",
                "paid_execution_authorized",
                "reference_question_validation_authorized",
            )
        ):
            raise ReferenceQuestionCheckpointError(
                "reference execution is unauthorized"
            )
    readiness = preflight(resume=resume, attempt=attempt)
    if readiness["status"] != "ready":
        raise ReferenceQuestionCheckpointError(
            "reference preflight blocked: " + ", ".join(readiness["blockers"])
        )
    pool = build_reference_pool()
    clusters = [SourceClusterV2.model_validate(row) for row in pool["clusters"]]
    requests = author_requests(pool)
    requests_by_cluster: dict[str, list[dict[str, Any]]] = {}
    for row in requests:
        requests_by_cluster.setdefault(row["cluster_id"], []).append(row)
    run_binding = {
        "instrument_id": attempt.instrument_id,
        "instrument_sha256": instrument["content_sha256"],
        "binding_id": attempt.binding_id,
        "binding_sha256": binding["content_sha256"],
        "source_pool_sha256": pool["content_sha256"],
        "code_revision": _git_revision(),
    }
    ledger = ProviderCallLedgerV1(
        attempt.ledger_path,
        run_binding=run_binding,
        maximum_calls=instrument["operational_bounds"]["maximum_logical_calls"],
        maximum_cost_usd=instrument["operational_bounds"]["maximum_cost_usd"],
        resume=resume,
    )
    try:
        for batch_number, cluster_batch in enumerate(
            _batches(clusters, instrument["dataset"]["clusters_per_batch"]), start=1
        ):
            batch_requests = [
                row
                for cluster in cluster_batch
                for row in requests_by_cluster[cluster.cluster_id]
            ]
            expected_ids = [row["case_id"] for row in batch_requests]
            author_system, author_prompt = _author_prompt(
                clusters=cluster_batch, requests=batch_requests
            )
            author_transport = DirectProviderJsonTransport(
                binding["providers"][AUTHOR_ROLE]
            )
            authored = await author_transport.call_with_ledger(
                ledger=ledger,
                request_key=f"author-{batch_number:03d}",
                provider_role=AUTHOR_ROLE,
                system=author_system,
                prompt=author_prompt,
                task="academic-reference-question-authoring",
                schema=_author_schema(len(expected_ids), attempt=attempt),
            )
            author_rows = _parse_authors(authored.content, expected_ids)
            request_by_id = {row["case_id"]: row for row in batch_requests}
            review_items = [
                {
                    "case_id": row.case_id,
                    "cluster_id": request_by_id[row.case_id]["cluster_id"],
                    "course_id": request_by_id[row.case_id]["course_id"],
                    "candidate_question": row.question,
                }
                for row in author_rows
            ]
            review_system, review_prompt = _review_prompt(
                clusters=cluster_batch, items=review_items
            )
            reviewer_transport = DirectProviderJsonTransport(
                binding["providers"][REVIEWER_ROLE]
            )
            reviewed = await reviewer_transport.call_with_ledger(
                ledger=ledger,
                request_key=f"review-{batch_number:03d}",
                provider_role=REVIEWER_ROLE,
                system=review_system,
                prompt=review_prompt,
                task="academic-reference-question-blind-review",
                schema=_review_schema(len(expected_ids)),
            )
            _parse_reviews(reviewed.content, expected_ids)
        snapshot = ledger.snapshot()
        if (
            snapshot["provider_calls"]
            != instrument["operational_bounds"]["maximum_logical_calls"]
        ):
            ledger.mark_invalid_execution()
            raise ReferenceQuestionCheckpointError("reference call count drifted")
        ledger.mark_complete()
        return {**ledger.snapshot(), "instrument_id": attempt.instrument_id}
    except KeyboardInterrupt:
        ledger.mark_interrupted()
        raise
    except Exception:
        ledger.mark_invalid_execution()
        raise
    finally:
        ledger.close()


def _ledger_rows(
    attempt: ReferenceQuestionAttempt = ATTEMPT_001,
) -> tuple[dict[str, str], list[tuple[str, ProviderJsonResponse]]]:
    if not attempt.ledger_path.is_file():
        raise ReferenceQuestionCheckpointError("reference ledger does not exist")
    connection = sqlite3.connect(attempt.ledger_path)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        rows = connection.execute(
            "SELECT provider_role, response_json FROM calls "
            "WHERE status = 'completed' ORDER BY sequence"
        ).fetchall()
    finally:
        connection.close()
    return metadata, [
        (role, ProviderJsonResponse.model_validate_json(response))
        for role, response in rows
    ]


def score(attempt: ReferenceQuestionAttempt = ATTEMPT_001) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(
        attempt.instrument_id, "method_evaluation_execution"
    )
    instrument = _instrument(attempt)
    metadata, rows = _ledger_rows(attempt)
    if metadata.get("status") != "completed":
        raise ReferenceQuestionCheckpointError("reference ledger is not complete")
    if len(rows) != instrument["operational_bounds"]["maximum_logical_calls"]:
        raise ReferenceQuestionCheckpointError("reference ledger coverage drifted")
    authors: list[ReferenceQuestionAuthorResponseV1] = []
    reviewers: list[ReferenceQuestionReviewerResponseV1] = []
    for role, response in rows:
        if role == AUTHOR_ROLE:
            authors.extend(
                ReferenceQuestionAuthorResponseV1.model_validate(row)
                for row in response.content.get("items", [])
            )
        elif role == REVIEWER_ROLE:
            reviewers.extend(
                ReferenceQuestionReviewerResponseV1.model_validate(row)
                for row in response.content.get("items", [])
            )
        else:
            raise ReferenceQuestionCheckpointError("unknown reference provider role")
    pool = build_reference_pool()
    scored = score_reference_questions(
        base_cases=[EvaluationCaseV1.model_validate(row) for row in pool["base_cases"]],
        gold=[EvaluationGoldV1.model_validate(row) for row in pool["gold"]],
        cluster_modalities={
            row["cluster_id"]: row["source_modality"] for row in pool["clusters"]
        },
        authors=authors,
        reviewers=reviewers,
        target_allocation=TARGET_ALLOCATION,
    )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": attempt.instrument_id,
        "binding_id": attempt.binding_id,
        "source_pool_sha256": pool["content_sha256"],
        **scored,
        "provider_calls": len(rows),
        "product_calls": 0,
        "private_data_used": False,
        "final_split_opened": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    if attempt.result_path.exists():
        raise ReferenceQuestionCheckpointError("reference result path already exists")
    attempt.result_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        attempt.result_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return {
        key: value
        for key, value in payload.items()
        if key not in {"decisions", "selected_cases", "selected_gold"}
    }


def _package(
    *,
    dataset_id: str,
    rows_key: str,
    rows: list[dict[str, Any]],
    attempt: ReferenceQuestionAttempt = ATTEMPT_001,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "construction_instrument_id": attempt.instrument_id,
        "case_count": len(rows),
        rows_key: rows,
        "private_data_used": False,
        "final_split_opened": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def materialize(attempt: ReferenceQuestionAttempt = ATTEMPT_001) -> dict[str, Any]:
    result = _load_hashed(
        attempt.result_path,
        key="instrument_id",
        identity=attempt.instrument_id,
    )
    if result.get("status") != "completed-go-deeper":
        raise ReferenceQuestionCheckpointError(
            "only a passing reference result can materialize"
        )
    if result.get("selected_case_count") != 500:
        raise ReferenceQuestionCheckpointError("selected reference set is incomplete")
    packages = {
        attempt.cases_path: _package(
            dataset_id=(
                "academic-factual-qa-open-10000-v1-development-reference-validated-"
                + attempt.instrument_id.rsplit("-", 1)[-1]
            ),
            rows_key="cases",
            rows=result["selected_cases"],
            attempt=attempt,
        ),
        attempt.gold_path: _package(
            dataset_id=(
                "academic-factual-qa-open-10000-v1-development-reference-validated-"
                + attempt.instrument_id.rsplit("-", 1)[-1]
                + "-gold"
            ),
            rows_key="gold",
            rows=result["selected_gold"],
            attempt=attempt,
        ),
    }
    if any(path.exists() for path in packages):
        raise ReferenceQuestionCheckpointError(
            "reference package output already exists"
        )
    for path, payload in packages.items():
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return {
        "instrument_id": attempt.instrument_id,
        "status": "materialized",
        "case_count": 500,
        "cases_content_sha256": packages[attempt.cases_path]["content_sha256"],
        "gold_content_sha256": packages[attempt.gold_path]["content_sha256"],
        "provider_calls": 0,
        "product_calls": 0,
        "final_split_opened": False,
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--score", action="store_true")
    mode.add_argument("--materialize", action="store_true")
    parser.add_argument(
        "--attempt",
        choices=sorted(ATTEMPTS),
        default=ATTEMPT_001.instrument_id,
    )
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    attempt = ATTEMPTS[arguments.attempt]
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            attempt.instrument_id, "external_model_evaluation"
        )
    if arguments.score:
        require_bounded_pilot_operation_allowed(
            attempt.instrument_id, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate(require_unauthorized=False, attempt=attempt)
    elif arguments.simulate:
        result = simulate(attempt=attempt)
    elif arguments.preflight:
        result = preflight(resume=arguments.resume, attempt=attempt)
    elif arguments.execute:
        result = asyncio.run(execute(resume=arguments.resume, attempt=attempt))
    elif arguments.score:
        result = score(attempt)
    else:
        result = materialize(attempt)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
