import json

import pytest

from scripts import run_paired_pedagogy_development as runner
from scripts.run_output_cap_progression_development import CARDS
from scripts.teaching_profile_responsiveness_packet import PROFILES
from tests.test_bounded_contract_progression_development import FakeClient


def packet():
    return {"packet_id": "paired-contract-v1", "split": "development",
        "sources": [{"course_id": "a", "concept_id": CARDS[0].concept_id,
            "label": CARDS[0].label, "text": CARDS[0].description},
            {"course_id": "other", "concept_id": "secret", "label": "secret", "text": "WRONG_COURSE"}],
        "contexts": [{"id": "case-one", "course_id": "a", "category": "explicit-explanation",
            "public": {"profile_values": PROFILES["explanatory"], "target_turn_index": 1,
                "student_turns": [{"content": "Explain cobalt ticket's epoch rule."},
                                  {"content": "Explain cobalt ticket's equal sequence rule."}]},
            "gold": {"secret": "NEVER_SEND_GOLD"}}]}


def test_packet_adapter_excludes_other_course_and_gold_from_runtime_inputs():
    data = runner.normalized_packet(packet())
    assert "WRONG_COURSE" not in json.dumps(data)
    assert "NEVER_SEND_GOLD" not in json.dumps(data)
    assert len(data["cases"][0]["cards"]) == 1
    rows = runner.schedule(data, 1, 2)
    assert [r["version"] for r in rows] == ["v4", "v5", "v5", "v4"]
    assert rows[0]["case"]["prompts"] == rows[1]["case"]["prompts"]


@pytest.mark.asyncio
async def test_pair_preserves_actual_history_restart_and_records_no_semantic_pass(tmp_path, monkeypatch):
    actual = runner.build_final_profile_runtime_factory
    seen = []
    def bridge(*args, **kwargs):
        # Instrument contract only: strip forthcoming v5 flag, run both through v4.
        seen.append(kwargs.pop("instructional_moves_enabled", False))
        assert "NEVER_SEND_GOLD" not in repr(kwargs)
        assert "WRONG_COURSE" not in repr(kwargs)
        return actual(*args, **kwargs)
    monkeypatch.setattr(runner, "build_final_profile_runtime_factory", bridge)
    monkeypatch.setattr(runner, "EXPECTED_IDS", {"v4": runner.EXPECTED_IDS["v4"], "v5": runner.EXPECTED_IDS["v4"]})
    result = await runner.run(tmp_path / "fresh", packet(), transport_factory=lambda _: FakeClient("v4"))
    assert sorted(seen) == [False, True]
    assert result["source_files_unchanged"] and result["semantic_quality_pass"] is None
    assert len(result["histories"]) == 2
    assert all(h["completed_turns"] == 2 and h["restarts"] == 1 for h in result["histories"])
    assert (tmp_path / "fresh" / "source-snapshot.zip").exists()
    for path in (tmp_path / "fresh").glob("*/turns.jsonl"):
        turns = [json.loads(x) for x in path.read_text().splitlines()]
        assert [t["student"] for t in turns] == runner.normalized_packet(packet())["cases"][0]["prompts"]
        assert all(t["turn"]["tutor_message"]["content"] for t in turns)
    with pytest.raises(FileExistsError):
        await runner.run(tmp_path / "fresh", packet())


