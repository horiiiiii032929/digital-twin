"""Tests for the blinded cross-course benchmark second review."""

from scripts.second_review_cross_course_benchmark import (
    CHECK_FIELDS,
    blinded_case,
    select_cases,
    validate_decision,
)


def _case(
    case_id: str,
    *,
    course_id: str,
    slice_name: str,
) -> dict:
    return {
        "case_id": case_id,
        "target_course_id": course_id,
        "slice": slice_name,
        "query": "Synthetic question?",
        "expected_action": "retrieve",
        "required_claims": ["Synthetic claim."],
        "gold_evidence": [
            {
                "supporting_quote": "Synthetic supporting evidence.",
                "visual_dependency": "text_sufficient",
            }
        ],
        "review": {
            "status": "researcher_verified",
            "researcher_verified": True,
            "notes": "Must not reach blinded prompt.",
        },
    }


def test_select_cases_is_stratified_and_deterministic() -> None:
    cases = []
    for course_id in ("IT5002", "CS5421", "IT5100B", "IT5100E"):
        cases.extend(
            _case(
                f"{course_id}-answerable-{index}",
                course_id=course_id,
                slice_name="answerable",
            )
            for index in range(5)
        )
        cases.extend(
            _case(
                f"{course_id}-confusion-{index}",
                course_id=course_id,
                slice_name="cross_course_confusion",
            )
            for index in range(3)
        )

    selected = select_cases(cases)

    assert len(selected) == 20
    assert [case["case_id"] for case in selected] == [
        case["case_id"] for case in select_cases(list(reversed(cases)))
    ]
    for course_id in ("IT5002", "CS5421", "IT5100B", "IT5100E"):
        course_cases = [
            case for case in selected if case["target_course_id"] == course_id
        ]
        assert sum(case["slice"] == "answerable" for case in course_cases) == 3
        assert (
            sum(
                case["slice"] == "cross_course_confusion"
                for case in course_cases
            )
            == 2
        )


def test_blinded_case_excludes_review_and_split_metadata() -> None:
    value = blinded_case(
        _case("case-1", course_id="IT5002", slice_name="answerable")
    )

    assert set(value) == {
        "question",
        "expected_action",
        "required_claims",
        "evidence",
    }
    assert "review" not in value
    assert "case_id" not in value


def test_validate_decision_requires_boolean_consistency() -> None:
    accepted = {
        "decision": "accept",
        **{field: True for field in CHECK_FIELDS},
        "reason": "All checks pass.",
    }
    assert validate_decision(accepted) == accepted

    rejected = {
        "decision": "reject",
        **{field: True for field in CHECK_FIELDS},
        "reason": "Inconsistent.",
    }
    rejected["claims_supported"] = False
    assert validate_decision(rejected) == rejected
