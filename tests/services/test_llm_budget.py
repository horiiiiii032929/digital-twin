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
        "reported_cost_usd": 0.6,
        "max_cost_usd": 5,
        "unknown_cost_calls": 0,
        "cost_reporting_failed": False,
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