@pytest.mark.asyncio
async def test_failed_factory_retains_both_histories_and_live_guard_precedes_output(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("fixture boundary failure")
    monkeypatch.setattr(runner, "build_final_profile_runtime_factory", broken)
    result = await runner.run(tmp_path / "failed", packet())
    assert len(result["histories"]) == 2
    assert all(h["error_type"] == "ValueError" and not h["completed"] for h in result["histories"])
    def deny(*args):
        raise PermissionError("not approved")
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", deny)
    with pytest.raises(PermissionError):
        await runner.run(tmp_path / "denied", packet(), live=True)
    assert not (tmp_path / "denied").exists()


@pytest.mark.asyncio
async def test_insufficient_budget_rejects_packet_before_output(tmp_path):
    with pytest.raises(ValueError, match="complete paired packet"):
        await runner.run(tmp_path / "too-small", packet(), maximum_calls=4)
    assert not (tmp_path / "too-small").exists()


@pytest.mark.asyncio
async def test_actual_arm_mismatch_and_cleanup_failure_preserve_aggregate(tmp_path, monkeypatch):
    from types import SimpleNamespace
    def close(runtime):
        raise OSError("injected cleanup failure")
    def bridge(*args, **kwargs):
        return lambda *args: SimpleNamespace(tutoring=SimpleNamespace(generator=SimpleNamespace(
            implementation_id="wrong-actual-arm", client=object())), close_runtime=close)
    monkeypatch.setattr(runner, "build_final_profile_runtime_factory", bridge)
    result = await runner.run(tmp_path / "cleanup", packet())
    assert result["decision"] == "incomplete-contract"
    assert len(result["histories"]) == 2
    assert all(h["observed_generator_id"] == "wrong-actual-arm" and h["cleanup_error"] == "OSError"
               and h["error_type"] == "RuntimeError" for h in result["histories"])
    assert (tmp_path / "cleanup" / "summary.json").exists()


def test_complete_development_packet_fits_finite_comparison_without_reading_confirmation():
    data = json.loads((runner.ROOT / "research/05_evaluation/datasets/meaningful-continuation-development-v2.json").read_text())
    normalized = runner.validate_packet(runner.normalized_packet(data))
    assert len(normalized["cases"]) == 48
    assert all(len({card["objective"] for card in case["cards"]}) == len(case["cards"])
               for case in normalized["cases"])
    assert sum(len(c["prompts"]) for c in normalized["cases"]) == 84
    assert len(runner.schedule(normalized, 7801, 1)) == 96
    assert 84 * 2 * 3 == 504 < 800
    assert 504 * .025 < 20
    assert "required_meanings" not in json.dumps(normalized)


class InstructionalContractClient:
    """Source-binding contract fixture; deliberately not a semantic oracle."""
    experimental_transport_configuration = {"model": "gpt-5.6-luna", "output_cap": 3000, "reasoning_effort": "low"}
    def __init__(self, version):
        self.version = version

    async def chat(self, messages, task):
        from src.digital_twin.grounding.models import GenerationUsage
        from src.digital_twin.llm import LlmResponse
        payload = json.loads(messages[-1].content)
        if task == "question_specific_conditional_revision":
            content = {"disposition": "repair", "fault": "missing_requested_answer", "proposed_move": "instructional",
                "target_concept": "synthetic governing condition", "diagnosis": "Synthetic conditional repair contract.",
                "replacement": payload["draft_proposal"]}
        elif task in {"question_specific_factual_revision", "question_specific_bounded_revision"}:
            content = payload["draft_proposal"]
        elif task in {"question_specific_compact_instruction", "question_specific_profile_authority", "question_specific_typed_instruction"}:
            source = payload["evidence"][0]
            content = {"action": "instruction", "units": [{"kind": "explanation",
                "text": "The approved source states the governing condition.",
                "source_ids": [source["citation_id"]]}], "missing_details": []}
        elif task == "reactive_tutoring_intent":
            content = {"schema_version": "3.0.0", "proposed_intent": "explain_concept", "reason_code": "synthetic_contract"}
        else:
            assert task in {"question_specific_profile_tutoring", "question_specific_instructional_tutoring", "question_specific_instructional_continuation", "question_specific_request_coverage"}
            source = payload["evidence"][0]
            content = {"boundary": "answerable", "aspects": [{"requirement": "approved source rule", "supported": True,
                "spans": [{"citation_id": source["citation_id"], "text": source["text"]}]}],
                "teaching_move": "explain", "hint_span": None, "question_focus": ""}
            if task in {"question_specific_instructional_tutoring", "question_specific_instructional_continuation", "question_specific_request_coverage"}:
                content.update(instructional_question=None, feedback=None,
                    explanation_steps=[{"text": "The approved source states the governing condition.", "aspect_indexes": [1]}])
            if task == "question_specific_request_coverage":
                for aspect in content["aspects"]:
                    aspect.update(request_focus=payload["question"][:160], goal="explain_rule")
                for name in ("hint_span", "question_focus", "missing_focus", "supported_focus"):
                    content.pop(name, None)
                content.update(partial_guidance=None, boundary_reason="none", supported_response_aspect_indexes=[])
            if task == "question_specific_instructional_continuation":
                content.update(partial_guidance=None, boundary_reason="none", missing_focus="", supported_focus="")
        return LlmResponse(provider_model="gpt-5.6-luna", provider_revision="injected-contract",
            usage=GenerationUsage(input_tokens=10, output_tokens=10, total_tokens=20, approximate_cost_usd=0),
            content=json.dumps(content))


@pytest.mark.asyncio
async def test_actual_v4_v5_constructed_generators_and_full_output(tmp_path):
    result = await runner.run(tmp_path / "actual-arms", packet(), transport_factory=InstructionalContractClient)
    assert all(h["completed"] for h in result["histories"])
    assert {h["observed_generator_id"] for h in result["histories"]} == {runner.EXPECTED_IDS[v] for v in ("v4", "v5")}
    assert all(h["restarts"] == 1 for h in result["histories"])
    assert result["semantic_quality_pass"] is None
    manifest = json.loads((tmp_path / "actual-arms" / "manifest.json").read_text())
    assert manifest["candidate"] == "v5" and manifest["output_cap"] == 3000
    assert set(manifest["candidate_ids"]) == {"v4", "v5"}
    assert isinstance(manifest["invocation_argv"], list)


def test_v6_is_explicit_and_v5_reproduction_schedule_remains_default():
    data = runner.normalized_packet(packet())
    assert {r["version"] for r in runner.schedule(data, 7801, 1)} == {"v4", "v5"}
    assert {r["version"] for r in runner.schedule(data, 7801, 1, "v6")} == {"v4", "v6"}
    assert {r["version"] for r in runner.schedule(data, 7801, 1, "v7")} == {"v4", "v7"}
    with pytest.raises(ValueError):
        runner.schedule(data, 7801, 1, "unknown")


@pytest.mark.asyncio
async def test_missing_end_snapshot_file_is_recorded_invalid_not_lost(tmp_path, monkeypatch):
    from pathlib import Path
    target = runner.ROOT / "research/04_experiments/2026-09-06-paired-pedagogy-runner-plan.md"
    original = Path.read_bytes
    reads = 0
    def disappear(path):
        nonlocal reads
        if path == target:
            reads += 1
            if reads == 3:
                raise FileNotFoundError("injected end-snapshot disappearance")
        return original(path)
    def broken(*args, **kwargs):
        raise ValueError("contract skips runtime")
    monkeypatch.setattr(Path, "read_bytes", disappear)
    monkeypatch.setattr(runner, "build_final_profile_runtime_factory", broken)
    result = await runner.run(tmp_path / "snapshot", packet())
    assert result["decision"] == "invalid-source-change"
    assert result["source_hash_errors"][str(target.relative_to(runner.ROOT))] == "FileNotFoundError"
    assert (tmp_path / "snapshot" / "summary.json").exists()


@pytest.mark.asyncio
async def test_actual_v6_arm_is_preserved_after_restart(tmp_path):
    result = await runner.run(tmp_path / "v6", packet(), transport_factory=InstructionalContractClient, candidate="v6")
    assert all(h["completed"] for h in result["histories"])
    for history in result["histories"]:
        expected = runner.EXPECTED_IDS[history["version"]]
        assert history["observed_generator_id"] == expected
        assert history["restarted_generator_ids"] == [expected]
    manifest = json.loads((tmp_path / "v6" / "manifest.json").read_text())
    assert manifest["candidate"] == "v6" and manifest["output_cap"] == 3000
    assert set(manifest["candidate_ids"]) == {"v4", "v6"}
    assert result["semantic_quality_pass"] is None


def test_mixed_stage_packet_keeps_own_denominator_and_finite_bound():
    data = json.loads((runner.ROOT / "research/05_evaluation/datasets/mixed-evidence-stage-development-v1.json").read_text())
    normalized = runner.validate_packet(runner.normalized_packet(data))
    assert len(normalized["cases"]) == 8
    assert sum(len(c["prompts"]) for c in normalized["cases"]) == 12
    assert 12 * 2 * 3 == 72 < 120
    assert 72 * .025 < 3


@pytest.mark.asyncio
async def test_actual_v7_arm_is_preserved_after_restart(tmp_path):
    result = await runner.run(tmp_path / "v7", packet(), transport_factory=InstructionalContractClient, candidate="v7")
    assert all(h["completed"] for h in result["histories"])
    for history in result["histories"]:
        expected = runner.EXPECTED_IDS[history["version"]]
        assert history["observed_generator_id"] == expected
        assert history["restarted_generator_ids"] == [expected]
    manifest = json.loads((tmp_path / "v7" / "manifest.json").read_text())
    assert manifest["candidate"] == "v7" and set(manifest["candidate_ids"]) == {"v4", "v7"}
    assert result["semantic_quality_pass"] is None


@pytest.mark.asyncio
async def test_input_packet_and_private_supporting_artifacts_are_archived_and_checked(tmp_path, monkeypatch):
    import hashlib
    directory = tmp_path / "input"
    directory.mkdir()
    path = directory / "packet.json"
    content = json.dumps(packet(), indent=3).encode()
    path.write_bytes(content)
    (directory / "source-lineage.json").write_text('{"synthetic":true}')
    (directory / "build_packet.py").write_text('# synthetic authoring provenance; never executed')
    def broken(*args, **kwargs):
        raise ValueError("contract skips runtime")
    monkeypatch.setattr(runner, "build_final_profile_runtime_factory", broken)
    await runner.run(tmp_path / "archived", packet(), packet_path=path,
        input_provenance_paths=(directory / "source-lineage.json", directory / "build_packet.py"))
    metadata = json.loads((tmp_path / "archived" / "manifest.json").read_text())
    assert metadata["original_packet_sha256"] == hashlib.sha256(content).hexdigest()
    assert metadata["input_packet_normalized_equal"]
    assert set(metadata["input_artifact_sha256"]) == {"packet.json", "source-lineage.json", "build_packet.py"}
    assert (tmp_path / "archived" / "input-artifacts" / "packet.json").read_bytes() == content
    def mutate(*args, **kwargs):
        (directory / "source-lineage.json").write_text('{"changed":true}')
        raise ValueError("contract source mutation")
    monkeypatch.setattr(runner, "build_final_profile_runtime_factory", mutate)
    result = await runner.run(tmp_path / "changed", packet(), packet_path=path,
        input_provenance_paths=(directory / "source-lineage.json", directory / "build_packet.py"))
    assert result["decision"] == "invalid-source-change"
    assert result["source_hash_errors"]["input-artifacts/source-lineage.json"] == "changed"
    with pytest.raises(ValueError, match="input packet bytes"):
        await runner.run(tmp_path / "mismatch", {**packet(), "packet_id": "wrong"}, packet_path=path)
    assert not (tmp_path / "mismatch").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("candidate", ["v8", "v9", "v10"])
async def test_v8_standalone_selection_uses_actual_compact_runtime(tmp_path, candidate):
    from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
    config = experimental_tutoring_configuration(candidate)
    assert config["output_cap"] == 3000
    assert config["runtime_flags"]["instructional_compact_response_enabled"]
    assert not any(name in config["runtime_flags"] for name in ("instructional_moves_enabled",
        "instructional_continuation_enabled", "instructional_request_coverage_enabled"))
    result = await runner.run(tmp_path / "compact", packet(), candidate=candidate, transport_factory=InstructionalContractClient)
    assert result["decision"] == "contract-only"
    assert all(h["observed_generator_id"] == runner.EXPECTED_IDS[h["version"]] for h in result["histories"])
    assert all(h["completed_turns"] == 2 and h["restarts"] == 1 for h in result["histories"])
    assert result["semantic_quality_pass"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["v10-luna-medium", "v10-sol-low", "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"])
async def test_paired_model_variant_keeps_v4_control_and_role_restart(tmp_path, variant):
    from tests.test_generation_role_model_comparison import fixture

    def transport(version, role=None):
        return fixture(version, role) if role else InstructionalContractClient(version)

    result = await runner.run(tmp_path / "variant", packet(), candidate=variant,
        maximum_calls=1200 if variant in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"} else 800,
        maximum_cost_usd=192 if variant in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"} else 128, transport_factory=transport)
    assert all(history["completed"] for history in result["histories"])
    candidate = next(history for history in result["histories"] if history["version"] == variant)
    assert candidate["observed_generator_id"] == runner.EXPECTED_IDS[variant]
    assert candidate["restarted_role_configurations"] == [candidate["role_configuration"]]
    assert result["source_files_unchanged"]
    assert result["arms"]["v4"]["provider_failures"] == 0
    assert result["arms"][variant]["provider_failures"] == 0
    if variant in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"}:
        rows = [json.loads(line) for line in (tmp_path / "variant" / candidate["id"] / "turns.jsonl").read_text().splitlines()]
        assert all(row["turn"]["tutor_message"]["trace"]["provider_model"] == ("gpt-5.6-luna" if variant in {"v14-luna-sol", "v14-luna-sol-medium"} else "gpt-5.6-sol") for row in rows)
        assert result["arms"][variant]["role_attempts"]["revision"] > 0


@pytest.mark.asyncio
async def test_paired_archive_default_excludes_adjacent_sealed_builder(tmp_path, monkeypatch):
    source = tmp_path / "packet.json"
    source.write_text(json.dumps(packet()))
    (tmp_path / "build_packet.py").write_text("NEVER_READ_SEALED_BUILDER")
    actual_read = type(source).read_bytes

    def read(path):
        if path == tmp_path / "build_packet.py":
            raise AssertionError("sealed sibling was read")
        return actual_read(path)

    monkeypatch.setattr(type(source), "read_bytes", read)
    result = await runner.run(tmp_path / "safe", packet(), packet_path=source,
        transport_factory=InstructionalContractClient)
    assert all(history["completed"] for history in result["histories"])
    assert list((tmp_path / "safe/input-artifacts").iterdir()) == [tmp_path / "safe/input-artifacts/packet.json"]


@pytest.mark.asyncio
async def test_v12_rejects_old_three_call_turn_budget_before_dispatch(tmp_path):
    # Two prompts per arm: four turns need20 calls, then enough per-role allocation.
    with pytest.raises(ValueError, match="complete paired packet"):
        await runner.run(tmp_path / "small", packet(), candidate="v12-luna-sol",
            maximum_calls=12, maximum_cost_usd=1.92)
    assert not (tmp_path / "small").exists()


@pytest.mark.asyncio
async def test_cheap_audit_variant_runs_through_actual_paired_adapter(tmp_path):
    from scripts.run_mixed_source_recovery_development import SourceBoundContractClient
    def transport(version, role=None):
        return SourceBoundContractClient(tmp_path/f'{version}-{role}-fixture.jsonl', audit_model='gpt-5.6-luna')
    result=await runner.run(tmp_path/'cheap-composed',packet(),candidate='v19-luna-luna-medium',
        maximum_calls=144,maximum_cost_usd=12,transport_factory=transport,candidate_context_retrieval=True)
    assert result['decision']=='contract-only'
    assert all(h['completed'] and h['completed_turns']==2 for h in result['histories'])
    assert result['arms']['v19-luna-luna-medium']['role_attempts']['revision']>=2
    turns=list(map(json.loads,(tmp_path/'cheap-composed/case-0-repeat-0-v19-luna-luna-medium/turns.jsonl').read_text().splitlines()))
    assert all(t['turn']['tutor_message']['action']=='answer' and t['turn']['citations'] for t in turns)


@pytest.mark.asyncio
async def test_unknown_factory_keyword_is_rejected_before_calls(tmp_path,monkeypatch):
    def old_factory(root,arm):raise AssertionError('must not invoke factory')
    monkeypatch.setattr(runner,'build_final_profile_runtime_factory',old_factory)
    with pytest.raises(TypeError,match='unexpected keyword'):
        await runner.run(tmp_path/'no-output',packet(),candidate='v19-luna-luna-medium')
    assert not (tmp_path/'no-output').exists()
