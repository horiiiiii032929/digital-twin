import asyncio
import json

import pytest

from scripts.run_final_profile_longitudinal import (
    CASE_CONTEXT, MODEL, RecordedRunClient, run, run_decision,
)
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import (
    LlmBudgetExceededError, LlmIdentityDriftError, LlmMalformedResponseError,
    LlmMessage, LlmResponse,
)

MESSAGES = [LlmMessage(role="user", content="Synthetic evaluation request")]
TASK = "reactive_tutoring_plan"


class SyntheticClient:
    def __init__(self, model=MODEL):
        self.model = model
        self.calls = 0

    async def chat(self, messages, task):
        self.calls += 1
        await asyncio.sleep(0)
        return LlmResponse(content="{}", provider_model=self.model, provider_revision="synthetic-revision",
            usage=GenerationUsage(input_tokens=10, output_tokens=5, total_tokens=15, approximate_cost_usd=0.001))


def recorded(tmp_path, transport, **kwargs):
    return RecordedRunClient(transport, tmp_path / "provider.jsonl", maximum_calls=2,
        maximum_cost_usd=0.02, network_mode="contract-test", **kwargs)


@pytest.mark.asyncio
async def test_parallel_calls_preserve_case_attribution_and_reservation(tmp_path):
    transport = SyntheticClient()
    client = recorded(tmp_path, transport)

    async def call(case):
        token = CASE_CONTEXT.set(case)
        try:
            await client.chat(MESSAGES, TASK)
        finally:
            CASE_CONTEXT.reset(token)

    await asyncio.gather(call("case-a"), call("case-b"))
    with pytest.raises(LlmBudgetExceededError):
        await client.chat(MESSAGES, TASK)
    assert transport.calls == 2
    assert client.reserved_usd == pytest.approx(0.02)
    assert {row["case"] for row in client.records} == {"case-a", "case-b"}
    ledger = [json.loads(line) for line in (tmp_path / "provider.jsonl").read_text().splitlines()]
    assert sum(row["status"] == "started" for row in ledger) == 2
    assert sum(row["status"] == "completed" for row in ledger) == 2


@pytest.mark.asyncio
async def test_identity_rejection_preserves_billed_usage_and_stops(tmp_path):
    transport = SyntheticClient("unexpected-model")
    client = recorded(tmp_path, transport)
    with pytest.raises(LlmIdentityDriftError):
        await client.chat(MESSAGES, TASK)
    assert client.records[0]["usage"]["approximate_cost_usd"] == 0.001
    assert client.records[0]["returned_revision"] == "synthetic-revision"
    with pytest.raises(LlmBudgetExceededError):
        await client.chat(MESSAGES, TASK)
    assert transport.calls == 1


@pytest.mark.asyncio
async def test_failure_exceeding_reserved_usage_stops_future_calls(tmp_path):
    class ExpensiveFailure:
        async def chat(self, messages, task):
            raise LlmMalformedResponseError(provider_model=MODEL,
                usage=GenerationUsage(approximate_cost_usd=0.03))

    client = recorded(tmp_path, ExpensiveFailure())
    with pytest.raises(LlmMalformedResponseError):
        await client.chat(MESSAGES, TASK)
    assert client.stopped
    assert client.records[0]["usage"]["approximate_cost_usd"] == 0.03


def test_empty_or_contract_runs_never_establish_live_coverage(tmp_path):
    client = recorded(tmp_path, SyntheticClient())
    assert run_decision([], client, contract=False) == "insufficient-live-coverage"
    assert run_decision([], client, contract=True) == "contract-smoke-only-not-live-evidence"
    assert run_decision([{"id": "missing"}], client, contract=False) == "insufficient-live-coverage"


@pytest.mark.asyncio
async def test_contract_smoke_writes_serializable_evidence_and_cannot_claim_live(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    output = tmp_path / "smoke"
    result = await run(output, contract=True, days=2, maximum_calls=20, maximum_cost_usd=0.2)
    assert result["decision"] == "contract-smoke-only-not-live-evidence"
    assert result["live_model_successes"] == 0
    assert result["release_qualified"] is False
    assert len(result["cases"]) == 4
    assert all("error" not in row for row in result["cases"])
    for filename in ("truth.jsonl", "responses.jsonl", "learner-evidence.jsonl"):
        rows = [json.loads(line) for line in (output / filename).read_text().splitlines()]
        assert len(rows) == 4
    with pytest.raises(FileExistsError):
        await run(output, contract=True, days=2)


@pytest.mark.asyncio
async def test_explicit_terra_identity_serializer_and_pricing_are_consistent(tmp_path):
    client = RecordedRunClient(SyntheticClient(model="gpt-5.6-terra"), tmp_path / "terra.jsonl",
        maximum_calls=2, maximum_cost_usd=.12, reservation_usd=.06,
        expected_model="gpt-5.6-terra", network_mode="contract-test")
    response = await client.chat(MESSAGES, TASK)
    assert response.provider_model == client.serializer.model == "gpt-5.6-terra"
    assert client.records[0]["requested_model"] == "gpt-5.6-terra"
    mismatched = RecordedRunClient(SyntheticClient(model=MODEL), tmp_path / "mismatch.jsonl",
        maximum_calls=2, maximum_cost_usd=.12, reservation_usd=.06,
        expected_model="gpt-5.6-terra", network_mode="contract-test")
    with pytest.raises(LlmIdentityDriftError):
        await mismatched.chat(MESSAGES, TASK)
    assert mismatched.records[0]["returned_model"] == MODEL
    with pytest.raises(ValueError, match="Reservation"):
        RecordedRunClient(SyntheticClient(), tmp_path / "underpriced.jsonl",
            maximum_calls=2, maximum_cost_usd=.12, reservation_usd=.01,
            expected_model="gpt-5.6-terra", network_mode="contract-test")
