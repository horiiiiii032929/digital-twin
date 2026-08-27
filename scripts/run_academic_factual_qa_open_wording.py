#!/usr/bin/env python3
"""Run the bounded public-only wording and advisory-review checkpoint."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import (  # noqa: E402
    normalize_question,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_wording import (  # noqa: E402
    QuestionWordingResponseV1,
    QuestionWordingReviewResponseV1,
    apply_reviewed_wording_responses,
    wording_requests,
    wording_review_requests,
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


INSTRUMENT_ID = "academic-factual-qa-open-10000-wording-development-001"
BINDING_ID = "academic-factual-qa-open-10000-wording-binding-001"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_wording_development_001.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_wording_binding_001.json"
)
CASES_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_cases_002.json"
)
GOLD_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_gold_002.json"
)
LEDGER_PATH = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-wording-development-001.sqlite3"
)
RESULT_PATH = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-wording-development-001-result.json"
)


class WordingCheckpointError(RuntimeError):
    """Raised when the bounded wording checkpoint violates its frozen contract."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WordingCheckpointError(f"JSON root is not an object: {path.name}")
    return value


def _load_hashed(path: Path, *, key: str, identity: str) -> dict[str, Any]:
    value = _load(path)
    if value.get(key) != identity:
        raise WordingCheckpointError(f"identity drifted: {path.name}")
    expected = canonical_json_sha256(
        {field: row for field, row in value.items() if field != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise WordingCheckpointError(f"content hash drifted: {path.name}")
    return value


def _instrument() -> dict[str, Any]:
    return _load_hashed(
        INSTRUMENT_PATH,
        key="instrument_id",
        identity=INSTRUMENT_ID,
    )


def _binding() -> dict[str, Any]:
    return _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)


def _validate_package(path: Path, *, expected_hash: str, rows_key: str) -> dict[str, Any]:
    value = _load(path)
    actual = canonical_json_sha256(
        {field: row for field, row in value.items() if field != "content_sha256"}
    )
    if value.get("content_sha256") != actual or actual != expected_hash:
        raise WordingCheckpointError(f"dataset package hash drifted: {path.name}")
    rows = value.get(rows_key)
    if not isinstance(rows, list) or len(rows) != 500:
        raise WordingCheckpointError(f"dataset package size drifted: {path.name}")
    return value


def _public_cases() -> list[EvaluationCaseV1]:
    instrument = _instrument()
    package = _validate_package(
        CASES_PATH,
        expected_hash=instrument["dataset"]["public_cases_content_sha256"],
        rows_key="cases",
    )
    return [EvaluationCaseV1.model_validate(row) for row in package["cases"]]


def _hidden_gold() -> list[EvaluationGoldV1]:
    instrument = _instrument()
    package = _validate_package(
        GOLD_PATH,
        expected_hash=instrument["dataset"]["hidden_gold_content_sha256"],
        rows_key="gold",
    )
    return [EvaluationGoldV1.model_validate(row) for row in package["gold"]]


def _batches(rows: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _items_schema(*, kind: str, count: int) -> dict[str, Any]:
    if kind == "author":
        properties: dict[str, Any] = {
            "case_id": {"type": "string", "minLength": 1},
            "question": {"type": "string", "minLength": 1, "maxLength": 500},
        }
        required = ["case_id", "question"]
    elif kind == "review":
        properties = {
            "case_id": {"type": "string", "minLength": 1},
            "accept": {"type": "boolean"},
            "faithfulness": {
                "type": "string",
                "enum": ["faithful", "meaning-shift", "unclear"],
            },
            "naturalness": {
                "type": "string",
                "enum": ["acceptable", "awkward"],
            },
            "rationale": {"type": "string", "minLength": 1, "maxLength": 240},
        }
        required = [
            "case_id",
            "accept",
            "faithfulness",
            "naturalness",
            "rationale",
        ]
    else:
        raise ValueError(f"unknown schema kind: {kind}")
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
                    "required": required,
                    "properties": properties,
                },
            }
        },
    }


