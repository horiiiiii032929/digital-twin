import asyncio
import json

import pytest

from services.llm import BudgetedLlmClient, OpenAiResponsesClient
from src.digital_twin.grounding import GenerationUsage
from src.digital_twin.llm import LlmBudgetExceededError, LlmMessage, LlmResponse

MESSAGES = [LlmMessage(role="user", content="Synthetic bounded request")]


class HeldCostClient:
    def __init__(self, *, cost=0.1, ceiling=0.2):
        self.cost, self.ceiling = cost, ceiling
        self.active = self.peak = self.calls = 0
        self.release = asyncio.Event()

    def conservative_request_cost_usd(self, messages, task):
        return self.ceiling

    async def chat(self, messages, task):
        self.calls += 1
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await self.release.wait()
            return LlmResponse(content="{}", provider_model="fixture/bounded", usage=GenerationUsage(
                input_tokens=1, output_tokens=1, total_tokens=2, approximate_cost_usd=self.cost))
        finally:
            self.active -= 1


async def wait_calls(client, count):
    async with asyncio.timeout(2):
        while client.calls < count:
            await asyncio.sleep(0)


@pytest.mark.asyncio
@pytest.mark.parametrize("cap,calls,expected", [(1.0, 20, 5), (0.6, 20, 3), (1.0, 2, 2)])
async def test_atomic_cost_and_call_reservations_overlap_only_within_both_caps(cap, calls, expected):
    transport = HeldCostClient()
    budget = BudgetedLlmClient(transport, max_calls=calls, max_cost_usd=cap, max_concurrency=5)
    tasks = [asyncio.create_task(budget.chat(MESSAGES, "fixture")) for _ in range(5)]
    await wait_calls(transport, expected)
    await asyncio.sleep(0.01)
    assert transport.calls == expected
    assert budget.snapshot()["inflight_reserved_usd"] == pytest.approx(expected * 0.2)
    transport.release.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert sum(isinstance(r, LlmResponse) for r in results) == expected
    assert all(isinstance(r, (LlmResponse, LlmBudgetExceededError)) for r in results)
    snapshot = budget.snapshot()
    assert snapshot["inflight_reserved_usd"] == 0
    assert snapshot["reported_cost_usd"] == pytest.approx(expected * 0.1)
    assert transport.peak == expected


@pytest.mark.asyncio
async def test_cancellation_before_admission_does_not_charge_and_after_admission_retains_reservation():
    transport = HeldCostClient()
    budget = BudgetedLlmClient(transport, max_calls=10, max_cost_usd=1, max_concurrency=2)
    active = [asyncio.create_task(budget.chat(MESSAGES, "fixture")) for _ in range(2)]
    await wait_calls(transport, 2)
    waiting = asyncio.create_task(budget.chat(MESSAGES, "fixture"))
    await asyncio.sleep(0)
    waiting.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiting
    assert budget.snapshot()["calls"] == 2
    active[0].cancel()
    with pytest.raises(asyncio.CancelledError):
        await active[0]
    assert budget.snapshot()["uncertain_reserved_usd"] == 0.2
    assert budget.snapshot()["inflight_reserved_usd"] == pytest.approx(0.2)
    with pytest.raises(LlmBudgetExceededError):
        await budget.chat(MESSAGES, "fixture")
    transport.release.set()
    await active[1]
    assert budget.snapshot()["inflight_calls"] == 0
    assert budget.snapshot()["inflight_reserved_usd"] == 0
    assert budget.snapshot()["reported_cost_usd"] == 0.1
    assert budget.snapshot()["unknown_cost_calls"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("cost", [None, 0.3])
async def test_unknown_usage_or_broken_ceiling_closes_new_admissions(cost):
    transport = HeldCostClient(cost=cost)
    transport.release.set()
    budget = BudgetedLlmClient(transport, max_calls=10, max_cost_usd=1, max_concurrency=5)
    with pytest.raises(LlmBudgetExceededError):
        await budget.chat(MESSAGES, "fixture")
    with pytest.raises(LlmBudgetExceededError):
        await budget.chat(MESSAGES, "fixture")
    assert transport.calls == 1
    assert budget.snapshot()["cost_reporting_failed"]
    assert budget.snapshot()["uncertain_reserved_usd"] == (0.2 if cost is None else 0)
    assert budget.snapshot()["call_records"][0]["reservation_exceeded"] == (cost is not None)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["serial-default", "unknown-ceiling"])
