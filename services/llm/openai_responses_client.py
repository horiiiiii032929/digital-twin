"""Direct, snapshot-pinned OpenAI Responses API client for R1 generation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import hashlib
import json
import math
import os
from typing import Any

import httpx

from src.digital_twin.generation.models import ModelTutorOutput, ModelTutorOutputV2
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.student.autonomy_models import (
    AutonomousPlannerOutputV1,
    ReactiveSemanticProposalV2,
)
from src.digital_twin.student.planning_architectures import (
    HierarchicalPlanningProposalV1,
    PlannerVerificationV1,
)
from src.digital_twin.llm import (
    LlmAuthenticationError,
    LlmConfigurationError,
    LlmIdentityDriftError,
    LlmMalformedResponseError,
    LlmMessage,
    LlmResponse,
    LlmTimeoutError,
    LlmUnavailableError,
    validate_llm_task,
)
from src.digital_twin.model_policy import require_active_release_model
from src.digital_twin.model_policy import OPENAI_MODEL_PRICING_USD_PER_MILLION


_Post = Callable[..., Awaitable[httpx.Response]]

_PROVIDER_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "default",
        "examples",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "multipleOf",
        "pattern",
        "uniqueItems",
    }
)


def _openai_strict_schema(value: Any) -> Any:
    """Translate Pydantic JSON Schema into OpenAI's strict portable subset.

    Pydantic omits fields with defaults from ``required`` and emits validation
    keywords that the Responses API does not consistently accept. The provider
    schema controls shape only; Pydantic validation after parsing remains the
    authority for lengths, ranges, and semantic invariants.
    """

    if isinstance(value, list):
        return [_openai_strict_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if key in _PROVIDER_UNSUPPORTED_SCHEMA_KEYWORDS or key == "required":
            continue
        if key == "const":
            normalized["enum"] = [item]
            continue
        normalized[key] = _openai_strict_schema(item)
    properties = normalized.get("properties")
    if isinstance(properties, dict):
        normalized["additionalProperties"] = False
        normalized["required"] = list(properties)
    return normalized


class OpenAiResponsesClient:
    """Call one exact OpenAI snapshot with strict, non-stored JSON output.

    The client deliberately exposes no router, provider fallback, tools,
    background mode, conversation state, or retry behavior. Product tasks map
    to server-owned schemas so model output cannot change the response contract.
    """

    API_URL = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        model: str,
        *,
        timeout_seconds: float = 30,
        max_output_tokens: int = 600,
        reasoning_effort: str = "none",
        input_price_usd_per_million: float | None = None,
        output_price_usd_per_million: float | None = None,
        credential_environment_variable: str = "OPENAI_API_KEY",
        post: _Post | None = None,
    ) -> None:
        self.model = require_active_release_model(model)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if isinstance(max_output_tokens, bool) or max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if reasoning_effort not in {"none", "low", "medium", "high", "xhigh"}:
            raise ValueError("reasoning_effort is unsupported")
        catalog_prices = OPENAI_MODEL_PRICING_USD_PER_MILLION.get(self.model)
        if catalog_prices is None and (
            input_price_usd_per_million is None
            or output_price_usd_per_million is None
        ):
            raise ValueError("OpenAI model pricing must be supplied or catalogued")
        resolved_input_price = (
            catalog_prices[0]
            if input_price_usd_per_million is None
            else input_price_usd_per_million
        )
        resolved_output_price = (
            catalog_prices[1]
            if output_price_usd_per_million is None
            else output_price_usd_per_million
        )
        for value in (resolved_input_price, resolved_output_price):
            if not math.isfinite(value) or value < 0:
                raise ValueError("OpenAI prices must be finite and non-negative")
        if credential_environment_variable != "OPENAI_API_KEY":
            raise ValueError("R1 OpenAI client must use OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.input_price = resolved_input_price
        self.output_price = resolved_output_price
        self.credential_environment_variable = credential_environment_variable
        self._post = post or self._post_direct

    async def _post_direct(self, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds)
        ) as client:
            return await client.post(**kwargs)

    @staticmethod
    def _schema(task: str) -> dict[str, Any]:
        if task == "grounded_tutor_atomic_claims":
            schema = ModelTutorOutputV2.model_json_schema()
        elif task in {
            "grounded_tutor_answer",
            "bounded_pedagogical_tutor_answer",
        }:
            schema = ModelTutorOutput.model_json_schema()
        elif task == "autonomous_tutoring_plan":
            schema = AutonomousPlannerOutputV1.model_json_schema()
        elif task == "reactive_tutoring_plan":
            schema = ReactiveSemanticProposalV2.model_json_schema()
        elif task == "hierarchical_autonomy_plan":
            schema = HierarchicalPlanningProposalV1.model_json_schema()
        elif task == "autonomy_plan_verifier":
            schema = PlannerVerificationV1.model_json_schema()
        else:
            raise LlmConfigurationError()
        return _openai_strict_schema(schema)

    def _payload(self, messages: list[LlmMessage], task: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "store": False,
            "input": [
                {
                    "role": message.role,
                    "content": [{"type": "input_text", "text": message.content}],
                }
                for message in messages
            ],
            "max_output_tokens": self.max_output_tokens,
            "reasoning": {"effort": self.reasoning_effort},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": task,
                    "strict": True,
                    "schema": self._schema(task),
                }
            },
            "metadata": {"task": task},
        }

    def _usage(self, payload: dict[str, Any]) -> GenerationUsage:
        usage = payload.get("usage", {})
        if not isinstance(usage, dict):
            raise ValueError("usage is not an object")
        input_tokens = _token_count(usage, "input_tokens")
        output_tokens = _token_count(usage, "output_tokens")
        cost = (
            input_tokens * self.input_price + output_tokens * self.output_price
        ) / 1_000_000
        return GenerationUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            approximate_cost_usd=cost,
        )

    @staticmethod
    def _privacy_safe_diagnostics(
        response: httpx.Response,
        payload: dict[str, Any] | None,
        *,
        stage: str,
    ) -> dict[str, Any]:
        output_item_types: list[str] = []
        content_part_types: list[str] = []
        output_text_count = 0
        refusal_present = False
        if isinstance(payload, dict):
            output = payload.get("output")
            if isinstance(output, list):
                for item in output:
                    if not isinstance(item, dict):
                        output_item_types.append(type(item).__name__)
                        continue
                    output_item_types.append(str(item.get("type") or "missing"))
                    content = item.get("content")
                    if not isinstance(content, list):
                        continue
                    for part in content:
                        if not isinstance(part, dict):
                            content_part_types.append(type(part).__name__)
                            continue
                        part_type = str(part.get("type") or "missing")
                        content_part_types.append(part_type)
                        output_text_count += int(part_type == "output_text")
                        refusal_present = refusal_present or part_type == "refusal"
        incomplete = payload.get("incomplete_details") if isinstance(payload, dict) else None
        provider_error = payload.get("error") if isinstance(payload, dict) else None
        return {
            "failure_stage": stage,
            "http_status": response.status_code,
            "response_sha256": hashlib.sha256(response.content).hexdigest(),
            "response_status": (
                str(payload.get("status"))
                if isinstance(payload, dict) and payload.get("status") is not None
                else None
            ),
            "incomplete_reason": (
                str(incomplete.get("reason"))
                if isinstance(incomplete, dict) and incomplete.get("reason") is not None
                else None
            ),
            "provider_error_code": (
                str(provider_error.get("code"))
                if isinstance(provider_error, dict) and provider_error.get("code") is not None
                else None
            ),
            "output_item_types": output_item_types,
            "content_part_types": content_part_types,
            "output_text_count": output_text_count,
            "refusal_present": refusal_present,
        }

    def _malformed(
        self,
        response: httpx.Response,
        payload: dict[str, Any] | None,
        *,
        stage: str,
        usage: GenerationUsage | None = None,
    ) -> LlmMalformedResponseError:
        observed_model = (
            str(payload.get("model"))
            if isinstance(payload, dict) and payload.get("model") is not None
            else None
        )
        return LlmMalformedResponseError(
            stage=stage,
            provider_model=observed_model,
            provider_revision=self.model if observed_model == self.model else None,
            usage=usage,
            diagnostics=self._privacy_safe_diagnostics(
                response,
                payload,
                stage=stage,
            ),
        )

    def _output_text(
        self,
        response: httpx.Response,
        payload: dict[str, Any],
        *,
        usage: GenerationUsage,
    ) -> str:
        if payload.get("status") != "completed":
            raise self._malformed(
                response, payload, stage="response-status", usage=usage
            )
        values: list[str] = []
        output = payload.get("output")
        if not isinstance(output, list):
            raise self._malformed(
                response, payload, stage="output-shape", usage=usage
            )
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                raise self._malformed(
                    response, payload, stage="content-shape", usage=usage
                )
            for part in content:
                if isinstance(part, dict) and part.get("type") == "refusal":
                    raise self._malformed(
                        response, payload, stage="refusal", usage=usage
                    )
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        values.append(text)
        if len(values) != 1:
            raise self._malformed(
                response, payload, stage="output-text-count", usage=usage
            )
        return values[0]

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        task = validate_llm_task(task)
        if not messages:
            raise ValueError("at least one LLM message is required")
        api_key = os.getenv(self.credential_environment_variable, "").strip()
        if not api_key:
            raise LlmAuthenticationError()
        try:
            response = await self._post(
                url=self.API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=self._payload(messages, task),
            )
        except httpx.TimeoutException as error:
            raise LlmTimeoutError() from error
        except httpx.HTTPError as error:
            raise LlmUnavailableError() from error
        if response.status_code in {401, 403}:
            raise LlmAuthenticationError()
        if response.status_code == 429 or response.status_code >= 500:
            raise LlmUnavailableError()
        if response.is_error:
            raise LlmConfigurationError()
        try:
            payload = response.json()
        except ValueError as error:
            raise self._malformed(
                response, None, stage="response-json-decode"
            ) from error
        if not isinstance(payload, dict):
            raise self._malformed(response, None, stage="response-root")
        observed_model = payload.get("model")
        if observed_model != self.model:
            raise LlmIdentityDriftError(
                provider_model=str(observed_model or "not-returned"),
                provider_revision=None,
            )
        try:
            usage = self._usage(payload)
        except (TypeError, ValueError) as error:
            raise self._malformed(
                response, payload, stage="usage-validation"
            ) from error
        output_text = self._output_text(response, payload, usage=usage)
        try:
            content = json.loads(output_text)
        except (TypeError, ValueError) as error:
            raise self._malformed(
                response, payload, stage="structured-json-decode", usage=usage
            ) from error
        if not isinstance(content, dict):
            raise self._malformed(
                response, payload, stage="structured-root", usage=usage
            )
        try:
            if task == "grounded_tutor_atomic_claims":
                validated = ModelTutorOutputV2.model_validate(content)
            elif task == "autonomous_tutoring_plan":
                validated = AutonomousPlannerOutputV1.model_validate(content)
            elif task == "reactive_tutoring_plan":
                validated = ReactiveSemanticProposalV2.model_validate(content)
            else:
                validated = ModelTutorOutput.model_validate(content)
        except (TypeError, ValueError) as error:
            raise self._malformed(
                response, payload, stage="schema-validation", usage=usage
            ) from error
        return LlmResponse(
            content=validated.model_dump_json(),
            provider_model=observed_model,
            provider_revision=self.model,
            usage=usage,
        )


def _token_count(usage: dict[str, Any], name: str) -> int:
    value = usage.get(name, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value