def _author_prompt(rows: list[dict[str, Any]]) -> tuple[str, str]:
    system = (
        "Rewrite each canonical question into clear, natural student language. "
        "Preserve its meaning and requested action exactly. Do not answer it, add "
        "facts, mention hidden evidence, or change case IDs. Return only the schema."
    )
    prompt = json.dumps({"public_question_requests": rows}, sort_keys=True)
    return system, prompt


def _review_prompt(rows: list[dict[str, Any]]) -> tuple[str, str]:
    system = (
        "Independently compare each candidate question with its canonical question. "
        "Accept only wording that preserves the same meaning and is natural. Do not "
        "answer the question or infer source truth. Return only the schema."
    )
    prompt = json.dumps({"public_wording_pairs": rows}, sort_keys=True)
    return system, prompt


def _parse_author(content: dict[str, Any], expected_ids: list[str]) -> list[QuestionWordingResponseV1]:
    items = content.get("items")
    if not isinstance(items, list):
        raise WordingCheckpointError("author response items are missing")
    rows = [QuestionWordingResponseV1.model_validate(row) for row in items]
    if [row.case_id for row in rows] != expected_ids:
        raise WordingCheckpointError("author response IDs or order drifted")
    return rows


def _parse_reviews(
    content: dict[str, Any], expected_ids: list[str]
) -> list[QuestionWordingReviewResponseV1]:
    items = content.get("items")
    if not isinstance(items, list):
        raise WordingCheckpointError("review response items are missing")
    rows = [QuestionWordingReviewResponseV1.model_validate(row) for row in items]
    if [row.case_id for row in rows] != expected_ids:
        raise WordingCheckpointError("review response IDs or order drifted")
    return rows


def _contains_normalized_sequence(*, needle: str, haystack: str) -> bool:
    expected = normalize_question(needle).split()
    observed = normalize_question(haystack).split()
    return bool(expected) and any(
        observed[index : index + len(expected)] == expected
        for index in range(len(observed) - len(expected) + 1)
    )


def _repo_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def validate(*, require_unauthorized: bool = True) -> dict[str, Any]:
    instrument = _instrument()
    binding = _binding()
    cases = _public_cases()
    if len({row.case_id for row in cases}) != 500:
        raise WordingCheckpointError("public case IDs are not unique")
    if set(binding["providers"]) != {"wording-author", "wording-reviewer"}:
        raise WordingCheckpointError("wording provider roles drifted")
    author = binding["providers"]["wording-author"]
    reviewer = binding["providers"]["wording-reviewer"]
    if author["provider"] != "openai" or reviewer["provider"] != "mistral":
        raise WordingCheckpointError("wording provider families drifted")
    transports = {
        role: DirectProviderJsonTransport(row)
        for role, row in binding["providers"].items()
    }
    sample = wording_requests(cases[:20])
    author_system, author_prompt = _author_prompt(
        [row.model_dump(mode="json") for row in sample]
    )
    author_payload = transports["wording-author"]._payload(  # noqa: SLF001
        system=author_system,
        prompt=author_prompt,
        task="wording-author-network-free-contract",
        schema=_items_schema(kind="author", count=20),
    )
    fake_responses = [
        QuestionWordingResponseV1(
            case_id=row.case_id,
            question=f"Could you explain this clearly: {row.canonical_question}",
        )
        for row in sample
    ]
    review_rows = wording_review_requests(cases=cases[:20], responses=fake_responses)
    review_system, review_prompt = _review_prompt(
        [row.model_dump(mode="json") for row in review_rows]
    )
    review_payload = transports["wording-reviewer"]._payload(  # noqa: SLF001
        system=review_system,
        prompt=review_prompt,
        task="wording-review-network-free-contract",
        schema=_items_schema(kind="review", count=20),
    )
    serialized = json.dumps(
        {"author": author_payload, "reviewer": review_payload}, sort_keys=True
    ).casefold()
    if "openrouter" in serialized or "deepseek" in serialized:
        raise WordingCheckpointError("router or retired provider leaked into binding")
    if author_payload.get("store") is not False:
        raise WordingCheckpointError("OpenAI wording request does not set store=false")
    if require_unauthorized and (
        any(binding["authorization"].values())
        or any(instrument["authorization"].values())
    ):
        raise WordingCheckpointError("build-only wording authority drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "binding_id": BINDING_ID,
        "status": "passed-build-only",
        "case_count": len(cases),
        "batch_count": instrument["dataset"]["batch_count"],
        "maximum_logical_calls": instrument["operational_bounds"][
            "maximum_logical_calls"
        ],
        "public_author_fields": sorted(sample[0].model_dump()),
        "public_reviewer_fields": sorted(review_rows[0].model_dump()),
        "strict_schema_requested": "json_schema" in serialized,
        "openai_store": author_payload["store"],
        "provider_calls": 0,
        "gold_loaded": False,
        "final_split_opened": False,
    }