async def test_control_and_unknown_cost_capability_remain_serial(mode):
    transport = HeldCostClient()
    if mode == "unknown-ceiling":
        transport.conservative_request_cost_usd = None
    budget = BudgetedLlmClient(transport, max_calls=10, max_cost_usd=1,
                              max_concurrency=5 if mode == "unknown-ceiling" else 1)
    tasks = [asyncio.create_task(budget.chat(MESSAGES, "fixture")) for _ in range(3)]
    await wait_calls(transport, 1)
    await asyncio.sleep(0.01)
    assert transport.calls == 1
    transport.release.set()
    await asyncio.gather(*tasks)
    assert transport.peak == 1


def test_known_provider_ceiling_covers_serialized_input_and_output_and_rejects_oversize():
    client = OpenAiResponsesClient("gpt-5.6-luna", max_output_tokens=500, reasoning_effort="low")
    size = len(json.dumps(client._payload(MESSAGES, "question_specific_profile_tutoring"), ensure_ascii=False).encode())
    assert client.conservative_request_cost_usd(MESSAGES, "question_specific_profile_tutoring") == (
        (size + 4096) * client.input_price + 500 * client.output_price) / 1_000_000
    with pytest.raises(LlmBudgetExceededError):
        client.conservative_request_cost_usd([LlmMessage(role="user", content="x" * 20_001)],
                                             "question_specific_profile_tutoring")


@pytest.mark.asyncio
async def test_settlement_releases_unused_ceiling_but_never_allows_more_than_remaining_ceiling():
    transport = HeldCostClient()
    transport.release.set()
    budget = BudgetedLlmClient(transport, max_calls=10, max_cost_usd=0.3, max_concurrency=5)
    await budget.chat(MESSAGES, "fixture")
    await budget.chat(MESSAGES, "fixture")
    with pytest.raises(LlmBudgetExceededError):
        await budget.chat(MESSAGES, "fixture")
    assert transport.calls == 2
    assert budget.snapshot()["reported_cost_usd"] == 0.2
    assert budget.snapshot()["inflight_reserved_usd"] == 0


@pytest.mark.asyncio
async def test_billed_provider_error_reconciles_reservation_and_preserves_diagnostics():
    from tests.services.test_llm_budget import DiagnosedMalformedClient
    from src.digital_twin.llm import LlmMalformedResponseError

    class BoundedMalformed(DiagnosedMalformedClient):
        def conservative_request_cost_usd(self, messages, task):
            return 0.3

    budget = BudgetedLlmClient(BoundedMalformed(), max_calls=2, max_cost_usd=1, max_concurrency=5)
    with pytest.raises(LlmMalformedResponseError):
        await budget.chat(MESSAGES, "fixture")
    snapshot = budget.snapshot()
    assert snapshot["reported_cost_usd"] == 0.25
    assert snapshot["inflight_reserved_usd"] == 0
    assert not snapshot["cost_reporting_failed"]
    assert snapshot["call_records"][0]["failure_diagnostics"]["failure_stage"] == "schema-validation"


@pytest.mark.asyncio
async def test_advertised_ceiling_cannot_disappear_while_other_calls_are_inflight():
    transport = HeldCostClient()
    transport.conservative_request_cost_usd = lambda messages, task: 0.2 if task == "known" else None
    budget = BudgetedLlmClient(transport, max_calls=10, max_cost_usd=0.2, max_concurrency=5)
    admitted = asyncio.create_task(budget.chat(MESSAGES, "known"))
    await wait_calls(transport, 1)
    with pytest.raises(LlmBudgetExceededError):
        await budget.chat(MESSAGES, "unknown")
    assert transport.calls == 1
    transport.release.set()
    await admitted

