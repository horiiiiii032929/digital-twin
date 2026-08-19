from collections import Counter

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status

from services.api.app.config import RuntimeMode
from services.api.app.dependencies import (
    IngestionJobServiceDependency,
    ProfessorAccountDependency,
    PublicationServiceDependency,
    SessionRepositoryDependency,
    SettingsDependency,
    SourceIngestionServiceDependency,
)
from services.api.app.schemas import (
    CourseCreateRequest,
    CourseSourceIngestionResponse,
    ReleaseCreateRequest,
    ReleaseEvaluationRequest,
    StudentAssignmentRequest,
)
from services.ingestion import IngestionJobError
from src.digital_twin.grounding import IngestionError, SourcePermissions
from src.digital_twin.operations import IngestionJob
from src.digital_twin.student import (
    Course,
    CourseMembership,
    DigitalTwinRelease,
    ProfessorCourseView,
    PublicationError,
    ReleaseEvaluationStatus,
    ReleasePreflightResult,
)
from src.digital_twin.tutor_policy import SourceLabel


router = APIRouter(prefix="/professor", tags=["professor-publication"])


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
    title: str = Query(min_length=1),
    version: int = Query(default=1, ge=1),
    display_allowed: bool = Query(default=False),
    source_label: SourceLabel = Query(default=SourceLabel.COURSE_APPROVED),
):
    content_type = request.headers.get("content-type", "").partition(";")[0].strip()
    if content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "pdf_required", "message": "Upload a PDF document."},
        )
    try:
        publication.authorize_source_ingestion(account_id, course_id)
        content = await request.body()
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
        return service.create_draft_from_onboarding(
            account_id,
            course_id,
            session,
            chunks=request.chunks,
            profile_id=request.profile_id,
            profile_version=request.profile_version,
            release_id=request.release_id,
        )
    except PublicationError as error:
        raise _http_error(error) from error


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
