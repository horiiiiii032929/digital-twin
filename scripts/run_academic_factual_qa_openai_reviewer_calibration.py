#!/usr/bin/env python3
"""Qualify the exact OpenAI semantic reviewer on 40 planted controls."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from typing import Any, Iterable

from dotenv import load_dotenv

from scripts.run_academic_factual_qa_panel_review_v2 import (
    _calibration_metrics,
    _ideal_vote,
    _truth_maps,
    validate_vote,
)
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
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-checkpoint-003"
BINDING_ID = "academic-factual-qa-open-10000-openai-binding-003"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_checkpoint_003.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_003.json"
)
PACKET_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_confirmation_002_blinded_review_packet.json"
)
CONTROLS_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_confirmation_002_calibration_controls.json"
)
LEDGER_PATH = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-openai-"
    "reviewer-calibration-002.sqlite3"
)
RESULT_PATH = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-openai-"
    "reviewer-calibration-002-result.json"
)


class OpenAiReviewerCalibrationError(RuntimeError):
    """Raised when the reviewer calibration violates its frozen contract."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OpenAiReviewerCalibrationError(f"JSON root is not an object: {path.name}")
    return value


def _load_hashed(path: Path, *, key: str, identity: str) -> dict[str, Any]:
    value = _load(path)
    if value.get(key) != identity:
        raise OpenAiReviewerCalibrationError(f"identity drifted: {path.name}")
    expected = canonical_sha256(
        {field: row for field, row in value.items() if field != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise OpenAiReviewerCalibrationError(f"content hash drifted: {path.name}")
    return value


def _require_content_hash(value: dict[str, Any], expected: str, label: str) -> None:
    actual = canonical_sha256(
        {field: row for field, row in value.items() if field != "content_sha256"}
    )
    if value.get("content_sha256") != actual or actual != expected:
        raise OpenAiReviewerCalibrationError(f"{label} content hash drifted")


def _instrument() -> dict[str, Any]:
    return _load_hashed(
        INSTRUMENT_PATH, key="instrument_id", identity=INSTRUMENT_ID
    )


def _binding() -> dict[str, Any]:
    return _load_hashed(BINDING_PATH, key="binding_id", identity=BINDING_ID)


def _packet() -> dict[str, Any]:
    instrument = _instrument()
    packet = _load(PACKET_PATH)
    _require_content_hash(
        packet,
        instrument["calibration"]["packet_content_sha256"],
        "blinded calibration packet",
    )
    items = packet.get("items")
    count = instrument["calibration"]["control_count"]
    if not isinstance(items, list) or len(items) < count:
        raise OpenAiReviewerCalibrationError("blinded calibration packet is incomplete")
    calibration = items[:count]
    if any(row.get("item_kind") != "calibration" for row in calibration):
        raise OpenAiReviewerCalibrationError("calibration packet ordering drifted")
    return {**packet, "items": calibration}


def _batches(rows: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _vote_schema(count: int) -> dict[str, Any]:
    vote = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "review_item_id",
            "case_semantically_valid",
            "expected_action",
            "question_answerable_from_supplied_sources",
            "atomic_claim_support",
            "citation_support",
            "boundary_reason",
            "ambiguity_detected",
            "evidence_ids",
            "defect_types",
            "concise_rationale",
        ],
        "properties": {
            "review_item_id": {"type": "string", "minLength": 1},
            "case_semantically_valid": {"type": "boolean"},
            "expected_action": {
                "type": "string",
                "enum": ["answer", "abstain", "clarify", "refuse"],
            },
            "question_answerable_from_supplied_sources": {"type": "boolean"},
            "atomic_claim_support": {
                "type": "string",
                "enum": [
                    "fully-supported",
                    "partially-supported",
                    "unsupported",
                    "not-applicable",
                ],
            },
            "citation_support": {
                "type": "string",
                "enum": ["complete-valid", "incomplete", "invalid", "not-applicable"],
            },
            "boundary_reason": {
                "anyOf": [{"type": "string"}, {"type": "null"}]
            },
            "ambiguity_detected": {"type": "boolean"},
            "evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "defect_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["action", "ambiguity", "boundary", "citation", "claim"],
                },
            },
            "concise_rationale": {"type": "string", "minLength": 1, "maxLength": 240},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["votes"],
        "properties": {
            "votes": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": vote,
            }
        },
    }


