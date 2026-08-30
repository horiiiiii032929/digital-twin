from __future__ import annotations

import asyncio
import base64
import hashlib
import inspect
import json
from pathlib import Path
import sqlite3
import struct

import pytest

from scripts import run_course_digital_twin_nonhuman_supplements as runner
from src.digital_twin.evaluation.models import ComponentEvaluationRecord
from src.digital_twin.evaluation.provider_json import (
    ProviderJsonResponse,
    canonical_sha256,
)


def _provider_snapshot(*, calls: int, cost: float = 0.0) -> dict[str, object]:
    return {
        "provider_calls": calls,
        "provider_attempts": calls,
        "reported_cost_usd": cost,
    }


def test_validate_binds_exact_program_002_and_public_inputs() -> None:
    result = runner.validate()

    assert result["program_id"] == runner.PROGRAM_ID
    assert result["program_sha256"] == runner.EXPECTED_PROGRAM_SHA256
    assert result["stages"] == [runner.VISUAL_STAGE, runner.PROFILE_STAGE]
    assert result["profile_conditions"] == ["C0", "C1", "C2"]
    assert result["skipped_condition"] == "C3"
    assert result["visual_asset_count"] == 30
    assert result["visual_case_count"] == 60
    assert result["profile_case_count"] == 12
    assert result["private_data_used"] is False
    assert result["hidden_data_opened"] is False
    assert result["professor_fidelity_claim"] is False

    source = inspect.getsource(runner)
    assert "course-digital-twin-evaluation-program-001" not in source
    assert "course_digital_twin_evaluation_live_stages" not in source


