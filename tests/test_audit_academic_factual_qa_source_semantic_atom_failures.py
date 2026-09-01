from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_academic_factual_qa_source_semantic_atom_failures import (
    DEFAULT_INSTRUMENT,
    FailureAdjudicationV1,
    FailureValidityAuditError,
    _audit,
    _instrument,
    validate,
)


def test_failure_validity_audit_covers_exact_16_failures() -> None:
    result = validate(DEFAULT_INSTRUMENT)

    assert result["status"] == "passed"
    assert result["failure_count"] == 16
    assert result["provider_calls"] == 0
    assert result["official_prior_metrics_changed"] is False


def test_failure_validity_audit_preserves_result_and_finds_dual_defect() -> None:
    result = _audit(_instrument(DEFAULT_INSTRUMENT))

    assert result["prior_result_status_unchanged"] == "completed-refine"
    assert result["official_prior_metrics_changed"] is False
    assert result["aggregate"] == {
        "gold_in_retrieved_top_3": 16,
        "selected_claim_source_supported": 16,
        "reference_invalid_for_release_scoring": 16,
        "corrected_expected_action_clarify": 16,
        "product_answered_instead_of_clarified": 16,
        "dual_reference_and_product_defect": 16,
        "evaluator_only_false_positive": 0,
        "product_only_failure": 0,
    }
    sensitivity = result["descriptive_sensitivity_only"]
    assert sensitivity["corrected_overall_action_accuracy"] == pytest.approx(0.968)
    assert sensitivity["corrected_boundary_action_accuracy"] == pytest.approx(100 / 116)
    assert result["interpretation"]["release_decision"] == "no-release-remains"


def test_adjudication_rejects_duplicate_plausible_regions() -> None:
    with pytest.raises(ValueError, match="plausible regions must be unique"):
        FailureAdjudicationV1.model_validate(
            {
                "case_id": "case-1",
                "question_uniquely_identifies_gold": False,
                "corrected_expected_action": "clarify",
                "selected_answer_relationship": "partial-supported",
                "plausible_region_ids": ["region-1", "region-1"],
                "reference_valid_for_release_scoring": False,
                "product_behavior_valid_under_corrected_action": False,
                "disposition": "dual-reference-and-product-ambiguity-defect",
                "rationale": "This sufficiently long rationale describes an ambiguous reference case.",
            }
        )


def test_instrument_rejects_hash_drift(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["expected_failure_count"] = 15
    path = tmp_path / "instrument.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(FailureValidityAuditError, match="instrument hash drifted"):
        _instrument(path)