def _prompt(items: list[dict[str, Any]], instructions: Any) -> tuple[str, str]:
    system = (
        "Act as a strict blinded factual-QA reviewer. Judge only the visible "
        "question, candidate record, supplied sources, claims, and citations. "
        "Detect unsupported claims, incorrect actions, and citation defects. "
        "Use only action, ambiguity, boundary, citation, or claim in defect_types. "
        "Do not assume hidden ground truth or repair the candidate. Return only "
        "the requested schema."
    )
    prompt = json.dumps(
        {"reviewer_instructions": instructions, "review_items": items},
        sort_keys=True,
    )
    return system, prompt


def _validate_semantics(vote: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    action = vote["expected_action"]
    answerable = action == "answer"
    if vote["question_answerable_from_supplied_sources"] is not answerable:
        raise OpenAiReviewerCalibrationError("answerability and action conflict")
    if answerable:
        if vote["boundary_reason"] is not None or vote["ambiguity_detected"]:
            raise OpenAiReviewerCalibrationError("answer vote has boundary metadata")
        if vote["atomic_claim_support"] == "not-applicable" or vote[
            "citation_support"
        ] == "not-applicable":
            raise OpenAiReviewerCalibrationError("answer vote omits support judgment")
    else:
        if not isinstance(vote["boundary_reason"], str) or not vote[
            "boundary_reason"
        ].strip():
            raise OpenAiReviewerCalibrationError("boundary vote lacks a reason")
        if vote["atomic_claim_support"] != "not-applicable" or vote[
            "citation_support"
        ] != "not-applicable":
            raise OpenAiReviewerCalibrationError("boundary vote contains answer support")
        if vote["evidence_ids"]:
            raise OpenAiReviewerCalibrationError("boundary vote contains evidence lineage")
        if vote["ambiguity_detected"] is not (action == "clarify"):
            raise OpenAiReviewerCalibrationError("ambiguity and action conflict")
    visible_ids = {
        row["evidence_id"]
        for row in item.get("provided_sources", [])
        if isinstance(row, dict) and isinstance(row.get("evidence_id"), str)
    }
    if not set(vote["evidence_ids"]).issubset(visible_ids):
        raise OpenAiReviewerCalibrationError("vote cites non-visible evidence")
    allowed_defects = {"action", "ambiguity", "boundary", "citation", "claim"}
    if not set(vote["defect_types"]).issubset(allowed_defects):
        raise OpenAiReviewerCalibrationError("vote contains an unknown defect type")
    if vote["case_semantically_valid"] is (bool(vote["defect_types"])):
        raise OpenAiReviewerCalibrationError("semantic validity conflicts with defects")
    if vote["citation_support"] in {"invalid", "incomplete"} and "citation" not in vote[
        "defect_types"
    ]:
        raise OpenAiReviewerCalibrationError("citation defect classification is missing")
    if vote["atomic_claim_support"] in {"unsupported", "partially-supported"} and (
        "claim" not in vote["defect_types"]
    ):
        raise OpenAiReviewerCalibrationError("claim defect classification is missing")
    return vote


def _parse_votes(
    content: dict[str, Any], expected_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = content.get("votes")
    if not isinstance(rows, list) or len(rows) != len(expected_items):
        raise OpenAiReviewerCalibrationError("reviewer vote coverage drifted")
    return [
        _validate_semantics(
            validate_vote(dict(row), expected_item_id=item["review_item_id"]), item
        )
        for row, item in zip(rows, expected_items, strict=True)
    ]


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
    packet = _packet()
    calibration = instrument["calibration"]
    controls = _load(CONTROLS_PATH)
    _require_content_hash(
        controls,
        calibration["hidden_controls_content_sha256"],
        "hidden calibration controls",
    )
    if controls.get("control_count") != 40 or len(controls.get("controls", [])) != 40:
        raise OpenAiReviewerCalibrationError("hidden calibration control count drifted")
    if controls.get("clean_control_count") != 20 or controls.get(
        "corrupted_control_count"
    ) != 20:
        raise OpenAiReviewerCalibrationError("calibration balance drifted")
    reviewer = binding["providers"][calibration["reviewer_role"]]
    if reviewer["provider"] != "openai" or reviewer["provider_model"] != (
        "gpt-5.4-2026-03-05"
    ):
        raise OpenAiReviewerCalibrationError("OpenAI reviewer binding drifted")
    if reviewer["maximum_transport_retries"] != 0:
        raise OpenAiReviewerCalibrationError("reviewer retries must remain zero")
    transport = DirectProviderJsonTransport(reviewer)
    sample = packet["items"][:4]
    system, prompt = _prompt(sample, packet.get("reviewer_instructions"))
    payload = transport._payload(  # noqa: SLF001 - network-free contract assertion
        system=system,
        prompt=prompt,
        task="openai-reviewer-calibration-network-free-contract",
        schema=_vote_schema(4),
    )
    serialized = json.dumps(payload, sort_keys=True).casefold()
    if payload.get("store") is not False or "openrouter" in serialized:
        raise OpenAiReviewerCalibrationError("direct non-stored OpenAI contract drifted")
    if require_unauthorized and (
        any(binding["authorization"].values())
        or any(instrument["authorization"].values())
        or any(instrument["execution"][key] for key in (
            "provider_execution_authorized",
            "paid_execution_authorized",
            "development_execution_authorized",
            "final_execution_authorized",
        ))
    ):
        raise OpenAiReviewerCalibrationError("build-only authorization drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "binding_id": BINDING_ID,
        "status": "passed-build-only",
        "control_count": len(packet["items"]),
        "clean_control_count": controls["clean_control_count"],
        "corrupted_control_count": controls["corrupted_control_count"],
        "planned_calls": 10,
        "provider_calls": 0,
        "expected_labels_visible_to_provider": False,
        "prior_provider_votes_imported": False,
        "openai_store": payload["store"],
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _instrument()
    binding = _binding()
    blockers: list[str] = []
    try:
        validate(require_unauthorized=False)
    except Exception as error:  # noqa: BLE001 - aggregate fail-closed blockers
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
        "calibration_execution_authorized",
        "semantic_review_execution_authorized",
    ):
        if not instrument["authorization"][key]:
            blockers.append(f"instrument-{key.replace('_', '-')}-false")
        if not binding["authorization"][key]:
            blockers.append(f"binding-{key.replace('_', '-')}-false")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    verified_at = datetime.fromisoformat(binding["verified_at"])
    age = (
        datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)
    ).total_seconds() / 3600
    if age < 0 or age > binding["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if instrument["authorization"]["final_execution_authorized"] or instrument[
        "execution"
    ]["final_execution_authorized"]:
        blockers.append("final-execution-must-remain-unauthorized")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
        "credential_values_emitted": False,
        "final_execution_authorized": False,
    }