def test_program_hash_check_rejects_rehashed_manifest_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = json.loads(runner.PROGRAM_PATH.read_text(encoding="utf-8"))
    payload["decision_id"] = "DRIFTED"
    payload["content_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    path = tmp_path / "program.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(runner, "PROGRAM_PATH", path)

    with pytest.raises(runner.SupplementaryEvaluationError, match="hash drifted"):
        runner.validate()


def test_direct_openai_bindings_enforce_store_identity_retries_and_caps() -> None:
    program = runner._load_program()
    bindings = runner._bindings(program)

    assert bindings["visual"]["provider"] == "openai"
    assert bindings["visual"]["provider_model"] == runner.VISUAL_MODEL
    assert bindings["profile"]["provider_model"] == runner.PROFILE_MODEL
    assert all(binding["request_store"] is False for binding in bindings.values())
    assert all(
        binding["maximum_transport_retries"] == 0 for binding in bindings.values()
    )
    assert runner.VISUAL_MAXIMUM_CALLS == 30
    assert runner.PROFILE_MAXIMUM_CALLS == 36
    assert runner.VISUAL_MAXIMUM_COST_USD == 2.0
    assert runner.PROFILE_MAXIMUM_COST_USD == 1.5
    assert runner.SUPPLEMENT_MAXIMUM_COST_USD == 3.5

    payload = runner.DirectProviderJsonTransport(bindings["visual"])._payload(
        system="test",
        prompt="test",
        task="test",
        schema=runner._visual_schema(),
        image_data_urls=["data:image/png;base64,AA=="],
    )
    assert payload["model"] == runner.VISUAL_MODEL
    assert payload["store"] is False
    assert "uniqueItems" not in json.dumps(runner._visual_schema())
    assert "uniqueItems" not in json.dumps(runner._profile_schema("case", "C2"))


def test_provider_side_unique_lists_are_enforced_deterministically() -> None:
    with pytest.raises(
        runner.SupplementaryEvaluationError,
        match="duplicate entities",
    ):
        runner._require_unique_string_lists(
            {
                "entities": ["duplicate", "duplicate"],
                "relationships": [],
                "uncertainty": [],
            },
            ("entities", "relationships", "uncertainty"),
        )


def test_visual_prompt_is_question_independent_and_profile_inputs_are_separated() -> (
    None
):
    dataset = runner._visual_dataset()
    profile = runner._synthetic_profile()
    answer_by_asset = {
        case["required_asset_ids"][0]: case
        for case in dataset["cases"]
        if case["expected_action"] == "answer"
    }
    for asset in dataset["assets"]:
        _, prompt = runner._visual_prompt(asset)
        case = answer_by_asset[asset["asset_id"]]
        assert case["question"] not in prompt
        assert case["canonical_answer"] not in prompt

    cases = runner._stratified_profile_cases(dataset)
    answerable = next(case for case in cases if case["expected_action"] == "answer")
    boundary = next(case for case in cases if case["expected_action"] != "answer")
    _, c0 = runner._profile_prompt(answerable, "C0", profile)
    _, c1 = runner._profile_prompt(answerable, "C1", profile)
    _, c2 = runner._profile_prompt(answerable, "C2", profile)
    _, c0_boundary = runner._profile_prompt(boundary, "C0", profile)

    assert answerable["canonical_answer"] not in c0
    assert json.loads(c0)["oracle_evidence"] is None
    assert json.loads(c0)["synthetic_profile"] is None
    assert (
        json.loads(c1)["oracle_evidence"]["canonical_source_fact"]
        == answerable["canonical_answer"]
    )
    assert json.loads(c1)["synthetic_profile"] is None
    assert (
        json.loads(c2)["oracle_evidence"]["canonical_source_fact"]
        == answerable["canonical_answer"]
    )
    assert json.loads(c2)["synthetic_profile"]
    assert json.loads(c0_boundary)["oracle_evidence"] is None


def test_visual_failure_is_terminal_refine_without_skipping_profile_stage() -> None:
    program = runner._load_program()
    dataset = runner._visual_dataset()
    profile = runner._synthetic_profile()
    cases = runner._stratified_profile_cases(dataset)
    case_by_asset = {
        case["required_asset_ids"][0]: case
        for case in dataset["cases"]
        if case["expected_action"] == "answer"
    }
    descriptions = [
        runner._simulated_description(asset, case_by_asset, passing=False)
        for asset in dataset["assets"]
    ]
    visual = runner._visual_evidence_payload(
        program=program,
        dataset=dataset,
        descriptions=descriptions,
        provider=_provider_snapshot(calls=30),
        code_revision="a" * 40,
    )
    profile_result = runner._profile_evidence_payload(
        program=program,
        dataset=dataset,
        profile=profile,
        cases=cases,
        outputs=runner._simulated_profile_outputs(cases, profile, passing=True),
        provider=_provider_snapshot(calls=36),
        code_revision="a" * 40,
    )
    combined = runner._combined_payload(
        program=program,
        visual=runner._hashed_payload(visual),
        profile=runner._hashed_payload(profile_result),
    )

    assert visual["stage_status"] == "completed-refine"
    assert visual["decision"]["outcome"] == "refine"
    assert profile_result["stage_status"] == "completed-go-deeper"
    assert combined["independent_quality_failures_do_not_skip_peer_stage"] is True
    assert [row["stage"] for row in combined["stage_results"]] == [
        runner.VISUAL_STAGE,
        runner.PROFILE_STAGE,
    ]


def test_final_visual_semantic_failure_is_invalid_and_accounted() -> None:
    program = runner._load_program()
    dataset = runner._visual_dataset()
    payload = runner._visual_invalid_semantic_payload(
        program=program,
        dataset=dataset,
        provider=_provider_snapshot(calls=30, cost=0.025),
        code_revision="a" * 40,
        duplicate_asset_count=3,
    )

    assert payload["stage_status"] == "invalid-execution"
    assert payload["quality_gates_passed"] is False
    assert payload["decision"]["outcome"] == "refine"
    assert payload["operational_summary"]["provider_calls"] == 30
    assert payload["candidates"][1]["failures_by_category"] == {
        "duplicate-semantic-list": 3,
        "incomplete-visual-description": 0,
    }


def test_profile_is_explicitly_c0_c2_and_discloses_c3_skip() -> None:
    program = runner._load_program()
    dataset = runner._visual_dataset()
    profile = runner._synthetic_profile()
    cases = runner._stratified_profile_cases(dataset)
    outputs = runner._simulated_profile_outputs(cases, profile, passing=True)
    payload = runner._profile_evidence_payload(
        program=program,
        dataset=dataset,
        profile=profile,
        cases=cases,
        outputs=outputs,
        provider=_provider_snapshot(calls=36),
        code_revision="a" * 40,
    )

    assert payload["stage"] == "synthetic-profile-c0-c2"
    assert payload["conditions_executed"] == ["C0", "C1", "C2"]
    assert payload["conditions_skipped"][0]["condition"] == "C3"
    assert "AFQC-103" in payload["conditions_skipped"][0]["reason"]
    assert {row["condition"] for row in payload["candidates"]} == {
        "C0",
        "C1",
        "C2",
    }
    assert payload["profile_boundary"]["professor_approved"] is False
    assert payload["profile_boundary"]["professor_fidelity_claim"] is False
    assert all(row["condition"] != "C3" for row in payload["case_evidence"])


def test_visual_candidate_rejects_unsupported_segments_and_raster_drift() -> None:
    program = runner._load_program()
    dataset = runner._visual_dataset()
    case_by_asset = {
        case["required_asset_ids"][0]: case
        for case in dataset["cases"]
        if case["expected_action"] == "answer"
    }
    descriptions = [
        runner._simulated_description(asset, case_by_asset, passing=True)
        for asset in dataset["assets"]
    ]
    descriptions[0]["description_text"] += "\nA private student failed this course."
    descriptions[0]["description_segments"].append(
        "A private student failed this course."
    )
    unsupported = runner._visual_evidence_payload(
        program=program,
        dataset=dataset,
        descriptions=descriptions,
        provider=_provider_snapshot(calls=30),
        code_revision="a" * 40,
    )
    assert unsupported["stage_status"] == "completed-refine"

    descriptions = [
        runner._simulated_description(asset, case_by_asset, passing=True)
        for asset in dataset["assets"]
    ]
    descriptions[0]["transmitted_image_sha256"] = "0" * 64
    drifted = runner._visual_evidence_payload(
        program=program,
        dataset=dataset,
        descriptions=descriptions,
        provider=_provider_snapshot(calls=30),
        code_revision="a" * 40,
    )
    assert drifted["stage_status"] == "completed-refine"


def test_oversized_svg_is_rasterized_within_memory_bound(tmp_path: Path) -> None:
    dataset = runner._visual_dataset()
    oversized = next(
        asset
        for asset in dataset["assets"]
        if asset["asset_id"] == "afqv001-asset-029"
    )

    data_url = runner._image_data_url(oversized, tmp_path)
    raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", raw[16:24])
    assert width <= runner.VISUAL_RASTER_MAX_WIDTH
    assert height <= runner.VISUAL_RASTER_MAX_HEIGHT
    assert width > 0
    assert height > 0


def test_profile_candidate_requires_real_feature_names_and_paired_effect() -> None:
    program = runner._load_program()
    dataset = runner._visual_dataset()
    profile = runner._synthetic_profile()
    cases = runner._stratified_profile_cases(dataset)
    outputs = runner._simulated_profile_outputs(cases, profile, passing=True)
    for row in outputs:
        if row["condition"] == "C2":
            paired = next(
                value
                for value in outputs
                if value["condition"] == "C1" and value["case_id"] == row["case_id"]
            )
            row["response"] = paired["response"]
            row["applied_profile_features"] = ["not-a-real-profile-dimension"]
    payload = runner._profile_evidence_payload(
        program=program,
        dataset=dataset,
        profile=profile,
        cases=cases,
        outputs=outputs,
        provider=_provider_snapshot(calls=36),
        code_revision="a" * 40,
    )
    assert payload["stage_status"] == "completed-refine"
    assert payload["paired_profile_effect_rate"] == 0.0
    assert payload["decision"]["selected_implementation_id"] is None


def test_simulation_is_provider_free_and_exercises_independent_failures() -> None:
    result = runner.simulate(visual_quality_pass=False, profile_quality_pass=False)

    assert result["status"] == "simulated"
    assert result["provider_calls"] == 0
    assert result["provider_inference_calls"] == 0
    assert result["simulated_accounted_calls"] == 66
    assert result["both_stages_executed"] is True
    assert result["visual_stage_status"] == "completed-refine"
    assert result["profile_stage_status"] == "completed-refine"
    assert result["conditions_executed"] == ["C0", "C1", "C2"]
    assert result["conditions_skipped"] == ["C3"]
    assert result["private_data_used"] is False
    assert result["hidden_data_opened"] is False


def test_public_preflight_enforces_exclusive_and_resume_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "supplements"
    monkeypatch.setattr(runner, "GENERATED_ROOT", tmp_path.resolve())
    monkeypatch.setattr(runner, "_repo_dirty", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _: "/usr/bin/rsvg-convert")
    monkeypatch.setattr(
        runner,
        "require_bounded_pilot_operation_allowed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")

    ready = runner.preflight(output_root=output, resume=False)
    assert ready["status"] == "ready"
    assert ready["public_only_preflight"] is True
    assert ready["provider_metadata_network_calls"] == 0
    assert ready["provider_inference_calls"] == 0

    output.mkdir()
    exclusive = runner.preflight(output_root=output, resume=False)
    assert "exclusive-output-root-used" in exclusive["blockers"]
    empty_resume = runner.preflight(output_root=output, resume=True)
    assert "resume-state-missing" in empty_resume["blockers"]

    (output / runner.VISUAL_LEDGER_NAME).write_bytes(b"resume-placeholder")
    resumable = runner.preflight(output_root=output, resume=True)
    assert resumable["status"] == "ready"
    (output / runner.COMBINED_EVIDENCE_NAME).write_text("{}", encoding="utf-8")
    terminal = runner.preflight(output_root=output, resume=True)
    assert "resume-output-is-terminal" in terminal["blockers"]


def test_interrupted_execution_resumes_atomically_and_corrupt_ledger_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "supplements"
    dataset = runner._visual_dataset()
    profile_cases = runner._stratified_profile_cases(dataset)
    profile_by_id = {case["case_id"]: case for case in profile_cases}
    monkeypatch.setattr(runner, "GENERATED_ROOT", tmp_path.resolve())
    monkeypatch.setattr(runner, "_repo_revision", lambda: "b" * 40)
    monkeypatch.setattr(
        runner,
        "require_bounded_pilot_operation_allowed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner.visual_builder,
        "build_dataset",
        lambda *, write_assets: dataset,
    )

    state = {"calls": 0, "interrupt_at": 5}

    async def fake_call(self, *, prompt: str, task: str, **_: object):
        state["calls"] += 1
        if state["interrupt_at"] == state["calls"]:
            raise KeyboardInterrupt
        request = json.loads(prompt)
        if task == "program-002-question-independent-visual-description":
            content = {
                "transcription": "Unrelated but valid visible educational content.",
                "entities": [],
                "relationships": [],
                "uncertainty": ["The exact requested fact is uncertain."],
            }
        else:
            case = profile_by_id[request["case_id"]]
            condition = request["condition"]
            action = runner._expected_profile_action(case, condition)
            answerable = (
                condition in {"C1", "C2"} and case["expected_action"] == "answer"
            )
            content = {
                "case_id": case["case_id"],
                "condition": condition,
                "action": action,
                "response": (
                    (
                        "Profile-guided explanation: " + case["canonical_answer"]
                        if condition == "C2"
                        else case["canonical_answer"]
                    )
                    if answerable
                    else (
                        "Profile-guided boundary: I cannot answer from authorized evidence."
                        if condition == "C2"
                        else "I cannot answer from authorized evidence."
                    )
                ),
                "evidence_region_ids": case["required_region_ids"]
                if answerable
                else [],
                "applied_profile_features": ["teaching_style"]
                if condition == "C2"
                else [],
            }
        return ProviderJsonResponse(
            content=content,
            provider_model=self.binding["provider_model"],
            provider_revision=self.binding["documented_revision"],
            endpoint_provider="OpenAI",
            input_tokens=10,
            output_tokens=10,
            cost_usd=0.001,
            latency_ms=1.0,
            attempt_count=1,
        )

    monkeypatch.setattr(runner.DirectProviderJsonTransport, "call", fake_call)

    def image(_asset: dict[str, object], _root: Path) -> str:
        return "data:image/png;base64,AA=="

    monkeypatch.setattr(runner, "_image_data_url", image)

    with pytest.raises(KeyboardInterrupt):
        asyncio.run(
            runner.execute(
                output_root=output,
                resume=False,
                image_data_url_factory=image,
                enforce_preflight=False,
            )
        )
    with sqlite3.connect(output / runner.VISUAL_LEDGER_NAME) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        call_count = connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
    assert metadata["status"] == "interrupted"
    assert call_count == 4

    state["interrupt_at"] = -1
    result = asyncio.run(
        runner.execute(
            output_root=output,
            resume=True,
            image_data_url_factory=image,
            enforce_preflight=False,
        )
    )
    assert result["status"] == "completed"
    assert result["provider_calls"] == 66
    assert result["reported_cost_usd"] == pytest.approx(0.066)
    assert result["stage_results"][0]["status"] == "completed-refine"
    assert result["stage_results"][1]["status"] == "completed-go-deeper"
    with sqlite3.connect(output / runner.VISUAL_LEDGER_NAME) as connection:
        assert connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 30
        assert (
            dict(connection.execute("SELECT key, value FROM metadata"))["status"]
            == "completed"
        )
    with sqlite3.connect(output / runner.PROFILE_LEDGER_NAME) as connection:
        assert connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 36

    (output / runner.COMBINED_EVIDENCE_NAME).unlink()
    with sqlite3.connect(output / runner.VISUAL_LEDGER_NAME) as connection:
        connection.execute(
            "UPDATE metadata SET value = 'corrupt' WHERE key = 'run_binding_sha256'"
        )
        connection.commit()
    with pytest.raises(
        runner.SupplementaryEvaluationError, match="completed ledger binding drifted"
    ):
        asyncio.run(
            runner.execute(
                output_root=output,
                resume=True,
                image_data_url_factory=image,
                enforce_preflight=False,
            )
        )


def test_profile_only_execution_is_independent_of_terminal_visual_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "profile-only"
    dataset = runner._visual_dataset()
    profile = runner._synthetic_profile()
    cases = runner._stratified_profile_cases(dataset)
    case_by_id = {case["case_id"]: case for case in cases}
    feature = next(iter(profile["dimensions"]))
    monkeypatch.setattr(runner, "GENERATED_ROOT", tmp_path.resolve())
    monkeypatch.setattr(runner, "_repo_revision", lambda: "c" * 40)
    monkeypatch.setattr(runner, "_repo_dirty", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _: "/usr/bin/rsvg-convert")
    monkeypatch.setattr(
        runner,
        "require_bounded_pilot_operation_allowed",
        lambda *_: None,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")

    async def fake_call(self, *, prompt: str, **_: object):
        request = json.loads(prompt)
        case = case_by_id[request["case_id"]]
        condition = request["condition"]
        answerable = condition in {"C1", "C2"} and case["expected_action"] == "answer"
        return ProviderJsonResponse(
            content={
                "case_id": case["case_id"],
                "condition": condition,
                "action": runner._expected_profile_action(case, condition),
                "response": (
                    ("Profile: " if condition == "C2" else "")
                    + case["canonical_answer"]
                    if answerable
                    else "I cannot answer from authorized evidence."
                ),
                "evidence_region_ids": case["required_region_ids"] if answerable else [],
                "applied_profile_features": [feature] if condition == "C2" else [],
            },
            provider_model=runner.PROFILE_MODEL,
            provider_revision=runner.PROFILE_MODEL,
            endpoint_provider="OpenAI",
            input_tokens=10,
            output_tokens=10,
            cost_usd=0.001,
            latency_ms=1.0,
            attempt_count=1,
        )

    monkeypatch.setattr(runner.DirectProviderJsonTransport, "call", fake_call)
    result = asyncio.run(runner.execute_profile_only(output_root=output))

    assert result["run_id"] == runner.PROFILE_RUN_ID
    assert result["operational_summary"]["provider_calls"] == 36
    assert not (output / runner.VISUAL_LEDGER_NAME).exists()
    assert (output / runner.PROFILE_LEDGER_NAME).exists()


def test_sanitized_payload_hashes_are_stable() -> None:
    result = runner.simulate()
    payload = runner._hashed_payload(result)
    assert (
        payload["content_sha256"]
        == hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
    )


def test_stage_payloads_convert_to_component_evaluation_records() -> None:
    program = runner._load_program()
    dataset = runner._visual_dataset()
    profile = runner._synthetic_profile()
    cases = runner._stratified_profile_cases(dataset)
    case_by_asset = {
        case["required_asset_ids"][0]: case
        for case in dataset["cases"]
        if case["expected_action"] == "answer"
    }
    visual = runner._visual_evidence_payload(
        program=program,
        dataset=dataset,
        descriptions=[
            runner._simulated_description(asset, case_by_asset, passing=False)
            for asset in dataset["assets"]
        ],
        provider=_provider_snapshot(calls=30),
        code_revision="a" * 40,
    )
    profile_result = runner._profile_evidence_payload(
        program=program,
        dataset=dataset,
        profile=profile,
        cases=cases,
        outputs=runner._simulated_profile_outputs(cases, profile, passing=True),
        provider=_provider_snapshot(calls=36),
        code_revision="a" * 40,
    )

    assert (
        ComponentEvaluationRecord.model_validate(visual).run_id == runner.VISUAL_RUN_ID
    )
    assert (
        ComponentEvaluationRecord.model_validate(profile_result).run_id
        == runner.PROFILE_RUN_ID
    )
