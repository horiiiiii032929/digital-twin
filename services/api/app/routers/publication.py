from collections import Counter
import hashlib
import json

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status

from services.api.app.config import RuntimeMode
from services.api.app.dependencies import (
    GovernedAutonomyServiceDependency,
    IngestionJobServiceDependency,
    ProactiveOutreachServiceDependency,
    TeachingProfileServiceDependency,
    ProfessorAccountDependency,
    PublicationServiceDependency,
    SessionRepositoryDependency,
    SettingsDependency,
    SourceIngestionServiceDependency,
)
from services.api.app.schemas import (
    AutonomyPolicyRequest,
    AutonomousGoalCreateRequest,
    AutonomousOpportunityCreateRequest,
    CourseDomainModelCreateRequest,
    CourseTutoringRuntimeProfileRequest,
    CourseCreateRequest,
    CourseSourceIngestionResponse,
    ReleaseCreateRequest,
    ReleaseEvaluationRequest,
    StudentAssignmentRequest,
    ProactiveTriggerRequest,
    TeachingProfileDraftRequest,
    TeachingProfileApprovalRequest,
    LearningGapReviewRequest,
)
from services.ingestion import IngestionJobError
from src.digital_twin.grounding import IngestionError, SourcePermissions
from src.digital_twin.operations import IngestionJob
from src.digital_twin.onboarding import (
    OnboardingSession,
    SessionWriteConflictError,
    bind_session_to_course,
)
from src.digital_twin.student import (
    AutonomousActionV1,
    AutonomousGoalV1,
    AutonomousOutcomeV1,
    AutonomousRecipientEligibilityV1,
    AgentTraceV2,
    GovernedAutonomyError,
    PedagogicalPolicyV2,
    ProactiveOpportunityV1,
    Course,
    CourseDomainModelV1,
    CourseTutoringRuntimeProfileV1,
    CourseMembership,
    DigitalTwinRelease,
    ProfessorCourseView,
    ProactiveOutreachError,
    ProactiveProcessResult,
    ProactiveTrigger,
    TeachingProfileError,
    TeachingProfilePreviewV1,
    TeachingProfileV1,
    LearningGapPrivacyPolicyV1,
    LearningGapAggregationResultV1,
    CourseImprovementDraftV1,
    aggregate_learning_gap_signals,
    build_course_improvement_drafts,
    AuditEvent,
    PublicationError,
    ReleaseEvaluationStatus,
    ReleasePreflightResult,
)
from src.digital_twin.tutor_policy import SourceLabel, timestamp_now


router = APIRouter(prefix="/professor", tags=["professor-publication"])


def _now() -> str:
    return timestamp_now()


@router.get(
    "/courses/{course_id}/teaching-profiles",
    response_model=list[TeachingProfileV1],
)
def list_teaching_profiles(
    course_id: str,
    account_id: ProfessorAccountDependency,
    profiles: TeachingProfileServiceDependency,
):
    try:
        return profiles.list(account_id, course_id)
    except TeachingProfileError as error:
        raise _teaching_profile_http_error(error) from error


@router.post(
    "/courses/{course_id}/teaching-profiles",
    response_model=TeachingProfileV1,
    status_code=status.HTTP_201_CREATED,
)
def create_teaching_profile(
    course_id: str,
    request: TeachingProfileDraftRequest,
    account_id: ProfessorAccountDependency,
    profiles: TeachingProfileServiceDependency,
):
    try:
        return profiles.create_draft(
            account_id, course_id, request.model_dump(mode="python")
        )
    except TeachingProfileError as error:
        raise _teaching_profile_http_error(error) from error


@router.get(
    "/courses/{course_id}/teaching-profiles/{profile_id}/preview",
    response_model=TeachingProfilePreviewV1,
)
def preview_teaching_profile(
    course_id: str,
    profile_id: str,
    account_id: ProfessorAccountDependency,
    profiles: TeachingProfileServiceDependency,
):
    try:
        return profiles.preview(account_id, course_id, profile_id)
    except TeachingProfileError as error:
        raise _teaching_profile_http_error(error) from error


