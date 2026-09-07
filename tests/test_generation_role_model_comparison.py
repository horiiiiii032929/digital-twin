import json

import pytest

from scripts import run_generation_role_model_comparison as runner
from scripts.recorded_generation_roles import create_recorded_generation_roles
from scripts.run_final_profile_longitudinal import RecordedRunClient
from services.llm import BudgetedLlmClient, OpenAiResponsesClient
from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter
from src.digital_twin.evaluation.experimental_tutoring_candidate import (
    experimental_tutoring_configuration,
)
from src.digital_twin.llm import LlmConfigurationError, LlmIdentityDriftError
from src.digital_twin.model_policy import ModelPolicyError
from tests.test_paired_pedagogy_development import InstructionalContractClient, packet


class RoleFixture(InstructionalContractClient):
    def __init__(self, config):
        super().__init__("v10")
        self.experimental_transport_configuration = dict(config)
        self.requests = []

    async def chat(self, messages, task):
        self.requests.append((messages, task))
        if task == "question_specific_conditional_revision":
            from tests.test_conditional_revision_generation import decision
            from src.digital_twin.llm import LlmResponse
            from tests.test_factual_revision_generation import usage
            return LlmResponse(content=json.dumps(decision()), provider_model="gpt-5.6-sol", usage=usage())
        result = await super().chat(messages,
            "question_specific_typed_instruction" if task in {"question_specific_factual_revision", "question_specific_bounded_revision"} else task)
        return result.model_copy(
            update={
                "provider_model": self.experimental_transport_configuration["model"]
            }
        )


def fixture(version, role):
    return RoleFixture(
        experimental_tutoring_configuration(version)["role_configuration"][role]
    )


def test_sol_requires_explicit_experimental_opt_in_and_serializer_matches(tmp_path):
    with pytest.raises(ModelPolicyError):
        OpenAiResponsesClient("gpt-5.6-sol")
    client = OpenAiResponsesClient(
        "gpt-5.6-sol",
        max_output_tokens=3000,
        reasoning_effort="low",
        experimental_sol_enabled=True,
    )
    with pytest.raises(ModelPolicyError):
        OpenAiResponsesClient("invented-model", experimental_sol_enabled=True)
    with pytest.raises(ValueError, match="reasoning"):
        RecordedRunClient(
            OpenAiResponsesClient(
                "gpt-5.6-luna", max_output_tokens=3000, reasoning_effort="medium"
            ),
            tmp_path / "bad.jsonl",
            maximum_calls=2,
            maximum_cost_usd=1,
            network_mode="contract",
            reservation_usd=0.16,
            max_output_tokens=3000,
        )
    recorded = RecordedRunClient(
        client,
        tmp_path / "sol.jsonl",
        maximum_calls=2,
        maximum_cost_usd=1,
        network_mode="contract",
        reservation_usd=0.16,
        max_output_tokens=3000,
        expected_model="gpt-5.6-sol",
        experimental_sol_enabled=True,
    )
    assert recorded.serializer.model == "gpt-5.6-sol"
    assert experimental_tutoring_configuration("v10")["model"] == "gpt-5.6-luna"


@pytest.mark.asyncio
async def test_actual_three_arm_histories_restart_identity_and_no_sibling_read(
    tmp_path,
):
    p = tmp_path / "inputs" / "development.json"
    p.parent.mkdir()
    p.write_text(json.dumps(packet()))
    (p.parent / "build_packet.py").write_text("SEALED_BUILDER_NEVER_ARCHIVE")
    (p.parent / "confirmation.json").write_text("SEALED_PACKET_NEVER_ARCHIVE")
    result = await runner.run(
        tmp_path / "run", packet(), packet_path=p, transport_factory=fixture
    )
    assert len(result["histories"]) == 3
    assert all(h["completed"] and h["restarts"] == 1 for h in result["histories"])
    for h in result["histories"]:
        config = experimental_tutoring_configuration(h["version"])
        assert h["observed_generation_model"] == config["model"]
        assert h["restarted_role_configurations"] == [config["role_configuration"]]
    assert result["source_files_unchanged"] and result["semantic_quality_pass"] is None
    assert sorted(x.name for x in (tmp_path / "run/input-artifacts").iterdir()) == [
        "development.json"
    ]
    for path in (tmp_path / "run").glob("provider-*.jsonl"):
        for row in map(json.loads, path.read_text().splitlines()):
            if row.get("status") != "completed":
                continue
            assert row["requested_reasoning_effort"] == (
                "medium" if "luna-medium-generation" in path.name else "low"
            )
            assert row["returned_model"] == (
                "gpt-5.6-sol" if "sol-low-generation" in path.name else "gpt-5.6-luna"
            )
    with pytest.raises(FileExistsError):
        await runner.run(tmp_path / "run", packet(), transport_factory=fixture)


