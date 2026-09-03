from __future__ import annotations

from collections import Counter

from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_020 as runner,
)


def test_020_is_fresh_set_valued_and_bounded_for_execution() -> None:
    result = runner.validate_attempt()

    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["set_valued_expectation_count"] == 600
    assert result["action_gold_contract"] == "set-valued-valid-actions-v2"
    assert result["reactive_provider_contract"] == (
        "minimal-reactive-intent-proposal-v3"
    )
    assert result["provider_execution_authorized"] is True
    assert result["paid_execution_authorized"] is True


def test_020_public_inputs_do_not_expose_action_gold() -> None:
    public = runner.package.public_payload()
    serialized = str(public)

    assert "acceptable_actions" not in serialized
    assert "preferred_action" not in serialized
    assert "expected_actions" not in serialized
    assert public["source_family_range"] == [401, 450]


def test_020_preregisters_repeated_confusion_equivalence_only() -> None:
    counts = Counter()
    for _condition, case, gold in runner.package.build_contract():
        repeated_times = {
            event.at_seconds
            for event in case.events
            if event.kind == "student-message"
            and event.payload.get("turn_kind") == "repeated-confusion"
        }
        for expected in gold.expected_actions:
            multiple = len(expected.acceptable_actions) > 1
            counts["multiple" if multiple else "single"] += 1
            if multiple:
                assert expected.earliest_seconds in repeated_times
                assert set(expected.acceptable_actions) == {
                    "ask-diagnostic-question",
                    "provide-hint-or-example",
                }
                assert expected.preferred_action == "provide-hint-or-example"

    assert counts["multiple"] == 600
    assert counts["single"] > 0


def test_020_preflight_recognizes_the_exact_bounded_authorization() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert "provider-execution-not-authorized" not in result["blockers"]
    assert "paid-execution-not-authorized" not in result["blockers"]
    assert "repository-freeze-authorization-missing" not in result["blockers"]
    assert result["hidden_gold_loaded"] is False


def test_020_network_free_product_simulation_passes() -> None:
    result = runner.shared.simulate(runner.CONTEXT)

    assert result["status"] == "passed-network-free-simulation"
    assert result["case_count"] == 820
    assert result["summary"]["all_valid_action_sets_matched"] is True
    assert result["summary"]["all_case_safety_contracts_passed"] is True
    assert result["provider_calls"] == 0
    assert result["cost_usd"] == 0
