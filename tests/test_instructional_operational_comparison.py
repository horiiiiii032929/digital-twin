import json

import pytest

from scripts import run_instructional_operational_comparison as comparison
from scripts import run_operational_dialogue_development as operating
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmMalformedResponseError
from tests.test_paired_pedagogy_development import InstructionalContractClient


class OperatingContractClient(InstructionalContractClient):
    async def chat(self, messages, task):
        try:
            return await super().chat(messages, task)
        except AssertionError:
            raise LlmMalformedResponseError(stage="injected-unimplemented-autonomy-contract",
                usage=GenerationUsage(approximate_cost_usd=0)) from None


def test_exact_eight_balanced_specs_and_rejected_unplanned_candidate():
    specs = comparison.candidate_operating_specs("v9")
    assert len(specs) == len({row["id"] for row in specs}) == 8
    assert [row["version"] for row in specs] == ["v4", "v9"] * 4
    assert {row["persona"] for row in specs} == {"fast-learner", "low-receptivity"}
    with pytest.raises(ValueError):
        comparison.candidate_operating_specs("v8")


@pytest.mark.asyncio
async def test_actual_eight_histories_record_cohort_restart_and_consent(tmp_path):
    root = tmp_path / "contract"
    result = await comparison.run_candidate_operating_matrix(root, candidate="v9",
        transport_factory=OperatingContractClient)
    assert result["completed"] == 8
    assert result["decision"] == "contract-only"
    assert result["operational_counters"]["restart_count"] == 8
    assert result["operational_counters"]["consent_changes"] == 16
    assert result["operational_counters"]["consent_violations"] == 0
    assert result["source_files_unchanged"]
    for spec in result["manifest"]["histories"]:
        config = json.loads((root / spec["id"] / "configuration.jsonl").read_text())
        assert len(config["histories"]) == 8 and config["executed_history_count"] == 8
        assert config["instrument_id"] == comparison.INSTRUMENT_ID
    assert all(row["restart_checks"][0]["equal"] for row in result["histories"])
    assert all(row["restart_checks"][0]["before"]["messages"]["count"] > 0 for row in result["histories"])
    assert all(audit["observed_invariants_pass"] for audit in result["history_output_audits"])
    assert result["provider_attempts"] <= 5000
    assert not result["release_qualified"] and not result["learning_effect_measured"]


def test_restart_snapshot_detects_dropped_stored_records():
    class Repository:
        messages = []
        def list_messages(self, *_): return self.messages
        def get_learner_state(self, *_): return None
        def get_learner_belief_state_v2(self, *_): return None
        def list_outreach_preferences(self, *_): return []
        def list_autonomous_actions(self, *_, **__): return []
        def list_proactive_messages(self, *_, **__): return []
    class Item:
        def model_dump(self, **_): return {"id": "persisted-message", "content": "Stored answer"}
    from types import SimpleNamespace
    repository = Repository()
    runtime = SimpleNamespace(repository=repository, conversation_id="c", student_id="s", course_id="course")
    repository.messages = [Item()]
    before = operating.durable_restart_snapshot(runtime)
    repository.messages = []
    after = operating.durable_restart_snapshot(runtime)
    assert before != after and before["messages"]["count"] == 1 and after["messages"]["count"] == 0


@pytest.mark.asyncio
async def test_diagnostic_failure_still_closes_runtime_and_retains_result(tmp_path, monkeypatch):
    from tests.test_operational_dialogue_development import SyntheticQuestionClient
    original = operating.build_final_profile_runtime_factory
    closed = []
    def factory(*args, **kwargs):
        build = original(*args, **kwargs)
        def instrument(runtime):
            close = runtime.close_runtime
            def tracked_close(value):
                closed.append(value.conversation_id)
                return close(value)
            runtime.close_runtime = tracked_close
            restart = runtime.restart_runtime
            runtime.restart_runtime = lambda value: instrument(restart(value))
            return runtime
        return lambda *inner: instrument(build(*inner))
    monkeypatch.setattr(operating, "build_final_profile_runtime_factory", factory)
    def fail(_):
        raise RuntimeError("synthetic diagnostic failure")
    monkeypatch.setattr(operating, "durable_lineage_audit", fail)
    root = tmp_path / "diagnostic-failure"
    spec = comparison.candidate_operating_specs("v9")[0]
    result = await operating.run_history(root, spec, planner_client=SyntheticQuestionClient(), days=2,
        verify_restart=True)
    assert result["decision"] == "failed-operational-history"
    assert result["diagnostic_error_type"] == "RuntimeError"
    assert closed
    assert json.loads((root / "result.jsonl").read_text())["diagnostic_error_type"] == "RuntimeError"


