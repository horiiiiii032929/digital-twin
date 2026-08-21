from __future__ import annotations

from copy import deepcopy

from scripts.validate_professor_digital_twin_transition import (
    profile_reference_eligible,
    validate_transition,
)


def test_professor_transition_keeps_factual_and_fidelity_layers_separate() -> None:
    result = validate_transition()

    assert result["status"] == "passed"
    assert result["conditions"] == ["C0", "C1", "C2", "C3"]
    assert result["hard_gate_count"] == 4
    assert result["fidelity_dimension_count"] == 5
    assert result["calibration_case_range"] == [8, 12]
    assert result["heldout_content_read"] is False
    assert result["provider_or_model_called"] is False


def test_unapproved_or_partly_approved_profile_cannot_be_reference() -> None:
    profile = {
        "status": "draft-unapproved",
        "dimensions": {
            "teaching_style": {
                "provenance": "explicit",
                "professor_approved": False,
            }
        },
        "approval": {
            "status": "pending",
            "approver_role": "professor",
            "approved_profile_sha256": None,
            "approved_at": None,
        },
    }

    assert profile_reference_eligible(profile) is False

    partial = deepcopy(profile)
    partial["status"] = "approved-reference"
    partial["approval"] = {
        "status": "approved",
        "approver_role": "professor",
        "approved_profile_sha256": "a" * 64,
        "approved_at": "2026-08-21T15:00:00+08:00",
    }
    assert profile_reference_eligible(partial) is False


def test_fully_professor_approved_profile_can_become_reference() -> None:
    profile = {
        "status": "approved-reference",
        "dimensions": {
            "teaching_style": {
                "provenance": "inferred",
                "professor_approved": True,
            },
            "academic_integrity": {
                "provenance": "explicit",
                "professor_approved": True,
            },
        },
        "approval": {
            "status": "approved",
            "approver_role": "professor",
            "approved_profile_sha256": "b" * 64,
            "approved_at": "2026-08-21T15:00:00+08:00",
        },
    }

    assert profile_reference_eligible(profile) is True
