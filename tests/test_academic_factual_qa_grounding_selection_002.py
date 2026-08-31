from scripts import run_academic_factual_qa_grounding_selection_002 as runner


def test_grounding_selection_build_is_finite_and_gold_isolated() -> None:
    result = runner.validate()

    assert result["status"] == "passed-build-only"
    assert result["candidate_case_count"] == 500
    assert result["control_case_count"] == 100
    assert result["maximum_canary_calls"] == 2
    assert result["maximum_total_calls"] == 602
    assert result["hidden_gold_loaded"] is False


def test_grounding_selection_simulations_stop_at_frozen_decisions() -> None:
    expected = {
        "pass": "completed-keep",
        "quality-failure": "completed-refine",
        "canary-failure": "invalid-execution",
        "provider-failure": "invalid-execution",
        "resume": "completed-keep",
    }

    for scenario, status in expected.items():
        result = runner.simulate(scenario=scenario)
        assert result["status"] == status
        assert result["gold_opened_before_responses"] is False
        assert result["provider_calls"] == 0
        assert result["network_calls"] == 0


def test_grounding_selection_preflight_is_blocked_before_authorization() -> None:
    result = runner.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert result["hidden_gold_loaded"] is False
