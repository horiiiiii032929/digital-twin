import json

import pytest

from scripts import run_factual_revision_controls as runner
from scripts.teaching_profile_responsiveness_packet import PROFILES
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmResponse


def control_packet():
    public = {"question": "Which input is being discussed?", "profile_values": PROFILES["explanatory"],
        "history": [], "sources": [{"id": "S1", "label": "Cobalt gate", "text": "Cobalt gate opens for input above8."}],
        "draft": {"action": "clarify", "units": [], "missing_details": []}}
    return {"packet_id": "revision-controls-test-v1", "contexts": [
        {"id": "opaque-1", "family": "NEVER_SEND_FAMILY", "public": public,
         "gold": {"draft_adequate": True, "required_meanings": ["NEVER_SEND_GOLD"]}},
        {"id": "opaque-2", "family": "NEVER_SEND_FAMILY", "public": public,
         "gold": {"draft_adequate": False}}]}


class EchoRevision:
    def __init__(self, *, unknown=False, invalid_boundary=False, mutate=None, bounded=False):
        self.messages = []
        self.tasks = []
        self.bounded = bounded
        self.unknown, self.invalid_boundary, self.mutate = unknown, invalid_boundary, mutate

    async def chat(self, messages, task):
        assert task in ({runner.TASK, "question_specific_bounded_revision"} if self.bounded else {runner.TASK})
        self.tasks.append(task)
        self.messages.append(messages)
        payload = json.loads(messages[-1].content)
        assert "NEVER_SEND" not in json.dumps(payload)
        assert set(payload["approved_teaching_profile"]) == {"configuration_id", "content_sha256", "preferences", "authority"}
        assert len(payload["approved_teaching_profile"]["content_sha256"]) == 64
        proposal = payload["draft_proposal"]
        if self.invalid_boundary:
            proposal = {"action": "clarify", "units": [{"kind": "explanation", "text": "It opens.", "source_ids": ["S1"]}], "missing_details": []}
        if self.mutate:
            self.mutate()
        return LlmResponse(content=json.dumps(proposal), provider_model=runner.MODEL,
            usage=GenerationUsage(input_tokens=20, output_tokens=10, total_tokens=30,
                approximate_cost_usd=None if self.unknown else .00028))


@pytest.mark.asyncio
async def test_actual_revision_and_render_preserve_clarify_prefix_without_gold(tmp_path):
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(control_packet()))
    client = EchoRevision()
    result = await runner.run(tmp_path / "output", path, injected_client=client)
    assert result["completed"] == 2 and result["provider_attempts"] == 2
    assert result["source_files_unchanged"]
    for row in result["cases"]:
        assert row["original_render"]["completed"] and row["revised_render"]["completed"]
        assert row["revised_render"]["answer"]["content"].startswith("Please clarify")
        assert row["provider_attempts"] == 1
    with pytest.raises(FileExistsError):
        await runner.run(tmp_path / "output", path, injected_client=client)


@pytest.mark.asyncio
async def test_typed_boundary_factual_units_fail_actual_composition(tmp_path):
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(control_packet()))
    result = await runner.run(tmp_path / "output", path, injected_client=EchoRevision(invalid_boundary=True))
    assert result["completed"] == 0 and result["provider_failures"] == 0
    assert all(r["revised_render"]["error_code"] == "boundary_contains_factual_units" for r in result["cases"])


@pytest.mark.asyncio
async def test_unknown_cost_stops_later_controls_without_dropping_them(tmp_path):
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(control_packet()))
    client = EchoRevision(unknown=True)
    result = await runner.run(tmp_path / "output", path, injected_client=client)
    assert len(result["cases"]) == 2 and result["completed"] == 0
    assert result["provider_attempts"] == 1 and len(client.messages) == 1
    assert result["unknown_cost_calls"] == 1 and result["provider_stopped"]


