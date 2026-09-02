"""Application service for governed autonomous tutoring jobs and delivery."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.clock import SystemUtcClock, UtcClock, utc_timestamp
from src.digital_twin.generation import citation_matches_chunk
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.protocols import TutorGenerator
from src.digital_twin.grounding.protocols import PostGenerationClaimValidator
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousActionStatus,
    AutonomousEventKind,
    AutonomousGoalStatus,
    AutonomousGoalV1,
    LearnerBeliefStateV2,
    LearnerObservationV2,
    AutonomousOutcomeKind,
    GroundedTutorResponseV2,
    PedagogicalPolicyV2,
    ProactiveOpportunityV1,
)
from src.digital_twin.student.autonomy_control import (
    AutonomousEvidenceAssessor,
    DeterministicAutonomousGoalManager,
    select_relevant_chunks,
)
from src.digital_twin.student.autonomy_runtime import (
    GRAPH_VERSION,
    AutonomousJobInput,
    AutonomousJobResult,
    GovernedAutonomousTutoringGraph,
)
from src.digital_twin.student.models import (
    AccountRole,
    AccountStatus,
    AuditEvent,
    EvidenceRecoveryMode,
    MembershipRole,
    OutreachChannel,
    ProactiveMessageStatus,
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


class AutonomousObservationSweepV1(BaseModel):
    """Counts from one deterministic, idempotent observer sweep."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observed_courses: int = Field(ge=0)
    observed_students: int = Field(ge=0)
    goals_created: int = Field(ge=0)
    opportunities_created: int = Field(ge=0)
    by_event: dict[str, int] = Field(default_factory=dict)


