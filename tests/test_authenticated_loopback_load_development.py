import json
import hashlib
import zipfile

import pytest

from scripts import run_authenticated_loopback_load_development as runner


@pytest.mark.asyncio
async def test_real_socket_credential_contract_preserves_provider_shutdown_and_counts(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = await runner.run(tmp_path / "fresh", contract=True, bounded_contract=True)
    assert not result["failures"], result
    assert result["decision"] == "contract-only", result
    assert result["source_unchanged"]
    archive_path = tmp_path / "fresh/source-snapshot.zip"
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == result["manifest"]["source_snapshot_sha256"]
    with zipfile.ZipFile(archive_path) as archive:
        assert all(hashlib.sha256(archive.read(path)).hexdigest() == digest
                   for path, digest in result["manifest"]["source_hashes_start"].items())
    assert result["persistence_pass"] and result["provider_evidence_pass"]
    assert result["server_exit_code"] == 0
    assert result["saved_message_counts"] == [4, 4]
    assert result["provider"]["provider_attempts"] == 4
    assert result["provider"]["maximum_provider_overlap"] >= 1
    assert result["peak_sampled_server_rss_bytes"] > 0
    timings = [json.loads(line) for line in (tmp_path / "fresh/provider-timing.jsonl").read_text().splitlines()]
    assert len([row for row in timings if row["event"] == "start"]) == 4
    assert all(row["budget_and_ledger_admission_wait_ms"] >= 0 for row in timings if row["event"] == "start")
    assert all(row["case"].startswith("group-0-student-") for row in timings)
    assert result["repetitions"][0]["http_failures"] == 0
    assert result["repetitions"][0]["non_answer_actions"] == 0
    with pytest.raises(FileExistsError):
        await runner.run(tmp_path / "fresh", contract=True)


@pytest.mark.asyncio
async def test_authorization_precedes_child_process_and_output(tmp_path, monkeypatch):
    def deny(instrument, operation):
        assert instrument == runner.INSTRUMENT_ID and operation == "external_model_evaluation"
        raise PermissionError("not authorized")
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", deny)
    with pytest.raises(PermissionError):
        await runner.run(tmp_path / "denied", contract=True)
    assert not (tmp_path / "denied").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("candidate, task", [("v8", "question_specific_compact_instruction"),
    ("v9", "question_specific_profile_authority"), ("v10", "question_specific_typed_instruction")])
async def test_compact_candidate_uses_same_config_over_authenticated_https(tmp_path, monkeypatch, candidate, task):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = await runner.run(tmp_path / "compact", contract=True, candidate=candidate)
    assert not result["failures"], result
    assert result["persistence_pass"] and result["provider_evidence_pass"]
    selection = result["manifest"]["candidate_configuration"]
    assert selection["implementation_id"] == f"question-specific-profile-grounded-{candidate}"
    assert result["manifest"]["output_cap"] == 3000
    observed = json.loads((tmp_path / "compact/candidate-observed.json").read_text())
    assert observed["implementation_id"] == selection["implementation_id"]
    calls = [json.loads(line) for line in (tmp_path / "compact/fixture-calls.jsonl").read_text().splitlines()]
    assert any(row["task"] == task for row in calls)
    assert result["saved_message_counts"] == [4, 4]


def test_isolated_server_cannot_expand_existing_call_budget(tmp_path):
    config = tmp_path / "server-config.json"
    config.write_text(json.dumps({"output": str(tmp_path), "maximum_calls": 301}))
    with pytest.raises(ValueError, match="preregistered caps"):
        runner.serve(config)


@pytest.mark.asyncio
@pytest.mark.parametrize("candidate", ["v10-luna-medium", "v10-sol-low", "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"])
async def test_role_variant_reaches_actual_authenticated_https(tmp_path, monkeypatch, candidate):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    output = tmp_path / "role"
    result = await runner.run(output, contract=True, candidate=candidate)
    assert not result["failures"], result
    assert result["persistence_pass"] and result["provider_evidence_pass"]
    selection = result["manifest"]["candidate_configuration"]
    assert selection["implementation_id"] == "question-specific-profile-grounded-" + candidate.split("-")[0]
    assert result["manifest"]["maximum_calls"] == (1200 if candidate in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"} else 800)
    assert result["manifest"]["maximum_reserved_usd"] == (192 if candidate in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"} else 128)
    calls = [json.loads(row) for row in (output / "provider-generation.jsonl").read_text().splitlines()
             if json.loads(row).get("status") == "completed"]
    assert calls
    assert all(row["returned_model"] == selection["model"] for row in calls)
    assert all(row["requested_reasoning_effort"] == selection["reasoning_effort"] for row in calls)
    assert result["saved_message_counts"] == [4, 4]
    if candidate in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"}:
        revision = [json.loads(line) for line in (output / "provider-revision.jsonl").read_text().splitlines() if json.loads(line).get("status") == "completed"]
        assert revision and all(row["returned_model"] == "gpt-5.6-sol" for row in revision)