@router.post(
    "/courses/{course_id}/teaching-profiles/{profile_id}/approve",
    response_model=TeachingProfileV1,
)
def approve_teaching_profile(
    course_id: str,
    profile_id: str,
    request: TeachingProfileApprovalRequest,
    account_id: ProfessorAccountDependency,
    profiles: TeachingProfileServiceDependency,
):
    try:
        return profiles.approve(
            account_id,
            course_id,
            profile_id,
            preview_sha256=request.preview_sha256,
        )
    except TeachingProfileError as error:
        raise _teaching_profile_http_error(error) from error


@router.post(
    "/courses/{course_id}/teaching-profiles/{profile_id}/withdraw",
    response_model=TeachingProfileV1,
)
def withdraw_teaching_profile(
    course_id: str,
    profile_id: str,
    account_id: ProfessorAccountDependency,
    profiles: TeachingProfileServiceDependency,
):
    try:
        return profiles.withdraw(account_id, course_id, profile_id)
    except TeachingProfileError as error:
        raise _teaching_profile_http_error(error) from error


@router.get("/courses/{course_id}/learning-gaps")
def list_learning_gaps(
    course_id: str,
    release_id: str,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
) -> dict[str, LearningGapAggregationResultV1 | list[CourseImprovementDraftV1]]:
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        signals = publication.repository.list_learning_gap_signals(
            course_id, release_id, active_at=_now()
        )
        aggregate = aggregate_learning_gap_signals(
            signals,
            course_id=course_id,
            release_id=release_id,
            policy=LearningGapPrivacyPolicyV1(),
            computed_at=_now(),
        )
        return {
            "aggregation": aggregate,
            "proposals": build_course_improvement_drafts(aggregate),
        }
    except (PublicationError, KeyError, ValueError) as error:
        if isinstance(error, PublicationError):
            raise _http_error(error) from error
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "learning_gap_unavailable", "message": str(error)},
        ) from error


@router.post("/courses/{course_id}/learning-gaps/review")
def review_learning_gap_proposal(
    course_id: str,
    request: LearningGapReviewRequest,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
) -> dict[str, str]:
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        reviewed_at = _now()
        signals = publication.repository.list_learning_gap_signals(
            course_id, request.release_id, active_at=reviewed_at
        )
        aggregate = aggregate_learning_gap_signals(
            signals,
            course_id=course_id,
            release_id=request.release_id,
            policy=LearningGapPrivacyPolicyV1(),
            computed_at=reviewed_at,
        )
        proposals = build_course_improvement_drafts(aggregate)
        proposal = next(
            (item for item in proposals if item.proposal_id == request.proposal_id),
            None,
        )
        if proposal is None:
            raise KeyError("learning_gap_proposal_not_found")
        publication.repository.save_audit_event(
            AuditEvent(
                id=f"learning-gap-review-{request.proposal_id[:16]}-{request.decision}",
                event_type="learning-gap-proposal-reviewed",
                account_id=account_id,
                course_id=course_id,
                details={
                    "proposal_id": request.proposal_id,
                    "release_id": request.release_id,
                    "aggregate_id": proposal.aggregate_id,
                    "decision": request.decision,
                    "rationale_supplied": bool(request.rationale.strip()),
                    "executable_change_created": False,
                },
            )
        )
        return {"proposal_id": request.proposal_id, "decision": request.decision}
    except (PublicationError, KeyError, ValueError) as error:
        if isinstance(error, PublicationError):
            raise _http_error(error) from error
        code = (
            "learning_gap_proposal_not_found"
            if isinstance(error, KeyError)
            else "learning_gap_review_invalid"
        )
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if isinstance(error, KeyError)
                else status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail={"code": code, "message": str(error)},
        ) from error


@router.get(
    "/courses/{course_id}/domain-model",
    response_model=CourseDomainModelV1 | None,
)
def get_course_domain_model(
    course_id: str,
    release_id: str,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        release = publication.repository.get_release(release_id)
        if release is None or release.course_id != course_id:
            raise KeyError("release_not_found")
        return publication.repository.get_course_domain_model(release_id)
    except PublicationError as error:
        raise _http_error(error) from error
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "release_not_found", "message": "Release not found."},
        ) from error


