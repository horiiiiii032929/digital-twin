from __future__ import annotations

from pydantic import ValidationError
import pytest

from scripts.build_academic_factual_qa_open_development_v3 import build_packages
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_wording import (
    QuestionWordingRequestV1,
    QuestionWordingResponseV1,
    QuestionWordingReviewResponseV1,
    apply_reviewed_wording_responses,
    apply_wording_responses,
    wording_review_requests,
    wording_requests,
)


def _rows() -> tuple[list[EvaluationCaseV1], list[EvaluationGoldV1]]:
    packages = build_packages()["packages"]
    cases = [
        EvaluationCaseV1.model_validate(row)
        for row in packages["cases"]["cases"][:3]
    ]
    ids = {row.case_id for row in cases}
    gold = [
        EvaluationGoldV1.model_validate(row)
        for row in packages["gold"]["gold"]
        if row["case_id"] in ids
    ]
    return cases, gold


def test_wording_request_excludes_gold_and_source_lineage() -> None:
    cases, _ = _rows()
    requests = wording_requests(cases)

    assert set(requests[0].model_dump()) == {
        "case_id",
        "course_id",
        "slice",
        "canonical_question",
    }
    with pytest.raises(ValidationError):
        QuestionWordingRequestV1.model_validate(
            {**requests[0].model_dump(), "canonical_answer": "forbidden"}
        )


def test_safe_wording_changes_only_the_public_question() -> None:
    cases, gold = _rows()
    responses = [
        QuestionWordingResponseV1(
            case_id=row.case_id,
            question=f"Could you explain this course concept for case {index}?",
        )
        for index, row in enumerate(cases, start=1)
    ]

    output, decisions = apply_wording_responses(
        cases=cases,
        gold=gold,
        responses=responses,
    )

    assert all(row.status == "accepted-model-wording" for row in decisions)
    assert [row.model_copy(update={"question": old.question}) for row, old in zip(output, cases, strict=True)] == cases


def test_leak_duplicate_and_missing_response_fail_back_to_canonical() -> None:
    cases, gold = _rows()
    answer = next(row.canonical_answer for row in gold if row.case_id == cases[0].case_id)
    responses = [
        QuestionWordingResponseV1(
            case_id=cases[0].case_id,
            question=f"Is the answer {answer}?",
        ),
        QuestionWordingResponseV1(
            case_id=cases[1].case_id,
            question="Explain this concept?",
        ),
        QuestionWordingResponseV1(
            case_id=cases[1].case_id,
            question="Explain it differently?",
        ),
    ]

    output, decisions = apply_wording_responses(
        cases=cases,
        gold=gold,
        responses=responses,
    )

    assert [row.status for row in decisions] == [
        "canonical-fallback",
        "canonical-fallback",
        "canonical-fallback",
    ]
    assert [row.question for row in output] == [row.question for row in cases]


def test_review_boundary_contains_only_public_question_wording() -> None:
    cases, _ = _rows()
    responses = [
        QuestionWordingResponseV1(
            case_id=row.case_id,
            question=f"Could a student ask this naturally for case {index}?",
        )
        for index, row in enumerate(cases, start=1)
    ]

    requests = wording_review_requests(cases=cases, responses=responses)

    assert set(requests[0].model_dump()) == {
        "case_id",
        "canonical_question",
        "candidate_question",
    }
    assert "canonical_answer" not in requests[0].model_dump_json()
    assert "claims" not in requests[0].model_dump_json()


def test_reviewer_rejection_forces_canonical_fallback() -> None:
    cases, gold = _rows()
    responses = [
        QuestionWordingResponseV1(
            case_id=row.case_id,
            question=f"Could you explain the requested concept for case {index}?",
        )
        for index, row in enumerate(cases, start=1)
    ]
    reviews = [
        QuestionWordingReviewResponseV1(
            case_id=row.case_id,
            accept=index != 2,
            faithfulness="faithful" if index != 2 else "meaning-shift",
            naturalness="acceptable",
            rationale="Bounded advisory review.",
        )
        for index, row in enumerate(cases, start=1)
    ]

    output, decisions = apply_reviewed_wording_responses(
        cases=cases,
        gold=gold,
        responses=responses,
        reviews=reviews,
    )

    assert decisions[1].status == "canonical-fallback"
    assert decisions[1].reason == "review-rejected-or-missing"
    assert output[1].question == cases[1].question
