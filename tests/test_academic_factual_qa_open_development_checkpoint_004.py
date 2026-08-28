from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from scripts import run_academic_factual_qa_open_advisory_audit_004 as advisory
from scripts import run_academic_factual_qa_open_development_checkpoint_004 as checkpoint
from scripts import run_academic_factual_qa_open_10000 as product_runner
from src.digital_twin.evaluation.provider_json import DirectProviderJsonTransport


def test_checkpoint_004_is_deterministic_primary_refine_and_revoked() -> None:
    result = checkpoint.validate(require_unauthorized=False)
    assert result["status"] == "passed-build-only"
    assert result["maximum_calls"] == 704
    assert result["maximum_cost_usd"] == 23.0
    assert result["deterministic_scoring_authoritative"] is True
    assert result["advisory_failure_invalidates_deterministic_measurement"] is False
    instrument = json.loads(checkpoint.INSTRUMENT_PATH.read_text(encoding="utf-8"))
    assert "reviewer-calibration" not in instrument["combined_checkpoint"]["stage_order"]
    assert not any(instrument["authorization"].values())
    assert instrument["execution"]["final_execution_authorized"] is False


def test_checkpoint_004_uses_only_exact_direct_openai_models() -> None:
    binding = json.loads(checkpoint.BINDING_PATH.read_text(encoding="utf-8"))
    assert set(binding["providers"]) == {"high-volume-generator", "semantic-reviewer"}
    assert binding["providers"]["high-volume-generator"]["provider_model"] == (
        "gpt-5.4-mini-2026-03-17"
    )
    assert binding["providers"]["semantic-reviewer"]["provider_model"] == (
        "gpt-5.4-2026-03-05"
    )
    serialized = json.dumps(binding).casefold()
    assert all(
        row["provider"] == "openai"
        and row["first_party_endpoint"] is True
        and row["maximum_transport_retries"] == 0
        and row["request_store"] is False
        for row in binding["providers"].values()
    )
    for retired in ("openrouter", "deepseek", "gemini", "mistral", "codex"):
        assert retired not in serialized


def test_advisory_payload_is_strict_non_stored_and_non_authoritative() -> None:
    binding = json.loads(checkpoint.BINDING_PATH.read_text(encoding="utf-8"))
    transport = DirectProviderJsonTransport(binding["providers"]["semantic-reviewer"])
    system, prompt = advisory._prompt(  # noqa: SLF001
        [
            {
                "case_id": "case-001",
                "question": "What does the source state?",
                "expected_action": "answer",
                "canonical_answer": "A source-linked answer.",
                "actual_action": "answer",
                "answer": "A source-linked answer.",
            }
        ]
    )
    payload = transport._payload(  # noqa: SLF001
        system=system,
        prompt=prompt,
        task="test-advisory",
        schema=advisory._schema(1),  # noqa: SLF001
    )
    assert payload["model"] == "gpt-5.4-2026-03-05"
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert "potential_authoritative_truth_defect" in json.dumps(payload)
    assert (
        advisory.validate(require_unauthorized=False)[
            "advisory_failure_invalidates_deterministic_measurement"
        ]
        is False
    )


def test_advisory_selection_covers_every_failure_and_seeded_passes() -> None:
    rows = [
        {
            "case_id": f"case-{index:03d}",
            "answerable": True,
            "fully_grounded_success": index >= 7,
            "boundary_safe": False,
        }
        for index in range(100)
    ]
    failures, sample = advisory.select_audit_cases(
        rows, passing_sample_count=40, seed=20260828
    )
    assert failures == [f"case-{index:03d}" for index in range(7)]
    assert len(sample) == 40
    assert not set(failures) & set(sample)
    assert advisory.select_audit_cases(
        rows, passing_sample_count=40, seed=20260828
    ) == (failures, sample)


def test_advisory_ledger_keeps_provider_failure_as_limitation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledger_path = tmp_path / "advisory.sqlite3"
    monkeypatch.setattr(advisory, "LEDGER_PATH", ledger_path)
    ledger = advisory.AdvisoryLedger(
        binding={"instrument": "fixture"},
        maximum_calls=2,
        maximum_cost=1.0,
        resume=False,
    )
    ledger.fail("request-001", "a" * 64, RuntimeError("malformed advisory"))
    ledger.finish()
    ledger.close()
    connection = sqlite3.connect(ledger_path)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        failure_count = connection.execute(
            "SELECT COUNT(*) FROM calls WHERE status='failed'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert metadata["status"] == "completed-with-limitations"
    assert failure_count == 1


def test_runtime_packages_remain_paired_after_wording() -> None:
    source = json.loads(checkpoint.SOURCE_CASES.read_text(encoding="utf-8"))
    packages = checkpoint.build_runtime_packages(
        {
            "instrument_id": checkpoint.INSTRUMENT_ID,
            "status": "completed-go-deeper",
            "cases": source["cases"],
        }
    )
    assert packages["candidate_cases"]["case_count"] == 500
    assert packages["control_cases"]["case_count"] == 100
    assert packages["candidate_cases"]["dataset_id"] == packages["candidate_gold"][
        "dataset_id"
    ]
    assert packages["control_cases"]["dataset_id"] == packages["control_gold"][
        "dataset_id"
    ]


def test_response_executor_still_has_no_hidden_gold_dependency() -> None:
    source = Path(product_runner.__file__).read_text(encoding="utf-8")
    assert "EvaluationGoldV1" not in source
    assert "DEFAULT_GOLD" not in source
    assert product_runner.validate_contract()["reference_answers_loaded"] is False


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("pass", "completed-keep"),
        ("wording-failure", "completed-refine"),
        ("product-failure", "completed-refine"),
        ("advisory-malformed", "completed-keep"),
        ("truth-defect", "needs-human-review"),
    ],
)
def test_simulations_have_finite_decision_boundaries(
    scenario: str, expected: str
) -> None:
    result = checkpoint.simulate(scenario=scenario)
    assert result["status"] == expected
    assert result["provider_calls"] == 0
    assert result["deterministic_result_changed_by_advisory"] is False


def test_completed_preflight_is_blocked_after_authority_revocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(checkpoint, "_repo_dirty", lambda: False)
    monkeypatch.setattr(checkpoint, "validate", lambda **_: {"status": "passed"})
    result = checkpoint.preflight()
    assert result["status"] == "blocked-not-authorized"
    assert "instrument-paid-execution-authorized-false" in result["blockers"]
    assert "freeze-external_model_evaluation-authorization-missing" in result[
        "blockers"
    ]
    assert result["final_execution_authorized"] is False


def test_resume_state_is_bound_to_instrument_binding_and_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "checkpoint-state.json"
    monkeypatch.setattr(checkpoint, "CHECKPOINT_STATE", state_path)
    monkeypatch.setattr(checkpoint, "_repo_revision", lambda: "revision")
    instrument = {"content_sha256": "instrument"}
    binding = {"content_sha256": "binding"}
    state = checkpoint._initial_state(instrument, binding)
    checkpoint._write_state(state, exclusive=True)
    assert checkpoint._resume_state(instrument, binding)["status"] == "running"
    with pytest.raises(checkpoint.DevelopmentCheckpointError, match="binding drifted"):
        checkpoint._resume_state(instrument, {"content_sha256": "changed"})
