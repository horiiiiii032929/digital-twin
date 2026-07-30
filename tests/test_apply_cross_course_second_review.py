"""Tests for applying the blinded benchmark second review."""

import pytest

from scripts.apply_cross_course_second_review import apply_second_review


def _dataset() -> dict:
    return {
        "dataset_status": "researcher_review",
        "cases": [
            {
                "case_id": f"case-{index}",
                "review": {
                    "status": "researcher_verified",
                    "researcher_verified": True,
                    "second_reviewed": False,
                    "notes": "Primary review.",
                },
            }
            for index in range(20)
        ],
    }


def _result() -> dict:
    return {
        "review_id": "review-v1",
        "model": "local-reviewer",
        "model_digest": "abc123",
        "decisions": [
            {
                "case_id": f"case-{index}",
                "decision": {
                    "decision": "reject" if index == 5 else "accept",
                },
            }
            for index in range(20)
        ],
    }


def _adjudication() -> dict:
    return {
        "review_id": "review-v1",
        "case_id": "case-5",
        "original_decision": "reject",
        "adjudication": "retain",
        "adjudicator": "researcher",
        "rationale": "The rejection used contradictory reasoning.",
    }


def test_apply_second_review_preserves_rejection_and_marks_sample() -> None:
    dataset = _dataset()

    apply_second_review(dataset, _result(), _adjudication())

    assert dataset["dataset_status"] == "approved"
    assert all(case["review"]["second_reviewed"] for case in dataset["cases"])
    assert "returned reject" in dataset["cases"][5]["review"]["notes"]
    assert "adjudicated as retain" in dataset["cases"][5]["review"]["notes"]


def test_apply_second_review_requires_matching_adjudication() -> None:
    adjudication = _adjudication()
    adjudication["case_id"] = "case-6"

    with pytest.raises(ValueError, match="case ID mismatch"):
        apply_second_review(_dataset(), _result(), adjudication)