def test_v10_is_explicit_and_v9_cohort_remains_reproducible():
    old = comparison.candidate_operating_specs("v9")
    new = comparison.candidate_operating_specs("v10")
    assert len(old) == len(new) == 8
    assert [row["version"] for row in old] == ["v4", "v9"] * 4
    assert [row["version"] for row in new] == ["v4", "v10"] * 4
    assert [(row["persona"], row["condition"], row["profile"], row["seed"]) for row in old] == [
        (row["persona"], row["condition"], row["profile"], row["seed"]) for row in new]


@pytest.mark.parametrize("outreach_id,expected", [("outreach-1", True), ("missing", False), (None, False)])
def test_outreach_audit_uses_actual_outreach_link_and_excludes_question_replies(tmp_path, outreach_id, expected):
    def turn(index, reason, response_id):
        return {"reason": reason, "responding_to_delivered_message_id": response_id,
            "turn": {"student_message": {"id": f"s{index}", "conversation_id": "c", "client_request_id": f"r{index}", "response_to_message_id": None},
                "tutor_message": {"id": f"t{index}", "conversation_id": "c", "response_to_message_id": f"s{index}", "action": "question"}}}
    turns = [turn(0, "initial", None), turn(1, "question-reply", "t0"), turn(2, "proactive-reply", outreach_id)]
    for name, rows in {"turns.jsonl": turns, "days.jsonl": [{"day": d} for d in range(1, 31)],
        "proactive.jsonl": [{"message": {"id": "outreach-1", "status": "delivered"}}]}.items():
        (tmp_path / name).write_text("\n".join(json.dumps(row) for row in rows))
    audit = comparison.audit_history_output(tmp_path, {"id": "history"})
    assert audit["outreach_reply_count"] == 1
    assert audit["outreach_replies_link_delivered_message"] is expected
    assert audit["observed_invariants_pass"] is expected
    assert audit["reactive_replies_link_actual_prior_question"]


@pytest.mark.asyncio
@pytest.mark.parametrize("candidate", ["v10-sol-low", "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"])
async def test_role_variant_eight_histories_preserve_model_reasoning_after_restart(tmp_path, candidate):
    from scripts.run_final_profile_longitudinal import ContractFailureClient
    class ExplicitContract(ContractFailureClient):
        def __init__(self, config):
            self.experimental_transport_configuration = dict(config)
    def transport(version, role=None, config=None):
        if role is None:
            return ContractFailureClient()
        return ExplicitContract(config)
    result = await comparison.run_candidate_operating_matrix(tmp_path / "variant", candidate=candidate, transport_factory=transport)
    assert result["completed"] == 8 and result["decision"] == "contract-only"
    assert result["manifest"]["maximum_provider_calls"] == 9600
    assert result["manifest"]["maximum_reserved_usd"] == 1536
    assert result["manifest"]["effective_inner_history_maximum_calls"] == 4800
    for history in result["histories"]:
        configs = history["observed_generation_configurations"]
        assert len(configs) == 2 and configs[0] == configs[1]
        if history["history"]["version"] == candidate:
            assert configs[0]["model"] == comparison.experimental_tutoring_configuration(candidate)["model"]
            assert configs[0]["role_configuration"]["planner"] == {"model": "gpt-5.6-luna", "reasoning_effort": "low", "output_cap": 3000}
    assert any("generation" in path.name for path in (tmp_path / "variant").glob("provider-*.jsonl"))


def test_observed_operating_role_mismatch_rejects_even_same_algorithm_id():
    from types import SimpleNamespace
    selection = comparison.experimental_tutoring_configuration("v10-sol-low")
    runtime = SimpleNamespace(tutoring=SimpleNamespace(generator=SimpleNamespace(
        model_id="gpt-5.6-sol", implementation_id=selection["implementation_id"], client=object())))
    with pytest.raises(RuntimeError, match="role configuration"):
        operating.operational_generation_configuration(runtime, selection)
