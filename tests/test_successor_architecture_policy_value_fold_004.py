from __future__ import annotations

import json

from scripts import build_successor_architecture_policy_value_fold_004 as builder
from scripts import run_successor_architecture_policy_value_fold_004 as runner
from src.digital_twin.student.autonomy_models import AutonomousActionKind


def test_successor_fold_is_fresh_byte_stable_and_gold_isolated():
    public, gold = builder.build_packages()

    assert public == builder.build_packages()[0]
    assert gold == builder.build_packages()[1]
    assert builder.validate()["status"] == "passed"
    assert public["case_count"] == gold["case_count"] == 150
    assert sum(row["guard"] == "eligible" for row in public["rows"]) == 120
    serialized = json.dumps(public)
    assert "expected_action" not in serialized
    assert "action_utilities" not in serialized
    assert gold["preferred_action_is_diagnostic_not_transition_validity"] is True


def test_successor_runner_is_bounded_and_unauthorized():
    validation = runner.validate()
    simulation = runner.simulate()
    preflight = runner.preflight(resume=False)

    assert validation["instrument_status"] == "reviewed-provider-unauthorized"
    assert validation["provider_execution_authorized"] is False
    assert validation["paid_execution_authorized"] is False
    assert simulation["maximum_provider_calls"] == 121
    assert simulation["condition_cell_count"] == 600
    assert simulation["gold_loaded"] is False
    assert "provider-execution-not-authorized" in preflight["blockers"]


def test_transition_validity_uses_authority_envelope_not_single_preference():
    public, gold = builder.build_packages()
    gold_by_id = {row["case_id"]: row for row in gold["rows"]}
    responses = []
    for condition in runner.CONDITIONS:
        for row in public["rows"]:
            case_id = row["case_id"]
            selected = gold_by_id[case_id]["expected_action"]
            if condition == runner.CONTROL_B and row["guard"] == "eligible":
                selected = AutonomousActionKind.NO_ACTION.value
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

    assert result["hard_gates"]["event_scoped_action_validity_is_1"] is True
    assert result["aggregate"][runner.CONTROL_B][
        "preferred_action_agreement"
    ] < 0.95
    assert result["status"] == "completed-go-deeper"
    assert (
        result["decision"]["provisional_confirmation_candidate"]
        == runner.CONTROL_A
    )


def test_provider_failure_requires_safe_condition_specific_fallback():
    public, gold = builder.build_packages()
    failure_case = next(row for row in public["rows"] if row["guard"] == "eligible")
    failure_id = failure_case["case_id"]
    gold_by_id = {row["case_id"]: row for row in gold["rows"]}
    responses = []
    for condition in runner.CONDITIONS:
        for row in public["rows"]:
            case_id = row["case_id"]
            selected = gold_by_id[case_id]["expected_action"]
            if case_id == failure_id and condition in {runner.CONTROL_B, runner.CONTROL_C}:
                selected = AutonomousActionKind.NO_ACTION.value
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
        planner_failures=[failure_id],
        provider_snapshot={"provider_calls": 0, "reported_cost_usd": 0.0},
    )

    assert result["provider_quality"][
        "fallback_safe_and_deterministic_rate"
    ] == 1.0
    assert result["hard_gates"]["fallback_is_safe_and_deterministic"] is True
