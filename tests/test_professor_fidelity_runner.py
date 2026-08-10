import pytest

from scripts.run_professor_fidelity_experiment import (
    ProfessorFidelityPlanError,
    build_preflight_manifest,
    load_instrument,
)


def test_professor_fidelity_instrument_is_frozen_with_four_conditions():
    instrument = load_instrument()

    assert instrument["status"] == "frozen-preflight"
    assert [condition["condition_id"] for condition in instrument["conditions"]] == [
        "C0",
        "C1",
        "C2",
        "C3",
    ]
    assert instrument["generator_binding"]["status"] == "pending-qualification"
    assert instrument["analysis"]["human_outcome_claims_allowed"] is False


def test_professor_fidelity_preflight_manifest_excludes_private_text():
    instrument = load_instrument()

    manifest = build_preflight_manifest(instrument)

    assert manifest["execution_enabled"] is False
    assert manifest["private_text_emitted"] is False
    assert manifest["dataset"] is None
    assert manifest["blocked_reasons"]
    assert not any("generator" in reason for reason in manifest["blocked_reasons"])
    assert manifest["generator_qualification"]["status"] == "qualified-selected"
    assert manifest["generator_qualification"]["candidate_binding"] == (
        "litellm-deepseek-v4-flash-nonthinking-v1"
    )
    assert manifest["prompt_binding"]["implementation_id"] == (
        "strict-evidence-grounded-prompt-v3"
    )
    assert manifest["generator_qualification"]["credential_value_emitted"] is False


def test_professor_fidelity_instrument_rejects_condition_drift():
    instrument = load_instrument()
    instrument["conditions"][0]["condition_id"] = "C9"

    with pytest.raises(ProfessorFidelityPlanError, match="ordered"):
        from scripts.run_professor_fidelity_experiment import _validate_instrument

        _validate_instrument(instrument)
