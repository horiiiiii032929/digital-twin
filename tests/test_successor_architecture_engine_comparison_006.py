from __future__ import annotations

import json

import pytest

from scripts import build_successor_architecture_engine_comparison_006 as builder
from scripts import run_successor_architecture_engine_comparison_006 as runner
from src.digital_twin.student.autonomy_models import AutonomousActionKind


def test_engine_package_is_fresh_byte_stable_and_gold_isolated():
    public, gold = builder.build_packages()

    assert public == builder.build_packages()[0]
    assert gold == builder.build_packages()[1]
    assert builder.validate()["status"] == "passed"
    assert public["case_count"] == gold["case_count"] == 300
    assert len({row["scenario_cluster_id"] for row in public["rows"]}) == 300
    assert sum(row["guard"] == "eligible" for row in public["rows"]) == 240
    serialized = json.dumps(public)
    assert "expected_action" not in serialized
    assert "action_utilities" not in serialized


def test_engine_runner_is_terminal_revoked_and_simulates_without_calls():
    validation = runner.validate()
    simulation = runner.simulate()
    preflight = runner.preflight(resume=False)

    assert validation["instrument_status"] == "completed-keep-authorization-revoked"
    assert validation["provider_execution_authorized"] is False
    assert validation["paid_execution_authorized"] is False
    assert simulation["maximum_provider_calls"] == 1444
    assert simulation["allocation_cell_count"] == 1200
    assert simulation["gold_loaded"] is False
    assert "provider-execution-not-authorized" in preflight["blockers"]
    assert "paid-execution-not-authorized" in preflight["blockers"]


def test_wording_rejects_free_text_and_renders_only_fixed_grounded_strategies():
    public, _gold = builder.build_packages()
    row = public["rows"][0]
    action = AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION

    with pytest.raises(ValueError, match="payload fields drifted"):
        runner._wording_response(
            row,
            action,
            {
                "case_id": row["case_id"],
                "action": action.value,
                "lead": "A free-form unsupported assertion.",
                "evidence_quote": "Changed evidence.",
                "learner_prompt": "What would you try next?",
            },
        )

    response = runner._wording_response(
        row,
        action,
        {
            "case_id": row["case_id"],
            "action": action.value,
            "lead_style": "reflective",
            "prompt_mode": "contrast",
        },
    )
    assert response.atomic_claims == [row["evidence_quote"]]
    assert f'"{row["evidence_quote"]}"' in response.content


def test_engine_scoring_prefers_cheaper_e1_when_factor_effects_are_equal():
    public, gold = builder.build_packages()
    gold_by_id = {row["case_id"]: row for row in gold["rows"]}
    allocations = {
        "e1": ("gpt-5.6-luna", "gpt-5.6-luna"),
        "e2": ("gpt-5.6-terra", "gpt-5.6-luna"),
        "e3": ("gpt-5.6-luna", "gpt-5.4-mini-2026-03-17"),
        "e4": ("gpt-5.6-terra", "gpt-5.4-mini-2026-03-17"),
    }
    responses = []
    for allocation_id, (planner_model, generator_model) in allocations.items():
        for row in public["rows"]:
            case_id = row["case_id"]
            selected = gold_by_id[case_id]["expected_action"]
            intervention = selected != AutonomousActionKind.NO_ACTION.value
            source_key = f"source-range-{case_id}"
            responses.append(
                {
                    "allocation_id": allocation_id,
                    "case_id": case_id,
                    "planner_model": planner_model,
                    "generator_model": generator_model,
                    "selected_action": selected,
                    "response": (
                        {
                            "action": selected,
                            "content": f"Use this: {row['evidence_quote']}",
                            "atomic_claims": [row["evidence_quote"]],
                            "source_range_keys": [source_key],
                            "citation_ids": [f"citation:{source_key}"],
                            "policy_action": "answer",
                        }
                        if intervention
                        else None
                    ),
                    "trace": {"course_id": "synthetic-autonomy-course"},
                    "planner_provider_success": True,
                    "generator_provider_success": True,
                }
            )
    role_metrics = {
        role: {
            "calls": 240,
            "completed_calls": 240,
            "completion_rate": 1.0,
            "input_tokens": 100,
            "output_tokens": 100,
            "cost_usd": cost,
            "p95_latency_ms": latency,
        }
        for role, cost, latency in (
            ("planner:gpt-5.6-luna", 0.1, 100),
            ("planner:gpt-5.6-terra", 1.0, 200),
            ("generator:e1:gpt-5.6-luna", 0.05, 100),
            ("generator:e2:gpt-5.6-luna", 0.05, 100),
            ("generator:e3:gpt-5.4-mini-2026-03-17", 0.25, 150),
            ("generator:e4:gpt-5.4-mini-2026-03-17", 0.25, 150),
        )
    }

    for response in responses:
        if response["response"] is None:
            continue
        row = next(row for row in public["rows"] if row["case_id"] == response["case_id"])
        action = AutonomousActionKind(response["selected_action"])
        response["response"]["content"] = runner._wording_response(
            row,
            action,
            {
                "case_id": row["case_id"],
                "action": action.value,
                "lead_style": "direct",
                "prompt_mode": "retrieve",
            },
        ).content

    result = runner._score(
        responses=responses,
        public_rows=public["rows"],
        gold_rows=gold["rows"],
        role_metrics=role_metrics,
        provider_snapshot={"provider_calls": 0, "reported_cost_usd": 0.0},
    )

    assert result["status"] == "completed-keep"
    assert result["decision"]["selected_allocation_id"] == "e1"
    assert all(result["global_hard_gates"].values())
    assert all(
        all(gates.values()) for gates in result["allocation_hard_gates"].values()
    )


def test_factor_effect_pools_both_levels_at_the_case_grain():
    by_allocation = {
        allocation_id: [
            {
                "case_id": f"case-{index}",
                "guard": "eligible",
                "intervention": True,
                "value": value,
            }
            for index in range(20)
        ]
        for allocation_id, value in {
            "e1": 0.0,
            "e2": 0.1,
            "e3": 0.0,
            "e4": 0.1,
        }.items()
    }

    effect = runner._factor_effect(
        by_allocation,
        candidate_allocations=("e2", "e4"),
        control_allocations=("e1", "e3"),
        field="value",
        seed="pooled-factor-test",
        eligible_only=True,
    )

    assert effect["n_pairs"] == 20
    assert effect["mean_difference"] == pytest.approx(0.1)
    assert effect["ci95"][0] > 0
