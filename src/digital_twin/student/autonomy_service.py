"""Application service for governed autonomous tutoring jobs and delivery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.grounding.protocols import TutorGenerator
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousActionStatus,
    AutonomousEventKind,
    AutonomousGoalV1,
    AutonomousOutcomeKind,
    PedagogicalPolicyV2,
    ProactiveOpportunityV1,
)
from src.digital_twin.student.autonomy_runtime import (
    GRAPH_VERSION,
    AutonomousJobInput,
    AutonomousJobResult,
    DeterministicAutonomousWordingGenerator,
    GovernedAutonomousTutoringGraph,
)
from src.digital_twin.student.models import (
    AccountRole,
    AccountStatus,
    MembershipRole,
    OutreachChannel,
    ProactiveTriggerKind,
)
from src.digital_twin.student.proactive import ProactiveOutreachService
from src.digital_twin.student.repository import StudentRepository


class GovernedAutonomyError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AutonomousProcessResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity_id: str
    outcome: str
    action_kind: AutonomousActionKind
    action_id: str
    trigger_id: str | None = None
    planning_proposals: int = Field(ge=0, le=1)
    generation_attempts: int = Field(ge=0, le=1)
    reason: str


class AutonomousRecipientEligibilityV1(BaseModel):
    """Professor-visible eligibility without exposing learner content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    student_account_id: str = Field(min_length=1, max_length=128)
    account_active: bool
    membership_active: bool
    consent_active: bool
    goal_eligible: bool
    outreach_eligible: bool
    ineligibility_reasons: list[str] = Field(default_factory=list, max_length=8)


class RepositoryGroundedWordingGenerator:
    """Adapt the selected grounded tutor generator to one proactive action."""

    def __init__(
        self,
        repository: StudentRepository,
        generator: TutorGenerator,
        *,
        model_id: str,
    ) -> None:
        self.repository = repository
        self.generator = generator
        self.model_id = model_id
        self.fallback = DeterministicAutonomousWordingGenerator()

    async def generate(self, job, plan):
        release = self.repository.get_release(job.opportunity.release_id)
        chunk = _resolve_evidence_chunk(release, job.opportunity.source_chunk_id)
        if release is None or chunk is None:
            return await self.fallback.generate(job, plan)
        question = (
            f"Create one concise in-app tutoring intervention for {job.opportunity.concept_id or 'the current objective'}. "
            f"Pedagogical action: {plan.action.value}. Expected learner action: "
            f"{plan.expected_learner_action or 'respond with the next learning step'}."
        )
        hit = RetrievalHit(chunk=chunk, relevance_score=1.0, raw_score=1.0)
        generate_for_intent = getattr(self.generator, "generate_for_intent", None)
        try:
            answer = (
                await generate_for_intent(
                    question,
                    [hit],
                    release.policy,
                    intent=_intent_for_action(plan.action),
                    help_level=1,
                    repair_reason=None,
                )
                if callable(generate_for_intent)
                else await self.generator.generate(question, [hit], release.policy)
            )
        except (RuntimeError, ValueError):
            return await self.fallback.generate(job, plan)
        if (
            answer.trace is None
            or answer.trace.policy_action != "answer"
            or not answer.citations
        ):
            return await self.fallback.generate(job, plan)
        source_key = job.evidence_keys[0]
        claims = [claim.text for claim in answer.atomic_claims] or [chunk.text]
        from src.digital_twin.student.autonomy_models import GroundedTutorResponseV2

        return GroundedTutorResponseV2(
            action=plan.action,
            content=answer.content,
            atomic_claims=claims[:8],
            citation_ids=[f"citation:{source_key}"],
            source_range_keys=[source_key],
            policy_action="answer",
        )


