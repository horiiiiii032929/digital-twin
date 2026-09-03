from __future__ import annotations

from collections import Counter

from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_021 as runner,
)
from src.digital_twin.action_router import DeterministicActionRouterV3


def test_021_is_fresh_reviewed_and_provider_unauthorized() -> None:
    result = runner.validate_attempt()

    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["set_valued_expectation_count"] == 600
    assert result["request_intent_contract"] == (
        DeterministicActionRouterV3.implementation_id
    )
    assert result["status"] == "reviewed-provider-unauthorized"
    assert result["provider_execution_authorized"] is False
    assert result["paid_execution_authorized"] is False


def test_021_is_source_and_wording_disjoint_from_020() -> None:
    public = runner.package.public_payload()
    messages = [
        event["payload"]["message"]
        for row in public["rows"]
        for event in row["case"]["events"]
        if event["kind"] == "student-message"
    ]

    assert public["source_family_range"] == [451, 500]
    assert public["source_disjoint_from_confirmations_012_through_020"] is True
    assert public["wording_disjoint_from_confirmation_020"] is True
    assert any("test my own reasoning" in message for message in messages)
    assert all("test my explanation" not in message for message in messages)


def test_021_public_inputs_do_not_expose_action_gold() -> None:
    serialized = str(runner.package.public_payload())

    assert "acceptable_actions" not in serialized
    assert "preferred_action" not in serialized
    assert "expected_actions" not in serialized


def test_021_retains_only_preregistered_repeated_confusion_equivalence() -> None:
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

    assert counts["multiple"] == 600
    assert counts["single"] > 0


def test_021_preflight_fails_closed_before_authorization() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["hidden_gold_loaded"] is False


def test_021_network_free_actual_product_simulation_passes() -> None:
    result = runner.shared.simulate(runner.CONTEXT)

    assert result["status"] == "passed-network-free-simulation"
    assert result["case_count"] == 820
    assert result["summary"]["all_valid_action_sets_matched"] is True
    assert result["summary"]["all_case_safety_contracts_passed"] is True
    assert result["provider_calls"] == 0
    assert result["cost_usd"] == 0
