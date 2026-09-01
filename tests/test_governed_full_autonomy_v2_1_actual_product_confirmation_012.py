import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_012 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_012 as runner,
)


def test_confirmation_012_is_fresh_source_disjoint_and_frozen() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "passed-frozen-provider-unauthorized"
    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["source_disjoint_from_evaluation_009"] is True
    assert instrument["dataset"]["source_family_range"] == [101, 150]
    assert instrument["authority"]["provider_execution_authorized"] is False


def test_confirmation_012_binds_hybrid_authority_boundary() -> None:
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert instrument["execution"]["selected_factual_generator"] == (
        "deterministic/evidence-set-v2"
    )
    assert instrument["execution"]["selected_complex_planner"] == "gpt-5.6-terra"
    assert runner.CONTEXT.expected_canary_models == {
        "t0-grounded-control": set(),
        "t1-v2-reactive": {"gpt-5.6-terra"},
    }


def test_confirmation_012_preflight_fails_closed_before_activation() -> None:
    result = runner.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
