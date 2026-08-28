#!/usr/bin/env python3
"""Run the non-blocking GPT-5.4 audit after deterministic development scoring.

The deterministic result is already complete before this module opens hidden
gold. Provider failures are durable limitations; they never rewrite or
invalidate deterministic measurements.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import subprocess
from typing import Any, Iterable

from dotenv import load_dotenv

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
)
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderJsonResponse,
    canonical_sha256,
)
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
GENERATED = ROOT / "reports/generated"
CASES_PATH = GENERATED / "academic-factual-qa-open-10000-v1-development-004-cases.json"
GOLD_PATH = GENERATED / "academic-factual-qa-open-10000-v1-development-004-gold.json"
RESPONSES_PATH = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-candidate-responses.sqlite3"
)
DETERMINISTIC_RESULT_PATH = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-candidate-result.json"
)
LEDGER_PATH = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-advisory-audit.sqlite3"
)
RESULT_PATH = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-004-advisory-audit-result.json"
)
REVIEWER_ROLE = "semantic-reviewer"


class AdvisoryAuditError(RuntimeError):
    """Raised when the audit harness itself violates its frozen contract."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdvisoryAuditError(f"JSON root is not an object: {path.name}")
    return value


def _load_hashed(path: Path, *, identity_key: str, identity: str) -> dict[str, Any]:
    value = _load(path)
    if value.get(identity_key) != identity:
        raise AdvisoryAuditError(f"identity drifted: {path.name}")
    expected = canonical_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise AdvisoryAuditError(f"content hash drifted: {path.name}")
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


def _batches(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _case_passed(row: dict[str, Any]) -> bool:
    return bool(
        row["fully_grounded_success"] if row["answerable"] else row["boundary_safe"]
    )


def select_audit_cases(
    case_scores: list[dict[str, Any]], *, passing_sample_count: int, seed: int
) -> tuple[list[str], list[str]]:
    failures = sorted(row["case_id"] for row in case_scores if not _case_passed(row))
    passing = sorted(row["case_id"] for row in case_scores if _case_passed(row))
    rng = random.Random(seed)
    sample = sorted(rng.sample(passing, min(passing_sample_count, len(passing))))
    return failures, sample


def _schema(count: int) -> dict[str, Any]:
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
                        "semantic_support",
                        "action_assessment",
                        "answer_assessment",
                        "citation_assessment",
                        "potential_authoritative_truth_defect",
                        "rationale",
                    ],
                    "properties": {
                        "case_id": {"type": "string", "minLength": 1},
                        "semantic_support": {
                            "type": "string",
                            "enum": ["supported", "unsupported", "unclear"],
                        },
                        "action_assessment": {
                            "type": "string",
                            "enum": ["correct", "incorrect", "unclear"],
                        },
                        "answer_assessment": {
                            "type": "string",
                            "enum": [
                                "supported",
                                "unsupported",
                                "not-applicable",
                                "unclear",
                            ],
                        },
                        "citation_assessment": {
                            "type": "string",
                            "enum": [
                                "complete",
                                "incomplete",
                                "invalid",
                                "not-applicable",
                                "unclear",
                            ],
                        },
                        "potential_authoritative_truth_defect": {"type": "boolean"},
                        "rationale": {"type": "string", "minLength": 1, "maxLength": 320},
                    },
                },
            }
        },
    }


def _prompt(rows: list[dict[str, Any]]) -> tuple[str, str]:
    system = (
        "Audit the supplied source-linked factual-QA records. Deterministic source, "
        "action, claim, and citation checks are authoritative. Your review is advisory: "
        "identify semantic limitations and flag a potential reference-truth defect only "
        "when the supplied canonical answer or expected action appears internally "
        "inconsistent with the question. Do not invent outside facts. Return only the schema."
    )
    return system, json.dumps({"audit_records": rows}, sort_keys=True)


def _parse_items(content: dict[str, Any], expected_ids: list[str]) -> list[dict[str, Any]]:
    items = content.get("items")
    if not isinstance(items, list) or [row.get("case_id") for row in items] != expected_ids:
        raise AdvisoryAuditError("advisory response IDs or order drifted")
    return items


