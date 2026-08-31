"""Versioned contracts for governed, event-driven tutoring autonomy.

These records intentionally contain structured decisions, not chain-of-thought.
Deterministic code owns identity, scope, policy, release, consent, delivery, and
state commits; a model may only propose bounded pedagogical fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.digital_twin.tutor_policy import timestamp_now


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AutonomousEventKind(StrEnum):
    STUDENT_MESSAGE = "student-message"
    REPEATED_CONFUSION = "repeated-confusion"
    MISCONCEPTION = "misconception"
    INCOMPLETE_OBJECTIVE = "incomplete-objective"
    SPACED_REVIEW_DUE = "spaced-review-due"
    STUDENT_INACTIVITY = "student-inactivity"
    EVIDENCE_RECOVERED = "evidence-recovered"
    NEW_COURSE_RELEASE = "new-course-release"
    PRACTICE_INCOMPLETE = "practice-incomplete"
    PROFESSOR_SCHEDULED = "professor-scheduled"
    CONSENT_CHANGED = "consent-changed"
    MEMBERSHIP_CHANGED = "membership-changed"
    RELEASE_CHANGED = "release-changed"
    POLICY_CHANGED = "policy-changed"


class AutonomousActionKind(StrEnum):
    ASK_DIAGNOSTIC_QUESTION = "ask-diagnostic-question"
    PROVIDE_HINT_OR_EXAMPLE = "provide-hint-or-example"
    RECOMMEND_APPROVED_SOURCE = "recommend-approved-source"
    ISSUE_RETRIEVAL_PRACTICE = "issue-retrieval-practice"
    SCHEDULE_FOLLOW_UP = "schedule-follow-up"
    SEND_IN_APP_CHECK_IN = "send-in-app-check-in"
    SUMMARIZE_PROGRESS = "summarize-progress"
    CREATE_PROFESSOR_INSIGHT_DRAFT = "create-professor-insight-draft"
    NO_ACTION = "no-action"


class AutonomousGoalStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AutonomousOpportunityStatus(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    COMPLETED = "completed"
    NO_ACTION = "no-action"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AutonomousActionStatus(StrEnum):
    PROPOSED = "proposed"
    DELIVERED = "delivered"
    SUPPRESSED = "suppressed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutonomousOutcomeKind(StrEnum):
    DELIVERED = "delivered"
    DISMISSED = "dismissed"
    ANSWERED = "answered"
    EXPIRED = "expired"
    FAILED = "failed"
    NO_ACTION = "no-action"


class TurnPerceptionV2(_Contract):
    schema_version: Literal["2.1.0"] = "2.1.0"
    event_kind: AutonomousEventKind
    request_type: str = Field(min_length=1, max_length=64)
    attempt_present: bool = False
    confusion: float = Field(default=0, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    engagement: float = Field(default=0.5, ge=0, le=1)
    ambiguous: bool = False
    misconception_observed: bool = False
    direct_solution_request: bool = False
    observed_at: str = Field(default_factory=timestamp_now)


class LearnerObservationV2(_Contract):
    schema_version: Literal["2.1.0"] = "2.1.0"
    observation_id: str = Field(min_length=1, max_length=128)
    learner_key: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    event_kind: AutonomousEventKind
    concept_ids: list[str] = Field(default_factory=list, max_length=16)
    perception: TurnPerceptionV2
    source_turn_key: str | None = Field(default=None, max_length=128)
    observed_at: str = Field(default_factory=timestamp_now)

    @field_validator("concept_ids")
    @classmethod
    def concepts_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("learner observation concept IDs must be unique")
        return value


class ConceptAttributionV2(_Contract):
    concept_id: str = Field(min_length=1, max_length=128)
    observed_mastery: float = Field(ge=0, le=1)
    attribution_confidence: float = Field(ge=0, le=1)
    evidence_keys: list[str] = Field(default_factory=list, max_length=16)


class LearnerHypothesisV2(_Contract):
    hypothesis_id: str = Field(min_length=1, max_length=128)
    concept_id: str = Field(min_length=1, max_length=128)
    kind: Literal["misconception", "knowledge-gap", "low-confidence", "inactive"]
    probability: float = Field(ge=0, le=1)
    observation_ids: list[str] = Field(min_length=1, max_length=16)
    status: Literal["tentative", "supported", "rejected"] = "tentative"


class LearnerBeliefStateV2(_Contract):
    schema_version: Literal["2.1.0"] = "2.1.0"
    learner_key: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    revision: int = Field(default=0, ge=0)
    concepts: list[ConceptAttributionV2] = Field(default_factory=list, max_length=64)
    hypotheses: list[LearnerHypothesisV2] = Field(default_factory=list, max_length=32)
    active_goal_ids: list[str] = Field(default_factory=list, max_length=3)
    updated_at: str = Field(default_factory=timestamp_now)

    @model_validator(mode="after")
    def identifiers_must_be_unique(self) -> "LearnerBeliefStateV2":
        for values, label in (
            ([item.concept_id for item in self.concepts], "concept"),
            ([item.hypothesis_id for item in self.hypotheses], "hypothesis"),
            (self.active_goal_ids, "goal"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"learner belief {label} IDs must be unique")
        return self


class PedagogicalPolicyV2(_Contract):
    schema_version: Literal["2.1.0"] = "2.1.0"
    course_id: str = Field(min_length=1, max_length=128)
    version: int = Field(ge=1)
    approved_by: str = Field(min_length=1, max_length=128)
    approved_profile_id: str = Field(min_length=1, max_length=128)
    approved_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_course_objectives: list[str] = Field(min_length=1, max_length=32)
    autonomy_enabled: bool = False
    paused: bool = False
    kill_switch: bool = False
    allowed_actions: list[AutonomousActionKind] = Field(default_factory=list)
    max_active_goals: int = Field(default=3, ge=1, le=3)
    max_messages_per_7_days: int = Field(default=3, ge=1, le=3)
    same_concept_cooldown_hours: int = Field(default=24, ge=1, le=168)
    planning_calls_per_event: int = Field(default=1, ge=0, le=1)
    generation_calls_per_event: int = Field(default=1, ge=0, le=1)
    repair_calls_per_event: int = Field(default=1, ge=0, le=1)
    provider_retries: int = Field(default=0, ge=0, le=0)
    recursion_limit: int = Field(default=12, ge=1, le=12)
    integrity_ceiling: str = Field(default="attempt-first", min_length=1, max_length=64)
    updated_at: str = Field(default_factory=timestamp_now)

    @field_validator("allowed_actions")
    @classmethod
    def actions_must_be_unique(cls, value: list[AutonomousActionKind]) -> list[AutonomousActionKind]:
        if len(value) != len(set(value)):
            raise ValueError("autonomy policy actions must be unique")
        return value

    @field_validator("approved_course_objectives")
    @classmethod
    def objectives_must_be_unique_and_trimmed(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or item != item.strip() for item in value):
            raise ValueError("approved course objectives must be non-blank and trimmed")
        if len(value) != len(set(value)):
            raise ValueError("approved course objectives must be unique")
        return value


class PedagogicalPlanV2(_Contract):
    schema_version: Literal["2.1.0"] = "2.1.0"
    action: AutonomousActionKind
    goal_id: str | None = Field(default=None, max_length=128)
    reason_code: str = Field(min_length=1, max_length=128)
    expected_learner_action: str | None = Field(default=None, max_length=500)
    required_evidence_keys: list[str] = Field(default_factory=list, max_length=8)
    outcome_observation: str | None = Field(default=None, max_length=500)
    stop_condition: str = Field(min_length=1, max_length=500)
    replan_condition: str | None = Field(default=None, max_length=500)


class LearnerStateDeltaV2(_Contract):
    schema_version: Literal["2.1.0"] = "2.1.0"
    previous_revision: int = Field(ge=0)
    next_revision: int = Field(ge=1)
    completed_goal_ids: list[str] = Field(default_factory=list, max_length=3)
    activated_goal_ids: list[str] = Field(default_factory=list, max_length=3)
    changed_concept_ids: list[str] = Field(default_factory=list, max_length=16)
    reason_code: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def revision_must_advance_once(self) -> "LearnerStateDeltaV2":
        if self.next_revision != self.previous_revision + 1:
            raise ValueError("learner-state delta must advance exactly one revision")
        return self


class GroundedTutorResponseV2(_Contract):
    schema_version: Literal["2.1.0"] = "2.1.0"
    action: AutonomousActionKind
    content: str = Field(min_length=1, max_length=8_000)
    atomic_claims: list[str] = Field(default_factory=list, max_length=8)
    citation_ids: list[str] = Field(default_factory=list, max_length=8)
    source_range_keys: list[str] = Field(default_factory=list, max_length=8)
    policy_action: Literal["answer", "clarify", "abstain", "refuse", "no-action"]

    @model_validator(mode="after")
    def answer_requires_lineage(self) -> "GroundedTutorResponseV2":
        if self.policy_action == "answer" and (
            not self.atomic_claims
            or not self.citation_ids
            or not self.source_range_keys
        ):
            raise ValueError("grounded answer requires claims, citations, and source ranges")
        if self.policy_action != "answer" and (
            self.atomic_claims or self.citation_ids or self.source_range_keys
        ):
            raise ValueError("non-answer response cannot claim evidence lineage")
        return self


class AgentTraceV2(_Contract):
    schema_version: Literal["2.1.0"] = "2.1.0"
    graph_version: str = Field(min_length=1, max_length=64)
    policy_version: int = Field(ge=1)
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    planner_model: str | None = Field(default=None, max_length=128)
    generator_model: str | None = Field(default=None, max_length=128)
    fast_path: bool = False
    planning_calls: int = Field(default=0, ge=0, le=1)
    generation_calls: int = Field(default=0, ge=0, le=1)
    repair_calls: int = Field(default=0, ge=0, le=1)
    decision_reason: str = Field(min_length=1, max_length=500)
    validation_results: dict[str, bool] = Field(default_factory=dict)
    started_at: str = Field(default_factory=timestamp_now)
    completed_at: str | None = None


class AutonomousGoalV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    goal_id: str = Field(min_length=1, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    policy_version: int = Field(ge=1)
    profile_id: str = Field(min_length=1, max_length=128)
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_version: str = Field(min_length=1, max_length=64)
    planner_model: str = Field(min_length=1, max_length=128)
    generator_model: str = Field(min_length=1, max_length=128)
    approved_course_objective: str = Field(min_length=1, max_length=500)
    learner_subgoal: str = Field(min_length=1, max_length=500)
    success_condition: str = Field(min_length=1, max_length=500)
    priority: int = Field(default=1, ge=1, le=5)
    attempt_limit: int = Field(default=3, ge=1, le=10)
    attempt_count: int = Field(default=0, ge=0)
    status: AutonomousGoalStatus = AutonomousGoalStatus.ACTIVE
    expires_at: str
    created_at: str = Field(default_factory=timestamp_now)
    updated_at: str = Field(default_factory=timestamp_now)

    @model_validator(mode="after")
    def attempts_and_expiry_must_be_valid(self) -> "AutonomousGoalV1":
        if self.attempt_count > self.attempt_limit:
            raise ValueError("goal attempt count exceeds its limit")
        _require_after(self.created_at, self.expires_at, "goal expiry")
        return self


class ProactiveOpportunityV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    opportunity_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    event_kind: AutonomousEventKind
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    policy_version: int = Field(ge=1)
    profile_id: str = Field(min_length=1, max_length=128)
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_version: str = Field(min_length=1, max_length=64)
    planner_model: str = Field(min_length=1, max_length=128)
    generator_model: str = Field(min_length=1, max_length=128)
    goal_id: str | None = Field(default=None, max_length=128)
    supporting_observation_ids: list[str] = Field(default_factory=list, max_length=16)
    concept_id: str | None = Field(default=None, max_length=128)
    source_chunk_id: str | None = Field(default=None, max_length=256)
    source_chunk_ids: list[str] = Field(default_factory=list, max_length=5)
    earliest_action_at: str
    latest_action_at: str
    status: AutonomousOpportunityStatus = AutonomousOpportunityStatus.PENDING
    created_at: str = Field(default_factory=timestamp_now)
    updated_at: str = Field(default_factory=timestamp_now)

    @model_validator(mode="after")
    def action_window_must_be_ordered(self) -> "ProactiveOpportunityV1":
        _require_after(self.earliest_action_at, self.latest_action_at, "opportunity window")
        if len(self.source_chunk_ids) != len(set(self.source_chunk_ids)):
            raise ValueError("opportunity source chunk IDs must be unique")
        if self.source_chunk_id and self.source_chunk_ids and self.source_chunk_id not in self.source_chunk_ids:
            raise ValueError("primary source chunk must be included in the evidence bundle")
        return self


class AutonomousPlanV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    plan_id: str = Field(min_length=1, max_length=128)
    opportunity_id: str = Field(min_length=1, max_length=128)
    goal_id: str | None = Field(default=None, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    policy_version: int = Field(ge=1)
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_version: str = Field(min_length=1, max_length=64)
    planner_model: str = Field(min_length=1, max_length=128)
    action: AutonomousActionKind
    reason_code: str = Field(min_length=1, max_length=128)
    expected_learner_action: str | None = Field(default=None, max_length=500)
    required_evidence_keys: list[str] = Field(default_factory=list, max_length=8)
    outcome_observation: str | None = Field(default=None, max_length=500)
    stop_condition: str = Field(min_length=1, max_length=500)
    replan_condition: str | None = Field(default=None, max_length=500)
    created_at: str = Field(default_factory=timestamp_now)


class AutonomousActionV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    action_id: str = Field(min_length=1, max_length=128)
    plan_id: str = Field(min_length=1, max_length=128)
    opportunity_id: str = Field(min_length=1, max_length=128)
    goal_id: str | None = Field(default=None, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    policy_version: int = Field(ge=1)
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_version: str = Field(min_length=1, max_length=64)
    generator_model: str = Field(min_length=1, max_length=128)
    kind: AutonomousActionKind
    status: AutonomousActionStatus = AutonomousActionStatus.PROPOSED
    proactive_trigger_id: str | None = Field(default=None, max_length=128)
    structured_reason: str = Field(min_length=1, max_length=500)
    validation_results: dict[str, bool] = Field(default_factory=dict)
    created_at: str = Field(default_factory=timestamp_now)
    updated_at: str = Field(default_factory=timestamp_now)


class AutonomousOutcomeV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    outcome_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    goal_id: str | None = Field(default=None, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    policy_version: int = Field(ge=1)
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_version: str = Field(min_length=1, max_length=64)
    kind: AutonomousOutcomeKind
    learner_observation_id: str | None = Field(default=None, max_length=128)
    goal_progress: float = Field(default=0, ge=0, le=1)
    next_wake_at: str | None = None
    recorded_at: str = Field(default_factory=timestamp_now)


class AutonomousWakeUpV1(_Contract):
    wake_up_id: str = Field(min_length=1, max_length=128)
    goal_id: str = Field(min_length=1, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    concept_id: str | None = Field(default=None, max_length=128)
    source_chunk_id: str | None = Field(default=None, max_length=256)
    due_at: str
    event_kind: AutonomousEventKind
    status: Literal["pending", "fired", "cancelled"] = "pending"
    created_at: str = Field(default_factory=timestamp_now)


class AutonomousPlannerOutputV1(_Contract):
    """The only fields a planner model may propose."""

    action: AutonomousActionKind
    reason_code: str = Field(min_length=1, max_length=128)
    expected_learner_action: str | None = Field(default=None, max_length=500)
    required_evidence_keys: list[str] = Field(default_factory=list, max_length=8)
    outcome_observation: str | None = Field(default=None, max_length=500)
    stop_condition: str = Field(min_length=1, max_length=500)
    replan_condition: str | None = Field(default=None, max_length=500)


def _require_after(start: str, end: str, label: str) -> None:
    try:
        start_at = datetime.fromisoformat(start)
        end_at = datetime.fromisoformat(end)
    except ValueError as error:
        raise ValueError(f"{label} must use ISO-8601 timestamps") from error
    if start_at.tzinfo is None or end_at.tzinfo is None:
        raise ValueError(f"{label} timestamps must be timezone-aware")
    if end_at.astimezone(UTC) <= start_at.astimezone(UTC):
        raise ValueError(f"{label} end must be after start")
