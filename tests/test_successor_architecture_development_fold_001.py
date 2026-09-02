import json
import sqlite3
from dataclasses import replace

import pytest

from scripts import build_successor_architecture_development_fold_001 as builder
from scripts import run_successor_architecture_development_fold_001 as runner
from src.digital_twin.evaluation.provider_json import ProviderJsonError
from src.digital_twin.student.autonomy_models import AutonomousActionKind
from src.digital_twin.student.planning_architectures import (
    AutonomyArchitectureId,
    HierarchicalPlanningProposalV1,
    PlannerVerificationV1,
)


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


def test_second_fold_is_fresh_disjoint_and_byte_stable():
    first_public, first_gold = builder.build_packages()
    second_public, second_gold = builder.build_packages(fold_number=2)

    assert second_public == builder.build_packages(fold_number=2)[0]
    assert second_gold == builder.build_packages(fold_number=2)[1]
    assert {row["case_id"] for row in first_public["rows"]}.isdisjoint(
        row["case_id"] for row in second_public["rows"]
    )
    assert second_public["content_sha256"] != first_public["content_sha256"]
    assert second_gold["content_sha256"] != first_gold["content_sha256"]
    assert builder.validate(fold_number=2)["status"] == "passed"


def test_third_fold_is_fresh_disjoint_and_byte_stable():
    first_public, _first_gold = builder.build_packages(fold_number=1)
    second_public, _second_gold = builder.build_packages(fold_number=2)
    third_public, third_gold = builder.build_packages(fold_number=3)

    assert third_public == builder.build_packages(fold_number=3)[0]
    assert third_gold == builder.build_packages(fold_number=3)[1]
    prior_ids = {
        row["case_id"]
        for package in (first_public, second_public)
        for row in package["rows"]
    }
    third_ids = {row["case_id"] for row in third_public["rows"]}
    prior_concepts = {
        row["state_card"]["concept_id"]
        for package in (first_public, second_public)
        for row in package["rows"]
    }
    third_concepts = {
        row["state_card"]["concept_id"] for row in third_public["rows"]
    }

    assert not prior_ids & third_ids
    assert not prior_concepts & third_concepts
    assert builder.validate(fold_number=3)["status"] == "passed"


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

    assert validation["instrument_status"] == "invalid-execution-authorization-revoked"
    assert validation["provider_execution_authorized"] is False
    assert validation["paid_execution_authorized"] is False
    assert simulation["maximum_provider_calls"] == 62
    assert original.output_root != corrective.output_root
    assert original.result_path != corrective.result_path


def test_single_case_successor_is_terminal_and_authority_revoked():
    context = runner._run_context("fold-002")
    validation = runner.validate(context)
    simulation = runner.simulate(context)

    assert validation["instrument_status"] == "invalid-execution-authorization-revoked"
    assert validation["provider_execution_authorized"] is False
    assert validation["paid_execution_authorized"] is False
    assert simulation["maximum_provider_calls"] == 242
    assert simulation["planner_batch_count"] == 120
    assert simulation["gold_loaded"] is False


def test_fold_002_corrective_preserves_science_with_fresh_output_identity():
    original = runner._run_context("fold-002")
    corrective = runner._run_context("fold-002-corrective")
    validation = runner.validate(corrective)
    simulation = runner.simulate(corrective)

    assert validation["instrument_status"] == "invalid-execution-authorization-revoked"
    assert validation["provider_execution_authorized"] is False
    assert validation["paid_execution_authorized"] is False
    assert simulation["maximum_provider_calls"] == 242
    assert simulation["planner_batch_count"] == 120
    assert simulation["gold_loaded"] is False
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


def test_single_case_schemas_fix_the_exact_case_identity():
    proposal = runner._proposal_schema("case-a")
    verifier = runner._verifier_schema("case-a")

    assert proposal["properties"]["case_id"] == {
        "type": "string",
        "enum": ["case-a"],
    }
    assert verifier["properties"]["case_id"] == {
        "type": "string",
        "enum": ["case-a"],
    }
    assert "rows" not in proposal["properties"]
    assert "rows" not in verifier["properties"]