@pytest.mark.asyncio
async def test_original_packet_change_invalidates_end_snapshot(tmp_path):
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(control_packet()))
    client = EchoRevision(mutate=lambda: path.write_text('{"changed":true}'))
    result = await runner.run(tmp_path / "output", path, injected_client=client)
    assert not result["source_files_unchanged"]
    assert result["source_hash_errors"]["original_packet"] == "changed"


@pytest.mark.asyncio
async def test_live_guard_runs_before_input_or_output(tmp_path, monkeypatch):
    def reject(*args):
        raise PermissionError("blocked")
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", reject)
    with pytest.raises(PermissionError):
        await runner.run(tmp_path / "output", tmp_path / "missing.json", execute=True)
    assert not (tmp_path / "output").exists()


def test_three_roles_partition_exact_total_and_preserve_two_role_default(tmp_path):
    from scripts.recorded_generation_roles import create_recorded_generation_roles
    from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
    new = create_recorded_generation_roles(experimental_tutoring_configuration("v12-luna-sol"),
        tmp_path / "new", maximum_calls=12, maximum_cost_usd=1.92)
    assert set(new.role_clients) == {"planner", "generation", "revision"}
    assert sum(c.maximum_calls for c in new.role_clients.values()) == 12
    assert sum(c.maximum_cost_usd for c in new.role_clients.values()) == pytest.approx(1.92)
    assert all(c.maximum_calls == 4 for c in new.role_clients.values())
    old = create_recorded_generation_roles(experimental_tutoring_configuration("v11-luna-low"),
        tmp_path / "old", maximum_calls=12, maximum_cost_usd=1.92)
    assert all(c.maximum_calls == 6 for c in old.role_clients.values())


@pytest.mark.asyncio
async def test_unknown_revision_cost_stops_other_role_dispatch(tmp_path):
    from scripts.recorded_generation_roles import create_recorded_generation_roles
    from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
    from src.digital_twin.generation.factual_revision import revise_instructional_proposal
    from src.digital_twin.llm import LlmBudgetExceededError, LlmMessage
    transport = EchoRevision(unknown=True)
    helper = create_recorded_generation_roles(experimental_tutoring_configuration("v12-luna-sol"),
        tmp_path / "roles", maximum_calls=12, maximum_cost_usd=1.92,
        transport_factory=lambda role, config: transport)
    payload, draft = runner.public_revision_input(control_packet()["contexts"][0])
    with pytest.raises(ValueError, match="reservation contract"):
        await revise_instructional_proposal(helper, payload=payload, draft=draft)
    with pytest.raises(LlmBudgetExceededError):
        await helper.chat([LlmMessage(role="user", content="{}")], "reactive_tutoring_intent")
    assert helper.attempts == 1 and len(transport.messages) == 1
    assert helper.role_clients["planner"].attempts == 0


@pytest.mark.asyncio
async def test_v13_selects_actual_restricted_task_and_keeps_v12_default(tmp_path):
    path = tmp_path / "packet.json"
    packet = control_packet()
    packet["contexts"][0]["public"] = json.loads(json.dumps(packet["contexts"][0]["public"]))
    packet["contexts"][0]["public"]["draft"] = {"action": "question", "units": [
        {"kind": "elicitation", "text": "Which condition should you inspect?", "source_ids": []}], "missing_details": []}
    path.write_text(json.dumps(packet))
    client = EchoRevision(bounded=True)
    result = await runner.run(tmp_path / "bounded", path, candidate="v13", injected_client=client)
    assert result["completed"] == 2
    assert client.tasks == ["question_specific_bounded_revision", runner.TASK]
    manifest = json.loads((tmp_path / "bounded/manifest.json").read_text())
    assert manifest["maximum_calls"] == 80 and manifest["maximum_reserved_usd"] == 12.8
    old = EchoRevision()
    await runner.run(tmp_path / "old", path, injected_client=old)
    assert old.tasks == [runner.TASK, runner.TASK]