@router.post(
    "/courses/{course_id}/domain-model",
    response_model=CourseDomainModelV1,
    status_code=status.HTTP_201_CREATED,
)
def create_course_domain_model(
    course_id: str,
    request: CourseDomainModelCreateRequest,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        release = publication.repository.get_release(request.release_id)
        if release is None or release.course_id != course_id:
            raise KeyError("release_not_found")
        release_payload = json.dumps(
            release.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        release_sha256 = hashlib.sha256(release_payload.encode("utf-8")).hexdigest()
        identity = hashlib.sha256(
            f"{course_id}:{request.release_id}:{request.version}".encode("utf-8")
        ).hexdigest()[:24]
        model = CourseDomainModelV1(
            domain_model_id=f"course-domain-{identity}",
            course_id=course_id,
            release_id=request.release_id,
            release_sha256=release_sha256,
            version=request.version,
            objectives=request.objectives,
            concepts=request.concepts,
            misconceptions=request.misconceptions,
            approved_by=account_id,
        )
        return publication.repository.save_course_domain_model(model)
    except PublicationError as error:
        raise _http_error(error) from error
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "release_not_found", "message": "Release not found."},
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "domain_model_invalid", "message": str(error)},
        ) from error


@router.get(
    "/courses/{course_id}/autonomy-traces",
    response_model=list[AgentTraceV2],
)
def list_autonomy_traces(
    course_id: str,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
    conversation_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return publication.repository.list_agent_traces_v2(
            course_id,
            conversation_id=conversation_id,
            limit=limit,
        )
    except PublicationError as error:
        raise _http_error(error) from error


@router.get("/courses/{course_id}/learners/{student_id}/belief-evidence")
def get_learner_belief_evidence(
    course_id: str,
    student_id: str,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        conversations = [
            item
            for item in publication.repository.list_course_conversations(course_id)
            if item.student_id == student_id
        ]
        states = [
            state
            for item in conversations
            if (state := publication.repository.get_learner_belief_state_v2(item.id))
            is not None
        ]
        return {
            "student_id": student_id,
            "course_id": course_id,
            "belief_states": states,
            "claim": "observed-evidence-only",
        }
    except PublicationError as error:
        raise _http_error(error) from error


@router.get("/courses/{course_id}/learner-belief-evidence")
def list_course_learner_belief_evidence(
    course_id: str,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        grouped = publication.repository.list_course_learner_belief_states(course_id)
        return [
            {
                "student_id": student_id,
                "course_id": course_id,
                "belief_states": states,
                "claim": "observed-evidence-only",
            }
            for student_id, states in sorted(grouped.items())
        ]
    except PublicationError as error:
        raise _http_error(error) from error


@router.get(
    "/courses/{course_id}/tutoring-runtime-profile",
    response_model=CourseTutoringRuntimeProfileV1 | None,
)
def get_tutoring_runtime_profile(
    course_id: str,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return publication.repository.get_course_tutoring_runtime_profile(course_id)
    except PublicationError as error:
        raise _http_error(error) from error


@router.put(
    "/courses/{course_id}/tutoring-runtime-profile",
    response_model=CourseTutoringRuntimeProfileV1,
)
def set_tutoring_runtime_profile(
    course_id: str,
    request: CourseTutoringRuntimeProfileRequest,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        current = publication.repository.get_course_tutoring_runtime_profile(course_id)
        changed_at = timestamp_now()
        profile = CourseTutoringRuntimeProfileV1(
            course_id=course_id,
            mode=request.mode,
            version=(current.version + 1 if current is not None else 1),
            changed_by=account_id,
            reason=request.reason,
            updated_at=changed_at,
        )
        saved = publication.repository.save_course_tutoring_runtime_profile(profile)
        if saved.mode == "grounded-assistant":
            publication.repository.cancel_autonomy_scope(
                course_id=course_id,
                changed_at=changed_at,
            )
        publication.repository.save_audit_event(
            AuditEvent(
                id=f"audit-runtime-profile-{course_id}-{saved.version}",
                event_type="course-tutoring-runtime-profile-changed",
                account_id=account_id,
                course_id=course_id,
                details={
                    "mode": saved.mode,
                    "version": saved.version,
                    "reason": saved.reason,
                    "pending_autonomy_cancelled": saved.mode == "grounded-assistant",
                },
                created_at=changed_at,
            )
        )
        return saved
    except PublicationError as error:
        raise _http_error(error) from error
    except (KeyError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "runtime_profile_invalid", "message": str(error)},
        ) from error


@router.get(
    "/courses/{course_id}/autonomy-policy",
    response_model=PedagogicalPolicyV2 | None,
)
def get_autonomy_policy(
    course_id: str,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return autonomy.repository.get_autonomy_policy(course_id)
    except PublicationError as error:
        raise _http_error(error) from error


@router.put(
    "/courses/{course_id}/autonomy-policy",
    response_model=PedagogicalPolicyV2,
)
def set_autonomy_policy(
    course_id: str,
    request: AutonomyPolicyRequest,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
):
    try:
        return autonomy.set_policy(
            account_id,
            course_id,
            **request.model_dump(mode="python"),
        )
    except GovernedAutonomyError as error:
        raise _autonomy_http_error(error) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "autonomy_policy_invalid", "message": str(error)},
        ) from error


@router.get(
    "/courses/{course_id}/autonomous-goals",
    response_model=list[AutonomousGoalV1],
)
def list_autonomous_goals(
    course_id: str,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
    publication: PublicationServiceDependency,
    student_account_id: str | None = None,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        if student_account_id is not None:
            return autonomy.repository.list_autonomous_goals(
                student_account_id, course_id
            )
        return autonomy.repository.list_course_autonomous_goals(course_id, limit=100)
    except PublicationError as error:
        raise _http_error(error) from error


@router.get(
    "/courses/{course_id}/autonomy-recipients",
    response_model=list[AutonomousRecipientEligibilityV1],
)
def list_autonomy_recipients(
    course_id: str,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return autonomy.list_recipient_eligibility(course_id)
    except PublicationError as error:
        raise _http_error(error) from error


@router.post(
    "/courses/{course_id}/autonomous-goals",
    response_model=AutonomousGoalV1,
    status_code=status.HTTP_201_CREATED,
)
def create_autonomous_goal(
    course_id: str,
    request: AutonomousGoalCreateRequest,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return autonomy.create_goal(
            student_id=request.student_account_id,
            course_id=course_id,
            approved_course_objective=request.approved_course_objective,
            learner_subgoal=request.learner_subgoal,
            success_condition=request.success_condition,
            expires_at=request.expires_at,
            priority=request.priority,
            attempt_limit=request.attempt_limit,
        )
    except PublicationError as error:
        raise _http_error(error) from error
    except GovernedAutonomyError as error:
        raise _autonomy_http_error(error) from error


@router.post(
    "/courses/{course_id}/autonomous-goals/{goal_id}/cancel",
    response_model=AutonomousGoalV1,
)
def cancel_autonomous_goal(
    course_id: str,
    goal_id: str,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
):
    try:
        return autonomy.cancel_goal(account_id, course_id, goal_id)
    except GovernedAutonomyError as error:
        raise _autonomy_http_error(error) from error


@router.post(
    "/courses/{course_id}/autonomous-opportunities",
    response_model=ProactiveOpportunityV1,
    status_code=status.HTTP_201_CREATED,
)
def create_autonomous_opportunity(
    course_id: str,
    request: AutonomousOpportunityCreateRequest,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
    publication: PublicationServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return autonomy.create_opportunity(
            student_id=request.student_account_id,
            course_id=course_id,
            event_kind=request.event_kind,
            earliest_action_at=request.earliest_action_at,
            latest_action_at=request.latest_action_at,
            goal_id=request.goal_id,
            concept_id=request.concept_id,
            source_chunk_id=request.source_chunk_id,
            source_chunk_ids=request.source_chunk_ids,
            supporting_observation_ids=request.supporting_observation_ids,
            idempotency_key=request.idempotency_key,
        )
    except PublicationError as error:
        raise _http_error(error) from error
    except GovernedAutonomyError as error:
        raise _autonomy_http_error(error) from error


@router.get(
    "/courses/{course_id}/autonomous-actions",
    response_model=list[AutonomousActionV1],
)
def list_autonomous_actions(
    course_id: str,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
    publication: PublicationServiceDependency,
    student_account_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return autonomy.repository.list_autonomous_actions(
            course_id, student_id=student_account_id, limit=limit
        )
    except PublicationError as error:
        raise _http_error(error) from error


@router.get(
    "/courses/{course_id}/autonomous-outcomes",
    response_model=list[AutonomousOutcomeV1],
)
def list_autonomous_outcomes(
    course_id: str,
    account_id: ProfessorAccountDependency,
    autonomy: GovernedAutonomyServiceDependency,
    publication: PublicationServiceDependency,
    student_account_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return autonomy.repository.list_autonomous_outcomes(
            course_id, student_id=student_account_id, limit=limit
        )
    except PublicationError as error:
        raise _http_error(error) from error


@router.get("/courses", response_model=list[ProfessorCourseView])
def list_courses(
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        return publication.list_courses(account_id)
    except PublicationError as error:
        raise _http_error(error) from error


@router.post(
    "/courses",
    response_model=Course,
    status_code=status.HTTP_201_CREATED,
)
def create_course(
    request: CourseCreateRequest,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        return publication.create_course(
            account_id,
            request.title,
            course_id=request.course_id,
        )
    except PublicationError as error:
        raise _http_error(error) from error


@router.post(
    "/courses/{course_id}/onboarding-sessions/{session_id}/bind",
    response_model=OnboardingSession,
)
def bind_onboarding_session(
    course_id: str,
    session_id: str,
    account_id: ProfessorAccountDependency,
    sessions: SessionRepositoryDependency,
    publication: PublicationServiceDependency,
):
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "session_not_found",
                "message": "Onboarding session was not found.",
            },
        )
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return sessions.save(bind_session_to_course(session, course_id))
    except PublicationError as error:
        raise _http_error(error) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": str(error),
                "message": "This tutor setup is already bound to another course.",
            },
        ) from error
    except (PermissionError, SessionWriteConflictError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "session_write_conflict",
                "message": "The tutor setup changed; reload it before binding.",
            },
        ) from error


@router.post(
    "/courses/{course_id}/students",
    response_model=CourseMembership,
    status_code=status.HTTP_201_CREATED,
)
def assign_student(
    course_id: str,
    request: StudentAssignmentRequest,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
):
    try:
        return publication.assign_student(
            account_id,
            course_id,
            request.student_account_id,
        )
    except PublicationError as error:
        raise _http_error(error) from error


@router.post(
    "/courses/{course_id}/proactive-triggers",
    response_model=ProactiveTrigger,
    status_code=status.HTTP_201_CREATED,
)
def schedule_proactive_trigger(
    course_id: str,
    request: ProactiveTriggerRequest,
    account_id: ProfessorAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
):
    try:
        return outreach.schedule_trigger(
            account_id,
            course_id,
            student_id=request.student_account_id,
            channel=request.channel,
            kind=request.kind,
            scheduled_for=request.scheduled_for,
            expires_at=request.expires_at,
            topic=request.topic,
            prompt=request.prompt,
            source_chunk_id=request.source_chunk_id,
            idempotency_key=request.idempotency_key,
        )
    except ProactiveOutreachError as error:
        raise _proactive_http_error(error) from error


@router.get(
    "/courses/{course_id}/proactive-triggers",
    response_model=list[ProactiveTrigger],
)
def list_proactive_triggers(
    course_id: str,
    account_id: ProfessorAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
):
    try:
        return outreach.list_triggers(account_id, course_id)
    except ProactiveOutreachError as error:
        raise _proactive_http_error(error) from error


@router.post(
    "/courses/{course_id}/proactive-triggers/{trigger_id}/cancel",
    response_model=ProactiveTrigger,
)
def cancel_proactive_trigger(
    course_id: str,
    trigger_id: str,
    account_id: ProfessorAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
):
    try:
        return outreach.cancel_trigger(account_id, course_id, trigger_id)
    except ProactiveOutreachError as error:
        raise _proactive_http_error(error) from error


@router.post(
    "/courses/{course_id}/proactive-triggers/{trigger_id}/process",
    response_model=ProactiveProcessResult,
)
def process_proactive_trigger_for_local_verification(
    course_id: str,
    trigger_id: str,
    account_id: ProfessorAccountDependency,
    outreach: ProactiveOutreachServiceDependency,
    publication: PublicationServiceDependency,
    settings: SettingsDependency,
):
    if settings.mode == RuntimeMode.STAGING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "manual_trigger_execution_disabled",
                "message": "Staging requires the separately gated outreach worker.",
            },
        )
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        trigger = outreach.repository.get_proactive_trigger(trigger_id)
        if trigger is None or trigger.course_id != course_id:
            raise ProactiveOutreachError(
                "proactive_trigger_not_found", "The proactive trigger was not found."
            )
        return outreach.process_trigger(trigger_id)
    except (PublicationError, ProactiveOutreachError) as error:
        if isinstance(error, PublicationError):
            raise _http_error(error) from error
        raise _proactive_http_error(error) from error


@router.put(
    "/courses/{course_id}/sources/{artifact_id}",
    response_model=CourseSourceIngestionResponse | IngestionJob,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_course_source(
    course_id: str,
    artifact_id: str,
    request: Request,
    response: Response,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
    ingestion: SourceIngestionServiceDependency,
    jobs: IngestionJobServiceDependency,
    settings: SettingsDependency,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    title: str = Query(min_length=1, max_length=240),
    version: int = Query(default=1, ge=1),
    display_allowed: bool = Query(default=False),
    source_label: SourceLabel = Query(default=SourceLabel.COURSE_APPROVED),
):
    if any(
        not value.strip() or len(value.strip()) > 128
        for value in (course_id, artifact_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "source_metadata_invalid",
                "message": "Course and source identifiers must be 1–128 characters.",
            },
        )
    content_type = request.headers.get("content-type", "").partition(";")[0].strip()
    if content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "pdf_required", "message": "Upload a PDF document."},
        )
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        content = await _read_bounded_body(request, settings.max_upload_bytes)
        if settings.mode == RuntimeMode.STAGING:
            job, _ = jobs.enqueue_pdf(
                content,
                idempotency_key=idempotency_key or "",
                course_id=course_id,
                artifact_id=artifact_id,
                title=title,
                version=version,
                professor_id=account_id,
                display_allowed=display_allowed,
                source_label=source_label,
            )
            response.status_code = status.HTTP_202_ACCEPTED
            return job
        result = ingestion.ingest_pdf(
            content,
            course_id=course_id,
            artifact_id=artifact_id,
            title=title,
            version=version,
            professor_id=account_id,
            permissions=SourcePermissions(
                processing_allowed=True,
                tutoring_allowed=True,
                display_allowed=display_allowed,
            ),
            source_label=source_label,
        )
    except PublicationError as error:
        raise _http_error(error) from error
    except IngestionJobError as error:
        code = (
            status.HTTP_413_CONTENT_TOO_LARGE
            if error.code == "source_too_large"
            else status.HTTP_507_INSUFFICIENT_STORAGE
            if error.code == "storage_quota_exceeded"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=code,
            detail={"code": error.code, "message": error.message},
        ) from error
    except (IngestionError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "source_ingestion_failed", "message": str(error)},
        ) from error

    kind_counts = Counter(region.kind.value for region in result.bundle.regions)
    return CourseSourceIngestionResponse(
        source_artifact_id=result.source.id,
        source_version=result.source.version,
        source_checksum=result.source.checksum,
        document_id=result.bundle.document.id,
        chunk_count=len(result.chunks),
        region_count=len(result.bundle.regions),
        region_kind_counts=dict(sorted(kind_counts.items())),
        processing_warnings=result.bundle.processing_warnings,
        chunks=result.chunks,
    )


@router.get("/ingestion-jobs/{job_id}", response_model=IngestionJob)
def get_ingestion_job(
    job_id: str,
    account_id: ProfessorAccountDependency,
    jobs: IngestionJobServiceDependency,
):
    try:
        return jobs.get_owned(account_id, job_id)
    except IngestionJobError as error:
        raise _job_http_error(error) from error


@router.get(
    "/courses/{course_id}/ingestion-jobs",
    response_model=list[IngestionJob],
)
def list_ingestion_jobs(
    course_id: str,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
    jobs: IngestionJobServiceDependency,
):
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        return jobs.list_owned(account_id, course_id)
    except PublicationError as error:
        raise _http_error(error) from error


@router.post("/ingestion-jobs/{job_id}/cancel", response_model=IngestionJob)
def cancel_ingestion_job(
    job_id: str,
    account_id: ProfessorAccountDependency,
    jobs: IngestionJobServiceDependency,
):
    try:
        return jobs.cancel_owned(account_id, job_id)
    except IngestionJobError as error:
        raise _job_http_error(error) from error


@router.post("/ingestion-jobs/{job_id}/retry", response_model=IngestionJob)
def retry_ingestion_job(
    job_id: str,
    account_id: ProfessorAccountDependency,
    jobs: IngestionJobServiceDependency,
):
    try:
        return jobs.retry_owned(account_id, job_id)
    except IngestionJobError as error:
        raise _job_http_error(error) from error


@router.post(
    "/courses/{course_id}/releases",
    response_model=DigitalTwinRelease,
    status_code=status.HTTP_201_CREATED,
)
def create_release_draft(
    course_id: str,
    request: ReleaseCreateRequest,
    account_id: ProfessorAccountDependency,
    sessions: SessionRepositoryDependency,
    service: PublicationServiceDependency,
    profiles: TeachingProfileServiceDependency,
    jobs: IngestionJobServiceDependency,
    settings: SettingsDependency,
):
    session = sessions.get(request.session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "session_not_found",
                "message": "Onboarding session was not found.",
            },
        )
    try:
        if settings.mode == RuntimeMode.STAGING:
            if request.chunks:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "code": "server_bound_sources_required",
                        "message": (
                            "Staging releases must use completed server-side ingestion jobs."
                        ),
                    },
                )
            chunks = jobs.release_chunks_owned(
                account_id, course_id, request.ingestion_job_ids
            )
        else:
            chunks = request.chunks
        teaching_profile = (
            profiles.require_approved(
                account_id, course_id, request.teaching_profile_id
            )
            if request.teaching_profile_id is not None
            else None
        )
        return service.create_draft_from_onboarding(
            account_id,
            course_id,
            session,
            chunks=chunks,
            profile_id=request.profile_id,
            profile_version=request.profile_version,
            teaching_profile_id=(
                teaching_profile.profile_id if teaching_profile is not None else None
            ),
            teaching_profile_sha256=(
                teaching_profile.content_sha256
                if teaching_profile is not None
                else None
            ),
            release_id=request.release_id,
        )
    except PublicationError as error:
        raise _http_error(error) from error
    except IngestionJobError as error:
        raise _job_http_error(error) from error
    except TeachingProfileError as error:
        raise _teaching_profile_http_error(error) from error


