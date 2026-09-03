from __future__ import annotations

from collections import Counter

from scripts import (
    run_governed_full_autonomy_v2_1_persona_confirmation_023 as runner,
)
from src.digital_twin.action_router import DeterministicActionRouterV3


def test_023_binds_the_frozen_selected_condition_package() -> None:
    result = runner.validate_attempt()

    assert result["case_count"] == 670
    assert result["source_family_count"] == 50
    assert result["selected_release_candidate"] == "t1-v2-autonomous"
    assert result["reactive_condition_role"] == "paired-grounding-diagnostic"
    assert result["request_intent_contract"] == (
        DeterministicActionRouterV3.implementation_id
    )
    assert result["status"] == "frozen-pending-execution"
    assert result["provider_execution_authorized"] is True
    assert result["paid_execution_authorized"] is True


def test_023_distribution_and_sources_are_fresh() -> None:
    public = runner.package.public_payload()
    counts = Counter(row["condition"] for row in public["rows"])
    source_ids = {
        runner.package.source_fixture_for_case(row["case"]["case_id"])["source_id"]
        for row in public["rows"]
    }

    assert counts == {
        "t0-grounded-control": 150,
        "t1-v2-reactive": 150,
        "t1-v2-autonomous": 370,
    }
    assert public["source_family_range"] == [501, 550]
    assert public["source_disjoint_from_confirmations_012_through_021"] is True
    assert public["wording_disjoint_from_confirmation_021"] is True
    assert len(source_ids) == 50


def test_023_public_inputs_do_not_expose_hidden_gold() -> None:
    serialized = str(runner.package.public_payload())

    assert "acceptable_actions" not in serialized
    assert "preferred_action" not in serialized
    assert "expected_actions" not in serialized


def test_023_canaries_exist_in_selected_autonomous_condition() -> None:
    public_rows = {
        row["case"]["case_id"]: row["condition"]
        for row in runner.package.public_payload()["rows"]
    }

    for case_id in runner.CONTEXT.canary_case_ids:
        assert public_rows[case_id] == "t1-v2-autonomous"


def test_023_authority_is_bounded_and_cannot_auto_promote() -> None:
    instrument = runner.json.loads(runner.INSTRUMENT.read_text(encoding="utf-8"))

    assert instrument["authority"]["automatic_promotion"] is False
    assert instrument["authority"]["maximum_provider_calls"] == 4100
    assert instrument["authority"]["maximum_cost_usd"] == 3.0
    assert instrument["execution"]["same_cases_quality_rerun_allowed"] is False
