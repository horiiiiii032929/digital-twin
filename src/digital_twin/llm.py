import re
from typing import Literal, Protocol

from pydantic import BaseModel, Field, field_validator

from src.digital_twin.grounding.models import GenerationUsage


LlmRole = Literal["system", "user", "assistant"]
_TASK_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class LlmMessage(BaseModel):
    role: LlmRole
    content: str = Field(min_length=1, max_length=100_000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, content: str) -> str:
        if not content.strip():
            raise ValueError("LLM message content must not be blank")
        return content


class LlmResponse(BaseModel):
    content: str = Field(min_length=1)
    provider_model: str = Field(min_length=1)
    provider_revision: str | None = None
    usage: GenerationUsage = Field(default_factory=GenerationUsage)

    @field_validator("content", "provider_model")
    @classmethod
    def required_strings_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("LLM response fields must not be blank")
        return normalized

    @field_validator("provider_revision")
    @classmethod
    def optional_revision_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


def validate_llm_task(task: str) -> str:
    normalized = task.strip()
    if not _TASK_PATTERN.fullmatch(normalized):
        raise ValueError("LLM task must be a short machine identifier")
    return normalized


class LlmError(RuntimeError):
    code = "llm-error"


class LlmTimeoutError(LlmError):
    code = "timeout"


class LlmAuthenticationError(LlmError):
    code = "authentication"


class LlmUnavailableError(LlmError):
    code = "unavailable"


class LlmBudgetExceededError(LlmUnavailableError):
    code = "budget-exceeded"


class LlmConfigurationError(LlmError):
    code = "configuration"


class LlmMalformedResponseError(LlmError):
    code = "malformed-response"


class LlmIdentityDriftError(LlmError):
    code = "identity-drift"

    def __init__(
        self,
        *,
        provider_model: str,
        provider_revision: str | None,
    ) -> None:
        super().__init__(self.code)
        self.provider_model = provider_model
        self.provider_revision = provider_revision


class LlmClient(Protocol):
    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        """Return a model response for a named application task."""


class FixtureLlmClient:
    def __init__(self, response_content: str | None = None) -> None:
        self.response_content = response_content

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        task = validate_llm_task(task)
        if not messages:
            raise ValueError("at least one LLM message is required")
        joined_messages = " ".join(message.content for message in messages)
        content = self.response_content or (
            f"fixture response for {task}: {joined_messages[:120]}"
        )
        return LlmResponse(content=content, provider_model="fixture/v1")
