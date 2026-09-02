import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_012 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_012 as runner,
)


def test_confirmation_012_is_fresh_source_disjoint_and_authorized() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "passed-frozen-authorized"
    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["source_disjoint_from_evaluation_009"] is True
    assert instrument["dataset"]["source_family_range"] == [101, 150]
    assert instrument["authority"]["provider_execution_authorized"] is True
    assert instrument["authority"]["paid_execution_authorized"] is True


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


def test_confirmation_012_classifies_proactive_cases_by_event_contract() -> None:
    cases = [case for _condition, case, _gold in builder.build_contract()]

    assert sum(runner.shared._is_proactive_evaluation_case(case) for case in cases) == 220
    assert all(
        runner.shared._is_proactive_evaluation_case(case)
        == any(event.kind == "practice-outcome" for event in case.events)
        for case in cases
    )


def test_confirmation_012_preflight_preserves_instrument_authority_but_honors_revocation() -> None:
    result = runner.preflight()

    assert "provider-execution-not-authorized" not in result["blockers"]
    assert "paid-execution-not-authorized" not in result["blockers"]
    # The immutable instrument preserves its original authorization, while the
    # repository allowlist is the revocable execution boundary. Confirmation
    # 012 is terminal and must not become executable again.
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
