import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_013 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_013 as runner,
)


def test_confirmation_013_is_fresh_and_authorized() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "passed-frozen-authorized"
    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["source_disjoint_from_confirmation_012"] is True
    assert instrument["dataset"]["source_family_range"] == [151, 200]


def test_confirmation_013_provider_failure_gold_matches_dependencies() -> None:
    rows = builder.build_contract()
    provider_failure_rows = [
        (condition, case, gold)
        for condition, case, gold in rows
        if any(event.kind == "provider-failure" for event in case.events)
        and "trajectory" in case.case_id
    ]

    assert len(provider_failure_rows) == 60
    for condition, _case, gold in provider_failure_rows:
        final_reactive = next(
            item for item in gold.expected_actions if item.earliest_seconds == 3_600
        )
        if condition in {"t0-grounded-control", "t1-v1-reactive-control"}:
            assert final_reactive.action == "provide-hint-or-example"
        else:
            assert final_reactive.action == "no-action"


def test_confirmation_013_preflight_reaches_environment_checks() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert "provider-execution-not-authorized" not in result["blockers"]
    assert "paid-execution-not-authorized" not in result["blockers"]
    assert "repository-freeze-authorization-missing" not in result["blockers"]
    assert result["provider_calls"] == 0
