"""Finite LangGraph runtime for governed proactive tutoring jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.student.autonomy_models import (
    AgentTraceV2,
    AutonomousActionKind,
    AutonomousActionStatus,
    AutonomousActionV1,
    AutonomousEventKind,
    AutonomousGoalV1,
    AutonomousOpportunityStatus,
    AutonomousOutcomeKind,
    AutonomousOutcomeV1,
    AutonomousPlanV1,
    AutonomousPlannerOutputV1,
    AutonomousWakeUpV1,
    GroundedTutorResponseV2,
    PedagogicalPolicyV2,
    ProactiveOpportunityV1,
)
from src.digital_twin.llm import LlmClient, LlmError, LlmMessage
from src.digital_twin.tutor_policy import timestamp_now


GRAPH_VERSION = "governed-autonomous-tutoring-graph-v2.1"
DETERMINISTIC_PLANNER_MODEL = "deterministic/autonomy-planner-v1"
DETERMINISTIC_GENERATOR_MODEL = "deterministic/autonomy-wording-v1"


class AutonomousRuntimeError(RuntimeError):
    pass


class AutonomousJobInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity: ProactiveOpportunityV1
    goal: AutonomousGoalV1 | None = None
    policy: PedagogicalPolicyV2
    professor_id: str = Field(min_length=1, max_length=128)
    current_release_id: str = Field(min_length=1, max_length=128)
    current_profile_id: str = Field(min_length=1, max_length=128)
    current_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    membership_active: bool
    consent_active: bool
    within_quiet_hours: bool = False
    recent_message_count: int = Field(default=0, ge=0)
    same_concept_cooldown_active: bool = False
    evidence_keys: list[str] = Field(default_factory=list, max_length=8)
    evidence_chunk_ids: list[str] = Field(default_factory=list, max_length=5)
    evidence_decision_reason: str = Field(default="not-assessed", min_length=1, max_length=256)
    evidence_complete: bool = False
    evidence_unique: bool = False
    evidence_current: bool = False
    evidence_authorized: bool = False
    now: str = Field(default_factory=timestamp_now)

    @model_validator(mode="after")
    def bindings_must_match(self) -> "AutonomousJobInput":
        opportunity = self.opportunity
        if len(self.evidence_keys) != len(set(self.evidence_keys)):
            raise ValueError("autonomous evidence keys must be unique")
        if len(self.evidence_chunk_ids) != len(set(self.evidence_chunk_ids)):
            raise ValueError("autonomous evidence chunk IDs must be unique")
        if self.evidence_complete and (
            not self.evidence_keys or not self.evidence_chunk_ids
        ):
            raise ValueError("complete autonomous evidence requires keys and chunk IDs")
        if self.goal is not None and (
            opportunity.goal_id != self.goal.goal_id
            or opportunity.student_id != self.goal.student_id
            or opportunity.course_id != self.goal.course_id
            or opportunity.release_id != self.goal.release_id
        ):
            raise ValueError("autonomous goal and opportunity scope differ")
        if (
            self.policy.course_id != opportunity.course_id
            or self.policy.version != opportunity.policy_version
            or self.policy.approved_profile_id != opportunity.profile_id
            or self.policy.approved_profile_sha256 != opportunity.profile_sha256
            or opportunity.graph_version != GRAPH_VERSION
        ):
            raise ValueError("autonomous input policy binding differs")
        return self


class AutonomousJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity: ProactiveOpportunityV1
    plan: AutonomousPlanV1
    action: AutonomousActionV1
    outcome: AutonomousOutcomeV1
    response: GroundedTutorResponseV2 | None = None
    wake_up: AutonomousWakeUpV1 | None = None
    trace: AgentTraceV2


class AutonomousPlanner(Protocol):
    model_id: str

    async def plan(self, job: AutonomousJobInput) -> AutonomousPlannerOutputV1: ...


class AutonomousWordingGenerator(Protocol):
    model_id: str

    async def generate(
        self,
        job: AutonomousJobInput,
        plan: AutonomousPlannerOutputV1,
    ) -> GroundedTutorResponseV2: ...


class DeterministicAutonomousPlanner:
    model_id = DETERMINISTIC_PLANNER_MODEL

    async def plan(self, job: AutonomousJobInput) -> AutonomousPlannerOutputV1:
        event = job.opportunity.event_kind
        action = {
            AutonomousEventKind.STUDENT_MESSAGE: (
                AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
            ),
            AutonomousEventKind.REPEATED_CONFUSION: (
                AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
            ),
            AutonomousEventKind.MISCONCEPTION: (
                AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
            ),
            AutonomousEventKind.INCOMPLETE_OBJECTIVE: (
                AutonomousActionKind.SEND_IN_APP_CHECK_IN
            ),
            AutonomousEventKind.SPACED_REVIEW_DUE: (
                AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE
            ),
            AutonomousEventKind.STUDENT_INACTIVITY: (
                AutonomousActionKind.SEND_IN_APP_CHECK_IN
            ),
            AutonomousEventKind.EVIDENCE_RECOVERED: (
                AutonomousActionKind.RECOMMEND_APPROVED_SOURCE
            ),
            AutonomousEventKind.NEW_COURSE_RELEASE: (
                AutonomousActionKind.RECOMMEND_APPROVED_SOURCE
            ),
            AutonomousEventKind.PRACTICE_INCOMPLETE: (
                AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
            ),
            AutonomousEventKind.PROFESSOR_SCHEDULED: (
                AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE
            ),
        }.get(event, AutonomousActionKind.NO_ACTION)
        return AutonomousPlannerOutputV1(
            action=action,
            reason_code=f"event-{event.value}",
            expected_learner_action=(
                "Respond in the course workspace."
                if action != AutonomousActionKind.NO_ACTION
                else None
            ),
            required_evidence_keys=(
                job.evidence_keys if action != AutonomousActionKind.NO_ACTION else []
            ),
            outcome_observation=(
                "Observe whether the learner responds, dismisses, or completes the goal."
                if action != AutonomousActionKind.NO_ACTION
                else None
            ),
            stop_condition="Stop after one bounded action or no-action decision.",
            replan_condition=(
                "Replan only after a new durable learner event or scheduled wake-up."
                if action != AutonomousActionKind.NO_ACTION
                else None
            ),
        )


class LiveAutonomousPlanner:
    """One model proposal with deterministic fallback and no retry."""

    def __init__(self, client: LlmClient, *, model_id: str) -> None:
        self.client = client
        self.model_id = model_id
        self.fallback = DeterministicAutonomousPlanner()

    async def plan(self, job: AutonomousJobInput) -> AutonomousPlannerOutputV1:
        policy = job.policy
        goal = job.goal
        prompt = {
            "role": "pedagogical planner",
            "instruction": (
                "Choose exactly one bounded action from allowed_actions. Do not infer or "
                "change identity, recipient, membership, release, policy, consent, timing, "
                "evidence, citations, or delivery. Select no-action when an intervention is "
                "not pedagogically necessary. Give a short reason code, observable learner "
                "outcome, and terminal stop/replan condition."
            ),
            "event_kind": job.opportunity.event_kind.value,
            "concept_id": job.opportunity.concept_id,
            "supporting_observation_count": len(
                job.opportunity.supporting_observation_ids
            ),
            "goal": (
                {
                    "learner_subgoal": goal.learner_subgoal,
                    "success_condition": goal.success_condition,
                    "attempt_count": goal.attempt_count,
                    "attempt_limit": goal.attempt_limit,
                }
                if goal is not None
                else None
            ),
            "allowed_actions": [action.value for action in policy.allowed_actions],
            "evidence_keys": job.evidence_keys,
        }
        import json

        try:
            response = await self.client.chat(
                [
                    LlmMessage(
                        role="system",
                        content=(
                            "Return only the requested structured pedagogical plan. "
                            "Never include chain-of-thought or personal data."
                        ),
                    ),
                    LlmMessage(
                        role="user",
                        content=json.dumps(prompt, sort_keys=True),
                    ),
                ],
                task="autonomous_tutoring_plan",
            )
            return AutonomousPlannerOutputV1.model_validate_json(response.content)
        except (LlmError, ValueError):
            return await self.fallback.plan(job)


class DeterministicAutonomousWordingGenerator:
    model_id = DETERMINISTIC_GENERATOR_MODEL

    async def generate(
        self,
        job: AutonomousJobInput,
        plan: AutonomousPlannerOutputV1,
    ) -> GroundedTutorResponseV2:
        if plan.action == AutonomousActionKind.NO_ACTION:
            return GroundedTutorResponseV2(
                action=plan.action,
                content="No proactive tutoring action was eligible.",
                policy_action="no-action",
            )
        concept = job.opportunity.concept_id or "your current course objective"
        wording = {
            AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION: (
                f"Quick check on {concept}: which part is still uncertain, and what have you tried?"
            ),
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE: (
                f"A short hint for {concept} is available from the approved course source. "
                "Try one next step, then reply with your reasoning."
            ),
            AutonomousActionKind.RECOMMEND_APPROVED_SOURCE: (
                f"New approved evidence is available for {concept}. Review the cited section, "
                "then tell me whether it resolves your earlier question."
            ),
            AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE: (
                f"Retrieval check for {concept}: explain the core idea from memory, then compare "
                "your explanation with the cited course section."
            ),
            AutonomousActionKind.SEND_IN_APP_CHECK_IN: (
                f"Would you like to continue your goal on {concept}? Reply with your next step or "
                "snooze this check-in."
            ),
            AutonomousActionKind.SUMMARIZE_PROGRESS: (
                f"Your current focus is {concept}. Review the cited material and choose the next step."
            ),
        }.get(plan.action, "A bounded tutoring follow-up is available in your course workspace.")
        return GroundedTutorResponseV2(
            action=plan.action,
            content=wording,
            atomic_claims=[f"The intervention concerns {concept}."],
            citation_ids=[f"citation:{key}" for key in plan.required_evidence_keys],
            source_range_keys=plan.required_evidence_keys,
            policy_action="answer",
        )


class _RuntimeState(TypedDict):
    job: AutonomousJobInput
    proposal: AutonomousPlannerOutputV1 | None
    plan: AutonomousPlanV1 | None
    response: GroundedTutorResponseV2 | None
    action: AutonomousActionV1 | None
    outcome: AutonomousOutcomeV1 | None
    wake_up: AutonomousWakeUpV1 | None
    trace: AgentTraceV2
    blocked_reason: str | None


class GovernedAutonomousTutoringGraph:
    """One event, one finite job, one terminal action or no-action."""

    implementation_id = GRAPH_VERSION
    recursion_limit = 12

    def __init__(
        self,
        *,
        planner: AutonomousPlanner | None = None,
        generator: AutonomousWordingGenerator | None = None,
    ) -> None:
        self.planner = planner or DeterministicAutonomousPlanner()
        self.generator = generator or DeterministicAutonomousWordingGenerator()
        self._graph = self._build_graph()

    async def run(self, job: AutonomousJobInput) -> AutonomousJobResult:
        initial: _RuntimeState = {
            "job": job,
            "proposal": None,
            "plan": None,
            "response": None,
            "action": None,
            "outcome": None,
            "wake_up": None,
            "trace": AgentTraceV2(
                graph_version=self.implementation_id,
                policy_version=job.policy.version,
                profile_sha256=job.policy.approved_profile_sha256,
                planner_model=self.planner.model_id,
                generator_model=self.generator.model_id,
                decision_reason="job-started",
            ),
            "blocked_reason": None,
        }
        result = await self._graph.ainvoke(
            initial,
            config={"recursion_limit": self.recursion_limit},
        )
        required = (result["plan"], result["action"], result["outcome"])
        if any(item is None for item in required):
            raise AutonomousRuntimeError("autonomous graph ended without durable records")
        return AutonomousJobResult(
            opportunity=result["job"].opportunity,
            plan=result["plan"],
            action=result["action"],
            outcome=result["outcome"],
            response=result["response"],
            wake_up=result["wake_up"],
            trace=result["trace"],
        )

    def _build_graph(self):
        graph = StateGraph(_RuntimeState)
        graph.add_node("observe", self._observe)
        graph.add_node("plan", self._plan)
        graph.add_node("authorize", self._authorize)
        graph.add_node("generate", self._generate)
        graph.add_node("validate", self._validate)
        graph.add_node("record_no_action", self._record_no_action)
        graph.add_node("finalize", self._finalize)
        graph.add_edge(START, "observe")
        graph.add_conditional_edges(
            "observe", self._after_observe, {"plan": "plan", "stop": "record_no_action"}
        )
        graph.add_edge("plan", "authorize")
        graph.add_conditional_edges(
            "authorize",
            self._after_authorize,
            {"generate": "generate", "stop": "record_no_action"},
        )
        graph.add_edge("generate", "validate")
        graph.add_conditional_edges(
            "validate",
            self._after_validate,
            {"pass": "finalize", "stop": "record_no_action"},
        )
        graph.add_edge("record_no_action", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    def _observe(self, state: _RuntimeState) -> dict:
        job = state["job"]
        now = _instant(job.now)
        opportunity = job.opportunity
        reason: str | None = None
        if opportunity.status not in {
            AutonomousOpportunityStatus.PENDING,
            AutonomousOpportunityStatus.LEASED,
        }:
            reason = "opportunity-not-active"
        elif now < _instant(opportunity.earliest_action_at):
            reason = "opportunity-not-due"
        elif now > _instant(opportunity.latest_action_at):
            reason = "opportunity-expired"
        elif job.goal is not None and job.goal.status.value != "active":
            reason = "goal-not-active"
        elif (
            job.goal is not None
            and job.goal.attempt_count >= job.goal.attempt_limit
        ):
            reason = "goal-attempt-limit-reached"
        return {"blocked_reason": reason}

    @staticmethod
    def _after_observe(state: _RuntimeState) -> str:
        return "stop" if state["blocked_reason"] else "plan"

    async def _plan(self, state: _RuntimeState) -> dict:
        proposal = await self.planner.plan(state["job"])
        job = state["job"]
        plan = AutonomousPlanV1(
            plan_id=f"autonomous-plan-{uuid4()}",
            opportunity_id=job.opportunity.opportunity_id,
            goal_id=job.opportunity.goal_id,
            student_id=job.opportunity.student_id,
            course_id=job.opportunity.course_id,
            release_id=job.opportunity.release_id,
            policy_version=job.opportunity.policy_version,
            profile_sha256=job.opportunity.profile_sha256,
            graph_version=self.implementation_id,
            planner_model=self.planner.model_id,
            created_at=job.now,
            **proposal.model_dump(mode="python"),
        )
        trace = state["trace"].model_copy(
            update={"planning_calls": 1, "decision_reason": proposal.reason_code}
        )
        return {"proposal": proposal, "plan": plan, "trace": trace}

    def _authorize(self, state: _RuntimeState) -> dict:
        job = state["job"]
        proposal = state["proposal"]
        if proposal is None:
            raise AutonomousRuntimeError("authorization requires a plan proposal")
        checks = {
            "autonomy-enabled": job.policy.autonomy_enabled,
            "not-paused": not job.policy.paused,
            "kill-switch-off": not job.policy.kill_switch,
            "membership-active": job.membership_active,
            "consent-active": job.consent_active,
            "current-release": job.current_release_id == job.opportunity.release_id,
            "approved-profile": (
                job.current_profile_id == job.opportunity.profile_id
                and job.current_profile_sha256 == job.opportunity.profile_sha256
            ),
            "outside-quiet-hours": not job.within_quiet_hours,
            "frequency-eligible": (
                job.recent_message_count < job.policy.max_messages_per_7_days
            ),
            "concept-cooldown-eligible": not job.same_concept_cooldown_active,
            "action-allowed": proposal.action in job.policy.allowed_actions,
            "evidence-complete": job.evidence_complete,
            "evidence-unique": job.evidence_unique,
            "evidence-current": job.evidence_current,
            "evidence-authorized": job.evidence_authorized,
            "evidence-lineage-present": bool(
                job.evidence_keys and proposal.required_evidence_keys
            ),
            "planned-evidence-authorized": (
                len(proposal.required_evidence_keys)
                == len(set(proposal.required_evidence_keys))
                and set(proposal.required_evidence_keys).issubset(
                    set(job.evidence_keys)
                )
            ),
        }
        if proposal.action == AutonomousActionKind.NO_ACTION:
            return {"blocked_reason": proposal.reason_code}
        failed = next((name for name, passed in checks.items() if not passed), None)
        trace = state["trace"].model_copy(
            update={
                "validation_results": checks,
                "decision_reason": (
                    failed or f"evidence-approved:{job.evidence_decision_reason}"
                ),
            }
        )
        return {"blocked_reason": failed, "trace": trace}

    @staticmethod
    def _after_authorize(state: _RuntimeState) -> str:
        return "stop" if state["blocked_reason"] else "generate"

    async def _generate(self, state: _RuntimeState) -> dict:
        proposal = state["proposal"]
        if proposal is None:
            raise AutonomousRuntimeError("generation requires an authorized proposal")
        response = await self.generator.generate(state["job"], proposal)
        trace = state["trace"].model_copy(update={"generation_calls": 1})
        return {"response": response, "trace": trace}

    def _validate(self, state: _RuntimeState) -> dict:
        response = state["response"]
        proposal = state["proposal"]
        job = state["job"]
        if response is None or proposal is None:
            return {"blocked_reason": "missing-generated-response"}
        checks = {
            **state["trace"].validation_results,
            "response-action-bound": response.action == proposal.action,
            "claim-lineage-complete": bool(response.source_range_keys),
            "claim-lineage-authorized": set(response.source_range_keys).issubset(
                set(job.evidence_keys)
            ),
            "citation-lineage-complete": len(response.citation_ids)
            == len(response.source_range_keys),
        }
        failed = next((name for name, passed in checks.items() if not passed), None)
        return {
            "blocked_reason": failed,
            "trace": state["trace"].model_copy(update={"validation_results": checks}),
        }

    @staticmethod
    def _after_validate(state: _RuntimeState) -> str:
        return "stop" if state["blocked_reason"] else "pass"

    def _record_no_action(self, state: _RuntimeState) -> dict:
        job = state["job"]
        proposal = state["proposal"] or AutonomousPlannerOutputV1(
            action=AutonomousActionKind.NO_ACTION,
            reason_code=state["blocked_reason"] or "not-eligible",
            stop_condition="Stop without delivery.",
        )
        plan = state["plan"] or AutonomousPlanV1(
            plan_id=f"autonomous-plan-{uuid4()}",
            opportunity_id=job.opportunity.opportunity_id,
            goal_id=job.opportunity.goal_id,
            student_id=job.opportunity.student_id,
            course_id=job.opportunity.course_id,
            release_id=job.opportunity.release_id,
            policy_version=job.opportunity.policy_version,
            profile_sha256=job.opportunity.profile_sha256,
            graph_version=self.implementation_id,
            planner_model=self.planner.model_id,
            created_at=job.now,
            **proposal.model_dump(mode="python"),
        )
        action = self._action(
            state,
            plan,
            kind=AutonomousActionKind.NO_ACTION,
            status=AutonomousActionStatus.SUPPRESSED,
        )
        outcome = self._outcome(
            state,
            action,
            kind=AutonomousOutcomeKind.NO_ACTION,
        )
        return {"plan": plan, "action": action, "outcome": outcome, "response": None}

    def _finalize(self, state: _RuntimeState) -> dict:
        plan = state["plan"]
        job = state["job"]
        action = state["action"]
        outcome = state["outcome"]
        wake_up = state["wake_up"]
        if plan is None:
            raise AutonomousRuntimeError("finalization requires a plan")
        if action is None:
            action = self._action(
                state,
                plan,
                kind=plan.action,
                status=AutonomousActionStatus.PROPOSED,
            )
        next_wake_at: str | None = None
        should_wake = (
            job.goal is not None
            and job.goal.status.value == "active"
            and (
                outcome is None
                or state["blocked_reason"]
                in {
                    "outside-quiet-hours",
                    "frequency-eligible",
                    "concept-cooldown-eligible",
                }
            )
        )
        if should_wake and job.goal is not None:
            next_wake_at = (_instant(job.now) + timedelta(hours=24)).isoformat()
            wake_up = AutonomousWakeUpV1(
                wake_up_id=f"autonomous-wakeup-{uuid4()}",
                goal_id=job.goal.goal_id,
                student_id=job.opportunity.student_id,
                course_id=job.opportunity.course_id,
                release_id=job.opportunity.release_id,
                concept_id=job.opportunity.concept_id,
                source_chunk_id=job.opportunity.source_chunk_id,
                due_at=next_wake_at,
                event_kind=AutonomousEventKind.INCOMPLETE_OBJECTIVE,
                created_at=job.now,
            )
        if outcome is None:
            outcome = self._outcome(
                state,
                action,
                kind=AutonomousOutcomeKind.DELIVERED,
                next_wake_at=next_wake_at,
            )
        elif next_wake_at is not None:
            outcome = outcome.model_copy(update={"next_wake_at": next_wake_at})
        trace = state["trace"].model_copy(
            update={
                "decision_reason": state["blocked_reason"] or plan.reason_code,
                "completed_at": job.now,
            }
        )
        return {"action": action, "outcome": outcome, "wake_up": wake_up, "trace": trace}

    @staticmethod
    def _action(
        state: _RuntimeState,
        plan: AutonomousPlanV1,
        *,
        kind: AutonomousActionKind,
        status: AutonomousActionStatus,
    ) -> AutonomousActionV1:
        job = state["job"]
        return AutonomousActionV1(
            action_id=f"autonomous-action-{uuid4()}",
            plan_id=plan.plan_id,
            opportunity_id=job.opportunity.opportunity_id,
            goal_id=job.opportunity.goal_id,
            student_id=job.opportunity.student_id,
            course_id=job.opportunity.course_id,
            release_id=job.opportunity.release_id,
            policy_version=job.opportunity.policy_version,
            profile_sha256=job.opportunity.profile_sha256,
            graph_version=GRAPH_VERSION,
            generator_model=state["trace"].generator_model or "not-called",
            kind=kind,
            status=status,
            structured_reason=state["blocked_reason"] or plan.reason_code,
            validation_results=state["trace"].validation_results,
            created_at=job.now,
            updated_at=job.now,
        )

    @staticmethod
    def _outcome(
        state: _RuntimeState,
        action: AutonomousActionV1,
        *,
        kind: AutonomousOutcomeKind,
        next_wake_at: str | None = None,
    ) -> AutonomousOutcomeV1:
        job = state["job"]
        return AutonomousOutcomeV1(
            outcome_id=f"autonomous-outcome-{uuid4()}",
            action_id=action.action_id,
            goal_id=job.opportunity.goal_id,
            student_id=job.opportunity.student_id,
            course_id=job.opportunity.course_id,
            release_id=job.opportunity.release_id,
            policy_version=job.opportunity.policy_version,
            profile_sha256=job.opportunity.profile_sha256,
            graph_version=GRAPH_VERSION,
            kind=kind,
            next_wake_at=next_wake_at,
            recorded_at=job.now,
        )


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("autonomous runtime timestamps must be timezone-aware")
    return parsed.astimezone(UTC)