@pytest.mark.asyncio
async def test_serial_bounded_transport_rejects_unaffordable_call_before_dispatch():
    transport = HeldCostClient(cost=.2, ceiling=.2)
    transport.release.set()
    budget = BudgetedLlmClient(transport, max_calls=3, max_cost_usd=.3, max_concurrency=1)
    await budget.chat(MESSAGES, "fixture")
    with pytest.raises(LlmBudgetExceededError):
        await budget.chat(MESSAGES, "fixture")
    assert transport.calls == 1
    assert budget.snapshot()["reported_cost_usd"] == pytest.approx(.2)


@pytest.mark.parametrize("max_calls", [1.5, float("nan"), float("inf"), "2"])
def test_budget_requires_integer_call_cap(max_calls):
    with pytest.raises(ValueError):
        BudgetedLlmClient(HeldCostClient(), max_calls=max_calls, max_cost_usd=1)

@pytest.mark.parametrize("cap", [1.5, float("nan"), float("inf"), "3000"])
@pytest.mark.parametrize("provider", ["openai", "litellm"])
def test_provider_output_token_bound_requires_integer(cap, provider):
    from services.llm import LiteLlmClient
    factory = (lambda: OpenAiResponsesClient("gpt-5.6-luna", max_output_tokens=cap)) if provider == "openai" else (
        lambda: LiteLlmClient("deepseek-v4-flash", max_output_tokens=cap))
    with pytest.raises(ValueError):
        factory()

@pytest.mark.asyncio
async def test_nested_budget_propagates_missing_estimator_without_inventing_one():
    class LegacyClient:
        async def chat(self, messages, task):
            return LlmResponse(content="{}", provider_model="fixture/legacy",
                usage=GenerationUsage(input_tokens=1, output_tokens=1, total_tokens=2, approximate_cost_usd=.1))
    parent = BudgetedLlmClient(LegacyClient(), max_calls=2, max_cost_usd=1)
    child = BudgetedLlmClient(parent, max_calls=1, max_cost_usd=1)
    await child.chat(MESSAGES, "fixture")
    assert child.snapshot()["calls"] == parent.snapshot()["calls"] == 1
    assert child.snapshot()["reported_cost_usd"] == parent.snapshot()["reported_cost_usd"] == .1
    with pytest.raises(LlmBudgetExceededError):
        await child.chat(MESSAGES, "fixture")
    assert parent.snapshot()["calls"] == 1


@pytest.mark.asyncio
async def test_nested_budget_with_real_estimator_preserves_outer_admission_bound():
    transport = HeldCostClient(cost=.2, ceiling=.2)
    transport.release.set()
    parent = BudgetedLlmClient(transport, max_calls=5, max_cost_usd=1)
    child = BudgetedLlmClient(parent, max_calls=5, max_cost_usd=.1)
    with pytest.raises(LlmBudgetExceededError):
        await child.chat(MESSAGES, "fixture")
    assert transport.calls == parent.snapshot()["calls"] == child.snapshot()["calls"] == 0

@pytest.mark.asyncio
@pytest.mark.parametrize("cost", [None, .3])
async def test_rejected_response_cost_exports_valid_failure_record(cost):
    from src.digital_twin.evaluation.autonomy_contract import AutonomyProviderCallV1
    transport = HeldCostClient(cost=cost, ceiling=.2)
    transport.release.set()
    budget = BudgetedLlmClient(transport, max_calls=2, max_cost_usd=1)
    with pytest.raises(LlmBudgetExceededError):
        await budget.chat(MESSAGES, "fixture")
    record = AutonomyProviderCallV1(**budget.snapshot()["call_records"][0])
    assert record.status == "failed" and record.error_code == LlmBudgetExceededError.code
    assert record.reserved_cost_usd == .2