@pytest.mark.asyncio
async def test_router_rejects_unknown_role_task_identity_and_preserves_budgets(
    tmp_path,
):
    selection = experimental_tutoring_configuration("v10-sol-low")
    router = create_recorded_generation_roles(
        selection,
        tmp_path / "provider",
        maximum_calls=4,
        maximum_cost_usd=1,
        transport_factory=lambda role, config: RoleFixture(config),
    )
    with pytest.raises(LlmConfigurationError):
        router.role_for_task("unregistered_task")
    with pytest.raises(LlmConfigurationError):
        router.client_for_role("other")
    with pytest.raises(ValueError):
        ExperimentalGenerationRoleRouter(
            planner_client=None, generation_client=None, role_configuration={}
        )
    assert router.role_for_task("hierarchical_autonomy_plan") == "planner"
    assert router.role_for_task("question_specific_typed_instruction") == "generation"
    bad = router.generation_client.client
    bad.experimental_transport_configuration["model"] = "gpt-5.6-luna"
    from src.digital_twin.llm import LlmMessage

    messages = [
        LlmMessage(
            role="user",
            content=json.dumps({"evidence": [{"citation_id": "S1", "text": "Rule"}]}),
        )
    ]
    budget = BudgetedLlmClient(router, max_calls=4, max_cost_usd=1)
    with pytest.raises(LlmIdentityDriftError):
        await budget.chat(messages, "question_specific_typed_instruction")
    assert (
        router.attempts == 1 and router.records[0]["usage"]["approximate_cost_usd"] == 0
    )


@pytest.mark.asyncio
async def test_insufficient_role_budget_fails_before_any_output(tmp_path):
    with pytest.raises(ValueError):
        await runner.run(
            tmp_path / "absent", packet(), maximum_calls=10, maximum_cost_usd=1
        )
    assert not (tmp_path / "absent").exists()


@pytest.mark.asyncio
async def test_unknown_generation_usage_stops_other_role_before_dispatch(tmp_path):
    from src.digital_twin.grounding.models import GenerationUsage
    from src.digital_twin.llm import LlmMessage, LlmBudgetExceededError

    class UnknownUsage(RoleFixture):
        async def chat(self, messages, task):
            response = await super().chat(messages, task)
            return response.model_copy(update={"usage": GenerationUsage()})

    selection = experimental_tutoring_configuration("v10-sol-low")
    created = {}

    def transport(role, config):
        created[role] = (UnknownUsage if role == "generation" else RoleFixture)(config)
        return created[role]

    router = create_recorded_generation_roles(selection, tmp_path / "unknown",
        maximum_calls=10, maximum_cost_usd=2, transport_factory=transport)
    messages = [LlmMessage(role="user", content=json.dumps({"evidence": [{"citation_id": "S1", "text": "Rule"}]}))]
    with pytest.raises(ValueError, match="reservation"):
        await router.chat(messages, "question_specific_typed_instruction")
    assert router.stopped and router.attempts == 1
    with pytest.raises(LlmBudgetExceededError):
        await router.chat(messages, "reactive_tutoring_intent")
    assert not created["planner"].requests and router.attempts == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"])
async def test_explicit_single_arm_uses_declared_budget_and_actual_prompt(tmp_path, variant):
    created = {}

    def transport(version, role):
        client = fixture(version, role)
        created[role] = client
        return client

    result = await runner.run(tmp_path / "v11", packet(), versions=(variant,),
        maximum_calls=24, maximum_cost_usd=4, transport_factory=transport)
    assert len(result["histories"]) == 1
    history = result["histories"][0]
    assert history["completed"] and history["restarts"] == 1
    expected_id = experimental_tutoring_configuration(variant)["implementation_id"]
    assert history["observed_generator_id"] == expected_id
    assert history["restarted_generator_ids"] == [expected_id]
    assert history["observed_generation_model"] == "gpt-5.6-luna"
    assert set(result["arms"]) == {variant}
    assert created["generation"].requests
    assert all(task == "question_specific_typed_instruction"
        for _, task in created["generation"].requests)
    manifest = json.loads((tmp_path / "v11/manifest.json").read_text())
    assert manifest["maximum_calls"] == 24
    assert manifest["candidate_ids"] == {variant: expected_id}
    if variant in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"}:
        assert manifest["conservative_planned_calls"] == manifest["planned_turns"] * 5
        assert created["revision"].requests
        assert all(task in {"question_specific_factual_revision", "question_specific_bounded_revision", "question_specific_conditional_revision"} for _, task in created["revision"].requests)
        assert set(result["arms"][variant]["roles"]) == {"planner", "generation", "revision"}
    assert "research/04_experiments/2026-09-06-evidence-strength-generation-plan.md" in manifest["source_hashes_start"]
    assert result["source_files_unchanged"]


@pytest.mark.asyncio
@pytest.mark.parametrize("versions", [(), ("v11-luna-low", "v11-luna-low"), ("unknown",)])
async def test_invalid_explicit_selections_fail_before_output(tmp_path, versions):
    with pytest.raises(ValueError, match="declared candidates"):
        await runner.run(tmp_path / "absent", packet(), versions=versions)
    assert not (tmp_path / "absent").exists()