def simulate() -> dict[str, Any]:
    cases = _public_cases()
    gold = _hidden_gold()
    responses = [
        QuestionWordingResponseV1(
            case_id=row.case_id,
            question=f"As a student, {row.question[0].casefold()}{row.question[1:]}",
        )
        for row in cases
    ]
    reviews = [
        QuestionWordingReviewResponseV1(
            case_id=row.case_id,
            accept=True,
            faithfulness="faithful",
            naturalness="acceptable",
            rationale="The simulated wording preserves the canonical question.",
        )
        for row in cases
    ]
    output, decisions = apply_reviewed_wording_responses(
        cases=cases,
        gold=gold,
        responses=responses,
        reviews=reviews,
    )
    duplicate_count = len(output) - len(
        {normalize_question(row.question) for row in output}
    )
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "simulated-network-free",
        "case_count": len(output),
        "accepted_wording_count": sum(
            row.status == "accepted-model-wording" for row in decisions
        ),
        "canonical_fallback_count": sum(
            row.status == "canonical-fallback" for row in decisions
        ),
        "normalized_duplicate_count": duplicate_count,
        "provider_calls": 0,
        "network_accessed": False,
        "private_data_used": False,
        "final_split_opened": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _instrument()
    binding = _binding()
    blockers: list[str] = []
    try:
        validate(require_unauthorized=False)
    except Exception as error:  # noqa: BLE001 - preflight must report all blockers
        blockers.append(f"build-validation-failed:{type(error).__name__}")
    if _repo_dirty():
        blockers.append("repository-dirty")
    if resume and not LEDGER_PATH.is_file():
        blockers.append("resume-ledger-missing")
    if not resume and LEDGER_PATH.exists():
        blockers.append("exclusive-ledger-path-used")
    if RESULT_PATH.exists():
        blockers.append("exclusive-result-path-used")
    operations = set(BOUNDED_PILOT_AUTHORIZATIONS.get(INSTRUMENT_ID, ()))
    for operation in ("external_model_evaluation", "method_evaluation_execution"):
        if operation not in operations:
            blockers.append(f"freeze-{operation}-authorization-missing")
    for key in (
        "provider_execution_authorized",
        "paid_execution_authorized",
        "wording_development_execution_authorized",
    ):
        if not binding["authorization"][key]:
            blockers.append(f"binding-{key.replace('_', '-')}-false")
        if not instrument["authorization"][key]:
            blockers.append(f"instrument-{key.replace('_', '-')}-false")
    for provider in binding["providers"].values():
        name = provider["credential_environment_variable"]
        if not os.getenv(name, "").strip():
            blockers.append(f"{name.casefold()}-missing")
    verified_at = datetime.fromisoformat(binding["verified_at"])
    age_hours = (
        datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)
    ).total_seconds() / 3600
    if age_hours < 0 or age_hours > binding["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if instrument["authorization"]["t0_product_execution_authorized"]:
        blockers.append("t0-product-execution-must-remain-unauthorized")
    if instrument["authorization"]["final_execution_authorized"]:
        blockers.append("final-execution-must-remain-unauthorized")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
        "credential_values_emitted": False,
        "t0_product_execution_authorized": False,
        "final_execution_authorized": False,
    }


def _transport_for_role(
    *, role: str, binding: dict[str, Any], recovered_failures: int, retry_limit: int
) -> DirectProviderJsonTransport:
    provider = dict(binding["providers"][role])
    if recovered_failures >= retry_limit:
        provider["maximum_transport_retries"] = 0
    return DirectProviderJsonTransport(provider)


