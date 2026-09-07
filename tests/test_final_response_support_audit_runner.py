"""Injected orchestration tests; injected verdicts do not establish audit efficacy."""
import json

import pytest

from scripts import run_final_response_support_audit as runner
from tests.test_final_response_audit import Audit, Repair
from tests.test_factual_revision_controls import control_packet


def packet(tmp_path):
    value = control_packet()
    for c in value["contexts"]:
        c["public"]["draft"] = {"action": "instruction", "units": [{"kind": "explanation",
            "text": "The gate opens for input above8.", "source_ids": ["S1"]}], "missing_details": []}
    path = tmp_path/"packet.json"
    path.write_text(json.dumps(value))
    return path


@pytest.mark.asyncio
async def test_pass_preserves_original_and_never_exposes_gold(tmp_path):
    audit, repair = Audit(), Repair()
    result = await runner.run(tmp_path/"run", packet(tmp_path), bank="fresh",
        injected_audit_client=audit, injected_repair_client=repair)
    assert result["provider_attempts"] == 4
    assert result["source_files_unchanged"]
    assert result["role_attempts"] == {"audit": 4, "repair": 0}
    for case in result["cases"]:
        for arm in ("C1", "C2"):
            assert case[arm]["outcome"] == "passed"
            assert case[arm]["delivered_text"] == case["C0"]["delivered_text"]
    assert not repair.calls
    assert "NEVER_SEND" not in json.dumps([[m.model_dump() for m in messages] for messages, task in audit.calls])
    ledger = [json.loads(line) for line in (tmp_path/"run"/"provider-audit.jsonl").read_text().splitlines()]
    assert all(r["requested_reasoning_effort"] == "high" and r["requested_output_cap"] == 3000 for r in ledger)


@pytest.mark.asyncio
async def test_one_repair_reaudited_and_role_limits(tmp_path):
    result = await runner.run(tmp_path/"run", packet(tmp_path), bank="fresh", concurrency=1,
        injected_audit_client=Audit(rejects=(2,)), injected_repair_client=Repair())
    assert result["cases"][0]["C2"]["outcome"] == "repaired"
    assert result["cases"][0]["C2"]["calls"] == 3
    assert result["role_attempts"] == {"audit": 5, "repair": 1}
    assert result["admitted_calls"] == 6
    assert result["reserved_usd"] == pytest.approx(.96)
    assert [r["requested_reasoning_effort"] for r in result["provider_records_by_role"]["repair"]] == ["medium"]


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["unknown", "hash", "identity"])
async def test_shared_failure_stops_every_remaining_arm_and_input(tmp_path, bad):
    audit = Audit(known=bad != "unknown", model="unexpected" if bad == "identity" else runner.MODEL,
                  mutation=(lambda v: v.update(proposal_sha256="0"*64)) if bad == "hash" else None)
    result = await runner.run(tmp_path/"run", packet(tmp_path), bank="fresh", concurrency=1,
        injected_audit_client=audit, injected_repair_client=Repair())
    assert result["provider_attempts"] == 1
    assert result["provider_stopped"]
    assert len(result["cases"]) == 2
    assert result["cases"][0]["C1"]["reason"] == "contract_or_provider_failure"
    assert result["cases"][0]["C2"]["outcome"] == "blocked"
    assert result["cases"][1]["C1"]["outcome"] == "blocked"


@pytest.mark.asyncio
async def test_source_provenance_change_invalidates_and_output_refuses_overwrite(tmp_path):
    provenance = tmp_path/"source.txt"
    provenance.write_text("before")
    def mutate(v):
        provenance.write_text("after")
    path = packet(tmp_path)
    result = await runner.run(tmp_path/"run", path, bank="fresh",
        injected_audit_client=Audit(mutation=mutate), injected_repair_client=Repair(),
        input_provenance_paths=[provenance])
    assert not result["source_files_unchanged"]
    assert str(provenance) in result["source_hash_errors"]
    with pytest.raises(FileExistsError):
        await runner.run(tmp_path/"run", path, bank="fresh", injected_audit_client=Audit(), injected_repair_client=Repair())


@pytest.mark.asyncio
async def test_sequences_do_not_borrow_and_c1_cannot_repair(tmp_path):
    shared = runner.SharedAdmission(1, tmp_path/"ledger.jsonl")
    arm = runner.ArmClient(shared, {}, "C1", "case")
    with pytest.raises(ValueError, match="sequence"):
        await arm.chat([], runner.REPAIR_TASK)
    assert shared.stopped and shared.calls == 0


@pytest.mark.asyncio
async def test_live_requires_exact_bank_and_no_injection(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", lambda *a: None)
    monkeypatch.setenv("OPENAI_API_KEY", "injected-not-real")
    with pytest.raises(ValueError, match="labelled live"):
        await runner.run(tmp_path/"run", packet(tmp_path), bank="fresh", execute=True,
            injected_audit_client=Audit())
    path = packet(tmp_path)
    value = json.loads(path.read_text())
    value["bank"] = "fresh"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="exact live"):
        await runner.run(tmp_path/"run", path, bank="fresh", execute=True,
                         expected_packet_sha256=runner.digest(path.read_bytes()))

