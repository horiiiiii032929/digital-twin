"""Bounded repair must preserve source checks and account for failed calls."""
import json
import pytest

from src.digital_twin.generation.contract_repair import ContractRepairInstructionalGenerator
from src.digital_twin.generation.models import PolicyAction
from src.digital_twin.llm import LlmMalformedResponseError
from src.digital_twin.grounding.models import GenerationUsage
from tests.test_compact_instruction_generation import runtime, generate, Client, proposal


def configure(runtime, values):
    rt, _, _, _ = runtime
    class SequenceClient(Client):
        def __init__(self):
            self.calls = 0
        async def chat(self, messages, task):
            self.value = values[min(self.calls, len(values) - 1)]
            self.calls += 1
            if isinstance(self.value, Exception):
                raise self.value
            return await super().chat(messages, "question_specific_compact_instruction")
    client = SequenceClient()
    rt.tutoring.generator = ContractRepairInstructionalGenerator(client,
        model_id="gpt-5.6-luna", bounded_contract_enabled=True, named_referent_context_enabled=True)
    return client


@pytest.mark.asyncio
async def test_valid_proposal_is_delivered_without_repair(runtime):
    client = configure(runtime, [proposal()])
    answer = await generate(runtime)
    assert client.calls == 1
    assert answer.trace.policy_action == PolicyAction.ANSWER
    assert answer.trace.usage.approximate_cost_usd == .0001


@pytest.mark.asyncio
async def test_partial_without_missing_detail_is_reproposed_not_silently_relabelled(runtime):
    invalid = {**proposal(), "action": "partial"}
    valid = proposal()
    valid["units"][0]["text"] = "The corrected response preserves the approved rule."
    client = configure(runtime, [invalid, valid])
    answer = await generate(runtime)
    assert client.calls == 2
    assert "corrected response" in answer.content
    assert answer.trace.usage.approximate_cost_usd == .0002


@pytest.mark.asyncio
async def test_repair_with_unknown_source_is_rejected_without_third_call(runtime):
    invalid = {**proposal(), "action": "partial"}
    unknown = proposal()
    unknown["units"][0]["source_ids"] = ["NOT_APPROVED"]
    client = configure(runtime, [invalid, unknown])
    answer = await generate(runtime)
    assert client.calls == 2
    assert answer.trace.policy_action == PolicyAction.SAFE_PROVIDER_FAILURE
    assert answer.trace.usage.approximate_cost_usd == .0002
    assert not answer.citations


@pytest.mark.asyncio
async def test_failed_repair_preserves_cost_of_both_calls(runtime):
    invalid = {**proposal(), "action": "partial"}
    failure = LlmMalformedResponseError(stage="synthetic", usage=GenerationUsage(approximate_cost_usd=.003))
    client = configure(runtime, [invalid, failure])
    answer = await generate(runtime)
    assert client.calls == 2
    assert answer.trace.policy_action == PolicyAction.SAFE_PROVIDER_FAILURE
    assert answer.trace.usage.approximate_cost_usd == pytest.approx(.0031)
