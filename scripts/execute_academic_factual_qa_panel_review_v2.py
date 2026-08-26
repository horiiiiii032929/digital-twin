#!/usr/bin/env python3
"""Prepare, preflight, simulate, or execute the confirmation-002 review panel.

Calibration attempt 001 is preserved as invalid. Corrective attempt 002 uses a
new exclusive ledger and remains unauthorized.
Live preflight performs metadata reads only. Provider inference is split into
calibration and confirmation phases so no confirmation vote is opened until
all three reviewers pass the frozen calibration gates and confirmation receives
separate authority.
"""

from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Protocol
from urllib.request import Request, urlopen

from dotenv import load_dotenv
import httpx

from scripts.build_academic_factual_qa_confirmation_v2 import canonical_sha256
from scripts.prepare_academic_factual_qa_panel_review_v2 import PACKET_PATH, validate_packet
from scripts.run_academic_factual_qa_panel_review_v2 import (
    GEMINI_REVIEWER_IDS,
    PanelReviewError,
    REVIEWER_IDS,
    _calibration_metrics,
    _load,
    _truth_maps,
    aggregate_panel,
    append_vote,
    build_researcher_packet,
    build_simulated_ledger,
    initialize_ledger,
    validate_resume,
    validate_vote,
    write_ledger_atomic,
)
from scripts.validate_academic_factual_qa_confirmation_v2 import validate_instrument
from scripts.validate_factual_qa_provider_freshness import parse_deepseek_pricing
from src.digital_twin.repository_freeze import (
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-confirmation-002"
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/academic_factual_qa_confirmation_002.json"
)
BINDING_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_confirmation_002_reviewer_bindings.json"
)
ATTEMPT_003_ID = "academic-factual-qa-confirmation-002-calibration-attempt-003"
ATTEMPT_003_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_confirmation_002_calibration_attempt_003.json"
)
DEFAULT_LEDGER_PATH = (
    ROOT
    / "reports/generated/academic-factual-qa-confirmation-002-calibration-attempt-002-ledger.json"
)
ATTEMPT_003_LEDGER_PATH = (
    ROOT
    / "reports/generated/"
    "academic-factual-qa-confirmation-002-calibration-attempt-003-ledger.json"
)
DEFAULT_RESEARCHER_PACKET_PATH = (
    ROOT
    / "reports/generated/academic-factual-qa-confirmation-002-researcher-audit-packet.json"
)
DEFAULT_CODEX_WORKSPACE = (
    ROOT / "reports/generated/academic-factual-qa-confirmation-002-codex-workspace"
)
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
DEEPSEEK_MODELS_URL = "https://api.deepseek.com/models"
DEEPSEEK_PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing/"
GOOGLE_PROVIDER_POLICY_URL = "https://openrouter.ai/api/frontend/v1/all-providers"


class PanelExecutionError(PanelReviewError):
    """Raised when execution or a live binding violates the frozen contract."""


class ProviderCallFailure(PanelExecutionError):
    """Provider failure carrying only sanitized, ledger-safe diagnostics."""

    def __init__(self, category: str, details: dict[str, Any]) -> None:
        super().__init__(category)
        self.category = category
        self.details = details


@dataclass(frozen=True)
class ProviderBatchResult:
    content: str
    provider_model: str
    provider_revision: str | None
    provider_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


class PanelTransport(Protocol):
    async def call(
        self,
        *,
        reviewer: dict[str, Any],
        items: list[dict[str, Any]],
        schema: dict[str, Any],
    ) -> ProviderBatchResult: ...


def _working_tree_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load_binding(path: Path = BINDING_PATH) -> dict[str, Any]:
    binding = _load(path)
    expected_hash = canonical_sha256(
        {key: value for key, value in binding.items() if key != "content_sha256"}
    )
    if binding.get("content_sha256") != expected_hash:
        raise PanelExecutionError("reviewer binding content hash drifted")
    if binding.get("instrument_id") not in {INSTRUMENT_ID, ATTEMPT_003_ID}:
        raise PanelExecutionError("reviewer binding instrument drifted")
    if binding.get("maximum_age_hours_for_execution") != 24:
        raise PanelExecutionError("reviewer binding freshness window drifted")
    contract = binding["execution_contract"]
    reviewers = {row["reviewer_id"]: row for row in binding["reviewers"]}
    reviewer_ids = tuple(reviewers)
    if reviewer_ids not in {REVIEWER_IDS, GEMINI_REVIEWER_IDS}:
        raise PanelExecutionError("reviewer binding order or identity drifted")
    maximum_calls = 20 if reviewer_ids == GEMINI_REVIEWER_IDS else 120
    if {
        "provider_batch_size": contract["provider_batch_size"],
        "maximum_provider_calls": contract["maximum_provider_calls"],
        "retries": contract["retries"],
        "maximum_input_tokens_per_call": contract["maximum_input_tokens_per_call"],
        "maximum_output_tokens_per_call": contract["maximum_output_tokens_per_call"],
    } != {
        "provider_batch_size": 4,
        "maximum_provider_calls": maximum_calls,
        "retries": 0,
        "maximum_input_tokens_per_call": 8192,
        "maximum_output_tokens_per_call": 3072,
    }:
        raise PanelExecutionError("review execution limits drifted")
    if reviewers[reviewer_ids[0]]["provider_model"] != "gpt-5.6-sol":
        raise PanelExecutionError("Codex model binding drifted")
    primary = reviewers[reviewer_ids[1]]
    if reviewer_ids == REVIEWER_IDS:
        if (
            primary["provider_model"] != "mistralai/mistral-small-2603"
            or primary["endpoint_provider"] != "Mistral"
            or primary["endpoint_tag"] != "mistral/zdr"
            or primary["routing"]["allow_fallbacks"] is not False
            or primary["routing"]["data_collection"] != "deny"
            or primary["routing"]["zdr"] is not True
        ):
            raise PanelExecutionError("Mistral routing binding drifted")
    elif (
        primary["provider_model"] != "google/gemini-3.7-flash"
        or primary["documented_revision"] != "google/gemini-3.7-flash-20260813"
        or primary["endpoint_provider"] != "Google AI Studio"
        or primary["endpoint_tag"] != "google-ai-studio"
        or primary["response_format"] != "gemini-json-schema-subset"
        or primary["context_window_tokens"] != 1048576
        or primary["maximum_output_tokens"] != 65536
        or primary["pricing_usd_per_million_input_tokens"] != 0.75
        or primary["pricing_usd_per_million_output_tokens"] != 3.75
        or primary["provider_policy"].get("training") is not False
        or primary["provider_policy"].get("retainsPrompts") is not True
        or primary["provider_policy"].get("retentionDays") != 55
        or primary["routing"]
        != {
            "only": ["google-ai-studio"],
            "order": ["google-ai-studio"],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "allow",
            "zdr": False,
        }
    ):
        raise PanelExecutionError("Gemini routing binding drifted")
    deepseek = reviewers[reviewer_ids[2]]
    if (
        deepseek["provider_model"] != "deepseek-v4-pro"
        or deepseek["documented_revision"] != "DeepSeek-V4-Pro-0813"
    ):
        raise PanelExecutionError("DeepSeek model binding drifted")
    cost = binding["cost_guard"]
    expected_reservation = 0.406426 if reviewer_ids == GEMINI_REVIEWER_IDS else 1.563034
    if (
        cost["conservative_peak_reservation_usd"] != expected_reservation
        or cost["emergency_hard_stop_usd"] != 3.0
        or cost["pre_call_reservation_required"] is not True
        or cost["post_call_reported_cost_check_required"] is not True
    ):
        raise PanelExecutionError("review cost guard drifted")
    return binding