def simulate(*, scenario: str = "pass") -> dict[str, Any]:
    packet = _packet()
    _, control_truth = _truth_maps()
    votes = [
        _ideal_vote(item, control_truth[item["review_item_id"]])
        for item in packet["items"]
    ]
    if scenario == "quality-failure":
        for row in votes:
            row["case_semantically_valid"] = True
            row["citation_support"] = (
                "complete-valid"
                if row["expected_action"] == "answer"
                else "not-applicable"
            )
    elif scenario == "malformed":
        return {
            "instrument_id": INSTRUMENT_ID,
            "status": "invalid-execution",
            "reason": "simulated-malformed-response",
            "provider_calls": 0,
        }
    elif scenario != "pass":
        raise ValueError(f"unknown simulation scenario: {scenario}")
    metrics = _calibration_metrics(votes, control_truth)
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "completed-go-deeper" if metrics["passed"] else "completed-refine",
        "metrics": metrics,
        "valid_vote_count": len(votes),
        "provider_calls": 0,
        "network_accessed": False,
    }


async def execute(*, resume: bool) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    instrument = _instrument()
    binding = _binding()
    for record in (instrument, binding):
        if not all(
            record["authorization"][key]
            for key in (
                "provider_execution_authorized",
                "paid_execution_authorized",
                "calibration_execution_authorized",
                "semantic_review_execution_authorized",
            )
        ):
            raise OpenAiReviewerCalibrationError("reviewer calibration is not authorized")
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise OpenAiReviewerCalibrationError(
            "reviewer calibration preflight is blocked: "
            + ", ".join(readiness["blockers"])
        )
    packet = _packet()
    calibration = instrument["calibration"]
    reviewer_role = calibration["reviewer_role"]
    transport = DirectProviderJsonTransport(binding["providers"][reviewer_role])
    run_binding = {
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "provider_binding_id": BINDING_ID,
        "provider_binding_sha256": binding["content_sha256"],
        "packet_sha256": calibration["packet_content_sha256"],
        "code_revision": _git_revision(),
        "expected_labels_visible_during_calls": False,
    }
    ledger = ProviderCallLedgerV1(
        LEDGER_PATH,
        run_binding=run_binding,
        maximum_calls=calibration["maximum_calls"],
        maximum_cost_usd=calibration["maximum_cost_usd"],
        resume=resume,
    )
    try:
        for batch_number, batch in enumerate(
            _batches(packet["items"], calibration["batch_size"]), start=1
        ):
            system, prompt = _prompt(batch, packet.get("reviewer_instructions"))
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"calibration-{batch_number:02d}",
                provider_role=reviewer_role,
                system=system,
                prompt=prompt,
                task="academic-factual-qa-openai-reviewer-calibration",
                schema=_vote_schema(len(batch)),
            )
            _parse_votes(response.content, batch)
        snapshot = ledger.snapshot()
        if snapshot["provider_calls"] != calibration["maximum_calls"]:
            ledger.mark_invalid_execution()
            raise OpenAiReviewerCalibrationError("calibration call count drifted")
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


