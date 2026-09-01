from __future__ import annotations

from scripts.run_governed_full_autonomy_v2_1_actual_product_smoke import (
    CONDITIONS,
    build_contract,
    simulate,
    validate,
)


def test_actual_product_smoke_instrument_is_network_free() -> None:
    result = validate()

    assert result["status"] == "valid"
    assert result["provider_execution_authorized"] is False
    assert result["condition_count"] == 4


def test_actual_product_smoke_contract_keeps_gold_outside_public_cases() -> None:
    rows = build_contract()

    assert [condition for condition, _, _ in rows] == list(CONDITIONS)
    assert len({case.case_id for _, case, _ in rows}) == 4
    for _, case, gold in rows:
        public = case.model_dump(mode="json")
        assert case.case_id == gold.case_id
        assert "expected_actions" not in public
        assert "required_invariants" not in public
        assert all("expected" not in event.payload for event in case.events)


def test_actual_product_smoke_drives_all_real_service_conditions() -> None:
    result = simulate()

    assert result["status"] == "passed-actual-product-smoke"
    assert result["summary"]["all_case_hard_gates_passed"] is True
    assert result["summary"]["action_accuracy"] == 1.0
    assert result["summary"]["restart_consistency_rate"] == 1.0
    assert result["independent_summary"]["all_case_hard_gates_passed"] is True
    assert result["independent_summary"]["safe_grounded_autonomous_success"] == 1.0
    assert result["provider_calls"] == 0
    assert result["tokens"] == 0
    assert result["cost_usd"] == 0
    assert result["product_quality_claim"] is False
    assert set(result["conditions"]) == set(CONDITIONS)
    assert all(
        item["diagnostic_trace"]["actual_product_services"] is True
        for item in result["conditions"].values()
    )
    autonomous = result["conditions"]["t1-v2-autonomous"]
    assert any(
        action["action_id"].startswith("autonomous:")
        and action["status"] == "delivered"
        for action in autonomous["actions"]
    )
