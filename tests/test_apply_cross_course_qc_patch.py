"""Tests for traceable private benchmark QC patch helpers."""

from scripts.apply_cross_course_qc_patch import apply_case_fields
from scripts.draft_cross_course_benchmark import sha256_text


def test_apply_case_fields_resets_review_and_rehashes_quote() -> None:
    case = {
        "case_id": "ccr1-example-01",
        "query": "Old query",
        "difficulty": "direct",
        "topic": "old",
        "required_claims": ["Old claim"],
        "gold_evidence": [
            {
                "supporting_quote": "Old quote",
                "quote_sha256": sha256_text("Old quote"),
            }
        ],
        "review": {
            "status": "researcher_verified",
            "researcher_verified": True,
            "second_reviewed": False,
            "reviewer": "researcher",
            "reviewed_at": "2026-07-28T00:00:00+09:00",
            "notes": "",
        },
    }

    apply_case_fields(
        case,
        {
            "query": "Revised query",
            "required_claims": ["Revised claim"],
            "supporting_quotes": ["Revised quote"],
        },
    )

    assert case["query"] == "Revised query"
    assert case["required_claims"] == ["Revised claim"]
    assert case["gold_evidence"][0]["quote_sha256"] == sha256_text(
        "Revised quote"
    )
    assert case["review"]["status"] == "machine_draft"
    assert case["review"]["researcher_verified"] is False
