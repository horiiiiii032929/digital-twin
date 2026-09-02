import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_014 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_014 as runner,
)


def test_confirmation_014_is_fresh_and_provider_unauthorized() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "reviewed-build-only-provider-unauthorized"
    assert result["provider_execution_authorized"] is False
    assert result["paid_execution_authorized"] is False
    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["source_disjoint_from_confirmations_012_013"] is True
    assert instrument["dataset"]["source_family_range"] == [201, 250]


def test_confirmation_014_binds_selected_h_e1_without_replacing_factual_generator() -> None:
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))
    binding = runner.shared._run_binding(network_free=False, context=runner.CONTEXT)

    assert runner.CONTEXT.engine_binding.engine_id == "h-e1"
    assert runner.CONTEXT.autonomy_architecture_id == "guarded-policy-value-planner-v2"
    assert runner.CONTEXT.bounded_strategy_generation is True
    assert instrument["execution"]["selected_factual_generator"] == (
        "deterministic/evidence-set-v2"
    )
    assert instrument["execution"]["selected_proactive_strategy_model"] == (
        "gpt-5.6-luna"
    )
    reactive = binding["conditions"]["t1-v2-reactive"]["model_bindings"]
    assert reactive == {
        "planner": "gpt-5.6-luna",
        "factual_generator": "deterministic/evidence-set-v2",
        "proactive_strategy_model": "gpt-5.6-luna",
    }


def test_confirmation_014_preflight_fails_closed_before_authorization() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
