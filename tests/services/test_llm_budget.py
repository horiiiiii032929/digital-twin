import math

import pytest

from services.llm import BudgetedLlmClient
from src.digital_twin.grounding import GenerationUsage
from src.digital_twin.llm import (
    LlmBudgetExceededError,
    LlmMessage,
    LlmResponse,
)


class CostedClient:
    async def chat(self, messages, task):
        del messages, task
        return LlmResponse(
            content='{"answer":"Synthetic","citation_ids":["S1"]}',
            provider_model="fixture/costed",
            usage=GenerationUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                approximate_cost_usd=0.6,
            ),
        )


def test_budget_rejects_non_finite_cost_cap():
    with pytest.raises(ValueError):
        BudgetedLlmClient(CostedClient(), max_calls=1, max_cost_usd=math.nan)


@pytest.mark.asyncio
async def test_budget_stops_before_call_limit():
    client = BudgetedLlmClient(CostedClient(), max_calls=1, max_cost_usd=5)
    message = [LlmMessage(role="user", content="Synthetic")]

    await client.chat(message, "test")
    with pytest.raises(LlmBudgetExceededError):
        await client.chat(message, "test")

    assert client.snapshot() == {
        "calls": 1,
        "max_calls": 1,
        "completed_calls": 1,
        "failed_calls": 0,
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
        "total_latency_ms": pytest.approx(0, abs=100),
        "latency_p50_ms": pytest.approx(0, abs=100),
        "latency_p95_ms": pytest.approx(0, abs=100),
        "reported_cost_usd": 0.6,
        "max_cost_usd": 5,
        "unknown_cost_calls": 0,
        "cost_reporting_failed": False,
        "call_records": [
            {
                "call_number": 1,
                "task": "test",
                "status": "completed",
                "provider_model": "fixture/costed",
                "provider_revision": None,
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "reported_cost_usd": 0.6,
                "latency_ms": pytest.approx(0, abs=100),
                "error_code": None,
            }
        ],
    }


@pytest.mark.asyncio
async def test_budget_stops_after_reported_cost_reaches_cap():
    client = BudgetedLlmClient(CostedClient(), max_calls=10, max_cost_usd=0.5)
    message = [LlmMessage(role="user", content="Synthetic")]

    await client.chat(message, "test")
    with pytest.raises(LlmBudgetExceededError):
        await client.chat(message, "test")


class UnknownCostClient:
    async def chat(self, messages, task):
        del messages, task
        return LlmResponse(
            content='{"answer":"Synthetic","citation_ids":["S1"]}',
            provider_model="fixture/unknown-cost",
        )


@pytest.mark.asyncio
async def test_budget_fails_closed_after_provider_cost_cannot_be_measured():
    client = BudgetedLlmClient(UnknownCostClient(), max_calls=10, max_cost_usd=5)
    message = [LlmMessage(role="user", content="Synthetic")]

    await client.chat(message, "test")
    with pytest.raises(LlmBudgetExceededError):
        await client.chat(message, "test")

    assert client.snapshot()["cost_reporting_failed"] is True


class FailedClient:
    async def chat(self, messages, task):
        del messages, task
        raise RuntimeError("synthetic failure")


@pytest.mark.asyncio
async def test_budget_records_failed_call_without_prompt_content():
    client = BudgetedLlmClient(FailedClient(), max_calls=2, max_cost_usd=5)
    message = [LlmMessage(role="user", content="Sensitive synthetic prompt")]

    with pytest.raises(RuntimeError, match="synthetic failure"):
        await client.chat(message, "test")

    snapshot = client.snapshot()
    assert snapshot["calls"] == 1
    assert snapshot["completed_calls"] == 0
    assert snapshot["failed_calls"] == 1
    assert snapshot["cost_reporting_failed"] is True
    assert snapshot["call_records"][0]["error_code"] == "RuntimeError"
    assert "Sensitive" not in str(snapshot)
