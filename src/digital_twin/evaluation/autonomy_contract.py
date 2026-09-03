"""Flow-independent contracts for full-autonomy product evaluation.

The public boundary deliberately names observable events, actions, time, and
state. It does not expose LangGraph nodes, Python classes, SQLite tables,
retrieval chunk IDs, prompts, or provider-specific response objects.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import math
import time
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


class ExpectedAutonomyActionV2(_Contract):
    """Observable action expectation with prospectively valid alternatives."""

    expectation_id: str = Field(min_length=1, max_length=128)
    acceptable_actions: list[AutonomyActionKindV1] = Field(min_length=1, max_length=8)
    preferred_action: AutonomyActionKindV1 | None = None
    earliest_seconds: int = Field(ge=0)
    latest_seconds: int = Field(ge=0)
    recipient_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    must_have_valid_lineage: bool = True

    @model_validator(mode="after")
    def alternatives_and_window_must_be_valid(self) -> "ExpectedAutonomyActionV2":
        if len(self.acceptable_actions) != len(set(self.acceptable_actions)):
            raise ValueError("acceptable autonomy actions must be unique")
        if self.preferred_action is not None and self.preferred_action not in set(
            self.acceptable_actions
        ):
            raise ValueError("preferred autonomy action must be acceptable")
        has_no_action = "no-action" in self.acceptable_actions
        if has_no_action and len(self.acceptable_actions) != 1:
            raise ValueError("no-action cannot be mixed with delivered alternatives")
        if self.latest_seconds < self.earliest_seconds:
            raise ValueError("autonomy action window is inverted")
        return self


class AutonomyEvaluationGoldV2(_Contract):
    """Prospective action-equivalence gold; V1 remains immutable history."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    case_id: str = Field(min_length=1, max_length=128)
    expected_actions: list[ExpectedAutonomyActionV2] = Field(default_factory=list)
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
    terminal_goal_status: Literal[
        "active", "completed", "expired", "cancelled", "none"
    ] = "none"

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


class AutonomyProviderCallV1(_Contract):
    """Privacy-safe accounting for one provider boundary crossing."""

    call_number: int = Field(ge=1)
    task: str = Field(min_length=1, max_length=64)
    status: Literal["completed", "failed"]
    provider_model: str | None = Field(default=None, max_length=128)
    provider_revision: str | None = Field(default=None, max_length=128)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    reported_cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    latency_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    error_code: str | None = Field(default=None, max_length=128)
    failure_diagnostics: dict[
        str, str | int | bool | None | list[str]
    ] | None = None

    @model_validator(mode="after")
    def accounting_must_be_consistent(self) -> "AutonomyProviderCallV1":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("provider call token total is inconsistent")
        if self.status == "completed" and self.provider_model is None:
            raise ValueError("completed provider call requires returned model identity")
        if self.status == "failed" and self.error_code is None:
            raise ValueError("failed provider call requires a bounded error code")
        if self.failure_diagnostics is not None:
            forbidden = {"content", "text", "message", "prompt", "refusal_text"}
            if forbidden.intersection(self.failure_diagnostics):
                raise ValueError("provider diagnostics contain unrestricted content")
        return self


class AutonomyOperationalMetricsV1(_Contract):
    provider_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    provider_latency_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    cost_usd: float = Field(default=0, ge=0, allow_inf_nan=False)
    call_records: list[AutonomyProviderCallV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def aggregate_must_match_calls(self) -> "AutonomyOperationalMetricsV1":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("autonomy operational token total is inconsistent")
        if self.provider_calls != len(self.call_records):
            raise ValueError("provider-call aggregate does not match call records")
        call_numbers = [item.call_number for item in self.call_records]
        if len(call_numbers) != len(set(call_numbers)):
            raise ValueError("provider call numbers must be unique")
        if self.call_records:
            if self.input_tokens != sum(item.input_tokens for item in self.call_records):
                raise ValueError("provider input-token aggregate is inconsistent")
            if self.output_tokens != sum(item.output_tokens for item in self.call_records):
                raise ValueError("provider output-token aggregate is inconsistent")
            measured_latency = sum(item.latency_ms for item in self.call_records)
            if not math.isclose(
                self.provider_latency_ms, measured_latency, abs_tol=0.01
            ):
                raise ValueError("provider latency aggregate is inconsistent")
            reported_costs = [
                item.reported_cost_usd
                for item in self.call_records
                if item.reported_cost_usd is not None
            ]
            if not math.isclose(self.cost_usd, sum(reported_costs), abs_tol=1e-8):
                raise ValueError("provider cost aggregate is inconsistent")
        return self


class AutonomyEvaluationResponseV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(min_length=1, max_length=128)
    actions: list[AutonomyObservedActionV1]
    final_state: AutonomyStateSnapshotV1
    operational_status: Literal["completed", "failed"]
    latency_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    operational_metrics: AutonomyOperationalMetricsV1 = Field(
        default_factory=AutonomyOperationalMetricsV1
    )
    diagnostic_trace: dict[str, Any] = Field(default_factory=dict)

    @property
    def provider_calls(self) -> int:
        return self.operational_metrics.provider_calls

    @property
    def tokens(self) -> int:
        return self.operational_metrics.total_tokens

    @property
    def cost_usd(self) -> float:
        return self.operational_metrics.cost_usd


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

    async def collect_operational_metrics(self) -> AutonomyOperationalMetricsV1: ...

    async def collect_diagnostic_trace(self) -> dict[str, Any]: ...


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
        collect_operational_metrics: Callable[
            [], Awaitable[AutonomyOperationalMetricsV1]
        ]
        | None = None,
        collect_diagnostic_trace: Callable[[], Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        self.manifest = manifest
        self._reset = reset
        self._submit_event = submit_event
        self._advance_time = advance_time
        self._restart = restart
        self._collect_actions = collect_actions
        self._snapshot_state = snapshot_state
        self._collect_operational_metrics = collect_operational_metrics
        self._collect_diagnostic_trace = collect_diagnostic_trace

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

    async def collect_operational_metrics(self) -> AutonomyOperationalMetricsV1:
        if self._collect_operational_metrics is None:
            return AutonomyOperationalMetricsV1()
        return await self._collect_operational_metrics()

    async def collect_diagnostic_trace(self) -> dict[str, Any]:
        if self._collect_diagnostic_trace is None:
            return {}
        return await self._collect_diagnostic_trace()


async def run_autonomy_case(
    adapter: AutonomyEvaluationAdapterV1,
    case: AutonomyEvaluationCaseV1,
) -> AutonomyEvaluationResponseV1:
    """Run one case without exposing its gold package to the product adapter."""

    started = time.perf_counter()
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
    actions = await adapter.collect_actions()
    final_state = await adapter.snapshot_state()
    metrics = await adapter.collect_operational_metrics()
    diagnostic_trace = await adapter.collect_diagnostic_trace()
    return AutonomyEvaluationResponseV1(
        case_id=case.case_id,
        actions=actions,
        final_state=final_state,
        operational_status="completed",
        latency_ms=max(0.0, (time.perf_counter() - started) * 1_000),
        operational_metrics=metrics,
        diagnostic_trace={
            "manifest": adapter.manifest.model_dump(mode="json"),
            **diagnostic_trace,
        },
    )
