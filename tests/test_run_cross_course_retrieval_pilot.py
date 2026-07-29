"""Tests for cross-course retrieval pilot metrics."""

from scripts.run_cross_course_retrieval_pilot import (
    assign_boundary_courses,
    score_ranking,
)


def test_score_ranking_rewards_complete_multi_evidence_at_three() -> None:
    result = score_ranking(
        ["gold-a", "gold-b"],
        ["noise", "gold-b", "gold-a", "other"],
    )

    assert result["complete_evidence_at_3"] is True
    assert result["recall_at_1"] == 0
    assert result["recall_at_3"] == 1
    assert result["recall_at_5"] == 1
    assert result["mrr"] == 0.5
    assert 0 < result["ndcg_at_10"] < 1


def test_score_ranking_penalizes_missing_evidence() -> None:
    result = score_ranking(
        ["gold-a", "gold-b"],
        ["gold-a", "noise"],
    )

    assert result["complete_evidence_at_3"] is False
    assert result["recall_at_3"] == 0.5
    assert result["mrr"] == 1


def test_assign_boundary_courses_is_deterministic_and_balanced() -> None:
    cases = [
        {"case_id": "negative-2", "slice": "no_evidence"},
        {"case_id": "positive", "slice": "answerable"},
        {"case_id": "negative-1", "slice": "adversarial_integrity"},
        {"case_id": "negative-3", "slice": "no_evidence"},
    ]

    result = assign_boundary_courses(cases, ["A", "B"])

    assert result == {
        "negative-1": "A",
        "negative-2": "B",
        "negative-3": "A",
    }
