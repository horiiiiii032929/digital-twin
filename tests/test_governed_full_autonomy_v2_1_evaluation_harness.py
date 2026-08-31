from scripts import run_governed_full_autonomy_v2_1_evaluation_harness as runner


def test_harness_contract_is_complete_and_provider_unauthorized() -> None:
    result = runner.validate()

    assert result["status"] == "passed-build-only"
    assert result["case_count"] == 820
    assert result["trajectory_case_count"] == 600
    assert result["long_horizon_case_count"] == 100
    assert result["proactive_opportunity_case_count"] == 120
    assert result["provider_calls"] == 0
    assert result["paid_execution_authorized"] is False
    assert len(result["public_contract_sha256"]) == 64
    assert len(result["gold_contract_sha256"]) == 64
    assert result["public_contract_sha256"] != result["gold_contract_sha256"]


def test_reference_simulation_exercises_every_condition_and_gate() -> None:
    result = runner.simulate()

    assert result["status"] == "passed-harness-simulation"
    assert result["summary"]["case_count"] == 820
    assert result["summary"]["all_case_hard_gates_passed"] is True
    assert result["summary"]["valid_pedagogical_transition_rate"] == 1.0
    assert result["summary"]["goal_termination_accuracy"] == 1.0
    assert result["provider_calls"] == 0
    assert result["tokens"] == 0
    assert result["cost_usd"] == 0
    assert result["product_quality_claim"] is False
    assert set(result["condition_summaries"]) == set(runner.CONDITIONS)


def test_public_cases_do_not_contain_gold_fields() -> None:
    forbidden = {
        "expected_actions",
        "expected_terminal_goal_status",
        "required_invariants",
    }
    for _, case, gold in runner.build_contract():
        assert not forbidden.intersection(case.model_dump(mode="json"))
        assert case.case_id == gold.case_id
