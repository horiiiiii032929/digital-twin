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
        max_concurrency: int = 1,
    ) -> None:
        if (
            isinstance(max_calls, bool)
            or not isinstance(max_calls, int)
            or max_calls <= 0
            or not math.isfinite(max_cost_usd)
            or max_cost_usd <= 0
        ):
            raise ValueError("provider call and cost caps must be positive")
        if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int) or not 1 <= max_concurrency <= 25:
            raise ValueError("max_concurrency must be an integer from 1 to 25")
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._inflight_cost_usd = 0.0
        self._uncertain_reserved_usd = 0.0
        self._inflight_calls = 0
        self._peak_inflight_calls = 0
        self.client = client
        self._cost_ceiling = getattr(client, "conservative_request_cost_usd", None)
        # A nested budget exposes the method even when its transport has no
        # estimator. Propagate that fixed capability absence, not a per-task
        # None from an otherwise bounded transport (which must still reject).
        if isinstance(client, BudgetedLlmClient) and not callable(client._cost_ceiling):
            self._cost_ceiling = None
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

    def conservative_request_cost_usd(self, messages: list[LlmMessage], task: str) -> float | None:
        return self._cost_ceiling(messages, task) if callable(self._cost_ceiling) else None

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        if not callable(self._cost_ceiling):
            return await self._chat_serial(messages, task)
        reservation = self.conservative_request_cost_usd(messages, task)
        if reservation is None:
            # An advertised ceiling cannot disappear for one task while other
            # bounded calls are in flight. Reject that request before admission.
            raise LlmBudgetExceededError()
        if not math.isfinite(reservation) or reservation < 0:
            raise ValueError("request cost ceiling must be finite and non-negative")
        async with self._semaphore:
            async with self._lock:
                total = self._reported_cost_usd + self._uncertain_reserved_usd + self._inflight_cost_usd
                if (self._reserved_calls >= self.max_calls or self._cost_reporting_failed
                        or total + reservation > self.max_cost_usd + 1e-12):
                    raise LlmBudgetExceededError()
                self._reserved_calls += 1
                number = self._reserved_calls
                self._inflight_calls += 1
                self._peak_inflight_calls = max(self._peak_inflight_calls, self._inflight_calls)
                self._inflight_cost_usd += reservation
            started = time.perf_counter()
            response = None
            error = None
            try:
                response = await self.client.chat(messages, task)
            except BaseException as caught:
                error = caught
                raise
            finally:
                # No await during reconciliation: cancellation cannot strand a reservation.
                # These fields are owned by this event loop; admission's lock section
                # also contains no await, so settlement is atomic with admission.
                self._inflight_calls -= 1
                self._inflight_cost_usd = (max(0.0, self._inflight_cost_usd - reservation)
                                           if self._inflight_calls else 0.0)
                usage = getattr(response if response is not None else error, "usage", None)
                cost = getattr(usage, "approximate_cost_usd", None)
                valid_cost = (isinstance(cost, (int, float)) and not isinstance(cost, bool)
                              and math.isfinite(cost) and cost >= 0)
                input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
                self._input_tokens += input_tokens
                self._output_tokens += output_tokens
                if valid_cost:
                    self._reported_cost_usd += cost
                    if cost > reservation + 1e-12:
                        self._cost_reporting_failed = True
                else:
                    self._unknown_cost_calls += 1
                    self._uncertain_reserved_usd += reservation
                    self._cost_reporting_failed = True
                self._call_records.append({
                    "call_number": number, "task": task,
                    "status": "completed" if response is not None and valid_cost and cost <= reservation + 1e-12 else "failed",
                    "provider_model": getattr(response if response is not None else error, "provider_model", None),
                    "provider_revision": getattr(response if response is not None else error, "provider_revision", None),
                    "input_tokens": input_tokens, "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "reported_cost_usd": round(float(cost), 10) if valid_cost else None,
                    "reserved_cost_usd": reservation,
                    "reservation_exceeded": valid_cost and cost > reservation + 1e-12,
                    "latency_ms": round(max(0.0, (time.perf_counter() - started) * 1000), 3),
                    "error_code": (getattr(error, "code", type(error).__name__) if error is not None
                                   else LlmBudgetExceededError.code if not valid_cost or cost > reservation + 1e-12
                                   else None),
                })
                diagnostics = getattr(error, "diagnostics", None)
                if isinstance(diagnostics, dict) and diagnostics:
                    self._call_records[-1]["failure_diagnostics"] = dict(diagnostics)
            if not valid_cost or cost > reservation + 1e-12:
                raise LlmBudgetExceededError()
            assert response is not None
            return response

    async def _chat_serial(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        async with self._lock:
            if (
                self._reserved_calls >= self.max_calls
                or self._reported_cost_usd >= self.max_cost_usd
                or self._cost_reporting_failed
            ):
                raise LlmBudgetExceededError()
            self._reserved_calls += 1
            call_number = self._reserved_calls
            self._inflight_calls += 1
            self._peak_inflight_calls = max(self._peak_inflight_calls, self._inflight_calls)
            started = time.perf_counter()
            try:
                response = await self.client.chat(messages, task)
            except BaseException as error:
                self._inflight_calls -= 1
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
            self._inflight_calls -= 1
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
            "max_concurrency": self.max_concurrency,
            "inflight_calls": self._inflight_calls,
            "peak_inflight_calls": self._peak_inflight_calls,
            "inflight_reserved_usd": self._inflight_cost_usd,
            "uncertain_reserved_usd": self._uncertain_reserved_usd,
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