async def execute(*, resume: bool) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    instrument = _instrument()
    binding = _binding()
    for record in (instrument, binding):
        authorization = record["authorization"]
        if not all(
            authorization[key]
            for key in (
                "provider_execution_authorized",
                "paid_execution_authorized",
                "wording_development_execution_authorized",
            )
        ):
            raise WordingCheckpointError("paid wording execution is not authorized")
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise WordingCheckpointError(
            "wording preflight is blocked: " + ", ".join(readiness["blockers"])
        )
    cases = _public_cases()
    requests = wording_requests(cases)
    case_by_id = {row.case_id: row for row in cases}
    batch_size = instrument["dataset"]["batch_size"]
    run_binding = {
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "provider_binding_id": BINDING_ID,
        "provider_binding_sha256": binding["content_sha256"],
        "public_cases_sha256": instrument["dataset"]["public_cases_content_sha256"],
        "code_revision": _git_revision(),
    }
    ledger = ProviderCallLedgerV1(
        LEDGER_PATH,
        run_binding=run_binding,
        maximum_calls=instrument["operational_bounds"]["maximum_logical_calls"],
        maximum_cost_usd=instrument["operational_bounds"]["maximum_cost_usd"],
        resume=resume,
    )
    retry_limit = instrument["operational_bounds"][
        "maximum_global_transport_retries"
    ]
    try:
        for batch_number, batch in enumerate(_batches(requests, batch_size), start=1):
            expected_ids = [row.case_id for row in batch]
            recovered = int(ledger.snapshot()["recovered_transport_failures"])
            author_transport = _transport_for_role(
                role="wording-author",
                binding=binding,
                recovered_failures=recovered,
                retry_limit=retry_limit,
            )
            system, prompt = _author_prompt(
                [row.model_dump(mode="json") for row in batch]
            )
            authored = await author_transport.call_with_ledger(
                ledger=ledger,
                request_key=f"author-{batch_number:03d}",
                provider_role="wording-author",
                system=system,
                prompt=prompt,
                task="academic-factual-qa-public-question-wording",
                schema=_items_schema(kind="author", count=len(batch)),
            )
            authored_rows = _parse_author(authored.content, expected_ids)
            public_cases = [case_by_id[row.case_id] for row in batch]
            review_requests = wording_review_requests(
                cases=public_cases,
                responses=authored_rows,
            )
            recovered = int(ledger.snapshot()["recovered_transport_failures"])
            reviewer_transport = _transport_for_role(
                role="wording-reviewer",
                binding=binding,
                recovered_failures=recovered,
                retry_limit=retry_limit,
            )
            review_system, review_prompt = _review_prompt(
                [row.model_dump(mode="json") for row in review_requests]
            )
            reviewed = await reviewer_transport.call_with_ledger(
                ledger=ledger,
                request_key=f"review-{batch_number:03d}",
                provider_role="wording-reviewer",
                system=review_system,
                prompt=review_prompt,
                task="academic-factual-qa-public-question-wording-review",
                schema=_items_schema(kind="review", count=len(batch)),
            )
            _parse_reviews(reviewed.content, expected_ids)
            snapshot = ledger.snapshot()
            if snapshot["provider_attempts"] > instrument["operational_bounds"][
                "maximum_physical_attempts"
            ]:
                ledger.mark_invalid_execution()
                raise WordingCheckpointError("physical provider attempt ceiling exceeded")
        snapshot = ledger.snapshot()
        if snapshot["provider_calls"] != instrument["operational_bounds"][
            "maximum_logical_calls"
        ]:
            ledger.mark_invalid_execution()
            raise WordingCheckpointError("logical provider call count drifted")
        ledger.mark_complete()
        return {**ledger.snapshot(), "instrument_id": INSTRUMENT_ID}
    except KeyboardInterrupt:
        ledger.mark_interrupted()
        raise
    except Exception:
        ledger.mark_invalid_execution()
        raise
    finally:
        ledger.close()


