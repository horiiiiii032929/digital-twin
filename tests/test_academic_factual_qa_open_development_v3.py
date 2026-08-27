from __future__ import annotations

from scripts.audit_academic_factual_qa_open_development_v2 import (
    audit_corrected_package,
)
from scripts.build_academic_factual_qa_open_development_v3 import build_packages
from scripts.build_academic_factual_qa_open_source_plan_v2 import (
    TARGET_MODALITY_COUNTS,
    build_source_plan,
)
from src.digital_twin.evaluation.factual_qa_references import SourceClusterV2


def test_complete_region_source_plan_is_balanced_stable_and_development_only() -> None:
    first = build_source_plan()
    second = build_source_plan()

    assert first["content_sha256"] == second["content_sha256"]
    assert first["cluster_count"] == 100
    assert first["case_count_after_deterministic_build"] == 500
    assert first["course_distribution"] == {
        "computer-networking": 25,
        "data-structures": 25,
        "operating-systems": 25,
        "python-programming": 25,
    }
    assert first["modality_distribution"] == TARGET_MODALITY_COUNTS
    assert first["provider_calls"] == 0
    assert first["private_data_read"] is False
    assert first["final_split_opened"] is False
    clusters = [SourceClusterV2.model_validate(row) for row in first["clusters"]]
    assert all(len(row.reference_targets) == 4 for row in clusters)


def test_corrected_development_package_is_separate_and_byte_stable() -> None:
    first = build_packages()
    second = build_packages()

    assert first["status"] == "passed-build-only"
    assert first["case_count"] == 500
    assert first["control_case_count"] == 100
    assert first["answerable_count"] == 400
    assert first["boundary_count"] == 100
    assert first["normalized_duplicate_count"] == 0
    assert first["canonical_answer_leak_count"] == 0
    assert first["provider_calls"] == 0
    assert first["final_cases_constructed"] == 0
    assert {
        key: value["content_sha256"] for key, value in first["packages"].items()
    } == {
        key: value["content_sha256"] for key, value in second["packages"].items()
    }
    assert all(
        "canonical_answer" not in row
        and "expected_action" not in row
        and "claims" not in row
        for row in first["packages"]["cases"]["cases"]
    )


def test_corrected_pre_spend_audit_passes_complete_reference_gates() -> None:
    result = audit_corrected_package()

    assert result["status"] == "completed-keep"
    assert result["case_count"] == 500
    assert result["answerable_case_count"] == 400
    assert result["boundary_case_count"] == 100
    assert result["public_gold_field_count"] == 0
    assert result["normalized_duplicate_count"] == 0
    assert result["canonical_answer_leak_count"] == 0
    assert result["complete_text_target_count"] == result["text_target_count"]
    assert result["complete_structured_target_count"] == result["structured_target_count"]
    assert result["defect_count"] == 0
    assert len(result["priority_packet"]) == 12
    assert result["provider_calls"] == 0
    assert result["final_split_opened"] is False