@pytest.mark.asyncio
async def test_v13_rejects_factual_unit_bypass_in_restricted_revision(tmp_path):
    path = tmp_path / "packet.json"
    packet = control_packet()
    for context in packet["contexts"]:
        context["public"]["draft"] = {"action": "question", "units": [
            {"kind": "elicitation", "text": "Which condition matters?", "source_ids": []}], "missing_details": []}
    path.write_text(json.dumps(packet))
    result = await runner.run(tmp_path / "bounded", path, candidate="v13",
        injected_client=EchoRevision(bounded=True, invalid_boundary=True))
    assert result["completed"] == 0 and result["provider_attempts"] == 2
    assert all("revised_render" not in row for row in result["cases"])


@pytest.mark.asyncio
async def test_v12_default_rejects_80_control_packet_before_output(tmp_path):
    path = tmp_path / "packet.json"
    packet = control_packet()
    packet["contexts"] = [{**packet["contexts"][0], "id": f"opaque-{index}"} for index in range(80)]
    path.write_text(json.dumps(packet))
    with pytest.raises(ValueError, match="candidate-sized"):
        await runner.run(tmp_path / "old", path, injected_client=EchoRevision())
    assert not (tmp_path / "old").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("repair", [False, True])
@pytest.mark.parametrize("candidate", ["v14", "v14-medium", "v15"])
async def test_v14_records_assessment_and_honest_authored_origin(tmp_path, repair, candidate):
    from tests.test_conditional_revision_generation import decision
    class Conditional:
        async def chat(self, messages, task):
            assert task == "question_specific_conditional_revision"
            public = json.loads(messages[-1].content)
            assert "NEVER_SEND" not in json.dumps(public)
            value = decision(public["draft_proposal"], "clarification") if repair else decision()
            return LlmResponse(content=json.dumps(value), provider_model=runner.MODEL,
                usage=GenerationUsage(input_tokens=20, output_tokens=10, total_tokens=30, approximate_cost_usd=.00028))
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(control_packet()))
    result = await runner.run(tmp_path / "conditional", path, candidate=candidate, injected_client=Conditional())
    assert result["completed"] == 2 and result["provider_attempts"] == 2
    for row in result["cases"]:
        assert len(row["assessment_input_sha256"]) == len(row["assessed_draft_sha256"]) == 64
        assert row["original_proposal_preserved"]
        assert row["response"]["provider_model"] == "gpt-5.6-sol"
        assert row["revised_render"]["answer"]["trace"]["provider_model"] == (
            "gpt-5.6-sol" if repair else "researcher-authored-no-provider")
    manifest = json.loads((tmp_path / "conditional/manifest.json").read_text())
    assert manifest["maximum_calls"] == 112 and manifest["maximum_reserved_usd"] == 17.92
    assert manifest["reasoning_effort"] == ("medium" if candidate in {"v14-medium", "v15"} else "low")
    assert result["source_files_unchanged"]


def test_medium_changes_only_revision_effort_in_explicit_runtime_configuration():
    from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
    from services.llm import OpenAiResponsesClient
    low = experimental_tutoring_configuration('v14-luna-sol')
    medium = experimental_tutoring_configuration('v14-luna-sol-medium')
    assert low['runtime_flags'] == medium['runtime_flags']
    assert low['implementation_id'] == medium['implementation_id']
    for role in ('planner', 'generation'):
        assert low['role_configuration'][role] == medium['role_configuration'][role]
    assert medium['role_configuration']['revision'] == {**low['role_configuration']['revision'], 'reasoning_effort': 'medium'}
    client = OpenAiResponsesClient('gpt-5.6-sol', max_output_tokens=3000, reasoning_effort='medium', experimental_sol_enabled=True)
    assert client._payload([], 'question_specific_conditional_revision')['reasoning'] == {'effort': 'medium'}