@pytest.mark.asyncio
async def test_single_case_model_failure_is_quarantined_for_safe_graph_fallback():
    public, _gold = builder.build_packages(fold_number=2)
    source = next(row for row in public["rows"] if row["guard"] == "eligible")

    class FailingTransport:
        async def call_with_ledger(self, **_kwargs):
            raise ProviderJsonError("provider returned malformed content")

    proposals, failures = await runner._call_planner_single_cases(
        transport=FailingTransport(),
        ledger=object(),
        public_rows=[source],
        concurrency=1,
    )

    assert proposals == {source["case_id"]: None}
    assert failures == [source["case_id"]]
    assert await runner._selected_c_rows([source], proposals) == []


@pytest.mark.asyncio
async def test_single_case_identity_drift_still_invalidates_the_run():
    public, _gold = builder.build_packages(fold_number=2)
    source = next(row for row in public["rows"] if row["guard"] == "eligible")

    class IdentityDriftTransport:
        async def call_with_ledger(self, **_kwargs):
            raise ProviderJsonError("provider model identity drifted")

    with pytest.raises(ProviderJsonError, match="identity drifted"):
        await runner._call_planner_single_cases(
            transport=IdentityDriftTransport(),
            ledger=object(),
            public_rows=[source],
            concurrency=1,
        )


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


@pytest.mark.asyncio
async def test_isolated_graph_database_uses_product_migrations_before_provider_graph(
    tmp_path,
):
    public, _gold = builder.build_packages(fold_number=2)
    row = next(item for item in public["rows"] if item["guard"] == "eligible")
    case_id = row["case_id"]
    proposal = HierarchicalPlanningProposalV1(
        selected_action=AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        reason_code="migration-regression",
        expected_learner_action="Explain the current reasoning.",
        outcome_observation="Observe the learner explanation.",
        stop_condition="Stop after one bounded response.",
        replan_condition="Replan after a durable learner reply.",
        episode_steps=[],
    )
    ledger = runner._ResponseLedger(
        tmp_path / "responses.sqlite3",
        binding={"test": "product-migration"},
        resume=False,
    )
    graph_database = tmp_path / "graph.sqlite3"
    try:
        await runner._run_graphs(
            public_rows=[row],
            proposals={case_id: proposal},
            verifications={case_id: PlannerVerificationV1(
                accept=True,
                reason_code="accepted",
            )},
            response_ledger=ledger,
            graph_ledger=graph_database,
        )
        assert len(ledger.rows()) == len(AutonomyArchitectureId)
    finally:
        ledger.close()

    with sqlite3.connect(graph_database) as connection:
        tables = {
            str(item[0])
            for item in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        completed_model_calls = connection.execute(
            "SELECT COUNT(*) FROM autonomous_model_calls_v2 "
            "WHERE status = 'completed'"
        ).fetchone()[0]

    assert "schema_migrations" in tables
    assert "autonomous_model_calls_v2" in tables
    assert completed_model_calls >= 1


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


def test_scoring_treats_case_failure_as_safe_quality_evidence_not_invalid_run():
    public, gold = builder.build_packages(fold_number=2)
    gold_by_id = {row["case_id"]: row for row in gold["rows"]}
    failed_case_id = next(
        row["case_id"]
        for row in public["rows"]
        if row["guard"] == "eligible"
        and gold_by_id[row["case_id"]]["expected_action"] != "no-action"
    )
    responses = []
    for architecture in AutonomyArchitectureId:
        for row in public["rows"]:
            case_id = row["case_id"]
            selected = gold_by_id[case_id]["expected_action"]
            if (
                case_id == failed_case_id
                and architecture
                != AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A
            ):
                selected = "no-action"
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
        {"provider_calls": 121, "reported_cost_usd": 0.01},
        {
            "planner_case_count": 120,
            "verifier_case_count": 0,
            "planner_failure_case_ids": [failed_case_id],
            "verifier_failure_case_ids": [],
        },
    )

    assert result["status"] == "completed-refine"
    assert result["provider_quality"]["provider_completion_rate"] == pytest.approx(
        119 / 120
    )
    assert result["hard_gates"]["provider_completion_at_least_0_995"] is False
    assert result["hard_gates"]["provider_failure_safe_fallback_rate_is_1"] is True
