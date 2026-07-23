from typing import Literal, Protocol

from pydantic import BaseModel, Field

from src.digital_twin.grounding.models import GenerationUsage


LlmRole = Literal["system", "user", "assistant"]


class LlmMessage(BaseModel):
    role: LlmRole
    content: str


class LlmResponse(BaseModel):
    content: str = Field(min_length=1)
    provider_model: str = Field(min_length=1)
    usage: GenerationUsage = Field(default_factory=GenerationUsage)


class LlmError(RuntimeError):
    code = "llm-error"


class LlmTimeoutError(LlmError):
    code = "timeout"


class LlmAuthenticationError(LlmError):
    code = "authentication"


class LlmUnavailableError(LlmError):
    code = "unavailable"


class LlmConfigurationError(LlmError):
    code = "configuration"


class LlmMalformedResponseError(LlmError):
    code = "malformed-response"


class LlmClient(Protocol):
    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        """Return a model response for a named application task."""


class FixtureLlmClient:
    def __init__(self, response_content: str | None = None) -> None:
        self.response_content = response_content

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        joined_messages = " ".join(message.content for message in messages)
        content = self.response_content or (
            f"fixture response for {task}: {joined_messages[:120]}"
        )
        return LlmResponse(content=content, provider_model="fixture/v1")
