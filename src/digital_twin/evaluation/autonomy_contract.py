"""Flow-independent contracts for full-autonomy product evaluation.

The public boundary deliberately names observable events, actions, time, and
state. It does not expose LangGraph nodes, Python classes, SQLite tables,
retrieval chunk IDs, prompts, or provider-specific response objects.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


AutonomyEventKindV1 = Literal[
    "student-message",
    "time-advanced",
    "practice-outcome",
    "consent-changed",
    "membership-changed",
    "release-changed",
    "policy-changed",
    "provider-failure",
    "runtime-restart",
]

AutonomyActionKindV1 = Literal[
    "ask-diagnostic-question",
    "provide-hint-or-example",
    "recommend-approved-source",
    "issue-retrieval-practice",
    "schedule-follow-up",
    "send-in-app-check-in",
    "summarize-progress",
    "create-professor-insight-draft",
    "no-action",
]


class AutonomyEvaluationEventV1(_Contract):
    event_id: str = Field(min_length=1, max_length=128)
    kind: AutonomyEventKindV1
    at_seconds: int = Field(ge=0)
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AutonomyEvaluationCaseV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    learner_id: str = Field(min_length=1, max_length=128)
    duration_seconds: int = Field(ge=0, le=90 * 24 * 60 * 60)
    events: list[AutonomyEvaluationEventV1] = Field(default_factory=list, max_length=1_000)

    @model_validator(mode="after")
    def events_must_be_unique_and_ordered(self) -> "AutonomyEvaluationCaseV1":
        event_ids = [event.event_id for event in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("autonomy evaluation event IDs must be unique")
        if [event.at_seconds for event in self.events] != sorted(
            event.at_seconds for event in self.events
        ):
            raise ValueError("autonomy evaluation events must be time ordered")
        if any(event.at_seconds > self.duration_seconds for event in self.events):
            raise ValueError("autonomy evaluation event exceeds case duration")
        return self


class ExpectedAutonomyActionV1(_Contract):
    expectation_id: str = Field(min_length=1, max_length=128)
    action: AutonomyActionKindV1
    earliest_seconds: int = Field(ge=0)
    latest_seconds: int = Field(ge=0)
    recipient_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    must_have_valid_lineage: bool = True

    @model_validator(mode="after")
    def window_must_be_valid(self) -> "ExpectedAutonomyActionV1":
        if self.latest_seconds < self.earliest_seconds:
            raise ValueError("autonomy action window is inverted")
        return self


class AutonomyEvaluationGoldV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(min_length=1, max_length=128)
    expected_actions: list[ExpectedAutonomyActionV1] = Field(default_factory=list)
    expected_terminal_goal_status: Literal[
        "active", "completed", "expired", "cancelled", "none"
    ]
    required_invariants: list[
        Literal[
            "no-unsupported-action",
            "correct-recipient",
            "correct-course-release",
            "valid-citation-lineage",
            "consent-respected",
            "quiet-hours-respected",
            "frequency-respected",
            "no-duplicate-delivery",
            "bounded-loop",
            "restart-consistent",
            "no-model-owned-authority-mutation",
        ]
    ] = Field(default_factory=list)

    @field_validator("required_invariants")
    @classmethod
    def invariants_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("autonomy evaluation invariants must be unique")
        return value


class AutonomyObservedActionV1(_Contract):
    action_id: str = Field(min_length=1, max_length=128)
    action: AutonomyActionKindV1
    at_seconds: int = Field(ge=0)
    recipient_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    status: Literal["delivered", "suppressed", "failed", "cancelled", "no-action"]
    citation_lineage_valid: bool
    structured_reason: str = Field(min_length=1, max_length=500)


class AutonomyStateSnapshotV1(_Contract):
    captured_at_seconds: int = Field(ge=0)
    active_goal_ids: list[str] = Field(default_factory=list)
    pending_opportunity_ids: list[str] = Field(default_factory=list)
    delivered_action_ids: list[str] = Field(default_factory=list)
    learner_state_revision: int = Field(default=0, ge=0)
    consent_active: bool
    release_id: str = Field(min_length=1, max_length=128)
    policy_version: int = Field(ge=1)
    restart_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def identifiers_must_be_unique(self) -> "AutonomyStateSnapshotV1":
        for values, label in (
            (self.active_goal_ids, "active goals"),
            (self.pending_opportunity_ids, "pending opportunities"),
            (self.delivered_action_ids, "delivered actions"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"autonomy snapshot has duplicate {label}")
        return self


class AutonomyEvaluationResponseV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(min_length=1, max_length=128)
    actions: list[AutonomyObservedActionV1]
    final_state: AutonomyStateSnapshotV1
    operational_status: Literal["completed", "failed"]
    latency_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    provider_calls: int = Field(default=0, ge=0)
    tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0, allow_inf_nan=False)
    diagnostic_trace: dict[str, Any] = Field(default_factory=dict)


class AutonomySystemManifestV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    system_id: str = Field(min_length=1, max_length=128)
    flow_id: str = Field(min_length=1, max_length=128)
    adapter_version: str = Field(min_length=1, max_length=64)
    code_revision: str = Field(min_length=1, max_length=128)
    graph_version: str = Field(min_length=1, max_length=64)
    release_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: int = Field(ge=1)
    model_bindings: dict[str, str] = Field(default_factory=dict)
    network_free: bool


class AutonomyEvaluationAdapterV1(Protocol):
    """Observable full-autonomy boundary, independent of application flow."""

    manifest: AutonomySystemManifestV1

    async def reset(self, case: AutonomyEvaluationCaseV1) -> None: ...

    async def submit_event(self, event: AutonomyEvaluationEventV1) -> None: ...

    async def advance_time(self, seconds: int) -> None: ...

    async def restart(self) -> None: ...

    async def collect_actions(self) -> list[AutonomyObservedActionV1]: ...

    async def snapshot_state(self) -> AutonomyStateSnapshotV1: ...


class CallbackAutonomyEvaluationAdapterV1:
    """Adapter for local services, future graphs, or deployed HTTP drivers."""

    def __init__(
        self,
        *,
        manifest: AutonomySystemManifestV1,
        reset: Callable[[AutonomyEvaluationCaseV1], Awaitable[None]],
        submit_event: Callable[[AutonomyEvaluationEventV1], Awaitable[None]],
        advance_time: Callable[[int], Awaitable[None]],
        restart: Callable[[], Awaitable[None]],
        collect_actions: Callable[[], Awaitable[list[AutonomyObservedActionV1]]],
        snapshot_state: Callable[[], Awaitable[AutonomyStateSnapshotV1]],
    ) -> None:
        self.manifest = manifest
        self._reset = reset
        self._submit_event = submit_event
        self._advance_time = advance_time
        self._restart = restart
        self._collect_actions = collect_actions
        self._snapshot_state = snapshot_state

    async def reset(self, case: AutonomyEvaluationCaseV1) -> None:
        await self._reset(case)

    async def submit_event(self, event: AutonomyEvaluationEventV1) -> None:
        await self._submit_event(event)

    async def advance_time(self, seconds: int) -> None:
        if seconds < 0:
            raise ValueError("autonomy adapter cannot move time backward")
        await self._advance_time(seconds)

    async def restart(self) -> None:
        await self._restart()

    async def collect_actions(self) -> list[AutonomyObservedActionV1]:
        return await self._collect_actions()

    async def snapshot_state(self) -> AutonomyStateSnapshotV1:
        return await self._snapshot_state()


async def run_autonomy_case(
    adapter: AutonomyEvaluationAdapterV1,
    case: AutonomyEvaluationCaseV1,
) -> AutonomyEvaluationResponseV1:
    """Run one case without exposing its gold package to the product adapter."""

    await adapter.reset(case)
    elapsed = 0
    for event in case.events:
        if event.at_seconds > elapsed:
            await adapter.advance_time(event.at_seconds - elapsed)
            elapsed = event.at_seconds
        if event.kind == "time-advanced":
            continue
        if event.kind == "runtime-restart":
            await adapter.restart()
            continue
        await adapter.submit_event(event)
    if elapsed < case.duration_seconds:
        await adapter.advance_time(case.duration_seconds - elapsed)
    return AutonomyEvaluationResponseV1(
        case_id=case.case_id,
        actions=await adapter.collect_actions(),
        final_state=await adapter.snapshot_state(),
        operational_status="completed",
        diagnostic_trace={"manifest": adapter.manifest.model_dump(mode="json")},
    )
