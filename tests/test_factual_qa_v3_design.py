from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.validate_factual_qa_v3_design import load_instrument, validate_instrument


def test_frozen_v3_design_passes() -> None:
    result = validate_instrument(load_instrument())

    assert result["status"] == "passed"
    assert result["regular_file_count"] == 2637
    assert result["external_execution_authorized"] is False


def test_external_execution_cannot_be_silently_enabled() -> None:
    payload = deepcopy(load_instrument())
    payload["model_policy"]["external_execution_authorized"] = True

    with pytest.raises(ValueError, match="external execution is not authorized"):
        validate_instrument(payload)


def test_mandatory_exclusion_cannot_be_removed() -> None:
    payload = deepcopy(load_instrument())
    payload["mandatory_exclusions"].remove("student_or_participant_data")

    with pytest.raises(ValueError, match="mandatory exclusions changed"):
        validate_instrument(payload)


def test_claim_evidence_requires_exact_quote() -> None:
    payload = deepcopy(load_instrument())
    payload["response_contract"]["evidence_required_fields"] = ["citation_id"]

    with pytest.raises(ValueError, match="evidence contract changed"):
        validate_instrument(payload)


def test_dummy_control_cannot_claim_real_course_quality() -> None:
    payload = deepcopy(load_instrument())
    payload["lanes"]["oracle_control"]["may_establish_real_course_quality"] = True

    with pytest.raises(ValueError, match="dummy control cannot establish"):
        validate_instrument(payload)


def test_audit_packet_cannot_drop_source_checksum() -> None:
    payload = deepcopy(load_instrument())
    payload["human_audit_required_fields"].remove("source_version_and_checksum")
    payload["human_audit_required_fields"].append("placeholder")

    with pytest.raises(ValueError, match="audit packet contract is incomplete"):
        validate_instrument(payload)