def binding_age_hours(
    binding: dict[str, Any], *, now: datetime | None = None
) -> float:
    try:
        verified = datetime.fromisoformat(binding["verified_at"])
    except (KeyError, TypeError, ValueError) as error:
        raise PanelExecutionError("binding verified_at is invalid") from error
    if verified.tzinfo is None:
        raise PanelExecutionError("binding verified_at lacks timezone")
    current = now or datetime.now(timezone.utc)
    age = (
        current.astimezone(timezone.utc) - verified.astimezone(timezone.utc)
    ).total_seconds() / 3600
    if age < 0:
        raise PanelExecutionError("reviewer binding is future dated")
    return age


def load_assets(attempt_path: Path | None = None) -> dict[str, Any]:
    parent_instrument = validate_instrument(INSTRUMENT_PATH)
    packet = _load(PACKET_PATH)
    validate_packet(packet)
    if attempt_path is None:
        instrument = parent_instrument
        contract = instrument["reviewer_binding_contract"]
        binding_path = ROOT / contract["path"]
        binding = load_binding(binding_path)
        if binding["content_sha256"] != contract["content_sha256"]:
            raise PanelExecutionError("instrument reviewer binding hash drifted")
        attempt_id = INSTRUMENT_ID
    else:
        instrument = _load(attempt_path)
        content_hash = instrument.get("content_sha256")
        unhashed = {key: value for key, value in instrument.items() if key != "content_sha256"}
        if content_hash != canonical_sha256(unhashed):
            raise PanelExecutionError("attempt instrument content hash drifted")
        if instrument.get("attempt_id") != ATTEMPT_003_ID:
            raise PanelExecutionError("attempt instrument identity drifted")
        parent = instrument.get("parent_instrument", {})
        if (
            parent.get("instrument_id") != INSTRUMENT_ID
            or parent.get("content_sha256") != canonical_sha256(parent_instrument)
            or parent.get("packet_sha256") != packet["content_sha256"]
        ):
            raise PanelExecutionError("attempt parent binding drifted")
        contract = instrument["reviewer_binding_contract"]
        binding_path = ROOT / contract["path"]
        binding = load_binding(binding_path)
        if (
            binding["binding_id"] != contract["binding_id"]
            or binding["content_sha256"] != contract["content_sha256"]
        ):
            raise PanelExecutionError("attempt reviewer binding hash drifted")
        attempt_id = instrument["attempt_id"]
    reviewer_ids = tuple(row["reviewer_id"] for row in binding["reviewers"])
    return {
        "instrument": instrument,
        "parent_instrument": parent_instrument,
        "binding": binding,
        "packet": packet,
        "attempt_id": attempt_id,
        "reviewer_ids": reviewer_ids,
    }


def _reviewer(binding: dict[str, Any], reviewer_id: str) -> dict[str, Any]:
    return next(row for row in binding["reviewers"] if row["reviewer_id"] == reviewer_id)


def _chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def response_schema(
    item_ids: list[str], *, gemini_compatible: bool = False
) -> dict[str, Any]:
    vote = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(
            {
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
            }
        ),
        "properties": {
            "review_item_id": {"type": "string", "enum": item_ids},
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
            "boundary_reason": {"type": ["string", "null"]},
            "ambiguity_detected": {"type": "boolean"},
            "evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
            "defect_types": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
            "concise_rationale": {"type": "string", "minLength": 1, "maxLength": 600},
        },
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["votes"],
        "properties": {
            "votes": {
                "type": "array",
                "items": vote,
                "minItems": len(item_ids),
                "maxItems": len(item_ids),
            }
        },
    }
    if gemini_compatible:
        # Gemini supports a documented JSON-Schema subset. Keep the provider
        # contract deliberately small and enforce these constraints locally in
        # parse_votes/validate_vote instead.
        vote["properties"]["evidence_ids"].pop("uniqueItems")
        vote["properties"]["defect_types"].pop("uniqueItems")
        vote["properties"]["concise_rationale"].pop("minLength")
        vote["properties"]["concise_rationale"].pop("maxLength")
        schema["properties"]["votes"].pop("minItems")
        schema["properties"]["votes"].pop("maxItems")
    return schema


SYSTEM_PROMPT = """You are a blinded academic factual-QA reviewer. Use only the supplied question, candidate record, and supplied public-source evidence. Do not infer hidden labels, use external knowledge, identify experimental conditions, or modify the source-derived truth. Judge every item exactly once and return only strict JSON matching the schema. A rationale must be concise (at most 80 words)."""