@router.patch(
    "/releases/{release_id}/evaluation",
    response_model=DigitalTwinRelease,
)
def record_release_evaluation(
    release_id: str,
    request: ReleaseEvaluationRequest,
    account_id: ProfessorAccountDependency,
    service: PublicationServiceDependency,
    settings: SettingsDependency,
):
    if (
        settings.mode == RuntimeMode.STAGING
        and request.status == ReleaseEvaluationStatus.PASSED
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "preflight_required",
                "message": "Run the deterministic release preflight before publication.",
            },
        )
    try:
        return service.record_evaluation(account_id, release_id, request.status)
    except PublicationError as error:
        raise _http_error(error) from error


@router.post(
    "/releases/{release_id}/preflight",
    response_model=ReleasePreflightResult,
)
def run_release_preflight(
    release_id: str,
    account_id: ProfessorAccountDependency,
    service: PublicationServiceDependency,
):
    try:
        return service.run_preflight(account_id, release_id)
    except PublicationError as error:
        raise _http_error(error) from error


@router.post(
    "/releases/{release_id}/publish",
    response_model=DigitalTwinRelease,
)
def publish_release(
    release_id: str,
    account_id: ProfessorAccountDependency,
    service: PublicationServiceDependency,
):
    try:
        return service.publish(account_id, release_id)
    except PublicationError as error:
        raise _http_error(error) from error


