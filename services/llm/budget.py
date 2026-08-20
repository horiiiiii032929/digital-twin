"""Process-local hard caps around an external LLM client."""

from __future__ import annotations

import asyncio
import math

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
        if (
            isinstance(max_calls, bool)
            or max_calls <= 0
            or not math.isfinite(max_cost_usd)
            or max_cost_usd <= 0
        ):
            raise ValueError("provider call and cost caps must be positive")
        self.client = client
        self.max_calls = max_calls
        self.max_cost_usd = max_cost_usd
        self._reserved_calls = 0
        self._reported_cost_usd = 0.0
        self._unknown_cost_calls = 0
        self._cost_reporting_failed = False
        self._lock = asyncio.Lock()

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        async with self._lock:
            if (
                self._reserved_calls >= self.max_calls
                or self._reported_cost_usd >= self.max_cost_usd
                or self._cost_reporting_failed
            ):
                raise LlmBudgetExceededError()
            self._reserved_calls += 1
            response = await self.client.chat(messages, task)
            cost = response.usage.approximate_cost_usd
            if cost is None:
                self._unknown_cost_calls += 1
                self._cost_reporting_failed = True
            else:
                self._reported_cost_usd += cost
        return response

    def snapshot(self) -> dict[str, int | float | bool]:
        return {
            "calls": self._reserved_calls,
            "max_calls": self.max_calls,
            "reported_cost_usd": round(self._reported_cost_usd, 8),
            "max_cost_usd": self.max_cost_usd,
            "unknown_cost_calls": self._unknown_cost_calls,
            "cost_reporting_failed": self._cost_reporting_failed,
        }
