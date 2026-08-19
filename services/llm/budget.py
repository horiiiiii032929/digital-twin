"""Process-local hard caps around an external LLM client."""

from __future__ import annotations

import asyncio

from src.digital_twin.llm import (
    LlmBudgetExceededError,
    LlmClient,
    LlmMessage,
    LlmResponse,
)


class BudgetedLlmClient:
    def __init__(
        self,
        client: LlmClient,
        *,
        max_calls: int,
        max_cost_usd: float,
    ) -> None:
        if max_calls <= 0 or max_cost_usd <= 0:
            raise ValueError("provider call and cost caps must be positive")
        self.client = client
        self.max_calls = max_calls
        self.max_cost_usd = max_cost_usd
        self._reserved_calls = 0
        self._reported_cost_usd = 0.0
        self._unknown_cost_calls = 0
        self._lock = asyncio.Lock()

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        async with self._lock:
            if (
                self._reserved_calls >= self.max_calls
                or self._reported_cost_usd >= self.max_cost_usd
            ):
                raise LlmBudgetExceededError()
            self._reserved_calls += 1
        response = await self.client.chat(messages, task)
        async with self._lock:
            cost = response.usage.approximate_cost_usd
            if cost is None:
                self._unknown_cost_calls += 1
            else:
                self._reported_cost_usd += cost
        return response

    def snapshot(self) -> dict[str, int | float]:
        return {
            "calls": self._reserved_calls,
            "max_calls": self.max_calls,
            "reported_cost_usd": round(self._reported_cost_usd, 8),
            "max_cost_usd": self.max_cost_usd,
            "unknown_cost_calls": self._unknown_cost_calls,
        }
