import json
from dataclasses import replace

import pytest

from scripts import build_successor_architecture_development_fold_001 as builder
from scripts import run_successor_architecture_development_fold_001 as runner
from src.digital_twin.student.planning_architectures import AutonomyArchitectureId


def test_development_fold_is_fresh_balanced_and_gold_isolated():
    public, gold = builder.build_packages()

    assert public["case_count"] == gold["case_count"] == 150
    assert [row["case_id"] for row in public["rows"]] == [
        row["case_id"] for row in gold["rows"]
    ]
    serialized = json.dumps(public)
    assert "expected_action" not in serialized
    assert "acceptable_actions" not in serialized
    assert "hidden_learner_knows" not in serialized
    assert "action_utilities" not in serialized
    assert sum(row["guard"] == "eligible" for row in public["rows"]) == 120

    eligible_utilities = [
        utility
        for row in gold["rows"]
        if row["expected_action"] != "no-action"
        for utility in row["action_utilities"].values()
        if 0 < utility < 1
    ]
    assert eligible_utilities
    assert len(set(eligible_utilities)) > 2


def test_development_fold_build_is_byte_stable():
    first = builder.build_packages()
    second = builder.build_packages()

    assert first == second
    assert builder.validate()["status"] == "passed"


def test_live_instrument_and_network_free_simulation_are_bounded():
    validation = runner.validate()
    simulation = runner.simulate()

    assert validation["status"] == "passed"
    assert validation["instrument_status"] == "invalid-execution-authorization-revoked"
    assert validation["provider_execution_authorized"] is False
    assert validation["paid_execution_authorized"] is False
    assert simulation["gold_loaded"] is False
    assert simulation["maximum_provider_calls"] == 62
    assert simulation["planner_batch_count"] == 30


def test_corrective_attempt_reuses_scientific_inputs_but_has_fresh_output_identity():
    original = runner.DEFAULT_CONTEXT
    corrective = runner._run_context("002")
    validation = runner.validate(corrective)
    simulation = runner.simulate(corrective)

    assert validation["instrument_status"] == "reviewed-provider-unauthorized"
    assert validation["provider_execution_authorized"] is False
    assert validation["paid_execution_authorized"] is False
    assert simulation["maximum_provider_calls"] == 62
    assert original.output_root != corrective.output_root
    assert original.result_path != corrective.result_path


def test_preflight_rejects_reused_result_path(tmp_path):
    existing = tmp_path / "existing-result.json"
    existing.write_text("{}\n", encoding="utf-8")
    context = replace(runner.DEFAULT_CONTEXT, result_path=existing)

    result = runner.preflight(resume=False, context=context)

    assert f"exclusive-output-exists:{existing.name}" in result["blockers"]


def test_provider_batch_schemas_are_strict_and_case_keyed():
    proposal = runner._proposal_schema()
    verifier = runner._verifier_schema()

    assert proposal["additionalProperties"] is False
    assert proposal["required"] == ["rows"]
    proposal_row = proposal["properties"]["rows"]["items"]
    assert "case_id" in proposal_row["required"]
    assert proposal_row["additionalProperties"] is False
    assert proposal_row["properties"]["episode_steps"]["maxItems"] == 3
    assert verifier["properties"]["rows"]["items"]["required"] == [
        "case_id",
        "accept",
        "reason_code",
    ]


def test_provider_id_validation_rejects_duplicates_and_unknown_ids():
    with pytest.raises(runner.ArchitectureDevelopmentError):
        runner._validate_id_set(
            [{"case_id": "case-a"}, {"case_id": "case-a"}],
            ["case-a", "case-b"],
        )
    with pytest.raises(runner.ArchitectureDevelopmentError):
        runner._validate_id_set([{"case_id": "unknown"}], ["case-a"])


def test_schema_valid_repeated_episode_actions_match_local_contract():
    repeated = {
        "case_id": "case-a",
        "selected_action": "ask-diagnostic-question",
        "reason_code": "observe-two-bounded-responses",
        "expected_learner_action": "Explain and then refine the answer.",
        "outcome_observation": "Observe both explanations.",
        "stop_condition": "Stop after the bounded episode.",
        "replan_condition": "Replan only after a durable response.",
        "episode_steps": [
            {
                "action": "ask-diagnostic-question",
                "expected_observation": "Observe the first explanation.",
                "stop_or_replan_predicate": "Continue only if uncertainty remains.",
            },
            {
                "action": "ask-diagnostic-question",
                "expected_observation": "Observe the refined explanation.",
                "stop_or_replan_predicate": "Stop after the second observation.",
            },
        ],
    }

    proposal = runner._proposal_from_row(repeated)

    assert len(proposal.episode_steps) == 2


def test_checkpoint_namespace_is_separate_without_changing_case_identity():
    public, _gold = builder.build_packages()
    row = public["rows"][0]

    a = runner._architecture_scoped_job(
        row, AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A
    )
    c = runner._architecture_scoped_job(
        row, AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C
    )

    assert a.opportunity.opportunity_id != c.opportunity.opportunity_id
    assert runner._case_id_from_opportunity(a.opportunity.opportunity_id) == row["case_id"]
    assert runner._case_id_from_opportunity(c.opportunity.opportunity_id) == row["case_id"]


def test_scoring_keeps_shared_state_diagnostic_outside_selection():
    public, gold = builder.build_packages()
    responses = []
    gold_by_id = {row["case_id"]: row for row in gold["rows"]}
    for architecture in AutonomyArchitectureId:
        for row in public["rows"]:
            case_id = row["case_id"]
            selected = gold_by_id[case_id]["expected_action"]
            responses.append(
                {
                    "architecture_id": architecture.value,
                    "case_id": case_id,
                    "selected_action": selected,
                    "response": (
                        None
                        if selected == "no-action"
                        else {"source_range_keys": [f"source-range-{case_id}"]}
                    ),
                    "trace": {"course_id": "synthetic-autonomy-course"},
                }
            )

    result = runner._score(
        responses,
        public["rows"],
        gold["rows"],
        {"provider_calls": 0, "reported_cost_usd": 0},
    )

    assert result["status"] == "completed-go-deeper"
    assert result["decision"]["selected_architecture_id"] is None
    assert result["shared_learner_state_diagnostic"]["selection_dimension"] is False
    assert all(
        metrics["acceptable_move_accuracy"] == 1
        for metrics in result["aggregate"].values()
    )
    assert all(
        0 < metrics["mean_policy_utility"] <= 1
        for metrics in result["aggregate"].values()
    )
