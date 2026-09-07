import json

import pytest

from scripts import run_teaching_profile_responsiveness_development as runner
from scripts.run_final_profile_longitudinal import MODEL
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmResponse


class MalformedClient:
    async def chat(self, messages, task):
        return LlmResponse(content="{}", provider_model=MODEL, provider_revision="contract-only",
            usage=GenerationUsage(input_tokens=10, output_tokens=5, total_tokens=15, approximate_cost_usd=0.001))


@pytest.mark.asyncio
async def test_actual_factory_contract_retains_all_24_arms_and_delivered_content(tmp_path):
    output = tmp_path / "new-run"
    result = await runner.run(output, contract=True, injected_client=MalformedClient())
    assert len(result["cases"]) == 24
    assert result["case_errors"] == 0, [(r["id"], r.get("error")) for r in result["cases"] if "error" in r]
    assert result["release_qualified"] is False
    assert result["live_model_successes"] == 0
    assert all("response" in row for row in result["cases"])
    assert all(row["response"]["tutor_message"]["content"] for row in result["cases"])
    assert len((output / "cases.jsonl").read_text().splitlines()) == 24
    assert result["manifest"]["manifest_sha256"]
    assert len(list((output / "runtimes").glob("*/*/runtime.sqlite3"))) == 24
    assert result["boundary_violations"] is None
    with pytest.raises(FileExistsError):
        await runner.run(output, contract=True, injected_client=MalformedClient())


@pytest.mark.asyncio
async def test_live_checks_exact_instrument_authorization_before_creating_output(tmp_path, monkeypatch):
    seen = []
    def deny(instrument, operation):
        seen.append((instrument, operation))
        raise PermissionError("not authorized")
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", deny)
    with pytest.raises(PermissionError):
        await runner.run(tmp_path / "absent", contract=False)
    assert seen == [("teaching-profile-responsiveness-development-001", "external_model_evaluation")]
    assert not (tmp_path / "absent").exists()


@pytest.mark.asyncio
async def test_every_runtime_failure_is_persisted(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("synthetic setup failure")
    monkeypatch.setattr(runner, "build_final_profile_runtime_factory", fail)
    result = await runner.run(tmp_path / "failures", contract=True)
    assert result["case_errors"] == 24
    rows = [json.loads(line) for line in (tmp_path / "failures/cases.jsonl").read_text().splitlines()]
    assert all(row["error"] == "ValueError" for row in rows)
    assert result["provider_attempts"] == 0


@pytest.mark.asyncio
async def test_v10_actual_context_intervention_and_provider_payload_binding(tmp_path):
    from tests.test_paired_pedagogy_development import InstructionalContractClient
    result = await runner.run(tmp_path / "v10", contract=True,
        injected_client=InstructionalContractClient("v10"), candidate="v10",
        maximum_calls=100, maximum_cost_usd=3)
    assert result["case_errors"] == 0
    assert len(result["cases"]) == 24
    assert result["source_files_unchanged"] is True
    assert result["manifest"]["output_cap"] == 3000
    assert (tmp_path / "v10/source-snapshot.zip").is_file()
    assert all(row["observed_generator_id"] == "question-specific-profile-grounded-v10" for row in result["cases"])
    binding = result["profile_request_binding"]
    assert binding["eligible_requests"] >= 12
    assert binding["all_dispatched_bindings_match"] is True
    assert any(row["status"] == "untested-no-generation-request" for row in binding["cases"])
    assert result["boundary_violations"] is None
    assert result["release_qualified"] is False


@pytest.mark.asyncio
async def test_v10_rejects_budget_that_cannot_cover_all_cases(tmp_path):
    with pytest.raises(ValueError, match="full24-case"):
        await runner.run(tmp_path / "insufficient", contract=True, candidate="v10")
    assert not (tmp_path / "insufficient").exists()


def test_profile_binding_detects_wrong_profile_in_actual_request(tmp_path):
    path = tmp_path / "provider.jsonl"
    path.write_text(json.dumps({"case": "x", "status": "started", "task": "question_specific_typed_instruction",
        "request_sha256": "sample", "messages": [{"role": "user", "content": json.dumps({
            "approved_teaching_profile": {"preferences": runner.PROFILES["explanatory"]}})}]}) + "\n")
    result = runner.inspect_profile_binding(path, [{"id": "x", "condition": "context-on", "profile": "socratic"}])
    assert result["eligible_requests"] == 1
    assert result["all_dispatched_bindings_match"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["v10-luna-medium", "v10-sol-low", "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol"])
async def test_generation_variants_bind_actual_roles_and_profile_payloads(tmp_path, variant):
    from tests.test_paired_pedagogy_development import InstructionalContractClient

    selection = runner.experimental_tutoring_configuration(variant)

    class RoleFixture(InstructionalContractClient):
        def __init__(self, model):
            super().__init__("v10")
            self.model = model

        async def chat(self, messages, task):
            if task == "question_specific_conditional_revision":
                from tests.test_conditional_revision_generation import decision
                from src.digital_twin.llm import LlmResponse
                from tests.test_factual_revision_generation import usage
                return LlmResponse(content=json.dumps(decision()), provider_model="gpt-5.6-sol", usage=usage())
            response = await super().chat(messages,
                "question_specific_typed_instruction" if task in {"question_specific_factual_revision", "question_specific_bounded_revision"} else task)
            return response.model_copy(update={"provider_model": self.model})

    result = await runner.run(tmp_path / variant, contract=True, candidate=variant,
        maximum_calls=150 if variant in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol"} else 100,
        maximum_cost_usd=30 if variant in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol"} else 20,
        injected_client={role: RoleFixture(config["model"])
            for role, config in selection["role_configuration"].items()})
    assert result["case_errors"] == 0
    assert len(result["cases"]) == 24
    assert result["live_model_successes"] == 0
    assert result["profile_request_binding"]["all_dispatched_bindings_match"] is True
    assert result["provider_attempts"] == sum(result["role_attempts"].values())
    assert result["provider_attempts"] <= result["manifest"]["maximum_calls"]
    if variant in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol"}:
        assert result["revision_profile_request_binding"]["all_dispatched_bindings_match"]
        assert result["role_attempts"]["revision"] > 0
        assert result["manifest"]["role_call_allocations"] == {role: 50 for role in selection["role_configuration"]}
        assert sum(result["manifest"]["role_cost_allocations"].values()) == 30
    assert result["manifest"]["model"] == selection["model"]
    assert result["manifest"]["planner_model"] == MODEL
    assert all(row["observed_generation_model_id"] == selection["model"] for row in result["cases"])
    for role, name in result["role_ledger_paths"].items():
        records = [json.loads(line) for line in (tmp_path / variant / name).read_text().splitlines()]
        started = [row for row in records if row["status"] == "started"]
        assert started
        config = selection["role_configuration"][role]
        assert all(row["requested_model"] == config["model"]
            and row["requested_reasoning_effort"] == config["reasoning_effort"]
            and row["requested_output_cap"] == 3000 for row in started)
        assert all((row["task"] == "question_specific_typed_instruction") == (role == "generation")
            for row in started)


@pytest.mark.asyncio
async def test_role_variant_rejects_insufficient_partitioned_budget_before_output(tmp_path):
    with pytest.raises(ValueError, match="requires100 calls"):
        await runner.run(tmp_path / "short", contract=True, candidate="v10-sol-low",
            maximum_calls=100, maximum_cost_usd=3)
    assert not (tmp_path / "short").exists()