def review_prompt(items: list[dict[str, Any]], schema: dict[str, Any]) -> str:
    return json.dumps(
        {
            "instructions": {
                "use_only_visible_sources": True,
                "validate_action_answer_claims_and_citations_separately": True,
                "empty_sources_cannot_support_an_answer": True,
                "report_visible_defects_without_guessing_hidden_mutations": True,
                "return_every_review_item_once": True,
            },
            "items": items,
            "output_schema": schema,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def estimate_input_tokens(items: list[dict[str, Any]]) -> int:
    schema = response_schema([row["review_item_id"] for row in items])
    rendered = SYSTEM_PROMPT + review_prompt(items, schema)
    return math.ceil(len(rendered) / 3)


def parse_votes(content: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise PanelExecutionError("provider response is not JSON") from error
    if not isinstance(value, dict) or set(value) != {"votes"}:
        raise PanelExecutionError("provider response root drifted")
    votes = value["votes"]
    expected_ids = [row["review_item_id"] for row in items]
    if not isinstance(votes, list) or len(votes) != len(expected_ids):
        raise PanelExecutionError("provider response vote count drifted")
    by_id: dict[str, dict[str, Any]] = {}
    for vote in votes:
        if not isinstance(vote, dict):
            raise PanelExecutionError("provider vote is not an object")
        item_id = vote.get("review_item_id")
        if item_id not in expected_ids or item_id in by_id:
            raise PanelExecutionError("provider response identity drifted")
        try:
            validated = validate_vote(vote, expected_item_id=item_id)
        except PanelReviewError as error:
            raise PanelExecutionError(str(error)) from error
        visible_item = next(row for row in items if row["review_item_id"] == item_id)
        visible_evidence_ids = {
            row["evidence_id"] for row in visible_item["provided_sources"]
        }
        if not set(validated["evidence_ids"]).issubset(visible_evidence_ids):
            raise PanelExecutionError("provider vote cites an unknown visible evidence ID")
        if validated["expected_action"] == "answer":
            if (
                validated["question_answerable_from_supplied_sources"] is not True
                or validated["boundary_reason"] is not None
                or validated["atomic_claim_support"] == "not-applicable"
                or validated["citation_support"] == "not-applicable"
            ):
                raise PanelExecutionError("provider answer vote is internally inconsistent")
        elif (
            validated["question_answerable_from_supplied_sources"] is not False
            or not isinstance(validated["boundary_reason"], str)
            or not validated["boundary_reason"].strip()
            or validated["atomic_claim_support"] != "not-applicable"
            or validated["citation_support"] != "not-applicable"
            or validated["evidence_ids"]
        ):
            raise PanelExecutionError("provider boundary vote is internally inconsistent")
        by_id[item_id] = validated
    if set(by_id) != set(expected_ids):
        raise PanelExecutionError("provider response coverage drifted")
    return [by_id[item_id] for item_id in expected_ids]


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PanelExecutionError(f"provider response has invalid {field}")
    return value


class HttpPanelTransport:
    """Direct no-retry transport for the two frozen provider reviewers."""

    async def call(
        self,
        *,
        reviewer: dict[str, Any],
        items: list[dict[str, Any]],
        schema: dict[str, Any],
    ) -> ProviderBatchResult:
        prompt = review_prompt(items, schema)
        if reviewer["provider"] == "openrouter":
            key = os.getenv(reviewer["credential_environment_variable"], "").strip()
            url = OPENROUTER_CHAT_URL
            payload: dict[str, Any] = {
                "model": reviewer["provider_model"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 3072,
                "temperature": reviewer["temperature"],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "academic_factual_qa_panel_votes",
                        "strict": True,
                        "schema": schema,
                    },
                },
                "provider": deepcopy(reviewer["routing"]),
                "usage": {"include": True},
            }
        else:
            key = os.getenv(reviewer["credential_environment_variable"], "").strip()
            url = "https://api.deepseek.com/chat/completions"
            payload = {
                "model": reviewer["provider_model"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 3072,
                "temperature": reviewer["temperature"],
                "thinking": {"type": reviewer["thinking"]},
                "response_format": {"type": "json_object"},
            }
        if not key:
            raise PanelExecutionError(
                f"credential missing: {reviewer['credential_environment_variable']}"
            )
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=httpx.Timeout(120)) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/horiiiiii032929/digital-twin",
                    "X-OpenRouter-Title": "Course Digital Twin evaluation",
                },
                json=payload,
            )
        latency_ms = (time.perf_counter() - started) * 1000
        try:
            value = response.json()
        except ValueError as error:
            raise ProviderCallFailure(
                "provider-http-non-json",
                {
                    "http_status": response.status_code,
                    "request_id": response.headers.get("x-request-id"),
                    "latency_ms": latency_ms,
                    "cost_accounting_status": "unavailable-provider-error",
                },
            ) from error
        if response.is_error or not isinstance(value, dict) or value.get("error"):
            provider_error = value.get("error") if isinstance(value, dict) else None
            error_code = (
                provider_error.get("code") if isinstance(provider_error, dict) else None
            )
            error_message = (
                provider_error.get("message")
                if isinstance(provider_error, dict)
                else None
            )
            raise ProviderCallFailure(
                "provider-http-error",
                {
                    "http_status": response.status_code,
                    "request_id": (
                        value.get("id") if isinstance(value, dict) else None
                    )
                    or response.headers.get("x-request-id"),
                    "provider_error_code": error_code,
                    "provider_error_message": (
                        str(error_message)[:500] if error_message is not None else None
                    ),
                    "latency_ms": latency_ms,
                    "cost_accounting_status": "unavailable-provider-error",
                },
            )
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise PanelExecutionError("provider response choices drifted")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise PanelExecutionError("provider response content is empty")
        model = value.get("model")
        if model != reviewer["provider_model"]:
            raise PanelExecutionError("provider response model identity drifted")
        provider_name = value.get("provider", reviewer["provider"])
        if (
            reviewer["provider"] == "openrouter"
            and provider_name != reviewer["endpoint_provider"]
        ):
            raise PanelExecutionError("OpenRouter endpoint provider drifted")
        usage = value.get("usage") if isinstance(value.get("usage"), dict) else {}
        input_tokens = _non_negative_int(usage.get("prompt_tokens"), "prompt_tokens")
        output_tokens = _non_negative_int(
            usage.get("completion_tokens"), "completion_tokens"
        )
        if reviewer["provider"] == "openrouter":
            estimated = (
                input_tokens * reviewer["pricing_usd_per_million_input_tokens"]
                + output_tokens * reviewer["pricing_usd_per_million_output_tokens"]
            ) / 1_000_000
            reported = usage.get("cost", estimated)
        else:
            reported = (
                input_tokens
                * reviewer["pricing_usd_per_million_cache_miss_input_tokens_peak"]
                + output_tokens * reviewer["pricing_usd_per_million_output_tokens_peak"]
            ) / 1_000_000
        if isinstance(reported, bool) or not isinstance(reported, (int, float)):
            raise PanelExecutionError("provider response cost is invalid")
        return ProviderBatchResult(
            content=content,
            provider_model=model,
            provider_revision=(
                value.get("system_fingerprint")
                if isinstance(value.get("system_fingerprint"), str)
                else None
            ),
            provider_name=str(provider_name),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(reported),
            latency_ms=latency_ms,
        )


