from __future__ import annotations

import copy

import pytest

from scripts.validate_evaluation_instruments import (
    INSTRUMENTS,
    load_json,
    validate_instruments,
    validate_judge_pair,
    validate_run,
    validate_state_card,
)


def test_frozen_evaluation_instruments_validate() -> None:
    result = validate_instruments()

    assert result["status"] == "passed"
    assert result["frozen_files"] == 20
    assert result["judge_examples"] == 2


def test_judge_quote_must_exist_in_blinded_response() -> None:
    input_record = load_json(
        INSTRUMENTS / "llm_judge_input_v1_synthetic_single.json"
    )
    output_record = load_json(
        INSTRUMENTS / "llm_judge_output_v1_synthetic_single.json"
    )
    changed = copy.deepcopy(output_record)
    changed["single_judgments"][0]["evidence_quote"] = "invented quote"

    with pytest.raises(ValueError, match="quote is absent"):
        validate_judge_pair(input_record, changed)


def test_simulator_rejects_two_transitions_for_one_state_event() -> None:
    state_card = load_json(
        INSTRUMENTS / "simulated_student_state_v1_synthetic_example.json"
    )
    changed = copy.deepcopy(state_card)
    duplicate = copy.deepcopy(changed["transitions"][0])
    duplicate["transition_id"] = "tr-s0-scaffold-duplicate"
    changed["transitions"].append(duplicate)

    with pytest.raises(ValueError, match="non-unique simulator transition"):
        validate_state_card(changed)


def test_missing_tutor_output_stays_in_primary_denominator() -> None:
    run = load_json(INSTRUMENTS / "evaluation_run_v1_synthetic_example.json")
    changed = copy.deepcopy(run)
    result = changed["case_results"][0]
    result["attempt_status"] = "missing"
    result["analysis_eligibility"] = "excluded"
    result["safe_grounded_task_success"] = False

    with pytest.raises(ValueError, match="must remain included"):
        validate_run(changed)
