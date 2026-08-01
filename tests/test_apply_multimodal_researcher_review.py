from __future__ import annotations

import pytest

from scripts.apply_multimodal_researcher_review import (
    REVIEW_ID,
    apply_review,
)
from scripts.build_multimodal_private_draft import CONFIRMED_SECOND_REVIEW_FIXES


def test_apply_review_marks_acceptance_and_preserves_revision_gate() -> None:
    dataset = {
        "cases": [
            {"case_id": "mmr1-synthetic-flow-01", "review": {"status": "pending", "researcher_verified": False, "notes": "old"}},
            {"case_id": "mmr1-synthetic-flow-02", "review": {"status": "pending", "researcher_verified": False, "notes": "old"}},
        ]
    }
    fixes = {case_id: True for case_id in CONFIRMED_SECOND_REVIEW_FIXES}
    checks = {name: True for name in ("source", "claims", "region", "taxonomy")}
    review = {
        "review_id": REVIEW_ID,
        "policy_confirmed": True,
        "fix_confirmations": fixes,
        "decisions": {
            "mmr1-synthetic-flow-01": {"checks": checks, "decision": "accept", "confirmed": True},
            "mmr1-synthetic-flow-02": {"checks": checks, "decision": "revise", "confirmed": True, "notes": "rewrite wording"},
        },
    }

    result = apply_review(dataset, review)

    assert result["cases"][0]["review"]["status"] == "researcher_verified"
    assert result["cases"][0]["review"]["researcher_verified"] is True
    assert result["cases"][1]["review"]["status"] == "pending"
    assert result["cases"][1]["review"]["researcher_verified"] is False
    assert "rewrite wording" in result["cases"][1]["review"]["notes"]


def test_apply_review_rejects_unconfirmed_case() -> None:
    dataset = {"cases": [{"case_id": "mmr1-synthetic-flow-01", "review": {}}]}
    fixes = {case_id: True for case_id in CONFIRMED_SECOND_REVIEW_FIXES}
    checks = {name: True for name in ("source", "claims", "region", "taxonomy")}
    review = {
        "review_id": REVIEW_ID,
        "policy_confirmed": True,
        "fix_confirmations": fixes,
        "decisions": {
            "mmr1-synthetic-flow-01": {"checks": checks, "decision": "accept", "confirmed": False}
        },
    }

    with pytest.raises(ValueError, match="not confirmed"):
        apply_review(dataset, review)
