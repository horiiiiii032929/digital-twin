from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_002 as builder,
)
from scripts.governed_full_autonomy_v2_1_actual_product_runtime import (
    build_runtime_factory,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_002 as runner,
)
from src.digital_twin.evaluation import (
    AutonomySystemManifestV1,
    run_autonomy_case,
    score_autonomy_case,
)
from src.digital_twin.evaluation.autonomy_product_adapter import (
    StudentProductAutonomyAdapterV1,
)


def test_actual_product_successor_has_realistic_virtual_time_portfolio() -> None:
    result = builder.validate()

    assert result["status"] == "passed-build-only"
    assert result["case_count"] == 820
    assert result["trajectory_case_count"] == 600
    assert result["long_horizon_case_count"] == 100
    assert result["proactive_opportunity_case_count"] == 120
    assert result["source_template_count"] == 50
    assert result["provider_execution_authorized"] is False


def test_actual_product_successor_uses_policy_windows_not_compressed_seconds() -> None:
    contract = builder.build_contract()
    long_cases = [
        case
        for _condition, case, _gold in contract
        if case.case_id.startswith("long-horizon-")
    ]
    autonomous_trajectories = [
        case
        for condition, case, _gold in contract
        if case.case_id.startswith("trajectory-") and condition == "t1-v2-autonomous"
    ]

    assert all(case.duration_seconds >= 30 * builder.DAY for case in long_cases)
    assert all(
        any(
            event.kind == "time-advanced" and event.at_seconds == builder.DAY
            for event in case.events
        )
        for case in autonomous_trajectories
    )


def test_actual_product_public_contract_does_not_contain_gold() -> None:
    public = builder.public_payload()

    forbidden = {
        "expected_actions",
        "expected_terminal_goal_status",
        "required_invariants",
    }
    assert all(not forbidden.intersection(row["case"]) for row in public["rows"])
    assert public["content_sha256"] != builder.hidden_gold_payload()["content_sha256"]


def test_frequency_gate_counts_only_autonomous_deliveries() -> None:
    response = SimpleNamespace(
        actions=[
            *[
                SimpleNamespace(
                    action_id=f"turn:{index}",
                    status="delivered",
                    action="provide-hint-or-example",
                    at_seconds=index * 60,
                )
                for index in range(8)
            ],
            *[
                SimpleNamespace(
                    action_id=f"autonomous:{index}",
                    status="delivered",
                    action="send-in-app-check-in",
                    at_seconds=index * builder.DAY,
                )
                for index in range(4)
            ],
        ]
    )

    assert runner._proactive_frequency_violation_count(
        [("t1-v2-autonomous", response)],
        window_seconds=7 * builder.DAY,
        maximum_deliveries=3,
    ) == 1


def test_actual_product_runner_is_blocked_after_authority_revocation() -> None:
    result = runner.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert "grounding-selection-002-keep-missing" in result["blockers"]
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False


@pytest.mark.asyncio
async def test_actual_product_network_free_representatives_cross_real_services(
    tmp_path,
) -> None:
    cases = {
        case.case_id: (condition, case, gold)
        for condition, case, gold in builder.build_contract()
    }
    case_ids = (
        "trajectory-001-t0-grounded-control-seed-1",
        "trajectory-006-t1-v1-reactive-control-seed-1",
        "trajectory-001-t1-v2-reactive-seed-1",
        "trajectory-006-t1-v2-autonomous-seed-1",
        "long-horizon-081",
        "opportunity-081",
    )

    for case_id in case_ids:
        condition, case, gold = cases[case_id]
        manifest = AutonomySystemManifestV1(
            system_id=f"test-{condition}",
            flow_id=condition,
            adapter_version=StudentProductAutonomyAdapterV1.adapter_version,
            code_revision="network-free-test",
            graph_version=condition,
            release_profile_sha256="0" * 64,
            policy_version=1,
            model_bindings={
                "planner": "deterministic",
                "generator": "deterministic",
            },
            network_free=True,
        )
        adapter = StudentProductAutonomyAdapterV1(
            condition=condition,
            manifest=manifest,
            runtime_factory=build_runtime_factory(
                tmp_path / case_id,
                condition,
                provider_backed=False,
            ),
            clock_origin=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        )
        try:
            response = await run_autonomy_case(adapter, case)
            score = score_autonomy_case(case, gold, response)
        finally:
            adapter.close()

        assert score.hard_gates_passed, (case_id, score.failure_codes)
        assert response.operational_metrics.provider_calls == 0
