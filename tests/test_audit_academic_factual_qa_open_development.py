from __future__ import annotations

from scripts.audit_academic_factual_qa_open_development import (
    _quality_flags,
    audit_development_package,
)


def test_pre_spend_audit_preserves_structural_pass_and_blocks_product_use() -> None:
    result = audit_development_package()

    assert result["status"] == "completed-refine"
    assert result["case_count"] == 500
    assert result["answerable_case_count"] == 400
    assert result["boundary_case_count"] == 100
    assert result["structural_gate_passed"] is True
    assert result["public_gold_field_count"] == 0
    assert result["normalized_duplicate_count"] == 0
    assert result["canonical_answer_leak_count"] == 0
    assert result["lineage_defect_count"] == 0
    assert result["canonical_template_case_count"] == 500
    assert result["high_risk_answerable_case_count"] == 227
    assert result["high_risk_cluster_count"] == 68
    assert result["provider_calls"] == 0
    assert result["private_data_used"] is False
    assert result["final_split_opened"] is False


def test_quality_flags_distinguish_complete_text_from_fragment() -> None:
    case = {"slice": "direct-factual"}
    complete = {
        "expected_action": "answer",
        "canonical_answer": "A complete source statement ends here.",
    }
    fragment = {
        "expected_action": "answer",
        "canonical_answer": "which stops in the middle",
    }

    assert _quality_flags(case, complete) == []
    assert _quality_flags(case, fragment) == [
        "possible-fragment-start",
        "possible-fragment-end",
    ]


def test_structured_quality_flags_require_matching_evidence_signal() -> None:
    answer = {"expected_action": "answer", "canonical_answer": "plain prose."}

    assert _quality_flags({"slice": "structured-code"}, answer) == [
        "structured-code-signal-missing"
    ]
    assert _quality_flags({"slice": "structured-equation"}, answer) == [
        "structured-equation-signal-missing"
    ]
    assert _quality_flags({"slice": "structured-table"}, answer) == [
        "structured-table-signal-missing"
    ]