def score() -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    instrument = _instrument()
    if not LEDGER_PATH.is_file():
        raise OpenAiReviewerCalibrationError("calibration ledger is missing")
    connection = sqlite3.connect(f"file:{LEDGER_PATH}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        rows = connection.execute(
            "SELECT response_json FROM calls WHERE status = 'completed' ORDER BY sequence"
        ).fetchall()
    finally:
        connection.close()
    if metadata.get("status") != "completed" or len(rows) != 10:
        raise OpenAiReviewerCalibrationError("calibration ledger is incomplete")
    packet = _packet()
    votes: list[dict[str, Any]] = []
    for batch_number, row in enumerate(rows):
        response = ProviderJsonResponse.model_validate_json(row[0])
        start = batch_number * 4
        batch_items = packet["items"][start : start + 4]
        votes.extend(_parse_votes(response.content, batch_items))
    # Hidden expected labels are opened only after every vote is durably complete.
    _, control_truth = _truth_maps()
    metrics = _calibration_metrics(votes, control_truth)
    configured = instrument["calibration"]["gates"]
    gates = {
        "action_accuracy": metrics["action_accuracy"]
        >= configured["action_accuracy_min"],
        "mutation_sensitivity": metrics["mutation_sensitivity"]
        >= configured["mutation_sensitivity_min"],
        "specificity": metrics["specificity"] >= configured["specificity_min"],
        "citation_defect_sensitivity": metrics["citation_defect_sensitivity"]
        >= configured["citation_defect_sensitivity_min"],
        "complete_vote_coverage": len(votes)
        == configured["valid_vote_count_required"],
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": "completed-go-deeper" if all(gates.values()) else "completed-refine",
        "decision": "Go Deeper" if all(gates.values()) else "Refine",
        "metrics": metrics,
        "gates": gates,
        "valid_vote_count": len(votes),
        "prior_provider_votes_imported": False,
        "expected_labels_opened_after_complete_ledger": True,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    if RESULT_PATH.exists():
        raise OpenAiReviewerCalibrationError("exclusive calibration result path is used")
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    mode.add_argument("--simulate", choices=("pass", "quality-failure", "malformed"))
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