def _ledger_rows() -> tuple[dict[str, str], list[tuple[str, str, ProviderJsonResponse]]]:
    if not LEDGER_PATH.is_file():
        raise WordingCheckpointError("wording ledger does not exist")
    connection = sqlite3.connect(LEDGER_PATH)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        rows = connection.execute(
            "SELECT request_key, provider_role, response_json FROM calls "
            "WHERE status = 'completed' ORDER BY sequence"
        ).fetchall()
    finally:
        connection.close()
    parsed = [
        (request_key, role, ProviderJsonResponse.model_validate_json(response_json))
        for request_key, role, response_json in rows
    ]
    return metadata, parsed


def score() -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    instrument = _instrument()
    metadata, rows = _ledger_rows()
    if metadata.get("status") != "completed":
        raise WordingCheckpointError("wording ledger is not durably complete")
    if len(rows) != instrument["operational_bounds"]["maximum_logical_calls"]:
        raise WordingCheckpointError("wording ledger call count is incomplete")
    cases = _public_cases()
    responses: list[QuestionWordingResponseV1] = []
    reviews: list[QuestionWordingReviewResponseV1] = []
    for _, role, response in rows:
        if role == "wording-author":
            items = response.content.get("items", [])
            responses.extend(QuestionWordingResponseV1.model_validate(row) for row in items)
        elif role == "wording-reviewer":
            items = response.content.get("items", [])
            reviews.extend(
                QuestionWordingReviewResponseV1.model_validate(row) for row in items
            )
        else:
            raise WordingCheckpointError("wording ledger contains an unknown role")
    if len(responses) != 500 or len(reviews) != 500:
        raise WordingCheckpointError("wording ledger response coverage drifted")

    # Hidden gold is first opened only after the complete provider ledger above.
    gold = _hidden_gold()
    output, decisions = apply_reviewed_wording_responses(
        cases=cases,
        gold=gold,
        responses=responses,
        reviews=reviews,
    )
    accepted = sum(row.status == "accepted-model-wording" for row in decisions)
    reviewer_accepted = sum(
        row.accept
        and row.faithfulness == "faithful"
        and row.naturalness == "acceptable"
        for row in reviews
    )
    candidate_duplicate_count = len(responses) - len(
        {normalize_question(row.question) for row in responses}
    )
    output_duplicate_count = len(output) - len(
        {normalize_question(row.question) for row in output}
    )
    gold_by_id = {row.case_id: row for row in gold}
    leak_count = sum(
        _contains_normalized_sequence(
            needle=gold_by_id[row.case_id].canonical_answer,
            haystack=row.question,
        )
        for row in responses
    )
    gates = {
        "provider_completion": len(rows)
        == instrument["operational_bounds"]["maximum_logical_calls"],
        "accepted_wording_rate": accepted / len(output)
        >= instrument["acceptance"]["accepted_wording_rate_min"],
        "reviewer_acceptance_rate": reviewer_accepted / len(reviews)
        >= instrument["acceptance"]["reviewer_acceptance_rate_min"],
        "canonical_fallback_coverage": len(output) == len(cases),
        "zero_duplicates": candidate_duplicate_count == 0
        and output_duplicate_count == 0,
        "zero_answer_leaks": leak_count == 0,
    }
    state = "completed-go-deeper" if all(gates.values()) else "completed-refine"
    payload: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": state,
        "case_count": len(output),
        "accepted_wording_count": accepted,
        "canonical_fallback_count": len(output) - accepted,
        "reviewer_accepted_count": reviewer_accepted,
        "candidate_normalized_duplicate_count": candidate_duplicate_count,
        "output_normalized_duplicate_count": output_duplicate_count,
        "canonical_answer_leak_count": leak_count,
        "gates": gates,
        "cases": [row.model_dump(mode="json") for row in output],
        "decisions": [row.model_dump(mode="json") for row in decisions],
        "private_data_used": False,
        "final_split_opened": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    if RESULT_PATH.exists():
        raise WordingCheckpointError("exclusive wording result path is already used")
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(RESULT_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return {
        key: value
        for key, value in payload.items()
        if key not in {"cases", "decisions"}
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--score", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
    if arguments.score:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate()
    elif arguments.simulate:
        result = simulate()
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
