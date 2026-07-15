from collections.abc import Awaitable, Callable
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
)


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
        completion: _Completion = litellm.acompletion,
        cost_calculator: _CostCalculator = litellm.completion_cost,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.completion = completion
        self.cost_calculator = cost_calculator

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        try:
            response = await self.completion(
                model=self.model,
                messages=[message.model_dump(mode="json") for message in messages],
                timeout=self.timeout_seconds,
                temperature=0,
                max_tokens=self.max_output_tokens,
                metadata={"task": task},
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
            input_tokens = int(_field(usage, "prompt_tokens", 0) or 0)
            output_tokens = int(_field(usage, "completion_tokens", 0) or 0)
            total_tokens = int(
                _field(usage, "total_tokens", input_tokens + output_tokens) or 0
            )
        except (TypeError, ValueError) as error:
            raise LlmMalformedResponseError() from error
        try:
            cost = float(self.cost_calculator(completion_response=response))
        except Exception:
            cost = None
        try:
            return LlmResponse(
                content=content,
                provider_model=str(_field(response, "model", self.model) or self.model),
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
    if not choices:
        return None
    message = _field(choices[0], "message", {})
    return _field(message, "content", None)


def _field(value: Any, name: str, default: Any) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)
