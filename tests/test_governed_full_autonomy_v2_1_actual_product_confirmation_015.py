import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_015 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_015 as runner,
)


def test_confirmation_015_is_fresh_corrected_and_terminally_revoked() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "completed-keep-post-run-release-blocked"
    assert result["provider_execution_authorized"] is False
    assert result["paid_execution_authorized"] is False
    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["prospectively_corrected_reference_count"] == 30
    assert result["source_disjoint_from_confirmations_012_013_014"] is True
    assert instrument["dataset"]["source_family_range"] == [251, 300]


def test_confirmation_015_aligns_every_post_failure_v2_turn_prospectively() -> None:
    corrected = []
    for condition, case, gold in builder.build_contract():
        if condition not in builder.V2_CONDITIONS:
            continue
        failure_times = [
            event.at_seconds for event in case.events if event.kind == "provider-failure"
        ]
        if not failure_times:
            continue
        expected = {
            action.earliest_seconds: action for action in gold.expected_actions
        }
        for event in case.events:
            if event.kind != "student-message" or event.at_seconds <= min(failure_times):
                continue
            action = expected[event.at_seconds]
            assert action.action == "provide-hint-or-example"
            assert action.must_have_valid_lineage is True
            corrected.append((condition, case.case_id, event.at_seconds))

    assert len(corrected) == 30


def test_confirmation_015_keeps_selected_h_e1_and_deterministic_facts() -> None:
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))
    binding = runner.shared._run_binding(network_free=False, context=runner.CONTEXT)

    assert runner.CONTEXT.engine_binding.engine_id == "h-e1"
    assert runner.CONTEXT.autonomy_architecture_id == "guarded-policy-value-planner-v2"
    assert runner.CONTEXT.bounded_strategy_generation is True
    assert instrument["execution"]["selected_factual_generator"] == (
        "deterministic/evidence-set-v2"
    )
    assert binding["conditions"]["t1-v2-reactive"]["model_bindings"] == {
        "planner": "gpt-5.6-luna",
        "factual_generator": "deterministic/evidence-set-v2",
        "proactive_strategy_model": "gpt-5.6-luna",
    }


def test_confirmation_015_network_free_simulation_checks_safety_not_quality() -> None:
    result = runner.shared.simulate(runner.CONTEXT)

    assert result["status"] == "passed-network-free-simulation"
    assert result["summary"]["case_count"] == 820
    # Network-free mode cannot reproduce the provider-backed fallback after a
    # planner outage, so its action score is intentionally not quality evidence.
    assert result["product_quality_claim"] is False
    assert result["summary"]["unauthorized_or_unexpected_actions"] == 0
    assert result["summary"]["provider_failure_safe_fallback_rate"] == 1.0
    assert result["summary"]["invalid_citation_lineage_count"] == 0
    assert result["provider_calls"] == 0


def test_confirmation_015_preflight_is_blocked_after_revocation() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert result["status"] == "blocked-not-authorized"
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
