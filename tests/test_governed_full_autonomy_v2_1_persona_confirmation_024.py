from __future__ import annotations

from scripts import (
    run_governed_full_autonomy_v2_1_persona_confirmation_024 as runner,
)


def test_024_reuses_023_scientific_package_and_only_changes_harness() -> None:
    result = runner.validate_attempt()

    assert result["case_count"] == 670
    assert result["status"] == "completed-keep-authorization-revoked"
    assert result["provider_execution_authorized"] is False
    assert result["paid_execution_authorized"] is False
    assert result["harness_only_changes"] == [
        "cost-ceiling-3-to-5",
        "clock-day-export",
    ]
    assert runner.package.public_payload()["dataset_id"].endswith("023")
    assert runner.package.DAY == 24 * 60 * 60


def test_024_is_bounded_and_not_automatic() -> None:
    instrument = runner.json.loads(runner.INSTRUMENT.read_text(encoding="utf-8"))

    assert instrument["authority"]["maximum_cost_usd"] == 5.0
    assert instrument["authority"]["maximum_provider_calls"] == 4100
    assert instrument["authority"]["automatic_promotion"] is False
    assert instrument["execution"]["same_cases_quality_rerun_allowed"] is False
