#!/usr/bin/env python3
"""Validate, simulate, preflight, or execute the bounded v2 data review."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
from typing import Any
from urllib.request import urlopen

from dotenv import load_dotenv
import httpx

from scripts.prepare_evidence_sufficiency_v2_independent_review import (
    RESPONSE_FIELDS,
    VERDICTS,
    build_review_packet,
    load_instrument,
    validate_judgments,
    validate_review_packet,
)
from scripts.run_factual_qa_v3_scale_pilot_100 import (
    PlannedInterruption,
    RawCall,
    RawTransport,
    _canonical_sha256,
    _checkpoint,
    _code_revision,
    _load_json,
    _sha256_file,
    _working_tree_dirty,
    _write_initial,
)
from services.llm.litellm_client import LiteLlmClient
from src.digital_twin.llm import LlmMessage
from src.digital_twin.repository_freeze import (
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/"
    "evidence_sufficiency_v2_independent_review_003.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/evidence-sufficiency-v2-independent-review-003.json"
)
DEFAULT_SIMULATION_OUTPUT = (
    ROOT / "reports/generated/"
    "evidence-sufficiency-v2-independent-review-003-simulation.json"
)
INSTRUMENT_ID = "evidence-sufficiency-v2-independent-review-003"
NATIVE_OPENROUTER_TRANSPORT = "openrouter-native-chat-completions-v1"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_REGISTRY_URL = "https://openrouter.ai/api/v1/models"


class ReviewRunnerError(ValueError):
    """Raised when the independent-review execution contract drifts."""


@dataclass(frozen=True)
class OpenRouterRawCall(RawCall):
    """Raw call plus OpenRouter-native routing diagnostics."""

    request_id: str | None = None
    generation_id: str | None = None
    openrouter_metadata: dict[str, Any] | None = None


class OpenRouterRequestError(RuntimeError):
    """Sanitized OpenRouter HTTP failure safe for ignored checkpoints."""

    def __init__(
        self,
        *,
        error_code: str,
        error_message: str,
        status_code: int | None = None,
        request_id: str | None = None,
        generation_id: str | None = None,
        openrouter_metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.status_code = status_code
        self.request_id = request_id
        self.generation_id = generation_id
        self.openrouter_metadata = deepcopy(openrouter_metadata)

    def record(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "error_detail": self.error_message,
            "http_status": self.status_code,
            "request_id": self.request_id,
            "generation_id": self.generation_id,
            "openrouter_metadata": deepcopy(self.openrouter_metadata),
        }


def _provider_binding(instrument: dict[str, Any]) -> dict[str, Any]:
    safety = instrument["execution_safety"]
    return {
        "provider": safety["reviewer_provider"],
        "provider_model": safety["reviewer_model"],
        "litellm_model": safety["reviewer_litellm_model"],
        "transport": safety.get("reviewer_transport", "litellm-openrouter-v1"),
        "api_url": safety.get("reviewer_api_url"),
        "provider_routing": deepcopy(safety["provider_routing"]),
        "timeout_seconds": safety["timeout_seconds"],
        "temperature": safety.get("temperature"),
        "reasoning_effort": safety.get("reasoning_effort"),
        "seed": safety.get("seed"),
        "backend_model": safety.get("reviewer_backend_model"),
        "max_input_tokens": safety["max_input_tokens_per_call"],
        "max_output_tokens": safety["max_output_tokens_per_call"],
        "pricing_usd_per_million_input_tokens": safety[
            "pricing_usd_per_million_input_tokens"
        ],
        "pricing_usd_per_million_output_tokens": safety[
            "pricing_usd_per_million_output_tokens"
        ],
        "response_format_mode": safety.get(
            "response_format_mode", "json-object-prompt-schema"
        ),
    }


def validate_runner_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = load_instrument(path)
    safety = instrument["execution_safety"]
    authorized = safety["provider_execution_authorized"]
    allowed_statuses = (
        {"frozen-pending-execution"}
        if authorized
        else {
            "reviewer-bound-provider-unauthorized",
            "completed-review-authorization-revoked",
            "invalid-execution-authorization-revoked",
        }
    )
    if instrument["status"] not in allowed_statuses:
        raise ReviewRunnerError("review status and authorization drifted")
    if authorized is not instrument["decision_rule"]["authorize_provider_execution"]:
        raise ReviewRunnerError("review authorization fields disagree")
    if safety["maximum_calls"] != 13 or safety["retries"] != 0:
        raise ReviewRunnerError("review call or retry limit drifted")
    if safety["maximum_cost_usd"] != 0.5:
        raise ReviewRunnerError("review cost ceiling drifted")
    if safety["maximum_reserved_cost_usd"] > safety["maximum_cost_usd"]:
        raise ReviewRunnerError("review reservation exceeds cost ceiling")
    if safety.get("timeout_seconds") != 120:
        raise ReviewRunnerError("review timeout drifted")
    expected_runner = {
        "path": "scripts/run_evidence_sufficiency_v2_independent_review.py",
        "sensitivity_first": True,
        "atomic_checkpoints": True,
        "resume_requires_exact_bindings": True,
        "raw_output_path": (f"reports/generated/{instrument['instrument_id']}.json"),
    }
    if instrument["instrument_id"].endswith(("-003", "-004", "-005", "-006")):
        expected_runner["preserve_malformed_response_content"] = True
    if instrument["instrument_id"].endswith(("-004", "-005", "-006")):
        expected_runner.update(
            {
                "preserve_provider_error_details": True,
                "request_router_metadata": True,
            }
        )
    if safety.get("runner") != expected_runner:
        raise ReviewRunnerError("review runner binding drifted")
    expected_routing = {
        "order": (
            ["openai"]
            if instrument["instrument_id"].endswith("-006")
            else ["google-ai-studio"]
            if instrument["instrument_id"].endswith("-005")
            else ["Mistral"]
        ),
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }
    if safety["provider_routing"] != expected_routing:
        raise ReviewRunnerError("review routing drifted")
    binding = _provider_binding(instrument)
    expected_model = (
        "openai/gpt-5.4-mini"
        if instrument["instrument_id"].endswith("-006")
        else "google/gemini-3.7-flash"
        if instrument["instrument_id"].endswith("-005")
        else "mistralai/mistral-small-2603"
    )
    if binding["provider_model"] != expected_model:
        raise ReviewRunnerError("review model drifted")
    expected_response_format = (
        "json-schema-strict"
        if instrument["instrument_id"].endswith(("-003", "-004", "-005", "-006"))
        else "json-object-prompt-schema"
    )
    if binding["response_format_mode"] != expected_response_format:
        raise ReviewRunnerError("review response format drifted")
    if (
        instrument["instrument_id"].endswith(("-003", "-004", "-005", "-006"))
        and safety.get("provider_context_window_tokens")
        != (
            400000
            if instrument["instrument_id"].endswith("-006")
            else 1048576
            if instrument["instrument_id"].endswith("-005")
            else 262144
        )
    ):
        raise ReviewRunnerError("review provider context binding drifted")
    if instrument["instrument_id"].endswith(("-004", "-005", "-006")) and {
        "transport": binding["transport"],
        "api_url": binding["api_url"],
    } != {
        "transport": NATIVE_OPENROUTER_TRANSPORT,
        "api_url": OPENROUTER_CHAT_URL,
    }:
        raise ReviewRunnerError("native OpenRouter transport binding drifted")
    for field in (
        "timeout_seconds",
        "max_input_tokens",
        "max_output_tokens",
        "pricing_usd_per_million_input_tokens",
        "pricing_usd_per_million_output_tokens",
    ):
        value = binding[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ReviewRunnerError(f"invalid reviewer binding: {field}")
    return instrument


def load_assets(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = validate_runner_instrument(path)
    packet = build_review_packet(instrument)
    validate_review_packet(packet, instrument)
    return {
        "instrument": instrument,
        "instrument_path": path,
        "packet": packet,
    }


def _response_schema(expected_count: int) -> dict[str, Any]:
    judgment = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(RESPONSE_FIELDS),
        "properties": {
            "item_id": {"type": "string"},
            "verdict": {"type": "string", "enum": sorted(VERDICTS)},
            "failed_dimensions": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            },
            "reason": {"type": "string"},
            "suggested_correction": {"type": "string"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["judgments"],
        "properties": {
            "judgments": {
                "type": "array",
                "items": judgment,
                "minItems": expected_count,
                "maxItems": expected_count,
            }
        },
    }


def _response_format_for_call(
    binding: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any] | None:
    if binding["response_format_mode"] != "json-schema-strict":
        return None
    expected_count = schema["properties"]["judgments"]["minItems"]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": f"evidence_sufficiency_review_{expected_count}",
            "strict": True,
            "schema": deepcopy(schema),
        },
    }


def _source_subset(
    packet: dict[str, Any], items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    source_ids = {
        evidence["source_unit_id"]
        for item in items
        for evidence in item["proposed_evidence"]
    } | {source_id for item in items for source_id in item["tempting_source_ids"]}
    source_map = {
        source["source_unit_id"]: source for source in packet["source_catalog"]
    }
    if not source_ids.issubset(source_map):
        raise ReviewRunnerError("review item refers to an unknown source")
    return [deepcopy(source_map[source_id]) for source_id in sorted(source_ids)]


def _review_prompt(packet: dict[str, Any], items: list[dict[str, Any]]) -> str:
    return json.dumps(
        {
            "response_contract": packet["response_contract"],
            "source_catalog": _source_subset(packet, items),
            "items": items,
            "instructions": {
                "judge_every_item_exactly_once": True,
                "use_only_supplied_sources": True,
                "approve_only_if_every_dimension_passes": True,
                "revise_when_a_specific_correction_is_available": True,
                "escalate_only_when_the_supplied_material_cannot_resolve_the_case": True,
                "do_not_change_authoritative_ground_truth": True,
                "output_exact_root_key": "judgments",
            },
        },
        ensure_ascii=False,
        sort_keys=True,
    )


SYSTEM_PROMPT = """You are an independent data-quality reviewer for a source-linked educational QA dataset. Review only the supplied items against the supplied source records. Do not use external knowledge. Return strict JSON matching the requested schema, include every item exactly once, and never rewrite or override authoritative ground truth."""


def _estimate_input_tokens(prompt: str, schema: dict[str, Any]) -> int:
    rendered = "\n".join((SYSTEM_PROMPT, prompt, json.dumps(schema, sort_keys=True)))
    return math.ceil(len(rendered) / 3)


def _validate_call_response(
    value: Any,
    *,
    expected_ids: set[str],
    instrument: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"judgments"}:
        raise ReviewRunnerError("review response root must contain judgments only")
    judgments = value["judgments"]
    if not isinstance(judgments, list) or len(judgments) != len(expected_ids):
        raise ReviewRunnerError("review response judgment count drifted")
    allowed_dimensions = set(instrument["review_contract"]["dimensions"])
    seen: set[str] = set()
    for judgment in judgments:
        if not isinstance(judgment, dict) or set(judgment) != RESPONSE_FIELDS:
            raise ReviewRunnerError("review judgment shape drifted")
        item_id = judgment["item_id"]
        verdict = judgment["verdict"]
        dimensions = judgment["failed_dimensions"]
        reason = judgment["reason"]
        correction = judgment["suggested_correction"]
        if item_id not in expected_ids or item_id in seen:
            raise ReviewRunnerError("review judgment identity drifted")
        seen.add(item_id)
        if verdict not in VERDICTS:
            raise ReviewRunnerError("review verdict drifted")
        if (
            not isinstance(dimensions, list)
            or len(dimensions) != len(set(dimensions))
            or any(value not in allowed_dimensions for value in dimensions)
        ):
            raise ReviewRunnerError("review dimensions drifted")
        if not isinstance(reason, str) or len(reason.strip()) < 20:
            raise ReviewRunnerError("review reason is too short")
        if not isinstance(correction, str):
            raise ReviewRunnerError("review correction must be a string")
        if verdict == "approve" and dimensions:
            raise ReviewRunnerError("approved judgment contains failed dimensions")
        if verdict == "revise" and not correction.strip():
            raise ReviewRunnerError("revision judgment lacks a correction")
    if seen != expected_ids:
        raise ReviewRunnerError("review response coverage drifted")
    return judgments


class ProviderReviewTransport:
    """Identity-pinned OpenRouter transport with retries disabled."""

    def __init__(self, binding: dict[str, Any]) -> None:
        self.binding = binding
        response_format = (
            {"type": "json_object"}
            if binding["response_format_mode"] == "json-object-prompt-schema"
            else None
        )
        self.client = LiteLlmClient(
            binding["litellm_model"],
            timeout_seconds=binding["timeout_seconds"],
            max_output_tokens=binding["max_output_tokens"],
            temperature=binding["temperature"],
            response_format=response_format,
            provider_options={
                "extra_body": {"provider": deepcopy(binding["provider_routing"])},
                "num_retries": 0,
            },
            expected_provider_model=binding["provider_model"],
        )

    async def call(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> RawCall:
        request = "\n".join(
            (prompt, "OUTPUT JSON SCHEMA:", json.dumps(schema, sort_keys=True))
        )
        response_format = _response_format_for_call(self.binding, schema)
        started = time.perf_counter()
        response = await self.client.chat(
            [
                LlmMessage(role="system", content=system),
                LlmMessage(role="user", content=request),
            ],
            task=task,
            response_format=response_format,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        usage = response.usage
        cost = (
            usage.input_tokens
            * float(self.binding["pricing_usd_per_million_input_tokens"])
            + usage.output_tokens
            * float(self.binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000
        return RawCall(
            content=response.content,
            provider_model=response.provider_model,
            provider_revision=response.provider_revision,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            approximate_cost_usd=cost,
            latency_ms=latency_ms,
        )


_OpenRouterPost = Callable[..., Awaitable[httpx.Response]]


def _sanitized_text(value: Any, *, maximum_length: int = 2_000) -> str:
    if not isinstance(value, str):
        return "OpenRouter request failed without a textual message."
    normalized = " ".join(value.split())
    return normalized[:maximum_length] or "OpenRouter request failed."


def _sanitized_router_metadata(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    allowed = {
        "requested",
        "strategy",
        "region",
        "summary",
        "attempt",
        "is_byok",
        "endpoints",
        "attempts",
        "pipeline",
    }
    return {key: deepcopy(value[key]) for key in allowed if key in value}


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OpenRouterRequestError(
            error_code="malformed-usage",
            error_message=f"OpenRouter response contained invalid {field}.",
        )
    return value


class NativeOpenRouterReviewTransport:
    """Direct official OpenRouter chat transport with observable failures."""

    def __init__(
        self,
        binding: dict[str, Any],
        *,
        post: _OpenRouterPost | None = None,
    ) -> None:
        self.binding = binding
        self._post = post or self._post_with_httpx

    async def _post_with_httpx(self, **kwargs: Any) -> httpx.Response:
        timeout = httpx.Timeout(self.binding["timeout_seconds"])
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(**kwargs)

    async def call(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> RawCall:
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise OpenRouterRequestError(
                error_code="credential-missing",
                error_message="OPENROUTER_API_KEY is not available.",
            )
        request = "\n".join(
            (prompt, "OUTPUT JSON SCHEMA:", json.dumps(schema, sort_keys=True))
        )
        payload = {
            "model": self.binding["provider_model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": request},
            ],
            "max_tokens": self.binding["max_output_tokens"],
            "response_format": _response_format_for_call(self.binding, schema),
            "provider": deepcopy(self.binding["provider_routing"]),
            "usage": {"include": True},
            "metadata": {"task": task},
        }
        if self.binding["temperature"] is not None:
            payload["temperature"] = self.binding["temperature"]
        if self.binding["reasoning_effort"] is not None:
            payload["reasoning"] = {
                "effort": self.binding["reasoning_effort"],
                "exclude": True,
            }
        if self.binding["seed"] is not None:
            payload["seed"] = self.binding["seed"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/horiiiiii032929/digital-twin",
            "X-Title": "Course Digital Twin evaluation",
            "X-OpenRouter-Metadata": "enabled",
        }
        started = time.perf_counter()
        try:
            response = await self._post(
                url=self.binding["api_url"],
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException as error:
            raise OpenRouterRequestError(
                error_code="timeout",
                error_message="OpenRouter request timed out.",
            ) from error
        except httpx.HTTPError as error:
            raise OpenRouterRequestError(
                error_code="network-error",
                error_message="OpenRouter network request failed.",
            ) from error
        latency_ms = (time.perf_counter() - started) * 1000
        request_id = response.headers.get("x-request-id")
        generation_id = response.headers.get("x-generation-id")
        try:
            value = response.json()
        except ValueError as error:
            raise OpenRouterRequestError(
                error_code="non-json-response",
                error_message="OpenRouter returned a non-JSON response.",
                status_code=response.status_code,
                request_id=request_id,
                generation_id=generation_id,
            ) from error
        if not isinstance(value, dict):
            raise OpenRouterRequestError(
                error_code="invalid-response-root",
                error_message="OpenRouter response root was not an object.",
                status_code=response.status_code,
                request_id=request_id,
                generation_id=generation_id,
            )
        router_metadata = _sanitized_router_metadata(value.get("openrouter_metadata"))
        error_value = value.get("error")
        if response.is_error or error_value is not None:
            error_object = error_value if isinstance(error_value, dict) else {}
            raise OpenRouterRequestError(
                error_code=str(error_object.get("code") or response.status_code),
                error_message=_sanitized_text(error_object.get("message")),
                status_code=response.status_code,
                request_id=request_id,
                generation_id=generation_id,
                openrouter_metadata=router_metadata,
            )
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise OpenRouterRequestError(
                error_code="malformed-choices",
                error_message="OpenRouter response did not contain exactly one choice.",
                status_code=response.status_code,
                request_id=request_id,
                generation_id=generation_id,
                openrouter_metadata=router_metadata,
            )
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise OpenRouterRequestError(
                error_code="malformed-content",
                error_message="OpenRouter response content was empty or invalid.",
                status_code=response.status_code,
                request_id=request_id,
                generation_id=generation_id,
                openrouter_metadata=router_metadata,
            )
        usage = value.get("usage") if isinstance(value.get("usage"), dict) else {}
        input_tokens = _non_negative_int(usage.get("prompt_tokens", 0), "prompt_tokens")
        output_tokens = _non_negative_int(
            usage.get("completion_tokens", 0), "completion_tokens"
        )
        reported_cost = usage.get("cost")
        if isinstance(reported_cost, bool) or not isinstance(
            reported_cost, (int, float)
        ):
            reported_cost = (
                input_tokens
                * float(self.binding["pricing_usd_per_million_input_tokens"])
                + output_tokens
                * float(self.binding["pricing_usd_per_million_output_tokens"])
            ) / 1_000_000
        if not math.isfinite(float(reported_cost)) or float(reported_cost) < 0:
            raise OpenRouterRequestError(
                error_code="malformed-cost",
                error_message="OpenRouter response contained invalid cost accounting.",
                status_code=response.status_code,
                request_id=request_id,
                generation_id=generation_id,
                openrouter_metadata=router_metadata,
            )
        provider_model = value.get("model")
        if not isinstance(provider_model, str) or not provider_model.strip():
            raise OpenRouterRequestError(
                error_code="malformed-model",
                error_message="OpenRouter response model identity was missing.",
                status_code=response.status_code,
                request_id=request_id,
                generation_id=generation_id,
                openrouter_metadata=router_metadata,
            )
        provider_revision = value.get("system_fingerprint")
        return OpenRouterRawCall(
            content=content,
            provider_model=provider_model.strip(),
            provider_revision=(
                provider_revision.strip()
                if isinstance(provider_revision, str) and provider_revision.strip()
                else None
            ),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            approximate_cost_usd=float(reported_cost),
            latency_ms=latency_ms,
            request_id=request_id,
            generation_id=generation_id,
            openrouter_metadata=router_metadata,
        )


def _provider_transport(binding: dict[str, Any]) -> RawTransport:
    if binding["transport"] == NATIVE_OPENROUTER_TRANSPORT:
        return NativeOpenRouterReviewTransport(binding)
    return ProviderReviewTransport(binding)


class SimulatedReviewTransport:
    """Network-free reviewer double for checkpoint and failure testing."""

    def __init__(
        self,
        *,
        model: str,
        verdicts: dict[str, str],
        malformed_call: int | None = None,
        provider_error_call: int | None = None,
        identity_drift_call: int | None = None,
        cost_per_call: float = 0.001,
        input_tokens: int = 500,
        output_tokens: int = 250,
    ) -> None:
        self.model = model
        self.verdicts = verdicts
        self.malformed_call = malformed_call
        self.provider_error_call = provider_error_call
        self.identity_drift_call = identity_drift_call
        self.cost_per_call = cost_per_call
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = 0

    async def call(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> RawCall:
        del system, task, schema
        self.calls += 1
        if self.provider_error_call == self.calls:
            raise RuntimeError("simulated provider failure")
        payload = json.loads(prompt)
        judgments = []
        for item in payload["items"]:
            verdict = self.verdicts.get(item["item_id"], "approve")
            judgments.append(
                {
                    "item_id": item["item_id"],
                    "verdict": verdict,
                    "failed_dimensions": (
                        [] if verdict == "approve" else ["claim-support"]
                    ),
                    "reason": "Network-free deterministic reviewer response.",
                    "suggested_correction": (
                        "Restore the source-linked deterministic proposal."
                        if verdict == "revise"
                        else ""
                    ),
                }
            )
        content = (
            "not-json"
            if self.malformed_call == self.calls
            else json.dumps({"judgments": judgments})
        )
        model = (
            "unexpected/reviewer"
            if self.identity_drift_call == self.calls
            else self.model
        )
        return RawCall(
            content=content,
            provider_model=model,
            provider_revision=f"simulated-{model}-revision",
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            approximate_cost_usd=self.cost_per_call,
            latency_ms=1.0,
        )


def _bindings(assets: dict[str, Any]) -> dict[str, Any]:
    return {
        "instrument_sha256": _sha256_file(assets["instrument_path"]),
        "packet_sha256": assets["packet"]["content_sha256"],
        "code_revision": _code_revision(),
        "runner_sha256": _sha256_file(Path(__file__)),
        "reviewer_binding_sha256": _canonical_sha256(
            _provider_binding(assets["instrument"])
        ),
    }


def _initial_state(assets: dict[str, Any], *, simulation: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_type": assets["instrument"]["instrument_id"],
        "status": "running",
        "simulation": simulation,
        "bindings": _bindings(assets),
        "data_boundary": "synthetic-public-evaluation-only",
        "private_data_read": False,
        "candidate_evaluation_opened": False,
        "dataset_frozen": False,
        "accounting": {
            "calls_attempted": 0,
            "calls_with_provider_response": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "external_cost_usd": 0.0,
            "input_token_limit_exceeded_count": 0,
            "output_token_limit_exceeded_count": 0,
            "latency_ms": [],
        },
        "sensitivity_outcome": None,
        "batch_outcomes": [],
        "judgments": [],
    }


def _load_resume(
    path: Path, assets: dict[str, Any], *, simulation: bool
) -> dict[str, Any]:
    state = _load_json(path)
    if state.get("status") != "running":
        raise ReviewRunnerError("only a running review checkpoint may resume")
    if state.get("simulation") is not simulation:
        raise ReviewRunnerError("review resume mode drifted")
    if state.get("bindings") != _bindings(assets):
        raise ReviewRunnerError("review resume bindings drifted")
    return state


def _call_record(raw: RawCall, binding: dict[str, Any]) -> dict[str, Any]:
    record = {
        "provider_model": raw.provider_model,
        "provider_revision": raw.provider_revision,
        "input_tokens": raw.input_tokens,
        "output_tokens": raw.output_tokens,
        "requested_max_input_tokens": binding["max_input_tokens"],
        "requested_max_output_tokens": binding["max_output_tokens"],
        "input_token_limit_exceeded": raw.input_tokens > binding["max_input_tokens"],
        "output_token_limit_exceeded": raw.output_tokens > binding["max_output_tokens"],
        "approximate_cost_usd": raw.approximate_cost_usd,
        "latency_ms": raw.latency_ms,
    }
    if isinstance(raw, OpenRouterRawCall):
        record.update(
            {
                "request_id": raw.request_id,
                "generation_id": raw.generation_id,
                "openrouter_metadata": deepcopy(raw.openrouter_metadata),
            }
        )
    return record


async def _safe_call(
    *,
    transport: RawTransport,
    items: list[dict[str, Any]],
    packet: dict[str, Any],
    state: dict[str, Any],
    instrument: dict[str, Any],
    output_path: Path,
    task: str,
    stop_after_calls: int | None,
) -> dict[str, Any]:
    safety = instrument["execution_safety"]
    accounting = state["accounting"]
    reservation_per_call = safety["maximum_reserved_cost_usd"] / safety["maximum_calls"]
    if (
        accounting["external_cost_usd"] + reservation_per_call
        > safety["maximum_cost_usd"]
    ):
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "cost-reservation-would-exceed-ceiling"
        _checkpoint(output_path, state)
        return {"status": "budget-stop", "value": None, "call": None}
    if accounting["calls_attempted"] >= safety["maximum_calls"]:
        raise ReviewRunnerError("review provider-call limit reached")
    if (
        stop_after_calls is not None
        and accounting["calls_attempted"] >= stop_after_calls
    ):
        _checkpoint(output_path, state)
        raise PlannedInterruption("planned interruption after durable checkpoint")
    expected_ids = {item["item_id"] for item in items}
    schema = _response_schema(len(items))
    prompt = _review_prompt(packet, items)
    binding = _provider_binding(instrument)
    if _estimate_input_tokens(prompt, schema) > binding["max_input_tokens"]:
        raise ReviewRunnerError("review prompt exceeds the frozen input limit")
    accounting["calls_attempted"] += 1
    try:
        raw = await transport.call(
            system=SYSTEM_PROMPT,
            prompt=prompt,
            task=task,
            schema=schema,
        )
    except Exception as error:
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "provider-error"
        outcome = {
            "status": "provider-error",
            "error_type": type(error).__name__,
            "value": None,
            "call": None,
        }
        if isinstance(error, OpenRouterRequestError):
            outcome.update(error.record())
        return outcome
    accounting["calls_with_provider_response"] += 1
    accounting["input_tokens"] += raw.input_tokens
    accounting["output_tokens"] += raw.output_tokens
    accounting["external_cost_usd"] += raw.approximate_cost_usd
    accounting["latency_ms"].append(raw.latency_ms)
    input_exceeded = raw.input_tokens > binding["max_input_tokens"]
    output_exceeded = raw.output_tokens > binding["max_output_tokens"]
    accounting["input_token_limit_exceeded_count"] += int(input_exceeded)
    accounting["output_token_limit_exceeded_count"] += int(output_exceeded)
    if raw.provider_model != binding["provider_model"]:
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "provider-model-identity-drift"
    elif input_exceeded or output_exceeded:
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "provider-token-limit-violation"
    elif accounting["external_cost_usd"] > safety["maximum_cost_usd"]:
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "cost-ceiling-exceeded"
    try:
        parsed = json.loads(raw.content)
        judgments = _validate_call_response(
            parsed,
            expected_ids=expected_ids,
            instrument=instrument,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "malformed-review-response"
        return {
            "status": "malformed-response",
            "error_type": type(error).__name__,
            "error_detail": str(error),
            "raw_response_content": raw.content,
            "value": None,
            "call": _call_record(raw, binding),
        }
    return {
        "status": "complete" if state["status"] == "running" else "invalid",
        "error_type": None,
        "value": judgments,
        "call": _call_record(raw, binding),
    }


def _sensitivity_passed(
    packet: dict[str, Any], judgments: list[dict[str, Any]]
) -> bool:
    verdicts = {judgment["item_id"]: judgment["verdict"] for judgment in judgments}
    return all(
        (
            verdicts[item_id] == "approve"
            if expected["expected_verdict"] == "approve"
            else verdicts[item_id] in {"revise", "escalate"}
        )
        for item_id, expected in packet["sensitivity_scoring_key"].items()
    )


def _priority_packet(
    packet: dict[str, Any], case_ids: list[str]
) -> list[dict[str, Any]]:
    by_id = {
        item["item_id"]: item
        for batch in packet["review_batches"]
        for item in batch["items"]
    }
    return [deepcopy(by_id[case_id]) for case_id in case_ids]


async def execute(
    assets: dict[str, Any],
    *,
    transport: RawTransport,
    output_path: Path,
    simulation: bool,
    resume: bool = False,
    stop_after_calls: int | None = None,
) -> dict[str, Any]:
    instrument = assets["instrument"]
    packet = assets["packet"]
    state = (
        _load_resume(output_path, assets, simulation=simulation)
        if resume
        else _initial_state(assets, simulation=simulation)
    )
    if not resume:
        _write_initial(output_path, state)

    if state["sensitivity_outcome"] is None:
        outcome = await _safe_call(
            transport=transport,
            items=packet["sensitivity_items"],
            packet=packet,
            state=state,
            instrument=instrument,
            output_path=output_path,
            task="evidence_sufficiency_v2_sensitivity",
            stop_after_calls=stop_after_calls,
        )
        state["sensitivity_outcome"] = outcome
        if outcome["value"]:
            state["judgments"].extend(outcome["value"])
        _checkpoint(output_path, state)
        if state["status"] != "running":
            return state
        if not _sensitivity_passed(packet, outcome["value"]):
            state["status"] = "completed-reviewer-unreliable"
            state["summary"] = {
                "status": state["status"],
                "sensitivity_passed": False,
                "bulk_calls_attempted": 0,
                "freeze_eligible": False,
            }
            _checkpoint(output_path, state)
            return state

    completed_batches = {outcome["batch_id"] for outcome in state["batch_outcomes"]}
    for batch in packet["review_batches"]:
        if batch["batch_id"] in completed_batches:
            continue
        outcome = await _safe_call(
            transport=transport,
            items=batch["items"],
            packet=packet,
            state=state,
            instrument=instrument,
            output_path=output_path,
            task="evidence_sufficiency_v2_review",
            stop_after_calls=stop_after_calls,
        )
        state["batch_outcomes"].append({"batch_id": batch["batch_id"], **outcome})
        if outcome["value"]:
            state["judgments"].extend(outcome["value"])
        _checkpoint(output_path, state)
        if state["status"] != "running":
            return state

    summary = validate_judgments(
        packet,
        state["judgments"],
        simulation=simulation,
        instrument=instrument,
    )
    summary.update(
        {
            "calls_attempted": state["accounting"]["calls_attempted"],
            "calls_with_provider_response": state["accounting"][
                "calls_with_provider_response"
            ],
            "input_tokens": state["accounting"]["input_tokens"],
            "output_tokens": state["accounting"]["output_tokens"],
            "external_cost_usd": state["accounting"]["external_cost_usd"],
            "provider_or_model_calls": (
                0 if simulation else state["accounting"]["calls_attempted"]
            ),
            "freeze_eligible": False,
        }
    )
    all_gates_pass = all(summary["gates"].values())
    state["status"] = (
        "simulation-completed"
        if simulation
        else "completed-review-ready-for-adjudication"
        if all_gates_pass
        else "completed-refine"
    )
    summary["status"] = state["status"]
    state["summary"] = summary
    state["priority_packet"] = _priority_packet(packet, summary["priority_case_ids"])
    _checkpoint(output_path, state)
    return state


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=20) as response:  # noqa: S310 - fixed official URLs
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ReviewRunnerError("provider metadata root is not an object")
    return value


def fetch_live_metadata(instrument: dict[str, Any]) -> dict[str, Any]:
    return {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "registry": _fetch_json(MODEL_REGISTRY_URL),
        "endpoints": _fetch_json(
            instrument["execution_safety"]["endpoint_metadata_source"]
        ),
    }


def _live_metadata_failures(
    instrument: dict[str, Any], live: dict[str, Any] | None
) -> list[str]:
    if live is None:
        return ["live-provider-match-not-checked"]
    safety = instrument["execution_safety"]
    model = next(
        (
            item
            for item in live.get("registry", {}).get("data", [])
            if item.get("id") == safety["reviewer_model"]
        ),
        None,
    )
    failures: list[str] = []
    if model is None:
        return ["reviewer-model-missing"]
    pricing = model.get("pricing", {})
    if safety.get("pricing_binding_scope") != "selected-endpoint" and (
        float(pricing.get("prompt", -1)) * 1_000_000
        != safety["pricing_usd_per_million_input_tokens"]
    ):
        failures.append("reviewer-input-price-drift")
    if safety.get("pricing_binding_scope") != "selected-endpoint" and (
        float(pricing.get("completion", -1)) * 1_000_000
        != safety["pricing_usd_per_million_output_tokens"]
    ):
        failures.append("reviewer-output-price-drift")
    expected_context = safety.get("provider_context_window_tokens")
    actual_model_context = int(model.get("context_length", 0))
    if (expected_context is not None and actual_model_context != expected_context) or (
        expected_context is None
        and actual_model_context < safety["max_input_tokens_per_call"]
    ):
        failures.append("reviewer-context-limit-drift")
    parameters = set(model.get("supported_parameters", []))
    required_parameters = {"max_tokens", "response_format"}
    if safety.get("response_format_mode") == "json-schema-strict":
        required_parameters.add("structured_outputs")
    if safety.get("temperature") is not None:
        required_parameters.add("temperature")
    if safety.get("reasoning_effort") is not None:
        required_parameters.add("reasoning_effort")
    if safety.get("seed") is not None:
        required_parameters.add("seed")
    if not required_parameters.issubset(parameters):
        failures.append("reviewer-required-parameters-missing")
    endpoints = live.get("endpoints", {}).get("data", {}).get("endpoints", [])
    endpoint_provider_name = safety.get("reviewer_endpoint_provider_name", "Mistral")
    endpoint_tag = safety.get("reviewer_endpoint_tag")
    active_endpoints = [
        endpoint
        for endpoint in endpoints
        if endpoint.get("provider_name") == endpoint_provider_name
        and (endpoint_tag is None or endpoint.get("tag") == endpoint_tag)
        and endpoint.get("status") == 0
    ]
    if not active_endpoints:
        failures.append("reviewer-endpoint-unavailable")
    price_matching_endpoints = [
        endpoint
        for endpoint in active_endpoints
        if (
            float(endpoint.get("pricing", {}).get("prompt", -1)) * 1_000_000
            == safety["pricing_usd_per_million_input_tokens"]
            and float(endpoint.get("pricing", {}).get("completion", -1)) * 1_000_000
            == safety["pricing_usd_per_million_output_tokens"]
        )
    ]
    if active_endpoints and not price_matching_endpoints:
        failures.append("reviewer-endpoint-price-drift")
    matching_endpoints = [
        endpoint
        for endpoint in price_matching_endpoints
        if expected_context is None
        or int(endpoint.get("context_length", 0)) == expected_context
    ]
    if price_matching_endpoints and not matching_endpoints:
        failures.append("reviewer-endpoint-context-drift")
    expected_backend = safety.get("reviewer_backend_model")
    if expected_backend is not None and not any(
        endpoint.get("name", "").endswith(expected_backend)
        for endpoint in matching_endpoints
    ):
        failures.append("reviewer-backend-model-drift")
    if safety.get("response_format_mode") == "json-schema-strict" and not any(
        "structured_outputs" in endpoint.get("supported_parameters", [])
        for endpoint in matching_endpoints
    ):
        failures.append("reviewer-structured-outputs-missing")
    return failures


def _default_output_path(instrument: dict[str, Any], *, simulation: bool) -> Path:
    raw_path = ROOT / instrument["execution_safety"]["runner"]["raw_output_path"]
    if not simulation:
        return raw_path
    return raw_path.with_name(f"{raw_path.stem}-simulation{raw_path.suffix}")


def _metadata_age_hours(instrument: dict[str, Any], now: datetime) -> float:
    verified = datetime.fromisoformat(
        instrument["execution_safety"]["reviewer_verified_at"]
    )
    return (
        now.astimezone(timezone.utc) - verified.astimezone(timezone.utc)
    ).total_seconds() / 3600


def build_preflight(
    assets: dict[str, Any],
    *,
    output_path: Path = DEFAULT_OUTPUT,
    live_metadata: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    instrument = assets["instrument"]
    instrument_id = instrument["instrument_id"]
    safety = instrument["execution_safety"]
    current = now or datetime.now(timezone.utc)
    age_hours = _metadata_age_hours(instrument, current)
    metadata_fresh = 0 <= age_hours <= safety["metadata_maximum_age_hours"]
    live_failures = _live_metadata_failures(instrument, live_metadata)
    binding = _provider_binding(instrument)
    prompts = [
        (packet_items, _response_schema(len(packet_items)))
        for packet_items in [assets["packet"]["sensitivity_items"]]
        + [batch["items"] for batch in assets["packet"]["review_batches"]]
    ]
    maximum_planned_input_tokens = max(
        _estimate_input_tokens(_review_prompt(assets["packet"], items), schema)
        for items, schema in prompts
    )
    credential_present = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    authorized = safety["provider_execution_authorized"] is True
    frozen = instrument["status"] == "frozen-pending-execution"
    bounded = instrument_id in BOUNDED_PILOT_AUTHORIZATIONS
    blockers = []
    if not authorized:
        blockers.append("provider-review-not-authorized")
    if not frozen:
        blockers.append("instrument-not-frozen")
    if not bounded:
        blockers.append("bounded-freeze-authorization-missing")
    if not credential_present:
        blockers.append("openrouter-credential-missing")
    if not metadata_fresh or live_failures:
        blockers.append("provider-metadata-not-current")
    if _working_tree_dirty():
        blockers.append("working-tree-dirty")
    if output_path.exists():
        blockers.append("output-path-already-exists")
    if maximum_planned_input_tokens > binding["max_input_tokens"]:
        blockers.append("planned-input-limit-exceeded")
    if not authorized:
        status = "blocked-not-authorized"
    elif not frozen or not bounded:
        status = "blocked-not-frozen"
    elif not metadata_fresh or live_failures:
        status = "blocked-provider-freshness"
    else:
        status = "ready" if not blockers else "blocked-preflight"
    return {
        "run_type": f"{instrument_id}-preflight",
        "instrument_id": instrument_id,
        "status": status,
        "blockers": blockers,
        "provider_execution_authorized": authorized,
        "instrument_frozen": frozen,
        "bounded_freeze_authorized": bounded,
        "credential_present": credential_present,
        "credential_value_emitted": False,
        "working_tree_dirty": _working_tree_dirty(),
        "output_available": not output_path.exists(),
        "metadata_age_hours": age_hours,
        "metadata_maximum_age_hours": safety["metadata_maximum_age_hours"],
        "metadata_fresh": metadata_fresh,
        "live_provider_match_checked": live_metadata is not None,
        "live_provider_failures": live_failures,
        "planned_calls": safety["maximum_calls"],
        "maximum_planned_input_tokens": maximum_planned_input_tokens,
        "maximum_reserved_cost_usd": safety["maximum_reserved_cost_usd"],
        "maximum_cost_usd": safety["maximum_cost_usd"],
        "provider_or_model_calls": 0,
        "candidate_evaluation_opened": False,
        "private_data_read": False,
    }


def _simulation_transport(assets: dict[str, Any]) -> SimulatedReviewTransport:
    scoring = assets["packet"]["sensitivity_scoring_key"]
    return SimulatedReviewTransport(
        model=assets["instrument"]["execution_safety"]["reviewer_model"],
        verdicts={
            item_id: expected["expected_verdict"]
            for item_id, expected in scoring.items()
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--preflight-live", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if (
        sum(
            (
                arguments.validate,
                arguments.preflight,
                arguments.preflight_live,
                arguments.simulate,
                arguments.execute,
            )
        )
        > 1
    ):
        parser.error("choose one validation, preflight, simulation, or execution mode")
    if arguments.resume and not (arguments.simulate or arguments.execute):
        parser.error("--resume requires --simulate or --execute")
    return arguments


def main() -> int:
    arguments = parse_args()
    load_dotenv(ROOT / ".env", override=False)
    assets = load_assets(arguments.instrument)
    output_path = arguments.output or _default_output_path(
        assets["instrument"], simulation=arguments.simulate
    )
    if arguments.validate:
        print(
            json.dumps(
                {
                    **validate_review_packet(assets["packet"], assets["instrument"]),
                    "runner_status": "validated-build-only",
                    "planned_calls": assets["instrument"]["execution_safety"][
                        "maximum_calls"
                    ],
                    "provider_or_model_calls": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if arguments.preflight or arguments.preflight_live:
        live = fetch_live_metadata(assets["instrument"]) if arguments.preflight_live else None
        print(
            json.dumps(
                build_preflight(
                    assets,
                    output_path=output_path,
                    live_metadata=live,
                    now=datetime.now(timezone.utc),
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if arguments.simulate:
        result = asyncio.run(
            execute(
                assets,
                transport=_simulation_transport(assets),
                output_path=output_path,
                simulation=True,
                resume=arguments.resume,
            )
        )
        print(json.dumps(result.get("summary", result), indent=2, sort_keys=True))
        return 0
    if arguments.execute:
        live = fetch_live_metadata(assets["instrument"])
        preflight = build_preflight(
            assets,
            output_path=output_path,
            live_metadata=live,
            now=datetime.now(timezone.utc),
        )
        if preflight["status"] != "ready":
            print(json.dumps(preflight, indent=2, sort_keys=True))
            return 2
        require_bounded_pilot_operation_allowed(assets["instrument"]["instrument_id"])
        result = asyncio.run(
            execute(
                assets,
                transport=_provider_transport(_provider_binding(assets["instrument"])),
                output_path=output_path,
                simulation=False,
                resume=arguments.resume,
            )
        )
        print(json.dumps(result.get("summary", result), indent=2, sort_keys=True))
        return 0
    print(
        json.dumps(
            build_preflight(assets, output_path=output_path),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