class SimulatedPanelTransport:
    """Network-free all-correct transport used to test the execution state machine."""

    def __init__(self, ideal_votes: dict[str, dict[str, Any]]) -> None:
        self.ideal_votes = ideal_votes

    async def call(
        self,
        *,
        reviewer: dict[str, Any],
        items: list[dict[str, Any]],
        schema: dict[str, Any],
    ) -> ProviderBatchResult:
        del schema
        return ProviderBatchResult(
            content=json.dumps(
                {"votes": [self.ideal_votes[row["review_item_id"]] for row in items]}
            ),
            provider_model=reviewer["provider_model"],
            provider_revision=reviewer.get("documented_revision"),
            provider_name=(
                reviewer.get("endpoint_provider") or reviewer["provider"]
            ),
            input_tokens=500,
            output_tokens=250,
            cost_usd=0.001,
            latency_ms=1.0,
        )


def _maximum_call_cost(binding: dict[str, Any], reviewer_id: str) -> float:
    reviewer = _reviewer(binding, reviewer_id)
    contract = binding["execution_contract"]
    input_tokens = contract["maximum_input_tokens_per_call"]
    output_tokens = contract["maximum_output_tokens_per_call"]
    if reviewer["provider"] == "openrouter":
        input_price = reviewer["pricing_usd_per_million_input_tokens"]
        output_price = reviewer["pricing_usd_per_million_output_tokens"]
    else:
        input_price = reviewer["pricing_usd_per_million_cache_miss_input_tokens_peak"]
        output_price = reviewer["pricing_usd_per_million_output_tokens_peak"]
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


def _initial_ledger(assets: dict[str, Any], *, simulation: bool) -> dict[str, Any]:
    ledger = initialize_ledger(
        packet_sha256=assets["packet"]["content_sha256"],
        instrument_sha256=canonical_sha256(assets["instrument"]),
        reviewer_bindings_sha256=assets["binding"]["content_sha256"],
        pricing_sha256=canonical_sha256(assets["binding"]["cost_guard"]),
    )
    ledger.update(
        {
            "schema_version": 2,
            "instrument_id": INSTRUMENT_ID,
            "attempt_id": assets["attempt_id"],
            "status": "running-calibration",
            "simulation": simulation,
            "code_revision": _code_revision(),
            "provider_call_records": [],
            "provider_failures": [],
            "provider_identities": {},
            "codex_task_id": None,
            "aggregate": None,
        }
    )
    return ledger


def _validate_execution_resume(
    ledger: dict[str, Any], assets: dict[str, Any], *, simulation: bool
) -> None:
    validate_resume(
        ledger,
        packet_sha256=assets["packet"]["content_sha256"],
        instrument_sha256=canonical_sha256(assets["instrument"]),
        reviewer_bindings_sha256=assets["binding"]["content_sha256"],
        pricing_sha256=canonical_sha256(assets["binding"]["cost_guard"]),
    )
    if ledger.get("instrument_id") != INSTRUMENT_ID:
        raise PanelExecutionError("resume instrument identity drifted")
    if ledger.get("attempt_id") != assets["attempt_id"]:
        raise PanelExecutionError("resume attempt identity drifted")
    if ledger.get("code_revision") != _code_revision():
        raise PanelExecutionError("resume code revision drifted")
    if ledger.get("simulation") is not simulation:
        raise PanelExecutionError("resume simulation state drifted")
    if ledger["provider_calls"] != len(ledger.get("provider_call_records", [])):
        raise PanelExecutionError("resume provider-call accounting drifted")


def _load_or_create_ledger(
    assets: dict[str, Any], output_path: Path, *, simulation: bool, resume: bool
) -> dict[str, Any]:
    if resume:
        ledger = _load(output_path)
        _validate_execution_resume(ledger, assets, simulation=simulation)
        return ledger
    ledger = _initial_ledger(assets, simulation=simulation)
    write_ledger_atomic(output_path, ledger, exclusive=True)
    return ledger


