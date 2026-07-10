from typing import Literal, Protocol

from pydantic import BaseModel


LlmRole = Literal["system", "user", "assistant"]


class LlmMessage(BaseModel):
    role: LlmRole
    content: str


class LlmClient(Protocol):
    async def chat(self, messages: list[LlmMessage], task: str) -> str:
        """Return a model response for a named application task."""


class FixtureLlmClient:
    async def chat(self, messages: list[LlmMessage], task: str) -> str:
        joined_messages = " ".join(message.content for message in messages)
        return f"fixture response for {task}: {joined_messages[:120]}"
