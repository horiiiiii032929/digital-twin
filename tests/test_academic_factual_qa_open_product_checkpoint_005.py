from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest

from scripts import build_academic_factual_qa_open_mixed_wording_005 as materializer
from scripts import run_academic_factual_qa_open_10000 as product_runner
from scripts import run_academic_factual_qa_open_product_checkpoint_005 as checkpoint
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.repository_freeze import RepositoryFreezeError


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_mixed_wording_package_is_exact_and_explicit() -> None:
    result = materializer.check()
    assert result["case_count"] == 500
    assert result["control_case_count"] == 100
    assert result["accepted_model_wording_count"] == 452
    assert result["canonical_fallback_count"] == 48
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False

    candidate = _load(materializer.CANDIDATE_CASES)
    control = _load(materializer.CONTROL_CASES)
    provenance = _load(materializer.PROVENANCE)
    assert set(candidate) == {
        "schema_version",
        "dataset_id",
        "split",
        "case_count",
        "cases",
        "content_sha256",
    }
    assert set(control) == set(candidate)
    candidate_ids = {row["case_id"] for row in candidate["cases"]}
    control_ids = {row["case_id"] for row in control["cases"]}
    assert len(candidate_ids) == 500
    assert len(control_ids) == 100
    assert control_ids < candidate_ids
    assert len({normalize_question(row["question"]) for row in candidate["cases"]}) == 500
    assert Counter(row["wording_source"] for row in provenance["wording_by_case"]) == {
        "accepted-model-wording": 452,
        "canonical-fallback": 48,
    }


def test_every_canonical_fallback_matches_the_original_public_question() -> None:
    candidate = {
        row["case_id"]: row
        for row in _load(materializer.CANDIDATE_CASES)["cases"]
    }
    source = {
        row["case_id"]: row
        for row in _load(materializer.SOURCE_CASES)["cases"]
    }
    provenance = _load(materializer.PROVENANCE)
    fallback_ids = {
        row["case_id"]
        for row in provenance["wording_by_case"]
        if row["wording_source"] == "canonical-fallback"
    }
    assert len(fallback_ids) == 48
    assert all(candidate[case_id]["question"] == source[case_id]["question"] for case_id in fallback_ids)


def test_mixed_wording_rematerialization_is_revoked() -> None:
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        materializer.write()


def test_product_checkpoint_is_build_only_and_has_no_wording_stage() -> None:
    result = checkpoint.validate()
    assert result["status"] == "passed-build-only"
    assert result["maximum_calls"] == 654
    assert result["maximum_cost_usd"] == 18.0
    assert result["wording_provider_calls"] == 0
    assert result["hidden_gold_visible_to_product"] is False
    instrument = _load(checkpoint.INSTRUMENT_PATH)
    assert instrument["combined_checkpoint"]["stage_order"] == [
        "candidate-500",
        "control-100",
        "deterministic-score-and-compare",
        "non-blocking-advisory-audit",
    ]
    assert not any(instrument["authorization"].values())
    assert instrument["execution"]["final_execution_authorized"] is False


def test_product_checkpoint_uses_only_exact_direct_openai_models() -> None:
    binding = _load(checkpoint.BINDING_PATH)
    assert set(binding["providers"]) == {"high-volume-generator", "semantic-reviewer"}
    assert binding["providers"]["high-volume-generator"]["provider_model"] == (
        "gpt-5.4-mini-2026-03-17"
    )
    assert binding["providers"]["semantic-reviewer"]["provider_model"] == (
        "gpt-5.4-2026-03-05"
    )
    assert all(
        row["provider"] == "openai"
        and row["first_party_endpoint"] is True
        and row["maximum_transport_retries"] == 0
        and row["request_store"] is False
        for row in binding["providers"].values()
    )
    serialized = json.dumps(binding).casefold()
    for retired in ("openrouter", "deepseek", "gemini", "mistral", "codex"):
        assert retired not in serialized


def test_candidate_and_control_manifests_differ_only_by_condition() -> None:
    candidate = _load(checkpoint.CANDIDATE_MANIFEST)
    control = _load(checkpoint.CONTROL_MANIFEST)
    assert candidate["known_benchmark"] is True
    assert control["known_benchmark"] is True
    assert candidate["evidence_gate"] == "structured-lexical-coverage-evidence-gate-v1"
    assert control["evidence_gate"] == "any-hit-evidence-gate-v1"
    for key in set(candidate) - {"flow_id", "evidence_gate"}:
        assert candidate[key] == control[key]


def test_response_executor_remains_physically_separate_from_hidden_gold() -> None:
    source = Path(product_runner.__file__).read_text(encoding="utf-8")
    assert "EvaluationGoldV1" not in source
    assert "DEFAULT_GOLD" not in source
    assert product_runner.validate_contract()["reference_answers_loaded"] is False
    checkpoint_source = Path(checkpoint.__file__).read_text(encoding="utf-8")
    assert "run_academic_factual_qa_open_wording" not in checkpoint_source


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("pass", "completed-keep"),
        ("product-failure", "completed-refine"),
        ("provider-failure", "invalid-execution"),
        ("advisory-malformed", "completed-keep"),
        ("truth-defect", "needs-human-review"),
    ],
)
def test_product_checkpoint_simulations_are_finite(
    scenario: str, expected: str
) -> None:
    result = checkpoint.simulate(scenario=scenario)
    assert result["status"] == expected
    assert result["wording_provider_calls"] == 0
    assert result["provider_calls"] == 0
    assert result["hidden_gold_visible_to_product"] is False
    assert result["deterministic_result_changed_by_advisory"] is False


def test_product_preflight_is_blocked_only_by_missing_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(checkpoint, "_repo_dirty", lambda: False)
    result = checkpoint.preflight()
    assert result["status"] == "blocked-not-authorized"
    assert result["wording_provider_calls"] == 0
    assert result["final_execution_authorized"] is False
    assert "instrument-paid-execution-authorized-false" in result["blockers"]
    assert "freeze-external_model_evaluation-authorization-missing" in result[
        "blockers"
    ]
    assert not any("wording" in blocker for blocker in result["blockers"])
    assert not any("missing" in blocker and "authorization" not in blocker for blocker in result["blockers"])


def test_resume_is_bound_to_dataset_instrument_binding_and_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "checkpoint-state.json"
    monkeypatch.setattr(checkpoint, "CHECKPOINT_STATE", state_path)
    monkeypatch.setattr(checkpoint, "_repo_revision", lambda: "revision")
    instrument = {
        "content_sha256": "instrument",
        "dataset": {
            "public_cases_content_sha256": "candidate",
            "control_cases_content_sha256": "control",
            "wording_provenance_content_sha256": "provenance",
        },
    }
    binding = {"content_sha256": "binding"}
    state = checkpoint._initial_state(instrument, binding)
    checkpoint._write_state(state, exclusive=True)
    assert checkpoint._resume_state(instrument, binding)["status"] == "running"
    changed = {**instrument, "dataset": {**instrument["dataset"], "public_cases_content_sha256": "changed"}}
    with pytest.raises(checkpoint.ProductCheckpointError, match="binding drifted"):
        checkpoint._resume_state(changed, binding)