@router.post(
    "/releases/{release_id}/withdraw",
    response_model=DigitalTwinRelease,
)
def withdraw_release(
    release_id: str,
    account_id: ProfessorAccountDependency,
    service: PublicationServiceDependency,
):
    try:
        return service.withdraw(account_id, release_id)
    except PublicationError as error:
        raise _http_error(error) from error


@router.post(
    "/releases/{release_id}/rollback",
    response_model=DigitalTwinRelease,
)
def rollback_release(
    release_id: str,
    account_id: ProfessorAccountDependency,
    service: PublicationServiceDependency,
):
    try:
        return service.rollback(account_id, release_id)
    except PublicationError as error:
        raise _http_error(error) from error


def _http_error(error: PublicationError) -> HTTPException:
    not_found = {"account_not_found", "course_not_found", "release_not_found"}
    forbidden = {
        "account_inactive",
        "professor_role_required",
        "course_access_denied",
        "course_scope_violation",
        "student_role_required",
    }
    code = (
        status.HTTP_404_NOT_FOUND
        if error.code in not_found
        else status.HTTP_403_FORBIDDEN
        if error.code in forbidden
        else status.HTTP_409_CONFLICT
    )
    return HTTPException(
        status_code=code,
        detail={"code": error.code, "message": error.message},
    )