@pytest.mark.asyncio
async def test_runner_serializer_uses_actual_new_task_schemas(tmp_path, monkeypatch):
    original = runner.RecordedRunClient
    captured = []

    class InspectRecorded(original):
        async def chat(self, messages, task):
            payload = self.serializer._payload(messages, task)
            captured.append((task, payload))
            return await super().chat(messages, task)

    monkeypatch.setattr(runner, "RecordedRunClient", InspectRecorded)
    await runner.run(tmp_path/"run", packet(tmp_path), bank="fresh", concurrency=1,
        injected_audit_client=Audit(rejects=(2,)), injected_repair_client=Repair())
    assert {task for task, p in captured} == {runner.SUPPORT_TASK, runner.QUALITY_TASK, runner.REPAIR_TASK}
    for task, payload in captured:
        assert payload["model"] == runner.MODEL and payload["max_output_tokens"] == 3000
        assert payload["reasoning"]["effort"] == ("medium" if task == runner.REPAIR_TASK else "high")
        schema = payload["text"]["format"]["schema"]
        assert ("proposal_sha256" in schema["properties"]) == (task != runner.REPAIR_TASK)
        assert payload["store"] is False


@pytest.mark.asyncio
async def test_concurrent_failure_allows_only_already_admitted_calls(tmp_path):
    import asyncio
    class YieldingAudit(Audit):
        async def chat(self, messages, task):
            await asyncio.sleep(.01)
            return await super().chat(messages, task)
    result = await runner.run(tmp_path/"run", packet(tmp_path), bank="fresh", concurrency=4,
        injected_audit_client=YieldingAudit(known=False), injected_repair_client=Repair())
    assert result["provider_attempts"] == 2
    assert result["provider_stopped"]
    assert all(c["C2"]["outcome"] == "blocked" for c in result["cases"])
    assert result["role_attempts"]["repair"] == 0


@pytest.mark.asyncio
async def test_frozen_baseline_and_expected_live_digest_are_enforced(tmp_path, monkeypatch):
    path = packet(tmp_path)
    value = json.loads(path.read_text())
    value["contexts"][0]["frozen_baseline_render"] = "Different original"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="frozen baseline"):
        await runner.run(tmp_path/"run", path, bank="exposed", injected_audit_client=Audit(), injected_repair_client=Repair())
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", lambda *a: None)
    monkeypatch.setenv("OPENAI_API_KEY", "injected-not-real")
    with pytest.raises(ValueError, match="SHA256"):
        await runner.run(tmp_path/"run", path, bank="exposed", execute=True, expected_packet_sha256="0"*64)
    with pytest.raises(ValueError, match="packet bank"):
        await runner.run(tmp_path/"run", path, bank="exposed", execute=True, expected_packet_sha256=runner.digest(path.read_bytes()))

@pytest.mark.asyncio
async def test_v2_runner_selection_serialization_and_manifest(tmp_path, monkeypatch):
    from tests.test_final_response_audit import VersionedAudit, VersionedRepair
    from src.digital_twin.generation import final_response_audit as h
    original = runner.RecordedRunClient
    captured = []
    class InspectRecorded(original):
        async def chat(self, messages, task):
            payload = self.serializer._payload(messages, task)
            captured.append((task, payload))
            return await super().chat(messages, task)
    monkeypatch.setattr(runner, "RecordedRunClient", InspectRecorded)
    result = await runner.run(tmp_path/"run", packet(tmp_path), bank="fresh", variant="v2", concurrency=1,
        injected_audit_client=VersionedAudit(rejects=(2,)), injected_repair_client=VersionedRepair())
    assert result["instrument_id"] == "final-response-support-audit-002"
    assert result["cases"][0]["C2"]["outcome"] == "repaired"
    assert {t for t,p in captured} == set(h.task_ids("v2"))
    manifest = json.loads((tmp_path/"run/manifest.json").read_text())
    assert manifest["variant"] == "v2" and manifest["tasks"] == list(h.task_ids("v2"))
    for task,p in captured:
        assert p["text"]["format"]["name"] == task
        assert p["reasoning"]["effort"] == ("medium" if task == h.V2_REPAIR_TASK else "high")
        assert p["model"] == h.MODEL and p["max_output_tokens"] == 3000


@pytest.mark.asyncio
async def test_v2_live_uses_its_explicit_guard(tmp_path, monkeypatch):
    seen = []
    def guard(program, operation):
        seen.append((program, operation))
        raise RuntimeError("preflight guard")
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", guard)
    with pytest.raises(RuntimeError, match="preflight guard"):
        await runner.run(tmp_path/"run", tmp_path/"missing", bank="exposed", execute=True, variant="v2")
    assert seen == [("final-response-support-audit-002", "external_model_evaluation")]
