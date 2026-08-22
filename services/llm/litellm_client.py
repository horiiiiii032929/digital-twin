from collections.abc import Awaitable, Callable
from copy import deepcopy
import math
from typing import Any

import litellm

from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import (
    LlmAuthenticationError,
    LlmConfigurationError,
    LlmMalformedResponseError,
    LlmMessage,
    LlmResponse,
    LlmTimeoutError,
    LlmUnavailableError,
    validate_llm_task,
)
from src.digital_twin.model_policy import require_registered_current_model


_Completion = Callable[..., Awaitable[Any]]
_CostCalculator = Callable[..., float]


class LiteLlmClient:
    """Environment-authenticated LiteLLM adapter with provider-neutral output."""

    def __init__(
        self,
        model: str,
        *,
        timeout_seconds: float = 30,
        max_output_tokens: int = 600,
        temperature: float | None = 0,
        response_format: dict[str, Any] | None = None,
        provider_options: dict[str, Any] | None = None,
        expected_provider_model: str | None = None,
        expected_provider_revision: str | None = None,
        completion: _Completion = litellm.acompletion,
        cost_calculator: _CostCalculator = litellm.completion_cost,
    ) -> None:
        model = require_registered_current_model(model)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if isinstance(max_output_tokens, bool) or max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if temperature is not None and (
            not math.isfinite(temperature) or not 0 <= temperature <= 2
        ):
            raise ValueError("temperature must be between 0 and 2")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.response_format = response_format
        self.provider_options = deepcopy(provider_options or {})
        self.expected_provider_model = require_registered_current_model(
            expected_provider_model or model
        )
        self.expected_provider_revision = _optional_string(expected_provider_revision)
        forbidden_options = {
            "api_key",
            "messages",
            "metadata",
            "model",
            "timeout",
            "max_tokens",
            "max_completion_tokens",
            "response_format",
            "temperature",
            "stream",
            "tools",
            "tool_choice",
        }
        overlap = forbidden_options.intersection(self.provider_options)
        if overlap:
            raise ValueError(
                "provider_options cannot override protected fields: "
                + ", ".join(sorted(overlap))
            )
        self.completion = completion
        self.cost_calculator = cost_calculator

    async def chat(
        self,
        messages: list[LlmMessage],
        task: str,
        *,
        response_format: dict[str, Any] | None = None,
    ) -> LlmResponse:
        task = validate_llm_task(task)
        if not messages:
            raise ValueError("at least one LLM message is required")
        try:
            completion_arguments = {
                "model": self.model,
                "messages": [message.model_dump(mode="json") for message in messages],
                "timeout": self.timeout_seconds,
                "max_tokens": self.max_output_tokens,
                "metadata": {"task": task},
            }
            if self.temperature is not None:
                completion_arguments["temperature"] = self.temperature
            selected_response_format = (
                response_format if response_format is not None else self.response_format
            )
            if selected_response_format is not None:
                completion_arguments["response_format"] = deepcopy(
                    selected_response_format
                )
            completion_arguments.update(deepcopy(self.provider_options))
            response = await self.completion(
                **completion_arguments,
            )
        except litellm.AuthenticationError as error:
            raise LlmAuthenticationError() from error
        except litellm.Timeout as error:
            raise LlmTimeoutError() from error
        except litellm.BadRequestError as error:
            raise LlmConfigurationError() from error
        except (
            litellm.RateLimitError,
            litellm.ServiceUnavailableError,
            litellm.APIConnectionError,
            litellm.APIError,
        ) as error:
            raise LlmUnavailableError() from error
        except Exception as error:
            raise LlmUnavailableError() from error

        content = _content(response)
        if not isinstance(content, str) or not content.strip():
            raise LlmMalformedResponseError()

        try:
            usage = _field(response, "usage", {})
            input_tokens = _usage_count(usage, "prompt_tokens", default=0)
            output_tokens = _usage_count(usage, "completion_tokens", default=0)
            total_tokens = _usage_count(
                usage,
                "total_tokens",
                default=input_tokens + output_tokens,
            )
            if total_tokens < input_tokens + output_tokens:
                raise ValueError("total token count is inconsistent")
        except (TypeError, ValueError) as error:
            raise LlmMalformedResponseError() from error
        try:
            cost = float(self.cost_calculator(completion_response=response))
        except Exception:
            cost = None
        try:
            provider_model = str(_field(response, "model", self.model) or self.model)
            provider_revision = _optional_string(
                _field(response, "system_fingerprint", None)
            )
            _validate_response_identity(
                provider_model,
                provider_revision,
                expected_model=self.expected_provider_model,
                expected_revision=self.expected_provider_revision,
            )
            return LlmResponse(
                content=content,
                provider_model=provider_model,
                provider_revision=provider_revision,
                usage=GenerationUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    approximate_cost_usd=cost,
                ),
            )
        except ValueError as error:
            raise LlmMalformedResponseError() from error


def _content(response: Any) -> Any:
    choices = _field(response, "choices", [])
    if not isinstance(choices, list) or len(choices) != 1:
        return None
    message = _field(choices[0], "message", {})
    return _field(message, "content", None)


def _field(value: Any, name: str, default: Any) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _usage_count(value: Any, name: str, *, default: int) -> int:
    raw = _field(value, name, default)
    if raw is None:
        raw = default
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return raw


def _validate_response_identity(
    provider_model: str,
    provider_revision: str | None,
    *,
    expected_model: str,
    expected_revision: str | None,
) -> None:
    try:
        require_registered_current_model(provider_model)
    except ValueError as error:
        raise LlmMalformedResponseError() from error
    if _canonical_model_id(provider_model) != _canonical_model_id(expected_model):
        raise LlmMalformedResponseError()
    if expected_revision is not None and provider_revision != expected_revision:
        raise LlmMalformedResponseError()


def _canonical_model_id(model: str) -> str:
    normalized = model.strip().casefold()
    if normalized.startswith("openrouter/"):
        normalized = normalized.removeprefix("openrouter/")
    if normalized.startswith("ollama/"):
        normalized = normalized.removeprefix("ollama/")
    if normalized.startswith("deepseek/deepseek-"):
        normalized = normalized.removeprefix("deepseek/")
    return normalized
