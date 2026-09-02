from __future__ import annotations

import json

from scripts import build_successor_architecture_confirmation_005 as builder
from scripts import run_successor_architecture_confirmation_005 as runner
from src.digital_twin.student.autonomy_models import AutonomousActionKind


def test_confirmation_is_fresh_byte_stable_and_gold_isolated():
    public, gold = builder.build_packages()

    assert public == builder.build_packages()[0]
    assert gold == builder.build_packages()[1]
    assert builder.validate()["status"] == "passed"
    assert public["case_count"] == gold["case_count"] == 1000
    assert len({row["scenario_cluster_id"] for row in public["rows"]}) == 1000
    assert sum(row["guard"] == "eligible" for row in public["rows"]) == 800
    serialized = json.dumps(public)
    assert "expected_action" not in serialized
    assert "action_utilities" not in serialized


def test_confirmation_runner_is_bounded_and_frozen_for_one_execution():
    validation = runner.validate()
    simulation = runner.simulate()
    preflight = runner.preflight(resume=False)

    assert validation["instrument_status"] == "frozen-pending-execution"
    assert validation["provider_execution_authorized"] is True
    assert validation["paid_execution_authorized"] is True
    assert simulation["maximum_provider_calls"] == 801
    assert simulation["condition_cell_count"] == 2000
    assert simulation["gold_loaded"] is False
    assert "provider-execution-not-authorized" not in preflight["blockers"]
    assert "paid-execution-not-authorized" not in preflight["blockers"]


def test_confirmation_selects_control_when_incremental_benefit_is_absent():
    public, gold = builder.build_packages()
    gold_by_id = {row["case_id"]: row for row in gold["rows"]}
    responses = []
    for condition in runner.CONDITIONS:
        for row in public["rows"]:
            case_id = row["case_id"]
            selected = gold_by_id[case_id]["expected_action"]
            intervention = selected != AutonomousActionKind.NO_ACTION.value
            responses.append(
                {
                    "architecture_id": condition,
                    "case_id": case_id,
                    "selected_action": selected,
                    "response": (
                        {"source_range_keys": [f"source-range-{case_id}"]}
                        if intervention
                        else None
                    ),
                    "trace": {"course_id": "synthetic-autonomy-course"},
                }
            )

    result = runner._score(
        responses=responses,
        public_rows=public["rows"],
        gold_rows=gold["rows"],
        planner_failures=[],
        provider_snapshot={"provider_calls": 0, "reported_cost_usd": 0.0},
    )

    assert all(result["hard_gates"].values())
    assert result["status"] == "completed-keep"
    assert result["decision"]["candidate_confirmed"] is False
    assert result["decision"]["selected_architecture_id"] == runner.CONTROL_A
