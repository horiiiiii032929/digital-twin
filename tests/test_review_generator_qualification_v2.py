import pytest

from scripts.review_generator_qualification_v2 import (
    CHECK_FIELDS,
    STRESS_PROBES,
    blinded_case,
    stable_seed,
    validate_decision,
    validate_stress_decision,
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
        "reason": "The answer action states the marker timing from source s1.",
    }
    assert validate_decision(approved) == approved

    invalid = {**approved, "uncertain": True}
    with pytest.raises(ValueError, match="does not agree"):
        validate_decision(invalid)


def test_review_rejects_copied_v1_template_reason():
    copied = {
        "decision": "approve",
        **{field: True for field in CHECK_FIELDS},
        "uncertain": False,
        "reason": "All applicable checks pass using only the supplied evidence.",
    }
    with pytest.raises(ValueError, match="generic template"):
        validate_decision(copied)


def test_stress_gate_requires_expected_failure_fields():
    probe = next(
        item for item in STRESS_PROBES if item["probe_id"] == "missing-citation"
    )
    decision = {
        "decision": "revise",
        **{field: True for field in CHECK_FIELDS},
        "citation_completeness": False,
        "uncertain": False,
        "reason": "The answer cites no source for the marker timing.",
    }
    validate_stress_decision(probe, decision)

    with pytest.raises(ValueError, match="missed checks"):
        validate_stress_decision(probe, {**decision, "citation_completeness": True})


def test_review_seed_is_stable_and_case_specific():
    assert stable_seed("case-a") == stable_seed("case-a")
    assert stable_seed("case-a") != stable_seed("case-b")
