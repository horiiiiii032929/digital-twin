#!/usr/bin/env python3
"""Validate the provider-free Professor Digital Twin transition contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ROOT = ROOT / "research/05_evaluation/instruments"
SCHEMA_PATH = INSTRUMENT_ROOT / "professor_digital_twin_profile_v1.schema.json"
PROFILE_PATH = INSTRUMENT_ROOT / "professor_digital_twin_profile_v1_synthetic.json"
PACKET_PATH = INSTRUMENT_ROOT / "professor_fidelity_calibration_packet_v1_template.json"
FIDELITY_PATH = INSTRUMENT_ROOT / "professor_fidelity_v1.json"
EXPECTED_CONDITIONS = ("C0", "C1", "C2", "C3")
EXPECTED_HARD_GATES = {
    "factual_correctness",
    "citation_grounding",
    "safety",
    "boundary_action",
}
EXPECTED_FIDELITY_DIMENSIONS = {
    "teaching_style",
    "explanation_depth",
    "example_policy",
    "misconception_handling",
    "academic_integrity",
}


class ProfessorTransitionError(ValueError):
    """Raised when a fidelity transition contract is unsafe or incomplete."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProfessorTransitionError(f"cannot load transition artifact: {path}") from error
    if not isinstance(value, dict):
        raise ProfessorTransitionError(f"transition artifact root is not an object: {path}")
    return value


def profile_reference_eligible(profile: dict[str, Any]) -> bool:
    approval = profile.get("approval", {})
    dimensions = profile.get("dimensions", {})
    return (
        profile.get("status") == "approved-reference"
        and approval.get("status") == "approved"
        and approval.get("approver_role") == "professor"
        and isinstance(approval.get("approved_profile_sha256"), str)
        and len(approval["approved_profile_sha256"]) == 64
        and isinstance(approval.get("approved_at"), str)
        and bool(dimensions)
        and all(
            isinstance(dimension, dict)
            and dimension.get("provenance") in {"explicit", "inferred"}
            and dimension.get("professor_approved") is True
            for dimension in dimensions.values()
        )
    )


def validate_transition() -> dict[str, Any]:
    schema = _load(SCHEMA_PATH)
    profile = _load(PROFILE_PATH)
    packet = _load(PACKET_PATH)
    fidelity = _load(FIDELITY_PATH)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(profile),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        raise ProfessorTransitionError(
            "synthetic professor profile violates schema: "
            + "; ".join(error.message for error in errors)
        )
    if profile_reference_eligible(profile):
        raise ProfessorTransitionError("unapproved synthetic profile became a reference")
    dimensions = profile["dimensions"]
    if set(dimensions) != EXPECTED_FIDELITY_DIMENSIONS:
        raise ProfessorTransitionError("professor profile dimensions drifted")
    if {dimension["provenance"] for dimension in dimensions.values()} != {
        "explicit",
        "inferred",
    }:
        raise ProfessorTransitionError("profile does not exercise both provenance modes")

    conditions = fidelity.get("conditions")
    if not isinstance(conditions, list):
        raise ProfessorTransitionError("professor fidelity conditions are absent")
    by_id = {condition.get("condition_id"): condition for condition in conditions}
    if tuple(by_id) != EXPECTED_CONDITIONS:
        raise ProfessorTransitionError("C0-C3 condition order or identity drifted")
    if by_id["C0"].get("evidence") != "none":
        raise ProfessorTransitionError("C0 must remain the no-context baseline")
    if by_id["C1"].get("evidence") != "oracle" or by_id["C2"].get("evidence") != "oracle":
        raise ProfessorTransitionError("C1 and C2 must share oracle evidence")
    if by_id["C1"].get("policy") == by_id["C2"].get("policy"):
        raise ProfessorTransitionError("C1 and C2 must isolate professor policy")
    if by_id["C2"].get("policy") != by_id["C3"].get("policy"):
        raise ProfessorTransitionError("C2 and C3 must share professor policy")
    if by_id["C3"].get("evidence") == "oracle":
        raise ProfessorTransitionError("C3 must exercise selected retrieval")

    if packet.get("status") != "template-awaiting-professor-guidance":
        raise ProfessorTransitionError("calibration packet must remain guidance-blocked")
    if packet.get("case_count_min") != 8 or packet.get("case_count_max") != 12:
        raise ProfessorTransitionError("calibration packet must remain bounded to 8-12 cases")
    if packet.get("conditions") != list(EXPECTED_CONDITIONS):
        raise ProfessorTransitionError("calibration packet conditions drifted")
    if set(packet.get("hard_gates", [])) != EXPECTED_HARD_GATES:
        raise ProfessorTransitionError("calibration hard gates drifted")
    if set(packet.get("fidelity_dimensions", [])) != EXPECTED_FIDELITY_DIMENSIONS:
        raise ProfessorTransitionError("calibration fidelity dimensions drifted")
    if EXPECTED_HARD_GATES.intersection(EXPECTED_FIDELITY_DIMENSIONS):
        raise ProfessorTransitionError("hard gates and fidelity dimensions overlap")
    if packet.get("cases") != []:
        raise ProfessorTransitionError("calibration template cannot pre-open evaluation cases")
    return {
        "status": "passed",
        "profile_schema": schema["$id"],
        "profile_status": profile["status"],
        "profile_reference_eligible": False,
        "provenance_modes": sorted(
            {dimension["provenance"] for dimension in dimensions.values()}
        ),
        "conditions": list(EXPECTED_CONDITIONS),
        "hard_gate_count": len(EXPECTED_HARD_GATES),
        "fidelity_dimension_count": len(EXPECTED_FIDELITY_DIMENSIONS),
        "calibration_case_range": [8, 12],
        "heldout_content_read": False,
        "provider_or_model_called": False,
    }


def main() -> int:
    print(json.dumps(validate_transition(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