def _validated_package(path: Path, *, rows_key: str) -> dict[str, Any]:
    value = _load(path)
    expected = canonical_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise AdvisoryAuditError(f"package hash drifted: {path.name}")
    if value.get("case_count") != len(value.get(rows_key, [])):
        raise AdvisoryAuditError(f"package count drifted: {path.name}")
    return value


def _responses() -> dict[str, EvaluationResponseV1]:
    connection = sqlite3.connect(f"file:{RESPONSES_PATH}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        if metadata.get("status") != "completed" or metadata.get("response_count") != "500":
            raise AdvisoryAuditError("candidate response ledger is incomplete")
        rows = connection.execute(
            "SELECT case_id, payload_json, payload_sha256 FROM responses ORDER BY sequence"
        ).fetchall()
    finally:
        connection.close()
    output: dict[str, EvaluationResponseV1] = {}
    for case_id, serialized, expected_hash in rows:
        if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != expected_hash:
            raise AdvisoryAuditError(f"response hash drifted: {case_id}")
        output[case_id] = EvaluationResponseV1.model_validate_json(serialized)
    return output


def _failure_reasons(score: dict[str, Any]) -> list[str]:
    checks = {
        "action": score["action_correct"],
        "answer-span": score["answer_span_recall"] == 1.0,
        "claim-precision": score["atomic_claim_precision"] == 1.0,
        "claim-recall": score["atomic_claim_recall"] == 1.0,
        "citation-precision": score["citation_precision"] == 1.0,
        "citation-recall": score["citation_recall"] == 1.0,
        "source-version": score["source_version_valid"],
        "boundary-safety": score["boundary_safe"] if not score["answerable"] else True,
        "operational": not score["operational_failure"],
    }
    return [key for key, passed in checks.items() if not passed]


def build_audit_rows() -> tuple[list[dict[str, Any]], list[str], list[str]]:
    result = _load(DETERMINISTIC_RESULT_PATH)
    if result.get("status") not in {"completed-keep", "completed-refine"}:
        raise AdvisoryAuditError("deterministic result is not complete")
    instrument = _load_hashed(
        INSTRUMENT_PATH, identity_key="instrument_id", identity=INSTRUMENT_ID
    )
    failures, sample = select_audit_cases(
        result["case_scores"],
        passing_sample_count=instrument["advisory_audit"]["passing_sample_count"],
        seed=instrument["advisory_audit"]["passing_sample_seed"],
    )
    cases = {
        row.case_id: row
        for row in (
            EvaluationCaseV1.model_validate(value)
            for value in _validated_package(CASES_PATH, rows_key="cases")["cases"]
        )
    }
    gold = {
        row.case_id: row
        for row in (
            EvaluationGoldV1.model_validate(value)
            for value in _validated_package(GOLD_PATH, rows_key="gold")["gold"]
        )
    }
    responses = _responses()
    scores = {row["case_id"]: row for row in result["case_scores"]}
    selected = failures + [case_id for case_id in sample if case_id not in set(failures)]
    rows: list[dict[str, Any]] = []
    for case_id in selected:
        case = cases[case_id]
        reference = gold[case_id]
        response = responses[case_id]
        score = scores[case_id]
        rows.append(
            {
                "case_id": case_id,
                "selection": "deterministic-failure" if case_id in failures else "seeded-pass",
                "course_id": case.course_id,
                "slice": case.slice,
                "question": case.question,
                "expected_action": reference.expected_action.value,
                "canonical_answer": reference.canonical_answer,
                "canonical_claim_spans": [row.answer_span for row in reference.claims],
                "boundary_reason": reference.boundary_reason,
                "actual_action": response.action.value,
                "answer": response.answer,
                "atomic_claims": [row.text for row in response.atomic_claims],
                "citation_count": len(response.citations),
                "deterministic_failure_reasons": _failure_reasons(score),
            }
        )
    return rows, failures, sample


class AdvisoryLedger:
    """Hash-bound SQLite ledger that permits recorded non-blocking failures."""

    def __init__(self, *, binding: dict[str, Any], maximum_calls: int, maximum_cost: float, resume: bool) -> None:
        self.maximum_calls = maximum_calls
        self.maximum_cost = maximum_cost
        expected = {
            "schema_version": "1",
            "run_binding_sha256": canonical_sha256(binding),
            "maximum_calls": str(maximum_calls),
            "maximum_cost_usd": str(maximum_cost),
        }
        if resume and not LEDGER_PATH.is_file():
            raise AdvisoryAuditError("advisory resume ledger is missing")
        if not resume and LEDGER_PATH.exists():
            raise AdvisoryAuditError("advisory ledger already exists")
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not resume:
            descriptor = os.open(LEDGER_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self.connection = sqlite3.connect(LEDGER_PATH, isolation_level=None)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                request_key TEXT NOT NULL UNIQUE,
                request_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                response_json TEXT,
                failure_type TEXT,
                failure_detail TEXT,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                latency_ms REAL NOT NULL DEFAULT 0
            )
            """
        )
        if resume:
            actual = dict(self.connection.execute("SELECT key, value FROM metadata"))
            if any(actual.get(key) != value for key, value in expected.items()):
                raise AdvisoryAuditError("advisory resume binding drifted")
            if actual.get("status") not in {"running", "interrupted"}:
                raise AdvisoryAuditError("advisory ledger is terminal")
            self._set("status", "running")
        else:
            with self.connection:
                for key, value in {**expected, "status": "running"}.items():
                    self.connection.execute("INSERT INTO metadata VALUES (?, ?)", (key, value))

    def _set(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO metadata VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def existing(self, request_key: str, request_sha256: str) -> bool:
        row = self.connection.execute(
            "SELECT request_sha256 FROM calls WHERE request_key=?", (request_key,)
        ).fetchone()
        if row is None:
            return False
        if row[0] != request_sha256:
            raise AdvisoryAuditError("advisory replay request drifted")
        return True

    def totals(self) -> tuple[int, float]:
        row = self.connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM calls"
        ).fetchone()
        return int(row[0]), float(row[1])

    def reserve(self, estimated_cost: float) -> None:
        calls, cost = self.totals()
        if calls >= self.maximum_calls:
            raise AdvisoryAuditError("advisory call ceiling reached")
        if cost + estimated_cost > self.maximum_cost:
            raise AdvisoryAuditError("advisory cost ceiling reached")

    def complete(self, request_key: str, request_sha256: str, response: ProviderJsonResponse) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO calls(request_key,request_sha256,status,response_json,input_tokens,output_tokens,cost_usd,latency_ms) VALUES (?,?,'completed',?,?,?,?,?)",
                (
                    request_key,
                    request_sha256,
                    response.model_dump_json(),
                    response.input_tokens,
                    response.output_tokens,
                    response.cost_usd,
                    response.latency_ms,
                ),
            )

    def fail(self, request_key: str, request_sha256: str, error: Exception) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO calls(request_key,request_sha256,status,failure_type,failure_detail) VALUES (?,?,'failed',?,?)",
                (request_key, request_sha256, type(error).__name__, str(error)[:500]),
            )

    def finish(self) -> None:
        failures = self.connection.execute(
            "SELECT COUNT(*) FROM calls WHERE status='failed'"
        ).fetchone()[0]
        self._set("status", "completed-with-limitations" if failures else "completed")

    def interrupt(self) -> None:
        self._set("status", "interrupted")

    def close(self) -> None:
        self.connection.close()


def validate(*, require_unauthorized: bool = True) -> dict[str, Any]:
    instrument = _load_hashed(
        INSTRUMENT_PATH, identity_key="instrument_id", identity=INSTRUMENT_ID
    )
    binding = _load_hashed(BINDING_PATH, identity_key="binding_id", identity=BINDING_ID)
    reviewer = binding["providers"][REVIEWER_ROLE]
    transport = DirectProviderJsonTransport(reviewer)
    system, prompt = _prompt(
        [
            {
                "case_id": "network-free-case",
                "question": "What does the source state?",
                "expected_action": "answer",
                "canonical_answer": "A source-linked answer.",
                "actual_action": "answer",
                "answer": "A source-linked answer.",
            }
        ]
    )
    payload = transport._payload(  # noqa: SLF001
        system=system,
        prompt=prompt,
        task="network-free-advisory-audit",
        schema=_schema(1),
    )
    if (
        payload.get("store") is not False
        or payload.get("model") != reviewer["provider_model"]
    ):
        raise AdvisoryAuditError("advisory OpenAI payload drifted")
    if require_unauthorized and (
        any(instrument["authorization"].values()) or any(binding["authorization"].values())
    ):
        raise AdvisoryAuditError("build-only advisory authority drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "decision_authority": instrument["method"]["decision_authority"],
        "passing_sample_count": instrument["advisory_audit"]["passing_sample_count"],
        "maximum_calls": instrument["advisory_audit"]["maximum_calls"],
        "maximum_cost_usd": instrument["advisory_audit"]["maximum_cost_usd"],
        "provider_calls": 0,
        "openai_store": payload["store"],
        "advisory_failure_invalidates_deterministic_measurement": False,
    }


def simulate(*, scenario: str) -> dict[str, Any]:
    if scenario not in {"complete", "malformed", "truth-defect"}:
        raise ValueError(f"unknown advisory simulation: {scenario}")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "needs-human-review" if scenario == "truth-defect" else "completed",
        "limitation_count": 1 if scenario == "malformed" else 0,
        "potential_truth_defect_count": 1 if scenario == "truth-defect" else 0,
        "deterministic_result_changed": False,
        "provider_calls": 0,
        "network_accessed": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _load_hashed(
        INSTRUMENT_PATH, identity_key="instrument_id", identity=INSTRUMENT_ID
    )
    binding = _load_hashed(BINDING_PATH, identity_key="binding_id", identity=BINDING_ID)
    blockers: list[str] = []
    try:
        validate(require_unauthorized=False)
    except Exception as error:  # noqa: BLE001
        blockers.append(f"build-validation-failed:{type(error).__name__}")
    if _repo_dirty():
        blockers.append("repository-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    if not all(path.is_file() for path in (CASES_PATH, GOLD_PATH, RESPONSES_PATH, DETERMINISTIC_RESULT_PATH)):
        blockers.append("deterministic-scoring-artifacts-incomplete")
    operations = set(BOUNDED_PILOT_AUTHORIZATIONS.get(INSTRUMENT_ID, ()))
    for operation in ("external_model_evaluation", "method_evaluation_execution"):
        if operation not in operations:
            blockers.append(f"freeze-{operation}-authorization-missing")
    for record_name, record in (("instrument", instrument), ("binding", binding)):
        for key in (
            "provider_execution_authorized",
            "paid_execution_authorized",
            "semantic_review_execution_authorized",
        ):
            if not record["authorization"][key]:
                blockers.append(f"{record_name}-{key.replace('_', '-')}-false")
    verified_at = datetime.fromisoformat(binding["verified_at"])
    age = (datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)).total_seconds() / 3600
    if age < 0 or age > binding["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if resume:
        if not LEDGER_PATH.is_file():
            blockers.append("resume-ledger-missing")
    elif LEDGER_PATH.exists():
        blockers.append("exclusive-ledger-path-used")
    if RESULT_PATH.exists():
        blockers.append("exclusive-result-path-used")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
        "credential_values_emitted": False,
    }


async def execute(*, resume: bool) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise AdvisoryAuditError("advisory preflight is blocked: " + ", ".join(readiness["blockers"]))
    instrument = _load_hashed(
        INSTRUMENT_PATH, identity_key="instrument_id", identity=INSTRUMENT_ID
    )
    binding = _load_hashed(BINDING_PATH, identity_key="binding_id", identity=BINDING_ID)
    rows, failures, sample = build_audit_rows()
    selection_sha256 = canonical_sha256(rows)
    reviewer = binding["providers"][REVIEWER_ROLE]
    transport = DirectProviderJsonTransport(reviewer)
    run_binding = {
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "binding_id": BINDING_ID,
        "binding_sha256": binding["content_sha256"],
        "deterministic_result_sha256": hashlib.sha256(DETERMINISTIC_RESULT_PATH.read_bytes()).hexdigest(),
        "selection_sha256": selection_sha256,
        "code_revision": _repo_revision(),
    }
    ledger = AdvisoryLedger(
        binding=run_binding,
        maximum_calls=instrument["advisory_audit"]["maximum_calls"],
        maximum_cost=instrument["advisory_audit"]["maximum_cost_usd"],
        resume=resume,
    )
    try:
        for number, batch in enumerate(_batches(rows, instrument["advisory_audit"]["batch_size"]), start=1):
            request_key = f"audit-{number:03d}"
            expected_ids = [row["case_id"] for row in batch]
            system, prompt = _prompt(batch)
            request_sha256 = canonical_sha256(
                {"request_key": request_key, "system": system, "prompt": prompt, "schema": _schema(len(batch))}
            )
            if ledger.existing(request_key, request_sha256):
                continue
            try:
                ledger.reserve(transport.estimated_cost(prompt=prompt))
                response = await transport.call(
                    system=system,
                    prompt=prompt,
                    task="academic-factual-qa-deterministic-result-advisory-audit",
                    schema=_schema(len(batch)),
                )
                _parse_items(response.content, expected_ids)
                ledger.complete(request_key, request_sha256, response)
            except Exception as error:  # noqa: BLE001 - advisory failures are limitations
                ledger.fail(request_key, request_sha256, error)
        ledger.finish()
    except KeyboardInterrupt:
        ledger.interrupt()
        raise
    finally:
        ledger.close()
    return score(expected_ids={row["case_id"] for row in rows}, failures=failures, sample=sample)


def score(
    *,
    expected_ids: set[str] | None = None,
    failures: list[str] | None = None,
    sample: list[str] | None = None,
) -> dict[str, Any]:
    if not LEDGER_PATH.is_file():
        raise AdvisoryAuditError("advisory ledger is missing")
    if expected_ids is None or failures is None or sample is None:
        rows, failures, sample = build_audit_rows()
        expected_ids = {row["case_id"] for row in rows}
    connection = sqlite3.connect(f"file:{LEDGER_PATH}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        calls = connection.execute(
            "SELECT status,response_json,failure_type,failure_detail FROM calls ORDER BY sequence"
        ).fetchall()
    finally:
        connection.close()
    if metadata.get("status") not in {"completed", "completed-with-limitations"}:
        raise AdvisoryAuditError("advisory ledger is not terminal")
    reviews: list[dict[str, Any]] = []
    limitations: list[dict[str, str]] = []
    for status, response_json, failure_type, failure_detail in calls:
        if status == "completed":
            response = ProviderJsonResponse.model_validate_json(response_json)
            reviews.extend(response.content["items"])
        else:
            limitations.append(
                {"failure_type": str(failure_type), "failure_detail": str(failure_detail)[:240]}
            )
    reviewed_ids = {row["case_id"] for row in reviews}
    missing_ids = sorted(expected_ids - reviewed_ids)
    truth_defects = sorted(
        row["case_id"] for row in reviews if row["potential_authoritative_truth_defect"]
    )
    payload = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": "needs-human-review" if truth_defects else "completed",
        "deterministic_failure_case_count": len(failures),
        "seeded_passing_case_count": len(sample),
        "selected_case_count": len(expected_ids),
        "reviewed_case_count": len(reviewed_ids),
        "missing_review_case_count": len(missing_ids),
        "missing_review_case_ids": missing_ids,
        "limitation_count": len(limitations) + len(missing_ids),
        "limitations": limitations,
        "potential_truth_defect_count": len(truth_defects),
        "potential_truth_defect_case_ids": truth_defects,
        "deterministic_result_changed": False,
        "reviewer_model": _load_hashed(
            BINDING_PATH, identity_key="binding_id", identity=BINDING_ID
        )["providers"][REVIEWER_ROLE]["provider_model"],
        "reviewer_role": REVIEWER_ROLE,
        "same_provider_model_review": True,
    }
    if RESULT_PATH.exists():
        raise AdvisoryAuditError("exclusive advisory result path is used")
    descriptor = os.open(RESULT_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return payload


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--validate-live", action="store_true")
    mode.add_argument("--simulate", choices=("complete", "malformed", "truth-defect"))
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--score", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    if arguments.validate or arguments.validate_live:
        result = validate(require_unauthorized=not arguments.validate_live)
    elif arguments.simulate:
        result = simulate(scenario=arguments.simulate)
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.execute:
        result = asyncio.run(execute(resume=arguments.resume))
    else:
        result = score()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