def _codex_vote_payload(
    *,
    votes: list[dict[str, Any]],
    item_kind: str,
    packet_sha256: str,
    task_id: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "reviewer_id": REVIEWER_IDS[0],
        "provider_model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
        "task_id": task_id,
        "packet_sha256": packet_sha256,
        "item_kind": item_kind,
        "votes": votes,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    return payload


def validate_codex_votes(
    path: Path,
    *,
    packet: dict[str, Any],
    item_kind: str,
    expected_task_id: str | None = None,
) -> dict[str, Any]:
    payload = _load(path)
    content_hash = payload.pop("content_sha256", None)
    if content_hash != canonical_sha256(payload):
        raise PanelExecutionError("Codex vote artifact hash drifted")
    payload["content_sha256"] = content_hash
    expected_items = [row for row in packet["items"] if row["item_kind"] == item_kind]
    if {
        "reviewer_id": payload.get("reviewer_id"),
        "provider_model": payload.get("provider_model"),
        "reasoning_effort": payload.get("reasoning_effort"),
        "packet_sha256": payload.get("packet_sha256"),
        "item_kind": payload.get("item_kind"),
    } != {
        "reviewer_id": REVIEWER_IDS[0],
        "provider_model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
        "packet_sha256": packet["content_sha256"],
        "item_kind": item_kind,
    }:
        raise PanelExecutionError("Codex vote binding drifted")
    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise PanelExecutionError("Codex task identity is missing")
    if expected_task_id is not None and task_id != expected_task_id:
        raise PanelExecutionError("Codex task identity changed between phases")
    votes = payload.get("votes")
    if not isinstance(votes, list) or len(votes) != len(expected_items):
        raise PanelExecutionError("Codex vote coverage drifted")
    expected_ids = [row["review_item_id"] for row in expected_items]
    by_id = {}
    for vote in votes:
        if not isinstance(vote, dict):
            raise PanelExecutionError("Codex vote is not an object")
        item_id = vote.get("review_item_id")
        if item_id not in expected_ids or item_id in by_id:
            raise PanelExecutionError("Codex vote identity drifted")
        by_id[item_id] = validate_vote(vote, expected_item_id=item_id)
    if set(by_id) != set(expected_ids):
        raise PanelExecutionError("Codex vote coverage is incomplete")
    payload["votes"] = [by_id[item_id] for item_id in expected_ids]
    return payload


def _append_codex_votes(ledger: dict[str, Any], payload: dict[str, Any]) -> None:
    existing = {
        (row["reviewer_id"], row["review_item_id"]) for row in ledger["votes"]
    }
    for vote in payload["votes"]:
        identity = (REVIEWER_IDS[0], vote["review_item_id"])
        if identity not in existing:
            append_vote(
                ledger,
                reviewer_id=REVIEWER_IDS[0],
                vote=vote,
                provider_call=False,
            )
    ledger["codex_task_id"] = payload["task_id"]


async def _run_batches(
    *,
    assets: dict[str, Any],
    ledger: dict[str, Any],
    output_path: Path,
    transport: PanelTransport,
    item_kind: str,
) -> bool:
    binding = assets["binding"]
    items = [row for row in assets["packet"]["items"] if row["item_kind"] == item_kind]
    completed = {
        (row["reviewer_id"], row["review_item_id"]) for row in ledger["votes"]
    }
    queued: dict[str, list[list[dict[str, Any]]]] = {}
    for reviewer_id in assets["reviewer_ids"][1:]:
        reviewer = _reviewer(binding, reviewer_id)
        remaining = [
            row for row in items if (reviewer_id, row["review_item_id"]) not in completed
        ]
        queued[reviewer_id] = _chunks(
            remaining, binding["execution_contract"]["provider_batch_size"]
        )
    schedule = [
        (reviewer_id, batches[0])
        for reviewer_id, batches in queued.items()
        if batches
    ] + [
        (reviewer_id, batch)
        for reviewer_id, batches in queued.items()
        for batch in batches[1:]
    ]
    for reviewer_id, batch in schedule:
            reviewer = _reviewer(binding, reviewer_id)
            if ledger["provider_calls"] >= binding["execution_contract"]["maximum_provider_calls"]:
                ledger["status"] = "invalid-execution"
                ledger["provider_failures"].append({"reason": "provider-call-limit"})
                write_ledger_atomic(output_path, ledger)
                return False
            reservation = _maximum_call_cost(binding, reviewer_id)
            hard_stop = binding["cost_guard"]["emergency_hard_stop_usd"]
            if ledger["reported_cost_usd"] + reservation > hard_stop:
                ledger["status"] = "invalid-execution"
                ledger["provider_failures"].append({"reason": "pre-call-budget-stop"})
                write_ledger_atomic(output_path, ledger)
                return False
            if estimate_input_tokens(batch) > binding["execution_contract"]["maximum_input_tokens_per_call"]:
                ledger["status"] = "invalid-execution"
                ledger["provider_failures"].append({"reason": "planned-input-limit"})
                write_ledger_atomic(output_path, ledger)
                return False
            schema = response_schema(
                [row["review_item_id"] for row in batch],
                gemini_compatible=(
                    reviewer.get("response_format") == "gemini-json-schema-subset"
                ),
            )
            raw: ProviderBatchResult | None = None
            try:
                raw = await transport.call(reviewer=reviewer, items=batch, schema=schema)
                contract = binding["execution_contract"]
                if (
                    raw.input_tokens > contract["maximum_input_tokens_per_call"]
                    or raw.output_tokens > contract["maximum_output_tokens_per_call"]
                ):
                    raise PanelExecutionError("provider token limit violated")
                identity = {
                    "provider_model": raw.provider_model,
                    "provider_revision": raw.provider_revision,
                    "provider_name": raw.provider_name,
                }
                previous_identity = ledger["provider_identities"].get(reviewer_id)
                if previous_identity is not None and previous_identity != identity:
                    raise PanelExecutionError("provider runtime identity drifted")
                votes = parse_votes(raw.content, batch)
            except Exception as error:  # one no-retry failure is durable and terminal
                ledger["provider_calls"] += 1
                ledger["malformed_response_count"] += int(
                    isinstance(error, PanelExecutionError)
                    and not isinstance(error, ProviderCallFailure)
                )
                failure = {
                    "reviewer_id": reviewer_id,
                    "item_ids": [row["review_item_id"] for row in batch],
                    "reason": type(error).__name__,
                    "detail": str(error)[:500],
                }
                call_record: dict[str, Any] = {**failure, "status": "failed"}
                if isinstance(error, ProviderCallFailure):
                    failure["category"] = error.category
                    call_record["category"] = error.category
                    call_record.update(error.details)
                elif raw is not None:
                    ledger["input_tokens"] += raw.input_tokens
                    ledger["output_tokens"] += raw.output_tokens
                    ledger["reported_cost_usd"] = round(
                        ledger["reported_cost_usd"] + raw.cost_usd, 9
                    )
                    call_record.update(
                        {
                            "provider_model": raw.provider_model,
                            "provider_revision": raw.provider_revision,
                            "provider_name": raw.provider_name,
                            "input_tokens": raw.input_tokens,
                            "output_tokens": raw.output_tokens,
                            "reported_cost_usd": raw.cost_usd,
                            "latency_ms": raw.latency_ms,
                            "response_content_sha256": canonical_sha256(
                                {"content": raw.content}
                            ),
                            "cost_accounting_status": "complete",
                        }
                    )
                ledger["provider_failures"].append(failure)
                ledger["provider_call_records"].append(call_record)
                ledger["status"] = "invalid-execution"
                write_ledger_atomic(output_path, ledger)
                return False
            ledger["provider_calls"] += 1
            ledger["provider_identities"].setdefault(reviewer_id, identity)
            ledger["input_tokens"] += raw.input_tokens
            ledger["output_tokens"] += raw.output_tokens
            ledger["reported_cost_usd"] = round(
                ledger["reported_cost_usd"] + raw.cost_usd, 9
            )
            ledger["provider_call_records"].append(
                {
                    "reviewer_id": reviewer_id,
                    "item_ids": [row["review_item_id"] for row in batch],
                    "status": "completed",
                    "provider_model": raw.provider_model,
                    "provider_revision": raw.provider_revision,
                    "provider_name": raw.provider_name,
                    "input_tokens": raw.input_tokens,
                    "output_tokens": raw.output_tokens,
                    "reported_cost_usd": raw.cost_usd,
                    "latency_ms": raw.latency_ms,
                }
            )
            for vote in votes:
                append_vote(
                    ledger,
                    reviewer_id=reviewer_id,
                    vote=vote,
                    provider_call=False,
                )
            if ledger["reported_cost_usd"] > hard_stop:
                ledger["status"] = "invalid-execution"
                ledger["provider_failures"].append({"reason": "post-call-budget-stop"})
                write_ledger_atomic(output_path, ledger)
                return False
            write_ledger_atomic(output_path, ledger)
    return True


def _all_calibration_metrics(
    ledger: dict[str, Any], reviewer_ids: tuple[str, str, str]
) -> dict[str, Any]:
    _, control_truth = _truth_maps()
    result = {}
    for reviewer_id in reviewer_ids:
        votes = [
            row
            for row in ledger["votes"]
            if row["reviewer_id"] == reviewer_id
            and row["review_item_id"] in control_truth
        ]
        result[reviewer_id] = (
            _calibration_metrics(votes, control_truth)
            if len(votes) == 40
            else {"passed": False, "reason": "incomplete-calibration"}
        )
    return result


async def execute_calibration(
    assets: dict[str, Any],
    *,
    codex_votes_path: Path,
    output_path: Path,
    transport: PanelTransport,
    simulation: bool,
    resume: bool,
) -> dict[str, Any]:
    ledger = _load_or_create_ledger(
        assets, output_path, simulation=simulation, resume=resume
    )
    if ledger["status"] not in {"running-calibration", "invalid-execution"}:
        raise PanelExecutionError("calibration resume state drifted")
    if ledger["status"] == "invalid-execution":
        return ledger
    codex = validate_codex_votes(
        codex_votes_path, packet=assets["packet"], item_kind="calibration"
    )
    _append_codex_votes(ledger, codex)
    write_ledger_atomic(output_path, ledger)
    if not await _run_batches(
        assets=assets,
        ledger=ledger,
        output_path=output_path,
        transport=transport,
        item_kind="calibration",
    ):
        return ledger
    metrics = _all_calibration_metrics(ledger, assets["reviewer_ids"])
    ledger["calibration"] = metrics
    passed = all(row["passed"] for row in metrics.values())
    if assets["attempt_id"] == ATTEMPT_003_ID:
        ledger["status"] = "completed-go-deeper" if passed else "completed-refine"
    else:
        ledger["status"] = (
            "calibration-completed-confirmation-not-started"
            if passed
            else "panel-calibration-failed"
        )
    write_ledger_atomic(output_path, ledger)
    return ledger


async def execute_confirmation(
    assets: dict[str, Any],
    *,
    codex_votes_path: Path,
    output_path: Path,
    researcher_packet_path: Path,
    transport: PanelTransport,
    simulation: bool,
) -> dict[str, Any]:
    ledger = _load(output_path)
    _validate_execution_resume(ledger, assets, simulation=simulation)
    if ledger["status"] != "calibration-completed-confirmation-not-started":
        raise PanelExecutionError("confirmation cannot start before calibration passes")
    codex = validate_codex_votes(
        codex_votes_path,
        packet=assets["packet"],
        item_kind="confirmation",
        expected_task_id=ledger["codex_task_id"],
    )
    _append_codex_votes(ledger, codex)
    ledger["status"] = "running-confirmation"
    write_ledger_atomic(output_path, ledger)
    if not await _run_batches(
        assets=assets,
        ledger=ledger,
        output_path=output_path,
        transport=transport,
        item_kind="confirmation",
    ):
        return ledger
    aggregate = aggregate_panel(
        ledger=ledger,
        packet=assets["packet"],
        reviewer_ids=assets["reviewer_ids"],
    )
    ledger["aggregate"] = aggregate
    ledger["status"] = aggregate["status"]
    write_ledger_atomic(output_path, ledger)
    if aggregate["status"] == "ready-researcher-audit":
        researcher = build_researcher_packet(
            aggregate=aggregate, packet=assets["packet"], ledger=ledger
        )
        write_ledger_atomic(researcher_packet_path, researcher, exclusive=True)
    return ledger


def prepare_codex_workspace(assets: dict[str, Any], output: Path) -> dict[str, Any]:
    if output.exists():
        raise PanelExecutionError(f"Codex workspace already exists: {output}")
    output.mkdir(parents=True)
    packet = assets["packet"]
    for kind in ("calibration", "confirmation"):
        value = {
            "schema_version": 1,
            "packet_id": f"{packet['packet_id']}-{kind}",
            "parent_packet_sha256": packet["content_sha256"],
            "item_kind": kind,
            "items": [row for row in packet["items"] if row["item_kind"] == kind],
        }
        value["content_sha256"] = canonical_sha256(value)
        (output / f"{kind}-packet.json").write_text(
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    (output / "REVIEW_INSTRUCTIONS.md").write_text(
        "# Blinded factual-QA panel review\n\n"
        "Use only the packet supplied for the current phase. Do not browse, use "
        "external knowledge, or inspect the source repository. Produce the exact vote "
        "schema specified by the packet contract. First complete calibration only and "
        "wait. Continue to confirmation only after the researcher reports that all "
        "three reviewers passed calibration. Keep the same task and report the runtime "
        "model as `gpt-5.6-sol` with reasoning effort `medium`.\n",
        encoding="utf-8",
    )
    return {
        "status": "prepared-no-review-call",
        "path": str(output),
        "files": sorted(path.name for path in output.iterdir()),
        "contains_hidden_truth": False,
        "provider_calls": 0,
    }


def _fetch_json(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = Request(url, headers=headers or {"User-Agent": "digital-twin-eval/1"})
    with urlopen(request, timeout=20) as response:  # noqa: S310 fixed official URLs
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise PanelExecutionError("provider metadata root is not an object")
    return value


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "digital-twin-eval/1"})
    with urlopen(request, timeout=20) as response:  # noqa: S310 fixed official URLs
        return response.read().decode("utf-8")


def live_metadata_failures(assets: dict[str, Any]) -> list[str]:
    binding = assets["binding"]
    failures: list[str] = []
    reviewer_ids = assets["reviewer_ids"]
    primary = _reviewer(binding, reviewer_ids[1])
    registry = _fetch_json(OPENROUTER_MODELS_URL)
    model = next(
        (row for row in registry.get("data", []) if row.get("id") == primary["provider_model"]),
        None,
    )
    if model is None:
        failures.append("openrouter-model-missing")
    else:
        pricing = model.get("pricing", {})
        if (
            int(model.get("context_length", 0)) != primary["context_window_tokens"]
            or float(pricing.get("prompt", -1)) * 1_000_000
            > primary["pricing_usd_per_million_input_tokens"]
            or float(pricing.get("completion", -1)) * 1_000_000
            > primary["pricing_usd_per_million_output_tokens"]
        ):
            failures.append("openrouter-model-metadata-drift")
        if primary.get("documented_revision") and model.get("canonical_slug") != primary[
            "documented_revision"
        ]:
            failures.append("openrouter-model-revision-drift")
    endpoints = _fetch_json(primary["endpoint_registry_source"])
    endpoint = next(
        (
            row
            for row in endpoints.get("data", {}).get("endpoints", [])
            if row.get("provider_name") == primary["endpoint_provider"]
            and row.get("tag") == primary["endpoint_tag"]
            and row.get("status") == 0
        ),
        None,
    )
    if endpoint is None:
        failures.append("openrouter-endpoint-missing")
    elif reviewer_ids == GEMINI_REVIEWER_IDS:
        endpoint_pricing = endpoint.get("pricing", {})
        required_parameters = {"max_tokens", "temperature", "response_format", "structured_outputs"}
        if (
            endpoint.get("name") != primary["endpoint_name"]
            or int(endpoint.get("context_length", 0)) != primary["context_window_tokens"]
            or int(endpoint.get("max_completion_tokens", 0))
            != primary["maximum_output_tokens"]
            or float(endpoint_pricing.get("prompt", -1)) * 1_000_000
            != primary["pricing_usd_per_million_input_tokens"]
            or float(endpoint_pricing.get("completion", -1)) * 1_000_000
            != primary["pricing_usd_per_million_output_tokens"]
            or not required_parameters.issubset(endpoint.get("supported_parameters", []))
        ):
            failures.append("gemini-endpoint-metadata-drift")
        policies = _fetch_json(GOOGLE_PROVIDER_POLICY_URL)
        provider = next(
            (
                row
                for row in policies.get("data", [])
                if row.get("displayName") == primary["endpoint_provider"]
            ),
            None,
        )
        if provider is None or provider.get("dataPolicy") != primary["provider_policy"]:
            failures.append("gemini-provider-policy-drift")
    deepseek = _reviewer(binding, reviewer_ids[2])
    key = os.getenv(deepseek["credential_environment_variable"], "").strip()
    models = (
        _fetch_json(DEEPSEEK_MODELS_URL, headers={"Authorization": f"Bearer {key}"})
        if key
        else {"data": []}
    )
    if deepseek["provider_model"] not in {
        row.get("id") for row in models.get("data", [])
    }:
        failures.append("deepseek-model-missing")
    pricing = parse_deepseek_pricing(_fetch_text(DEEPSEEK_PRICING_URL))
    current = pricing["models"].get(deepseek["provider_model"])
    if current != {
        "documented_revision": deepseek["documented_revision"],
        "peak_cache_miss_input_per_million_usd": deepseek[
            "pricing_usd_per_million_cache_miss_input_tokens_peak"
        ],
        "peak_output_per_million_usd": deepseek[
            "pricing_usd_per_million_output_tokens_peak"
        ],
    }:
        failures.append("deepseek-model-or-price-drift")
    return failures


def build_preflight(
    assets: dict[str, Any],
    *,
    live: bool,
    output_path: Path = DEFAULT_LEDGER_PATH,
    codex_votes_path: Path | None = None,
) -> dict[str, Any]:
    instrument = assets["instrument"]
    binding = assets["binding"]
    safety = instrument["execution_safety"]
    age = binding_age_hours(binding)
    fresh = age <= binding["maximum_age_hours_for_execution"]
    live_failures = live_metadata_failures(assets) if live else ["live-metadata-not-checked"]
    credentials = {
        row["reviewer_id"]: bool(
            os.getenv(row["credential_environment_variable"], "").strip()
        )
        for row in binding["reviewers"]
        if "credential_environment_variable" in row
    }
    blockers = []
    if not all(
        binding["authorization"][key]
        for key in (
            "codex_review_authorized",
            "provider_review_authorized",
            "paid_execution_authorized",
        )
    ) or not all(
        safety[key]
        for key in (
            "calibration_execution_authorized",
            "codex_review_authorized",
            "provider_review_authorized",
            "paid_execution_authorized",
        )
    ):
        blockers.append("calibration-execution-not-authorized")
    if assets["attempt_id"] not in BOUNDED_PILOT_AUTHORIZATIONS:
        blockers.append("bounded-freeze-authorization-missing")
    if instrument["status"] != "frozen-pending-execution":
        blockers.append("instrument-not-frozen-for-execution")
    if not fresh or live_failures:
        blockers.append("reviewer-metadata-not-current")
    if not all(credentials.values()):
        blockers.append("provider-credential-missing")
    if _working_tree_dirty():
        blockers.append("working-tree-dirty")
    if output_path.exists():
        blockers.append("output-path-already-exists")
    expected_codex_votes = codex_votes_path or (
        ROOT / binding["reviewers"][0]["calibration_vote_path"]
    )
    if not expected_codex_votes.exists():
        blockers.append("codex-calibration-votes-missing")
    return {
        "instrument_id": assets["attempt_id"],
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "binding_age_hours": age,
        "binding_fresh": fresh,
        "live_metadata_checked": live,
        "live_metadata_failures": live_failures,
        "credentials_present": credentials,
        "credential_values_emitted": False,
        "maximum_provider_calls": binding["execution_contract"]["maximum_provider_calls"],
        "conservative_peak_reservation_usd": binding["cost_guard"][
            "conservative_peak_reservation_usd"
        ],
        "emergency_hard_stop_usd": binding["cost_guard"]["emergency_hard_stop_usd"],
        "provider_or_model_calls": 0,
    }


def require_execution_authorized(
    assets: dict[str, Any],
    *,
    phase: str,
    output_path: Path,
    codex_votes_path: Path,
    resume: bool,
) -> None:
    instrument = assets["instrument"]
    binding = assets["binding"]
    safety = instrument["execution_safety"]
    required_authorities = [
        "calibration_execution_authorized",
        "codex_review_authorized",
        "provider_review_authorized",
        "paid_execution_authorized",
    ]
    binding_authorities = [
        "codex_review_authorized",
        "provider_review_authorized",
        "paid_execution_authorized",
    ]
    if phase == "confirmation":
        required_authorities.append("confirmation_execution_authorized")
        binding_authorities.append("confirmation_review_authorized")
    if instrument["status"] != "frozen-pending-execution":
        raise PanelExecutionError("instrument is not frozen for execution")
    if not all(safety[key] for key in required_authorities):
        raise PanelExecutionError("instrument review execution is not authorized")
    if not all(binding["authorization"][key] for key in binding_authorities):
        raise PanelExecutionError("reviewer binding execution is not authorized")
    if binding_age_hours(binding) > binding["maximum_age_hours_for_execution"]:
        raise PanelExecutionError("reviewer binding is stale")
    if _working_tree_dirty():
        raise PanelExecutionError("working tree is dirty")
    if not codex_votes_path.is_file():
        raise PanelExecutionError("Codex vote artifact is missing")
    credentials = [
        row["credential_environment_variable"]
        for row in binding["reviewers"]
        if "credential_environment_variable" in row
    ]
    if any(not os.getenv(name, "").strip() for name in credentials):
        raise PanelExecutionError("provider credential is missing")
    if live_metadata_failures(assets):
        raise PanelExecutionError("live reviewer metadata drifted")
    if phase == "calibration":
        if resume is not output_path.is_file():
            raise PanelExecutionError("calibration output/resume state drifted")
    elif phase == "confirmation":
        if not output_path.is_file():
            raise PanelExecutionError("calibration ledger is missing")
    else:
        raise PanelExecutionError("unknown execution phase")


def _simulated_codex_artifact(
    assets: dict[str, Any], *, item_kind: str, path: Path
) -> None:
    packet, ledger = build_simulated_ledger(
        "pass", reviewer_ids=assets["reviewer_ids"]
    )
    votes = [
        {key: value for key, value in row.items() if key != "reviewer_id"}
        for row in ledger["votes"]
        if row["reviewer_id"] == assets["reviewer_ids"][0]
        and any(
            item["review_item_id"] == row["review_item_id"]
            and item["item_kind"] == item_kind
            for item in packet["items"]
        )
    ]
    payload = _codex_vote_payload(
        votes=votes,
        item_kind=item_kind,
        packet_sha256=assets["packet"]["content_sha256"],
        task_id="simulated-isolated-codex-task",
    )
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


async def simulate_full(assets: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise PanelExecutionError(f"simulation output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    calibration = output_dir / "codex-calibration.json"
    confirmation = output_dir / "codex-confirmation.json"
    ledger_path = output_dir / "ledger.json"
    researcher_path = output_dir / "researcher.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=calibration)
    _simulated_codex_artifact(assets, item_kind="confirmation", path=confirmation)
    packet, ideal = build_simulated_ledger(
        "pass", reviewer_ids=assets["reviewer_ids"]
    )
    del packet
    ideal_votes = {
        row["review_item_id"]: {
            key: value for key, value in row.items() if key != "reviewer_id"
        }
        for row in ideal["votes"]
        if row["reviewer_id"] == assets["reviewer_ids"][1]
    }
    transport = SimulatedPanelTransport(ideal_votes)
    calibrated = await execute_calibration(
        assets,
        codex_votes_path=calibration,
        output_path=ledger_path,
        transport=transport,
        simulation=True,
        resume=False,
    )
    if assets["attempt_id"] == ATTEMPT_003_ID:
        return calibrated
    if calibrated["status"] != "calibration-completed-confirmation-not-started":
        return calibrated
    return await execute_confirmation(
        assets,
        codex_votes_path=confirmation,
        output_path=ledger_path,
        researcher_packet_path=researcher_path,
        transport=transport,
        simulation=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--preflight-live", action="store_true")
    mode.add_argument("--prepare-codex-workspace", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--execute-calibration", action="store_true")
    mode.add_argument("--execute-confirmation", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--attempt", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--codex-votes", type=Path)
    parser.add_argument("--codex-workspace", type=Path, default=DEFAULT_CODEX_WORKSPACE)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    assets = load_assets(args.attempt)
    output_path = args.output or (
        ATTEMPT_003_LEDGER_PATH
        if assets["attempt_id"] == ATTEMPT_003_ID
        else DEFAULT_LEDGER_PATH
    )
    if args.execute_calibration or args.execute_confirmation:
        require_bounded_pilot_operation_allowed(assets["attempt_id"])
    if args.validate:
        result = {
            "instrument_id": assets["attempt_id"],
            "status": (
                "validated-attempt-003"
                if assets["attempt_id"] == ATTEMPT_003_ID
                else "validated-attempt-002-invalid-authorization-revoked"
            ),
            "binding_sha256": assets["binding"]["content_sha256"],
            "maximum_provider_calls": assets["binding"]["execution_contract"][
                "maximum_provider_calls"
            ],
            "provider_or_model_calls": 0,
        }
    elif args.preflight or args.preflight_live:
        result = build_preflight(
            assets, live=args.preflight_live, output_path=output_path
        )
    elif args.prepare_codex_workspace:
        result = prepare_codex_workspace(assets, args.codex_workspace)
    elif args.simulate:
        result = asyncio.run(simulate_full(assets, output_path))
    elif args.execute_calibration:
        if args.codex_votes is None:
            raise PanelExecutionError("--codex-votes is required for calibration")
        require_execution_authorized(
            assets,
            phase="calibration",
            output_path=output_path,
            codex_votes_path=args.codex_votes,
            resume=args.resume,
        )
        result = asyncio.run(
            execute_calibration(
                assets,
                codex_votes_path=args.codex_votes,
                output_path=output_path,
                transport=HttpPanelTransport(),
                simulation=False,
                resume=args.resume,
            )
        )
    else:
        if args.codex_votes is None:
            raise PanelExecutionError("--codex-votes is required for confirmation")
        require_execution_authorized(
            assets,
            phase="confirmation",
            output_path=output_path,
            codex_votes_path=args.codex_votes,
            resume=True,
        )
        result = asyncio.run(
            execute_confirmation(
                assets,
                codex_votes_path=args.codex_votes,
                output_path=output_path,
                researcher_packet_path=DEFAULT_RESEARCHER_PACKET_PATH,
                transport=HttpPanelTransport(),
                simulation=False,
            )
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
