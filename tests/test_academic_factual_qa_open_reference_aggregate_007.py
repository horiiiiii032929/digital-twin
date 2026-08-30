from __future__ import annotations

from collections import Counter

from scripts import build_academic_factual_qa_open_reference_aggregate_007 as builder
from src.digital_twin.evaluation import EvaluationCaseV1, EvaluationGoldV1


def test_question_stratified_reference_package_is_complete_and_stable() -> None:
    result = builder.check()

    assert result["status"] == "passed-question-stratified-reference-package"
    assert result["case_count"] == 500
    assert result["answerable_count"] == 400
    assert result["boundary_count"] == 100
    assert result["control_case_count"] == 100
    assert result["source_cluster_count"] == 134
    assert result["provider_calls"] == 0
    assert result["product_calls"] == 0
    assert result["final_split_opened"] is False


def test_question_stratification_preserves_course_and_position_balance() -> None:
    packages = builder.validate_packages()
    cases = [
        EvaluationCaseV1.model_validate(row)
        for row in packages[builder.CASES_PATH]["cases"]
    ]
    gold = [
        EvaluationGoldV1.model_validate(row)
        for row in packages[builder.GOLD_PATH]["gold"]
    ]

    assert Counter(row.course_id for row in cases) == Counter(
        {course_id: 125 for course_id in builder.COURSES}
    )
    assert Counter(builder._case_position(row.case_id) for row in cases) == Counter(  # noqa: SLF001
        {position: 100 for position in ("q1", "q2", "q3", "q4", "q5")}
    )
    assert sum(row.expected_action.value == "answer" for row in gold) == 400
    assert all(row.claims for row in gold if row.expected_action.value == "answer")
    assert all(
        not row.claims for row in gold if row.expected_action.value != "answer"
    )


def test_paired_control_is_a_balanced_candidate_subset() -> None:
    packages = builder.validate_packages()
    cases = [
        EvaluationCaseV1.model_validate(row)
        for row in packages[builder.CASES_PATH]["cases"]
    ]
    control = [
        EvaluationCaseV1.model_validate(row)
        for row in packages[builder.CONTROL_CASES_PATH]["cases"]
    ]

    assert {row.case_id for row in control} < {row.case_id for row in cases}
    assert Counter(row.course_id for row in control) == Counter(
        {course_id: 25 for course_id in builder.COURSES}
    )
    assert Counter(builder._case_position(row.case_id) for row in control) == Counter(  # noqa: SLF001
        {position: 20 for position in ("q1", "q2", "q3", "q4", "q5")}
    )