class GovernedAutonomyService:
    """Own authoritative autonomy state; models only propose plans and wording."""

    def __init__(
        self,
        repository: StudentRepository,
        outreach: ProactiveOutreachService,
        *,
        graph: GovernedAutonomousTutoringGraph | None = None,
        lease_seconds: int = 300,
    ) -> None:
        if not 30 <= lease_seconds <= 900:
            raise ValueError("autonomy lease must be between 30 and 900 seconds")
        self.repository = repository
        self.outreach = outreach
        self.graph = graph or GovernedAutonomousTutoringGraph()
        self.lease_seconds = lease_seconds

    def set_policy(
        self,
        professor_id: str,
        course_id: str,
        *,
        approved_course_objectives: list[str],
        allowed_actions: list[AutonomousActionKind],
        autonomy_enabled: bool,
        paused: bool = False,
        kill_switch: bool = False,
    ) -> PedagogicalPolicyV2:
        course = self.repository.get_course(course_id)
        release = self.repository.get_published_release(course_id)
        if (
            course is None
            or course.owner_professor_id != professor_id
            or release is None
            or release.teaching_profile_id is None
            or release.teaching_profile_sha256 is None
        ):
            raise GovernedAutonomyError(
                "approved_release_required",
                "Autonomy requires the course owner and an approved-profile release.",
            )
        current = self.repository.get_autonomy_policy(course_id)
        boundary_unchanged = bool(
            current is not None
            and current.approved_by == professor_id
            and current.approved_profile_id == release.teaching_profile_id
            and current.approved_profile_sha256 == release.teaching_profile_sha256
            and current.approved_course_objectives == approved_course_objectives
            and current.allowed_actions == allowed_actions
        )
        policy = PedagogicalPolicyV2(
            course_id=course_id,
            version=(current.version if boundary_unchanged and current else (current.version + 1 if current else 1)),
            approved_by=professor_id,
            approved_profile_id=release.teaching_profile_id,
            approved_profile_sha256=release.teaching_profile_sha256,
            approved_course_objectives=approved_course_objectives,
            autonomy_enabled=autonomy_enabled,
            paused=paused,
            kill_switch=kill_switch,
            allowed_actions=allowed_actions,
        )
        return self.repository.save_autonomy_policy(policy)

    def list_recipient_eligibility(
        self, course_id: str
    ) -> list[AutonomousRecipientEligibilityV1]:
        course = self.repository.get_course(course_id)
        if course is None:
            return []
        release = self.repository.get_published_release(course_id)
        policy = self.repository.get_autonomy_policy(course_id)
        scope_active = bool(
            release is not None
            and release.teaching_profile_id
            and release.teaching_profile_sha256
            and policy is not None
            and policy.autonomy_enabled
            and not policy.paused
            and not policy.kill_switch
        )
        recipients: list[AutonomousRecipientEligibilityV1] = []
        student_ids = [
            membership.account_id
            for membership in self.repository.list_course_memberships(course_id)
            if membership.role == MembershipRole.STUDENT
        ]
        for student_id in student_ids:
            account = self.repository.get_account(student_id)
            membership = self.repository.get_membership(student_id, course_id)
            preference = self.repository.get_outreach_preference(
                student_id, course_id, OutreachChannel.IN_APP
            )
            account_active = bool(
                account is not None
                and account.role == AccountRole.STUDENT
                and account.status == AccountStatus.ACTIVE
            )
            membership_active = bool(
                membership is not None
                and membership.role == MembershipRole.STUDENT
                and membership.active
            )
            consent_active = bool(preference is not None and preference.enabled)
            reasons: list[str] = []
            if not account_active:
                reasons.append("Student account is inactive")
            if not membership_active:
                reasons.append("Course membership is inactive")
            if not scope_active:
                reasons.append("Autonomy policy is not active")
            if not consent_active:
                reasons.append("Private check-in consent is off")
            goal_eligible = account_active and membership_active and scope_active
            recipients.append(
                AutonomousRecipientEligibilityV1(
                    student_account_id=student_id,
                    account_active=account_active,
                    membership_active=membership_active,
                    consent_active=consent_active,
                    goal_eligible=goal_eligible,
                    outreach_eligible=goal_eligible and consent_active,
                    ineligibility_reasons=reasons,
                )
            )
        return recipients

    def create_goal(
        self,
        *,
        student_id: str,
        course_id: str,
        approved_course_objective: str,
        learner_subgoal: str,
        success_condition: str,
        expires_at: str,
        priority: int = 1,
        attempt_limit: int = 3,
    ) -> AutonomousGoalV1:
        policy, release = self._active_scope(student_id, course_id)
        if approved_course_objective not in policy.approved_course_objectives:
            raise GovernedAutonomyError(
                "objective_not_approved",
                "The learner goal must derive from a professor-approved objective.",
            )
        goal = AutonomousGoalV1(
            goal_id=f"autonomous-goal-{uuid4()}",
            student_id=student_id,
            course_id=course_id,
            release_id=release.id,
            policy_version=policy.version,
            profile_id=policy.approved_profile_id,
            profile_sha256=policy.approved_profile_sha256,
            graph_version=GRAPH_VERSION,
            planner_model=self.graph.planner.model_id,
            generator_model=self.graph.generator.model_id,
            approved_course_objective=approved_course_objective,
            learner_subgoal=learner_subgoal,
            success_condition=success_condition,
            priority=priority,
            attempt_limit=attempt_limit,
            expires_at=expires_at,
        )
        return self.repository.save_autonomous_goal(goal)

    def create_opportunity(
        self,
        *,
        student_id: str,
        course_id: str,
        event_kind: AutonomousEventKind,
        earliest_action_at: str,
        latest_action_at: str,
        goal_id: str | None = None,
        concept_id: str | None = None,
        source_chunk_id: str | None = None,
        supporting_observation_ids: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> ProactiveOpportunityV1:
        policy, release = self._active_scope(student_id, course_id)
        opportunity = ProactiveOpportunityV1(
            opportunity_id=f"autonomous-opportunity-{uuid4()}",
            idempotency_key=idempotency_key or f"autonomy:{uuid4()}",
            event_kind=event_kind,
            student_id=student_id,
            course_id=course_id,
            release_id=release.id,
            policy_version=policy.version,
            profile_id=policy.approved_profile_id,
            profile_sha256=policy.approved_profile_sha256,
            graph_version=GRAPH_VERSION,
            planner_model=self.graph.planner.model_id,
            generator_model=self.graph.generator.model_id,
            goal_id=goal_id,
            supporting_observation_ids=supporting_observation_ids or [],
            concept_id=concept_id,
            source_chunk_id=source_chunk_id,
            earliest_action_at=earliest_action_at,
            latest_action_at=latest_action_at,
        )
        return self.repository.save_autonomous_opportunity(opportunity)

    def materialize_due_wakeups(
        self, *, now: datetime | None = None, limit: int = 100
    ) -> int:
        instant = _utc(now or datetime.now(UTC))
        count = 0
        for wake in self.repository.list_due_autonomous_wakeups(
            instant.isoformat(), limit=limit
        ):
            goal = self.repository.get_autonomous_goal(wake.goal_id)
            policy = self.repository.get_autonomy_policy(wake.course_id)
            if (
                goal is None
                or policy is None
                or goal.status.value != "active"
                or not policy.autonomy_enabled
                or policy.paused
                or policy.kill_switch
            ):
                continue
            opportunity = ProactiveOpportunityV1(
                opportunity_id=f"autonomous-opportunity-{uuid4()}",
                idempotency_key=f"wake-up:{wake.wake_up_id}",
                event_kind=wake.event_kind,
                student_id=wake.student_id,
                course_id=wake.course_id,
                release_id=wake.release_id,
                policy_version=goal.policy_version,
                profile_id=goal.profile_id,
                profile_sha256=goal.profile_sha256,
                graph_version=goal.graph_version,
                planner_model=goal.planner_model,
                generator_model=goal.generator_model,
                goal_id=goal.goal_id,
                concept_id=wake.concept_id,
                source_chunk_id=wake.source_chunk_id,
                earliest_action_at=instant.isoformat(),
                latest_action_at=(instant + timedelta(hours=24)).isoformat(),
            )
            if self.repository.materialize_autonomous_wakeup(
                wake.wake_up_id, opportunity, fired_at=instant.isoformat()
            ):
                count += 1
        return count

    async def process_due(
        self,
        *,
        worker_id: str,
        now: datetime | None = None,
        limit: int = 100,
    ) -> list[AutonomousProcessResultV1]:
        instant = _utc(now or datetime.now(UTC))
        self.repository.expire_autonomous_goals(expired_at=instant.isoformat())
        self.repository.expire_autonomous_opportunities(
            expired_at=instant.isoformat()
        )
        self.materialize_due_wakeups(now=instant, limit=limit)
        results: list[AutonomousProcessResultV1] = []
        for opportunity in self.repository.list_due_autonomous_opportunities(
            instant.isoformat(), limit=limit
        ):
            policy = self.repository.get_autonomy_policy(opportunity.course_id)
            if (
                policy is None
                or not policy.autonomy_enabled
                or policy.paused
                or policy.kill_switch
            ):
                continue
            claimed = self.repository.claim_autonomous_opportunity(
                opportunity.opportunity_id,
                lease_owner=worker_id,
                acquired_at=instant.isoformat(),
                lease_expires_at=(
                    instant + timedelta(seconds=self.lease_seconds)
                ).isoformat(),
            )
            if claimed is not None:
                results.append(await self._process_claimed(claimed, instant))
        return results

    async def _process_claimed(
        self,
        opportunity: ProactiveOpportunityV1,
        instant: datetime,
    ) -> AutonomousProcessResultV1:
        policy = self.repository.get_autonomy_policy(opportunity.course_id)
        release = self.repository.get_published_release(opportunity.course_id)
        course = self.repository.get_course(opportunity.course_id)
        membership = self.repository.get_membership(
            opportunity.student_id, opportunity.course_id
        )
        account = self.repository.get_account(opportunity.student_id)
        preference = self.repository.get_outreach_preference(
            opportunity.student_id,
            opportunity.course_id,
            OutreachChannel.IN_APP,
        )
        goal = (
            self.repository.get_autonomous_goal(opportunity.goal_id)
            if opportunity.goal_id
            else None
        )
        chunk = _resolve_evidence_chunk(release, opportunity.source_chunk_id)
        evidence_keys = [_source_range_key(chunk)] if chunk is not None else []
        max_version = 0
        if release is not None and chunk is not None:
            source_id = chunk.source_artifact_id or chunk.document_id
            max_version = max(
                (
                    item.source_version
                    for item in release.chunks
                    if (item.source_artifact_id or item.document_id) == source_id
                ),
                default=0,
            )
        recent_since = (instant - timedelta(days=7)).isoformat()
        recent_count = self.repository.count_recent_proactive_messages(
            opportunity.student_id,
            opportunity.course_id,
            since=recent_since,
        )
        cooldown = self._same_concept_cooldown(opportunity, instant, policy)
        job = AutonomousJobInput(
            opportunity=opportunity,
            goal=goal,
            policy=policy or _disabled_policy(opportunity, course),
            professor_id=course.owner_professor_id if course else "unavailable",
            current_release_id=release.id if release else "unavailable",
            current_profile_id=(release.teaching_profile_id if release else None)
            or "unavailable",
            current_profile_sha256=(
                release.teaching_profile_sha256 if release else None
            )
            or "0" * 64,
            membership_active=bool(
                account is not None
                and account.role == AccountRole.STUDENT
                and account.status == AccountStatus.ACTIVE
                and membership is not None
                and membership.role == MembershipRole.STUDENT
                and membership.active
            ),
            consent_active=bool(preference is not None and preference.enabled),
            within_quiet_hours=(
                _inside_quiet_hours(instant, preference) if preference else False
            ),
            recent_message_count=recent_count,
            same_concept_cooldown_active=cooldown,
            evidence_keys=evidence_keys,
            evidence_complete=chunk is not None,
            evidence_unique=chunk is not None,
            evidence_current=bool(chunk is not None and chunk.source_version == max_version),
            evidence_authorized=bool(chunk is not None and chunk.retrieval_allowed),
            now=instant.isoformat(),
        )
        result = await self.graph.run(job)
        result = await self._deliver(result, course.owner_professor_id if course else None, instant)
        self.repository.commit_autonomous_job(result)
        return AutonomousProcessResultV1(
            opportunity_id=opportunity.opportunity_id,
            outcome=result.outcome.kind.value,
            action_kind=result.action.kind,
            action_id=result.action.action_id,
            trigger_id=result.action.proactive_trigger_id,
            planning_proposals=result.trace.planning_calls,
            generation_attempts=result.trace.generation_calls,
            reason=result.trace.decision_reason,
        )

    async def _deliver(
        self,
        result: AutonomousJobResult,
        professor_id: str | None,
        instant: datetime,
    ) -> AutonomousJobResult:
        if (
            result.action.kind == AutonomousActionKind.NO_ACTION
            or result.response is None
            or professor_id is None
            or result.opportunity.source_chunk_id is None
        ):
            return result
        trigger = self.outreach.schedule_trigger(
            professor_id,
            result.opportunity.course_id,
            student_id=result.opportunity.student_id,
            channel=OutreachChannel.IN_APP,
            kind=_trigger_kind(result.opportunity.event_kind),
            scheduled_for=instant.isoformat(),
            expires_at=result.opportunity.latest_action_at,
            topic="Autonomous course-tutor follow-up",
            prompt=result.response.content,
            source_chunk_id=result.opportunity.source_chunk_id,
            idempotency_key=f"autonomous-action:{result.opportunity.idempotency_key}",
        )
        delivered = self.outreach.process_trigger(trigger.id, now=instant)
        status = (
            AutonomousActionStatus.DELIVERED
            if delivered.outcome == "delivered"
            else AutonomousActionStatus.SUPPRESSED
            if delivered.outcome in {"suppressed", "deferred-quiet-hours"}
            else AutonomousActionStatus.FAILED
        )
        outcome_kind = (
            AutonomousOutcomeKind.DELIVERED
            if status == AutonomousActionStatus.DELIVERED
            else AutonomousOutcomeKind.NO_ACTION
            if status == AutonomousActionStatus.SUPPRESSED
            else AutonomousOutcomeKind.FAILED
        )
        action = result.action.model_copy(
            update={
                "proactive_trigger_id": trigger.id,
                "status": status,
                "updated_at": instant.isoformat(),
            }
        )
        outcome = result.outcome.model_copy(update={"kind": outcome_kind})
        return result.model_copy(update={"action": action, "outcome": outcome})

    def _active_scope(self, student_id: str, course_id: str):
        policy = self.repository.get_autonomy_policy(course_id)
        release = self.repository.get_published_release(course_id)
        membership = self.repository.get_membership(student_id, course_id)
        if (
            policy is None
            or not policy.autonomy_enabled
            or policy.paused
            or policy.kill_switch
            or release is None
            or membership is None
            or membership.role != MembershipRole.STUDENT
            or not membership.active
        ):
            raise GovernedAutonomyError(
                "autonomy_scope_unavailable",
                "Autonomy requires active policy, membership, and release scope.",
            )
        return policy, release

    def _same_concept_cooldown(
        self,
        opportunity: ProactiveOpportunityV1,
        now: datetime,
        policy: PedagogicalPolicyV2 | None,
    ) -> bool:
        if opportunity.concept_id is None or policy is None:
            return False
        cutoff = now - timedelta(hours=policy.same_concept_cooldown_hours)
        for action in self.repository.list_autonomous_actions(
            opportunity.course_id, student_id=opportunity.student_id
        ):
            if _instant(action.created_at) <= cutoff:
                continue
            prior = self.repository.get_autonomous_opportunity(action.opportunity_id)
            if prior is not None and prior.concept_id == opportunity.concept_id:
                return True
        return False


def _resolve_evidence_chunk(release, source_chunk_id: str | None):
    if release is None or source_chunk_id is None:
        return None
    matches = [
        chunk
        for chunk in release.chunks
        if chunk.id == source_chunk_id and chunk.retrieval_allowed
    ]
    return matches[0] if len(matches) == 1 else None


def _source_range_key(chunk) -> str:
    return ":".join(
        (
            chunk.source_artifact_id or chunk.document_id,
            str(chunk.source_version),
            chunk.content_hash,
            chunk.locator,
        )
    )


def _intent_for_action(action: AutonomousActionKind) -> str:
    return {
        AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION: "diagnose_understanding",
        AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE: "give_hint",
        AutonomousActionKind.RECOMMEND_APPROVED_SOURCE: "explain_concept",
        AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE: "give_retrieval_practice",
        AutonomousActionKind.SEND_IN_APP_CHECK_IN: "check_understanding",
        AutonomousActionKind.SUMMARIZE_PROGRESS: "summarize_progress",
    }.get(action, "check_understanding")


def _trigger_kind(event: AutonomousEventKind) -> ProactiveTriggerKind:
    if event == AutonomousEventKind.EVIDENCE_RECOVERED:
        return ProactiveTriggerKind.EVIDENCE_RECOVERY
    if event in {AutonomousEventKind.MISCONCEPTION, AutonomousEventKind.REPEATED_CONFUSION}:
        return ProactiveTriggerKind.MISCONCEPTION_FOLLOW_UP
    if event in {
        AutonomousEventKind.SPACED_REVIEW_DUE,
        AutonomousEventKind.PROFESSOR_SCHEDULED,
    }:
        return ProactiveTriggerKind.SCHEDULED_RETRIEVAL_PRACTICE
    return ProactiveTriggerKind.STUDENT_FOLLOW_UP


def _inside_quiet_hours(now: datetime, preference) -> bool:
    local = now.astimezone(ZoneInfo(preference.timezone))
    current = local.strftime("%H:%M")
    start = preference.quiet_hours_start
    end = preference.quiet_hours_end
    return start <= current < end if start < end else current >= start or current < end


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("autonomy worker time must be timezone-aware")
    return value.astimezone(UTC)


def _instant(value: str) -> datetime:
    return _utc(datetime.fromisoformat(value))


def _disabled_policy(opportunity: ProactiveOpportunityV1, course) -> PedagogicalPolicyV2:
    return PedagogicalPolicyV2(
        course_id=opportunity.course_id,
        version=opportunity.policy_version,
        approved_by=course.owner_professor_id if course else "unavailable",
        approved_profile_id=opportunity.profile_id,
        approved_profile_sha256=opportunity.profile_sha256,
        approved_course_objectives=["Unavailable policy scope"],
        autonomy_enabled=False,
        kill_switch=True,
        allowed_actions=[],
    )
