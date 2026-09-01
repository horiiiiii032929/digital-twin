"""Process-local hard caps around an external LLM client."""

from __future__ import annotations

import asyncio
import math
import time
from typing import Any

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
        self._input_tokens = 0
        self._output_tokens = 0
        self._call_records: list[dict[str, Any]] = []
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
            call_number = self._reserved_calls
            started = time.perf_counter()
            try:
                response = await self.client.chat(messages, task)
            except BaseException as error:
                latency_ms = max(0.0, (time.perf_counter() - started) * 1_000)
                usage = getattr(error, "usage", None)
                input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
                total_tokens = input_tokens + output_tokens
                cost = getattr(usage, "approximate_cost_usd", None)
                if cost is None:
                    self._unknown_cost_calls += 1
                    self._cost_reporting_failed = True
                else:
                    self._input_tokens += input_tokens
                    self._output_tokens += output_tokens
                    self._reported_cost_usd += float(cost)
                record = {
                        "call_number": call_number,
                        "task": task,
                        "status": "failed",
                        "provider_model": getattr(error, "provider_model", None),
                        "provider_revision": getattr(
                            error, "provider_revision", None
                        ),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "reported_cost_usd": (
                            round(float(cost), 10) if cost is not None else None
                        ),
                        "latency_ms": round(latency_ms, 3),
                        "error_code": getattr(error, "code", type(error).__name__),
                    }
                diagnostics = getattr(error, "diagnostics", None)
                if isinstance(diagnostics, dict) and diagnostics:
                    record["failure_diagnostics"] = dict(diagnostics)
                self._call_records.append(record)
                raise
            latency_ms = max(0.0, (time.perf_counter() - started) * 1_000)
            cost = response.usage.approximate_cost_usd
            self._input_tokens += response.usage.input_tokens
            self._output_tokens += response.usage.output_tokens
            if cost is None:
                self._unknown_cost_calls += 1
                self._cost_reporting_failed = True
            else:
                self._reported_cost_usd += cost
            self._call_records.append(
                {
                    "call_number": call_number,
                    "task": task,
                    "status": "completed",
                    "provider_model": response.provider_model,
                    "provider_revision": response.provider_revision,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "reported_cost_usd": (
                        round(cost, 10) if cost is not None else None
                    ),
                    "latency_ms": round(latency_ms, 3),
                    "error_code": None,
                }
            )
        return response

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = round((len(ordered) - 1) * percentile)
        return ordered[index]

    def snapshot(self) -> dict[str, Any]:
        latencies = [float(row["latency_ms"]) for row in self._call_records]
        return {
            "calls": self._reserved_calls,
            "max_calls": self.max_calls,
            "completed_calls": sum(
                row["status"] == "completed" for row in self._call_records
            ),
            "failed_calls": sum(
                row["status"] == "failed" for row in self._call_records
            ),
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "total_tokens": self._input_tokens + self._output_tokens,
            "total_latency_ms": round(sum(latencies), 3),
            "latency_p50_ms": round(self._percentile(latencies, 0.50), 3),
            "latency_p95_ms": round(self._percentile(latencies, 0.95), 3),
            "reported_cost_usd": round(self._reported_cost_usd, 8),
            "max_cost_usd": self.max_cost_usd,
            "unknown_cost_calls": self._unknown_cost_calls,
            "cost_reporting_failed": self._cost_reporting_failed,
            "call_records": [dict(row) for row in self._call_records],
        }