def _proactive_http_error(error: ProactiveOutreachError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.code == "proactive_trigger_not_found"
        else status.HTTP_403_FORBIDDEN
        if error.code in {"professor_course_forbidden", "course_forbidden"}
        else status.HTTP_409_CONFLICT
        if error.code
        in {
            "trigger_idempotency_conflict",
            "proactive_trigger_not_cancellable",
        }
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(
        status_code=code,
        detail={"code": error.code, "message": error.message},
    )


def _teaching_profile_http_error(error: TeachingProfileError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.code == "teaching_profile_not_found"
        else status.HTTP_403_FORBIDDEN
        if error.code == "course_forbidden"
        else status.HTTP_409_CONFLICT
        if error.code
        in {
            "teaching_profile_not_draft",
            "teaching_profile_not_approved",
            "teaching_profile_not_withdrawable",
            "teaching_profile_preview_drifted",
        }
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(
        status_code=code,
        detail={"code": error.code, "message": error.message},
    )


def _autonomy_http_error(error: GovernedAutonomyError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.code == "autonomy_goal_not_found"
        else status.HTTP_403_FORBIDDEN
        if error.code
        in {
            "approved_release_required",
            "objective_not_approved",
            "course_forbidden",
        }
        else status.HTTP_409_CONFLICT
        if error.code == "autonomy_scope_unavailable"
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(
        status_code=code,
        detail={"code": error.code, "message": error.message},
    )


def _job_http_error(error: IngestionJobError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.code == "job_not_found"
        else status.HTTP_409_CONFLICT
    )
    return HTTPException(
        status_code=code,
        detail={"code": error.code, "message": error.message},
    )


async def _read_bounded_body(request: Request, limit: int) -> bytes:
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail={
                    "code": "source_too_large",
                    "message": "The upload exceeds the configured size limit.",
                },
            )
        content.extend(chunk)
    return bytes(content)
