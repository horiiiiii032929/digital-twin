from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from src.digital_twin.evaluation import (
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationEventV1,
    AutonomyObservedActionV1,
    AutonomyStateSnapshotV1,
    AutonomySystemManifestV1,
    CallbackAutonomyEvaluationAdapterV1,
    run_autonomy_case,
)


def _manifest() -> AutonomySystemManifestV1:
    return AutonomySystemManifestV1(
        system_id="network-free-autonomy-contract",
        flow_id="flow-independent-synthetic-driver",
        adapter_version="1.0.0",
        code_revision="test-revision",
        graph_version="governed-autonomous-tutoring-graph-v2.1",
        release_profile_sha256=hashlib.sha256(b"profile").hexdigest(),
        policy_version=1,
        model_bindings={"planner": "deterministic", "generator": "deterministic"},
        network_free=True,
    )


class _FiniteDriver:
    def __init__(self) -> None:
        self.elapsed = 0
        self.restart_count = 0
        self.consent = True
        self.release_id = "release-a"
        self.actions: list[AutonomyObservedActionV1] = []

    async def reset(self, case: AutonomyEvaluationCaseV1) -> None:
        self.elapsed = 0
        self.restart_count = 0
        self.consent = True
        self.release_id = case.release_id
        self.actions = []

    async def submit_event(self, event: AutonomyEvaluationEventV1) -> None:
        if event.kind == "consent-changed":
            self.consent = bool(event.payload.get("enabled"))
            return
        if event.kind == "student-message" and self.consent:
            self.actions.append(
                AutonomyObservedActionV1(
                    action_id=f"action-{event.event_id}",
                    action="ask-diagnostic-question",
                    at_seconds=self.elapsed,
                    recipient_id="student-a",
                    course_id="course-a",
                    release_id=self.release_id,
                    status="delivered",
                    citation_lineage_valid=True,
                    structured_reason="bounded synthetic response",
                )
            )

    async def advance_time(self, seconds: int) -> None:
        self.elapsed += seconds

    async def restart(self) -> None:
        self.restart_count += 1

    async def collect_actions(self) -> list[AutonomyObservedActionV1]:
        return list(self.actions)

    async def snapshot_state(self) -> AutonomyStateSnapshotV1:
        return AutonomyStateSnapshotV1(
            captured_at_seconds=self.elapsed,
            active_goal_ids=[] if not self.consent else ["goal-a"],
            pending_opportunity_ids=[],
            delivered_action_ids=[item.action_id for item in self.actions],
            learner_state_revision=len(self.actions),
            consent_active=self.consent,
            release_id=self.release_id,
            policy_version=1,
            restart_count=self.restart_count,
        )


def _adapter(driver: _FiniteDriver) -> CallbackAutonomyEvaluationAdapterV1:
    return CallbackAutonomyEvaluationAdapterV1(
        manifest=_manifest(),
        reset=driver.reset,
        submit_event=driver.submit_event,
        advance_time=driver.advance_time,
        restart=driver.restart,
        collect_actions=driver.collect_actions,
        snapshot_state=driver.snapshot_state,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [7, 30])
async def test_flow_independent_harness_runs_time_events_and_restarts(days: int) -> None:
    events = [
        AutonomyEvaluationEventV1(
            event_id=f"turn-{day}",
            kind="student-message",
            at_seconds=day * 86_400,
            payload={"message": "synthetic attempt"},
        )
        for day in range(days)
    ]
    events.append(
        AutonomyEvaluationEventV1(
            event_id="restart-midway",
            kind="runtime-restart",
            at_seconds=(days // 2) * 86_400,
        )
    )
    events.append(
        AutonomyEvaluationEventV1(
            event_id="consent-off",
            kind="consent-changed",
            at_seconds=days * 86_400,
            payload={"enabled": False},
        )
    )
    events.sort(key=lambda item: (item.at_seconds, item.event_id))
    case = AutonomyEvaluationCaseV1(
        case_id=f"network-free-{days}-day",
        course_id="course-a",
        release_id="release-a",
        learner_id="student-a",
        duration_seconds=days * 86_400,
        events=events,
    )

    response = await run_autonomy_case(_adapter(_FiniteDriver()), case)

    assert response.operational_status == "completed"
    assert len(response.actions) == days
    assert len({item.action_id for item in response.actions}) == days
    assert response.final_state.restart_count == 1
    assert response.final_state.consent_active is False
    assert response.final_state.active_goal_ids == []
    assert response.provider_calls == 0


def test_contract_rejects_duplicate_or_out_of_order_events() -> None:
    with pytest.raises(ValidationError):
        AutonomyEvaluationCaseV1(
            case_id="invalid",
            course_id="course-a",
            release_id="release-a",
            learner_id="student-a",
            duration_seconds=10,
            events=[
                AutonomyEvaluationEventV1(
                    event_id="same", kind="student-message", at_seconds=5
                ),
                AutonomyEvaluationEventV1(
                    event_id="same", kind="student-message", at_seconds=1
                ),
            ],
        )


@pytest.mark.asyncio
async def test_callback_adapter_rejects_backward_time() -> None:
    adapter = _adapter(_FiniteDriver())
    with pytest.raises(ValueError, match="backward"):
        await adapter.advance_time(-1)
