"""Direct, snapshot-pinned OpenAI Responses API client for R1 generation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import json
import math
import os
from typing import Any

import httpx

from src.digital_twin.generation.models import ModelTutorOutput, ModelTutorOutputV2
from src.digital_twin.grounding.models import GenerationUsage
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


_Post = Callable[..., Awaitable[httpx.Response]]


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
        input_price_usd_per_million: float = 0.75,
        output_price_usd_per_million: float = 4.5,
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
        for value in (
            input_price_usd_per_million,
            output_price_usd_per_million,
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError("OpenAI prices must be finite and non-negative")
        if credential_environment_variable != "OPENAI_API_KEY":
            raise ValueError("R1 OpenAI client must use OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.input_price = input_price_usd_per_million
        self.output_price = output_price_usd_per_million
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
            return ModelTutorOutputV2.model_json_schema()
        if task in {
            "grounded_tutor_answer",
            "bounded_pedagogical_tutor_answer",
        }:
            return ModelTutorOutput.model_json_schema()
        raise LlmConfigurationError()

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

    @staticmethod
    def _output_text(payload: dict[str, Any]) -> str:
        if payload.get("status") != "completed":
            raise LlmMalformedResponseError()
        values: list[str] = []
        output = payload.get("output")
        if not isinstance(output, list):
            raise LlmMalformedResponseError()
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                raise LlmMalformedResponseError()
            for part in content:
                if isinstance(part, dict) and part.get("type") == "refusal":
                    raise LlmMalformedResponseError()
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        values.append(text)
        if len(values) != 1:
            raise LlmMalformedResponseError()
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
            raise LlmMalformedResponseError() from error
        if not isinstance(payload, dict):
            raise LlmMalformedResponseError()
        observed_model = payload.get("model")
        if observed_model != self.model:
            raise LlmIdentityDriftError(
                provider_model=str(observed_model or "not-returned"),
                provider_revision=None,
            )
        try:
            content = json.loads(self._output_text(payload))
            if not isinstance(content, dict):
                raise ValueError("structured output root is not an object")
            validated = (
                ModelTutorOutputV2.model_validate(content)
                if task == "grounded_tutor_atomic_claims"
                else ModelTutorOutput.model_validate(content)
            )
            usage = payload.get("usage", {})
            if not isinstance(usage, dict):
                raise ValueError("usage is not an object")
            input_tokens = _token_count(usage, "input_tokens")
            output_tokens = _token_count(usage, "output_tokens")
        except (TypeError, ValueError) as error:
            raise LlmMalformedResponseError() from error
        cost = (
            input_tokens * self.input_price + output_tokens * self.output_price
        ) / 1_000_000
        return LlmResponse(
            content=validated.model_dump_json(),
            provider_model=observed_model,
            provider_revision=self.model,
            usage=GenerationUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                approximate_cost_usd=cost,
            ),
        )


def _token_count(usage: dict[str, Any], name: str) -> int:
    value = usage.get(name, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value
