import pytest

from scripts.review_generator_qualification_v2 import (
    CHECK_FIELDS,
    blinded_case,
    stable_seed,
    validate_decision,
)


def test_blinded_case_excludes_candidate_identity_and_prior_result():
    case = {
        "scenario_type": "ambiguity",
        "question": "Which bridge?",
        "expected_action": "clarify",
        "required_claim_term_groups": [],
        "forbidden_answer_terms": [],
        "citation_required": False,
        "candidate_evidence": [
            {"source_id": "shown", "text": "Shown", "presented": True},
            {"source_id": "hidden", "text": "Hidden", "presented": False},
        ],
    }
    result = {
        "actual_action": "answer",
        "answer": "There are two meanings.",
        "citation_sources": ["shown"],
        "provider_model": "must-not-leak",
        "deterministic_checks_passed": False,
    }

    payload = blinded_case(case, result)

    assert payload["presented_evidence"] == [{"source_id": "shown", "text": "Shown"}]
    assert "provider_model" not in str(payload)
    assert "deterministic" not in str(payload)


def test_review_decision_requires_all_checks_and_no_uncertainty():
    approved = {
        "decision": "approve",
        **{field: True for field in CHECK_FIELDS},
        "uncertain": False,
        "reason": "All checks pass.",
    }
    assert validate_decision(approved) == approved

    invalid = {**approved, "uncertain": True}
    with pytest.raises(ValueError, match="does not agree"):
        validate_decision(invalid)


def test_review_seed_is_stable_and_case_specific():
    assert stable_seed("case-a") == stable_seed("case-a")
    assert stable_seed("case-a") != stable_seed("case-b")
