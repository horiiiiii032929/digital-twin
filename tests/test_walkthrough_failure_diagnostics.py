"""Offline reproductions of initial-provider diagnostic loss in lifecycle 006."""
import pytest

from src.digital_twin.generation.contract_repair import ContractRepairInstructionalGenerator
from src.digital_twin.generation.instructional_source_state import SourceStateInstructionalGenerator
from src.digital_twin.llm import (
    LlmBudgetExceededError, LlmTimeoutError, LlmUnavailableError,
    LlmMalformedResponseError,
)
from tests.test_compact_instruction_generation import runtime, generate


@pytest.mark.asyncio
@pytest.mark.parametrize("error,code", [
    (LlmBudgetExceededError(), "budget-exceeded"),
    (LlmTimeoutError(), "timeout"),
    (LlmUnavailableError(), "unavailable"),
    (LlmMalformedResponseError(stage="schema-validation"), "provider_schema_validation"),
    (LlmMalformedResponseError(stage="private-stage-do-not-log",
        diagnostics={"private": "private-value-do-not-log"}), "malformed-response"),
])
async def test_initial_failure_preserves_code_without_changing_requests_or_decisions(runtime, error, code):
    requests = []

    class FailingClient:
        async def chat(self, messages, task):
            requests.append((task, [m.model_dump(mode="json") for m in messages]))
            raise error

    class PreviousDiagnostics(SourceStateInstructionalGenerator):
        def _failure_answer(self, error, *, response, started):
            # Pre-fix behavior for failures before final audit: generic compact code only.
            return ContractRepairInstructionalGenerator._failure_answer(
                self, error, response=response, started=started)

    def make(cls):
        return cls(FailingClient(), model_id="gpt-5.6-luna", audit_model="gpt-5.6-luna",
            bounded_contract_enabled=True, named_referent_context_enabled=True, clock=lambda: 1.0)

    runtime[0].tutoring.generator = make(PreviousDiagnostics)
    control = await generate(runtime)
    runtime[0].tutoring.generator = make(SourceStateInstructionalGenerator)
    candidate = await generate(runtime)

    assert len(requests) == 2 and requests[0] == requests[1]  # one attempt per run, no retry
    assert candidate.trace.policy_action == "safe-provider-failure"
    assert not candidate.citations and not candidate.atomic_claims
    assert f"generation_failure={code}" in candidate.trace.validation_scope
    assert "private-" not in candidate.model_dump_json()
    assert candidate.model_copy(update={"trace": candidate.trace.model_copy(update={
        "validation_scope": control.trace.validation_scope,
    })}) == control  # exact returned fields except bounded diagnostic text


@pytest.mark.asyncio
async def test_budget_diagnostic_survives_saved_graph_fallback(runtime):
    from tests.test_compact_instruction_generation import QUESTION
    rt = runtime[0]
    calls = []

    class Blocked:
        async def chat(self, messages, task):
            calls.append(task)
            raise LlmBudgetExceededError()

    rt.tutoring.generator = SourceStateInstructionalGenerator(
        Blocked(), model_id="gpt-5.6-luna", audit_model="gpt-5.6-luna",
        bounded_contract_enabled=True, named_referent_context_enabled=True)
    turn = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id,
        content=QUESTION, client_request_id="diagnostic-budget-control")
    saved = rt.repository.list_messages(rt.conversation_id)
    assert len(saved) == 2 and len(calls) == 1
    assert saved[-1].id == turn.tutor_message.id
    assert "generation_failure=budget-exceeded" in saved[-1].trace.validation_scope
    assert saved[-1].action == "safe-graph-failure"
    assert "verified reply" in saved[-1].content