class RepositoryGroundedWordingGenerator:
    """Adapt the selected grounded tutor generator to one proactive action."""

    def __init__(
        self,
        repository: StudentRepository,
        generator: TutorGenerator,
        *,
        model_id: str,
        claim_validator: PostGenerationClaimValidator,
    ) -> None:
        self.repository = repository
        self.generator = generator
        self.model_id = model_id
        self.claim_validator = claim_validator

    async def generate(self, job, plan):
        release = self.repository.get_release(job.opportunity.release_id)
        chunks = _resolve_evidence_chunks(release, job.evidence_chunk_ids)
        if release is None or not chunks:
            return _failed_grounded_response(plan.action)
        # Evidence completeness was assessed against this authoritative query.
        # Keep pedagogical intent in the dedicated intent/help arguments so the
        # generator cannot silently re-derive a different claim count from
        # synthesized wording.
        question = (
            job.goal.approved_course_objective
            if job.goal is not None
            else job.opportunity.concept_id or "approved course objective"
        )
        hits = [
            RetrievalHit(
                chunk=chunk,
                relevance_score=max(0.0, 1.0 - index * 0.05),
                raw_score=max(0.0, 1.0 - index * 0.05),
            )
            for index, chunk in enumerate(chunks)
        ]
        generate_for_intent = getattr(self.generator, "generate_for_intent", None)
        try:
            answer = (
                await generate_for_intent(
                    question,
                    hits,
                    release.policy,
                    intent=_intent_for_action(plan.action),
                    help_level=1,
                    repair_reason=None,
                )
                if callable(generate_for_intent)
                else await self.generator.generate(question, hits, release.policy)
            )
        except (RuntimeError, ValueError):
            return _failed_grounded_response(plan.action)
        if (
            answer.trace is None
            or answer.trace.policy_action != "answer"
            or not answer.citations
        ):
            return _failed_grounded_response(plan.action)
        cited_keys: list[str] = []
        for citation in answer.citations:
            matches = [
                hit.chunk for hit in hits if citation_matches_chunk(citation, hit.chunk)
            ]
            if len(matches) != 1:
                return _failed_grounded_response(plan.action)
            key = _source_range_key(matches[0])
            if key not in cited_keys:
                cited_keys.append(key)
        if not cited_keys or not set(cited_keys).issubset(set(job.evidence_keys)):
            return _failed_grounded_response(plan.action)
        claims = [claim.text for claim in answer.atomic_claims]
        if not claims:
            return _failed_grounded_response(plan.action)
        try:
            validation = self.claim_validator.validate(answer.atomic_claims, hits)
        except (RuntimeError, ValueError):
            return _failed_grounded_response(plan.action)
        if not validation.releasable:
            return _failed_grounded_response(plan.action)
        from src.digital_twin.student.autonomy_models import GroundedTutorResponseV2

        return GroundedTutorResponseV2(
            action=plan.action,
            content=answer.content,
            atomic_claims=claims[:8],
            citation_ids=[f"citation:{key}" for key in cited_keys],
            source_range_keys=cited_keys,
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
        evidence_assessor: AutonomousEvidenceAssessor | None = None,
        goal_manager: DeterministicAutonomousGoalManager | None = None,
        lease_seconds: int = 300,
        clock: UtcClock | None = None,
    ) -> None:
        if not 30 <= lease_seconds <= 900:
            raise ValueError("autonomy lease must be between 30 and 900 seconds")
        self.repository = repository
        self.outreach = outreach
        self.graph = graph or GovernedAutonomousTutoringGraph(
            checkpoint_database_path=getattr(repository, "path", ":memory:"),
        )
        self.evidence_assessor = evidence_assessor or AutonomousEvidenceAssessor()
        self.goal_manager = goal_manager or DeterministicAutonomousGoalManager()
        self.lease_seconds = lease_seconds
        self.clock = clock or SystemUtcClock()

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
            version=(
                current.version
                if boundary_unchanged and current
                else (current.version + 1 if current else 1)
            ),
            approved_by=professor_id,
            approved_profile_id=release.teaching_profile_id,
            approved_profile_sha256=release.teaching_profile_sha256,
            approved_course_objectives=approved_course_objectives,
            autonomy_enabled=autonomy_enabled,
            paused=paused,
            kill_switch=kill_switch,
            allowed_actions=allowed_actions,
            updated_at=utc_timestamp(self.clock.now()),
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

    def cancel_goal(
        self,
        professor_id: str,
        course_id: str,
        goal_id: str,
        *,
        now: datetime | None = None,
    ) -> AutonomousGoalV1:
        """Cancel one learner goal and every pending job derived from it."""

        course = self.repository.get_course(course_id)
        if course is None or course.owner_professor_id != professor_id:
            raise GovernedAutonomyError(
                "course_forbidden",
                "Only the course professor can cancel an autonomous learner goal.",
            )
        goal = self.repository.get_autonomous_goal(goal_id)
        if goal is None or goal.course_id != course_id:
            raise GovernedAutonomyError(
                "autonomy_goal_not_found",
                "The autonomous learner goal was not found in this course.",
            )
        changed_at = utc_timestamp(_utc(now or self.clock.now()))
        cancelled = self.repository.set_autonomous_goal_status(
            goal_id,
            AutonomousGoalStatus.CANCELLED,
            changed_at=changed_at,
        )
        self.repository.save_audit_event(
            AuditEvent(
                id=f"autonomous-goal-cancelled-{uuid4()}",
                event_type="autonomous-goal-cancelled",
                account_id=professor_id,
                course_id=course_id,
                release_id=cancelled.release_id,
                details={
                    "goal_id": cancelled.goal_id,
                    "student_id": cancelled.student_id,
                    "previous_status": goal.status.value,
                    "pending_work_cancelled": goal.status
                    == AutonomousGoalStatus.ACTIVE,
                },
            )
        )
        return cancelled

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
            created_at=utc_timestamp(self.clock.now()),
            updated_at=utc_timestamp(self.clock.now()),
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
        source_chunk_ids: list[str] | None = None,
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
            source_chunk_ids=(
                source_chunk_ids
                if source_chunk_ids is not None
                else ([source_chunk_id] if source_chunk_id else [])
            ),
            earliest_action_at=earliest_action_at,
            latest_action_at=latest_action_at,
            created_at=utc_timestamp(self.clock.now()),
            updated_at=utc_timestamp(self.clock.now()),
        )
        return self.repository.save_autonomous_opportunity(opportunity)

    def observe_events(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
        inactivity_hours: int = 72,
    ) -> AutonomousObservationSweepV1:
        """Materialize due opportunities from durable product state only."""

        if isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("autonomy observer limit must be between 1 and 500")
        if isinstance(inactivity_hours, bool) or not 24 <= inactivity_hours <= 720:
            raise ValueError("inactivity threshold must be between 24 and 720 hours")
        instant = _utc(now or self.clock.now())
        goals_created = 0
        opportunities_created = 0
        observed_students = 0
        observed_courses = 0
        by_event: dict[str, int] = {}
        for policy in self.repository.list_autonomy_policies():
            if opportunities_created >= limit:
                break
            if not policy.autonomy_enabled or policy.paused or policy.kill_switch:
                continue
            release = self.repository.get_published_release(policy.course_id)
            if (
                release is None
                or release.teaching_profile_id != policy.approved_profile_id
                or release.teaching_profile_sha256 != policy.approved_profile_sha256
            ):
                continue
            observed_courses += 1
            conversations = self.repository.list_course_conversations(policy.course_id)
            by_student: dict[str, list] = {}
            for conversation in conversations:
                by_student.setdefault(conversation.student_id, []).append(conversation)
            for membership in self.repository.list_course_memberships(policy.course_id):
                if opportunities_created >= limit:
                    break
                if membership.role != MembershipRole.STUDENT or not membership.active:
                    continue
                student_id = membership.account_id
                account = self.repository.get_account(student_id)
                preference = self.repository.get_outreach_preference(
                    student_id, policy.course_id, OutreachChannel.IN_APP
                )
                if (
                    account is None
                    or account.status != AccountStatus.ACTIVE
                    or account.role != AccountRole.STUDENT
                    or preference is None
                    or not preference.enabled
                ):
                    continue
                observed_students += 1
                student_conversations = by_student.get(student_id, [])
                current = next(
                    (
                        conversation
                        for conversation in student_conversations
                        if conversation.release_id == release.id
                    ),
                    None,
                )
                old = next(
                    (
                        conversation
                        for conversation in student_conversations
                        if conversation.release_id != release.id
                    ),
                    None,
                )
                learner_state = (
                    self.repository.get_learner_state(current.id) if current else None
                )
                learner_belief = (
                    self.repository.get_learner_belief_state_v2(current.id)
                    if current
                    else None
                )
                learner_observations = (
                    self.repository.list_learner_observations_v2(current.id)
                    if current
                    else []
                )
                goals = self.repository.list_autonomous_goals(
                    student_id, policy.course_id, active_only=True
                )
                if not goals and (current is not None or old is not None):
                    evidence = _policy_evidence(policy, release)
                    if evidence:
                        objective = self.goal_manager.select_objective(policy, evidence)
                        goal = self.goal_manager.build_goal(
                            student_id=student_id,
                            release=release,
                            policy=policy,
                            objective=objective,
                            learner_state=learner_belief or learner_state,
                            observed_at=instant.isoformat(),
                            planner_model=self.graph.planner.model_id,
                            generator_model=self.graph.generator.model_id,
                        )
                        try:
                            goal = self.repository.save_autonomous_goal(goal)
                            goals = [goal]
                            goals_created += 1
                        except ValueError:
                            goals = self.repository.list_autonomous_goals(
                                student_id, policy.course_id, active_only=True
                            )
                for goal in goals:
                    if opportunities_created >= limit:
                        break
                    if goal.attempt_count >= goal.attempt_limit:
                        continue
                    evidence = select_relevant_chunks(
                        goal.approved_course_objective, release.chunks
                    )
                    if not evidence:
                        continue
                    event = self._observed_event(
                        goal,
                        current=current,
                        prior_release_conversation=old,
                        learner_belief=learner_belief,
                        learner_observations=learner_observations,
                        now=instant,
                        inactivity_hours=inactivity_hours,
                    )
                    if event is None:
                        continue
                    latest_student_message = None
                    if current is not None:
                        latest_student_message = next(
                            (
                                message
                                for message in reversed(
                                    self.repository.list_messages(current.id)
                                )
                                if message.role == "student"
                            ),
                            None,
                        )
                    latest_v2_observation = (
                        learner_observations[-1] if learner_observations else None
                    )
                    observation_key = (
                        latest_v2_observation.observation_id
                        if latest_v2_observation is not None
                        else latest_student_message.id
                        if latest_student_message is not None
                        else release.id
                    )
                    key_digest = hashlib.sha256(
                        f"{event.value}:{goal.goal_id}:{observation_key}".encode(
                            "utf-8"
                        )
                    ).hexdigest()
                    key = f"observer:{event.value}:{key_digest}"
                    if (
                        self.repository.get_autonomous_opportunity_by_key(key)
                        is not None
                    ):
                        continue
                    primary = evidence[0]
                    self.create_opportunity(
                        student_id=student_id,
                        course_id=policy.course_id,
                        goal_id=goal.goal_id,
                        event_kind=event,
                        concept_id=(
                            latest_v2_observation.concept_ids[0]
                            if latest_v2_observation is not None
                            and latest_v2_observation.concept_ids
                            else primary.source_artifact_id or primary.document_id
                        )[:128],
                        source_chunk_id=primary.id,
                        source_chunk_ids=[chunk.id for chunk in evidence],
                        supporting_observation_ids=(
                            [latest_v2_observation.observation_id]
                            if latest_v2_observation is not None
                            else [latest_student_message.id]
                            if latest_student_message is not None
                            else []
                        ),
                        earliest_action_at=instant.isoformat(),
                        latest_action_at=(instant + timedelta(hours=24)).isoformat(),
                        idempotency_key=key,
                    )
                    opportunities_created += 1
                    by_event[event.value] = by_event.get(event.value, 0) + 1
        return AutonomousObservationSweepV1(
            observed_courses=observed_courses,
            observed_students=observed_students,
            goals_created=goals_created,
            opportunities_created=opportunities_created,
            by_event=by_event,
        )

    def observe_evidence_recovery(
        self,
        professor_id: str,
        course_id: str,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> AutonomousObservationSweepV1:
        """Convert source-recovery findings into governed V2 opportunities."""

        if isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError(
                "evidence-recovery observer limit must be between 1 and 500"
            )
        instant = _utc(now or self.clock.now())
        scan = self.outreach.scan_evidence_recovery(
            professor_id,
            course_id,
            mode=EvidenceRecoveryMode.SHADOW,
            now=instant,
            limit=limit,
        )
        policy = self.repository.get_autonomy_policy(course_id)
        release = self.repository.get_published_release(course_id)
        if (
            policy is None
            or not policy.autonomy_enabled
            or policy.paused
            or policy.kill_switch
            or release is None
            or release.id != scan.release_id
            or release.teaching_profile_id != policy.approved_profile_id
            or release.teaching_profile_sha256 != policy.approved_profile_sha256
        ):
            return AutonomousObservationSweepV1(
                observed_courses=1,
                observed_students=0,
                goals_created=0,
                opportunities_created=0,
            )
        observed_students: set[str] = set()
        goals_created = 0
        opportunities_created = 0
        for decision in scan.decisions:
            if opportunities_created >= limit or decision.action != "propose":
                continue
            if decision.source_chunk_id is None:
                continue
            chunk = _resolve_evidence_chunk(release, decision.source_chunk_id)
            if chunk is None:
                continue
            observed_students.add(decision.student_id)
            key = (
                f"observer:evidence-recovered:{release.id}:"
                f"{decision.student_message_id}"
            )
            if self.repository.get_autonomous_opportunity_by_key(key) is not None:
                continue
            goals = self.repository.list_autonomous_goals(
                decision.student_id, course_id, active_only=True
            )
            objective = self.goal_manager.select_objective(policy, [chunk])
            goal = next(
                (
                    item
                    for item in goals
                    if item.approved_course_objective == objective
                    and item.attempt_count < item.attempt_limit
                ),
                None,
            )
            if goal is None and len(goals) < policy.max_active_goals:
                current_conversation = next(
                    (
                        item
                        for item in self.repository.list_course_conversations(course_id)
                        if item.student_id == decision.student_id
                        and item.release_id == release.id
                    ),
                    None,
                )
                learner_belief = (
                    self.repository.get_learner_belief_state_v2(current_conversation.id)
                    if current_conversation is not None
                    else None
                )
                goal = self.goal_manager.build_goal(
                    student_id=decision.student_id,
                    release=release,
                    policy=policy,
                    objective=objective,
                    learner_state=learner_belief,
                    observed_at=instant.isoformat(),
                    planner_model=self.graph.planner.model_id,
                    generator_model=self.graph.generator.model_id,
                )
                try:
                    goal = self.repository.save_autonomous_goal(goal)
                    goals_created += 1
                except ValueError:
                    goal = None
            if goal is None:
                continue
            try:
                self.create_opportunity(
                    student_id=decision.student_id,
                    course_id=course_id,
                    goal_id=goal.goal_id,
                    event_kind=AutonomousEventKind.EVIDENCE_RECOVERED,
                    concept_id=(chunk.source_artifact_id or chunk.document_id)[:128],
                    source_chunk_id=chunk.id,
                    source_chunk_ids=[chunk.id],
                    supporting_observation_ids=[
                        decision.student_message_id,
                        decision.tutor_message_id,
                    ],
                    earliest_action_at=instant.isoformat(),
                    latest_action_at=(instant + timedelta(days=14)).isoformat(),
                    idempotency_key=key,
                )
            except (GovernedAutonomyError, ValueError):
                continue
            opportunities_created += 1
        return AutonomousObservationSweepV1(
            observed_courses=1,
            observed_students=len(observed_students),
            goals_created=goals_created,
            opportunities_created=opportunities_created,
            by_event={
                AutonomousEventKind.EVIDENCE_RECOVERED.value: opportunities_created
            },
        )

    def _observed_event(
        self,
        goal: AutonomousGoalV1,
        *,
        current,
        prior_release_conversation,
        learner_belief: LearnerBeliefStateV2 | None,
        learner_observations: list[LearnerObservationV2],
        now: datetime,
        inactivity_hours: int,
    ) -> AutonomousEventKind | None:
        if prior_release_conversation is not None and current is None:
            return AutonomousEventKind.NEW_COURSE_RELEASE
        if current is None:
            return None
        if learner_belief is not None and learner_observations:
            latest = learner_observations[-1]
            if latest.perception.misconception_observed:
                return AutonomousEventKind.MISCONCEPTION
            recent = learner_observations[-2:]
            if (
                len(recent) == 2
                and all(item.perception.confusion >= 0.7 for item in recent)
                and bool(set(recent[0].concept_ids) & set(recent[1].concept_ids))
            ):
                return AutonomousEventKind.REPEATED_CONFUSION
            if latest.assessment_outcome.value in {"partial", "incorrect"}:
                return AutonomousEventKind.PRACTICE_INCOMPLETE
        messages = self.repository.list_messages(current.id)
        latest_student = next(
            (message for message in reversed(messages) if message.role == "student"),
            None,
        )
        if latest_student is not None:
            last_at = _utc(datetime.fromisoformat(latest_student.created_at))
            if now - last_at >= timedelta(hours=inactivity_hours):
                return AutonomousEventKind.STUDENT_INACTIVITY
        actions = self.repository.list_autonomous_actions(
            goal.course_id, student_id=goal.student_id
        )
        for action in reversed(actions):
            if action.goal_id != goal.goal_id:
                continue
            outcome = self.repository.get_autonomous_outcome(action.action_id)
            if outcome is None:
                continue
            if outcome.kind in {
                AutonomousOutcomeKind.DISMISSED,
                AutonomousOutcomeKind.ANSWERED,
            }:
                return None
            if outcome.kind not in {
                AutonomousOutcomeKind.DELIVERED,
                AutonomousOutcomeKind.FAILED,
            }:
                continue
            delivered_at = _utc(datetime.fromisoformat(outcome.recorded_at))
            if now - delivered_at >= timedelta(hours=24):
                return AutonomousEventKind.PRACTICE_INCOMPLETE
            return None
        created_at = _utc(datetime.fromisoformat(goal.created_at))
        if now - created_at >= timedelta(hours=24):
            return AutonomousEventKind.SPACED_REVIEW_DUE
        return None

    def materialize_due_wakeups(
        self, *, now: datetime | None = None, limit: int = 100
    ) -> int:
        instant = _utc(now or self.clock.now())
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
        instant = _utc(now or self.clock.now())
        self.repository.expire_autonomous_goals(expired_at=instant.isoformat())
        self.repository.expire_autonomous_opportunities(expired_at=instant.isoformat())
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
        evidence = self.evidence_assessor.assess(
            release,
            opportunity,
            query=(
                goal.approved_course_objective
                if goal is not None
                else opportunity.concept_id or "approved course objective"
            ),
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
            evidence_keys=evidence.source_range_keys,
            evidence_chunk_ids=evidence.selected_chunk_ids,
            evidence_decision_reason=evidence.reason,
            evidence_complete=evidence.complete,
            evidence_unique=evidence.unique,
            evidence_current=evidence.current,
            evidence_authorized=evidence.authorized,
            now=instant.isoformat(),
        )
        result = await self.graph.run(job)
        result = await self._deliver(
            result, course.owner_professor_id if course else None, instant
        )
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
            # Bind delivery to the immutable opportunity window.  Using the
            # worker's retry time here would turn a crash-recovery retry into
            # an idempotency conflict after the message had already committed.
            scheduled_for=result.opportunity.earliest_action_at,
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
            or (
                delivered.outcome == "duplicate"
                and delivered.message is not None
                and delivered.message.message.status
                in {ProactiveMessageStatus.DELIVERED, ProactiveMessageStatus.READ}
            )
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


def _failed_grounded_response(
    action: AutonomousActionKind,
) -> GroundedTutorResponseV2:
    return GroundedTutorResponseV2(
        action=action,
        content="No validated proactive tutoring response was available.",
        policy_action="no-action",
    )


def _policy_evidence(policy: PedagogicalPolicyV2, release) -> list[DocumentChunk]:
    selected: dict[str, DocumentChunk] = {}
    for objective in policy.approved_course_objectives:
        for chunk in select_relevant_chunks(objective, release.chunks):
            selected.setdefault(chunk.id, chunk)
    return list(selected.values())[:5]


def _resolve_evidence_chunks(release, source_chunk_ids: list[str]):
    if (
        release is None
        or not source_chunk_ids
        or len(source_chunk_ids) != len(set(source_chunk_ids))
    ):
        return []
    chunks = []
    for source_chunk_id in source_chunk_ids:
        chunk = _resolve_evidence_chunk(release, source_chunk_id)
        if chunk is None:
            return []
        chunks.append(chunk)
    return chunks


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
    if event in {
        AutonomousEventKind.MISCONCEPTION,
        AutonomousEventKind.REPEATED_CONFUSION,
    }:
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


def _disabled_policy(
    opportunity: ProactiveOpportunityV1, course
) -> PedagogicalPolicyV2:
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
