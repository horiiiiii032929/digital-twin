from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.generation import DeterministicEvidenceSetGroundedGenerator
from src.digital_twin.grounding import DominanceScopedAmbiguitySafeEvidenceGateV3
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmBudgetExceededError, LlmMessage, LlmResponse
from src.digital_twin.student import GuardedPolicyValuePlanner
from src.digital_twin.student.autonomy_service import BoundedStrategyGroundedWordingGenerator

CARDS = (ConceptCardV1(
    "fresh-test-semaphore", "semaphore permits",
    "A counting semaphore limits concurrent access by granting permits before entry and returning permits on exit.",
    "Explain how semaphore permits limit concurrent access.",
),)


class FakeClient:
    def __init__(self):
        self.calls = 0

    async def chat(self, messages, task):
        self.calls += 1
        return LlmResponse(
            content="{}", provider_model="gpt-5.6-luna", provider_revision="test-revision",
            usage=GenerationUsage(input_tokens=10, output_tokens=5, total_tokens=15, approximate_cost_usd=0.001),
        )


def make_runtime(tmp_path, client, **kwargs):
    factory = build_final_profile_runtime_factory(
        tmp_path, "t1-v2-autonomous", concept_cards=CARDS, fixture_id="fresh-runtime-test-v1",
        planner_client=client, **kwargs,
    )
    return factory(SimpleNamespace(case_id="fresh-case"), VirtualUtcClock(datetime(2026, 9, 5, tzinfo=UTC)))


def test_final_factory_binds_production_components_without_network(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = FakeClient()
    runtime = make_runtime(tmp_path, client)
    try:
        assert runtime.tutoring.profile_id == "student-tutor-r1-local-final"
        assert runtime.tutoring.retriever_selection.implementation.implementation_id == "bm25-v1"
        assert isinstance(runtime.tutoring.generator, DeterministicEvidenceSetGroundedGenerator)
        assert isinstance(runtime.tutoring.evidence_gate, DominanceScopedAmbiguitySafeEvidenceGateV3)
        assert isinstance(runtime.autonomy.graph.planner, GuardedPolicyValuePlanner)
        assert isinstance(runtime.autonomy.graph.generator, BoundedStrategyGroundedWordingGenerator)
        assert runtime.autonomy.graph.generator.model_id == "gpt-5.6-luna"
        assert client.calls == 0
    finally:
        runtime.close_runtime(runtime)


@pytest.mark.asyncio
async def test_restart_preserves_case_budget_usage_identity_and_conversation(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = FakeClient()
    runtime = make_runtime(tmp_path, client, maximum_case_calls=2)
    messages = [LlmMessage(role="user", content="synthetic budget test")]
    try:
        await runtime.autonomy.graph.generator.strategy_client.chat(messages, "runtime-budget-test")
        original_conversation = runtime.conversation_id
        runtime = runtime.restart_runtime(runtime)
        assert runtime.conversation_id == original_conversation
        assert runtime.repository.get_conversation(original_conversation) is not None
        await runtime.autonomy.graph.generator.strategy_client.chat(messages, "runtime-budget-test")
        with pytest.raises(LlmBudgetExceededError):
            await runtime.autonomy.graph.generator.strategy_client.chat(messages, "runtime-budget-test")
        metrics = await runtime.collect_metrics(runtime)
        assert metrics.provider_calls == 2
        assert metrics.total_tokens == 30
        assert metrics.cost_usd == pytest.approx(0.002)
        assert all(row.provider_revision == "test-revision" for row in metrics.call_records)
        assert client.calls == 2
    finally:
        runtime.close_runtime(runtime)


def test_existing_runtime_is_never_overwritten(tmp_path):
    runtime = make_runtime(tmp_path, FakeClient())
    runtime.close_runtime(runtime)
    with pytest.raises(FileExistsError):
        make_runtime(tmp_path, FakeClient())


def test_explicit_terra_comparator_uses_truthful_model_and_rejects_autonomous_scope(tmp_path):
    from types import SimpleNamespace
    from datetime import UTC, datetime
    from scripts.run_final_profile_longitudinal import CARDS, ContractFailureClient
    from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
    from src.digital_twin.clock import VirtualUtcClock
    factory = build_final_profile_runtime_factory(tmp_path / "terra", "t1-v2-reactive",
        concept_cards=CARDS, fixture_id="terra-reactive-comparator", planner_client=ContractFailureClient(),
        teaching_profile_context_enabled=True, question_specific_generation_enabled=True,
        experimental_planner_model_id="gpt-5.6-terra")
    runtime = factory(SimpleNamespace(case_id="terra-identity"), VirtualUtcClock(datetime(2026, 9, 6, tzinfo=UTC)))
    try:
        assert runtime.tutoring.generator.model_id == "gpt-5.6-terra"
        assert runtime.tutoring.tutoring_graph.generator_model_id == "gpt-5.6-terra"
    finally:
        runtime.close_runtime(runtime)
    with pytest.raises(ValueError, match="reactive generation"):
        build_final_profile_runtime_factory(tmp_path / "unsupported", "t1-v2-autonomous",
            concept_cards=CARDS, fixture_id="terra-autonomy-not-evaluated", planner_client=ContractFailureClient(),
            question_specific_generation_enabled=True, experimental_planner_model_id="gpt-5.6-terra")
