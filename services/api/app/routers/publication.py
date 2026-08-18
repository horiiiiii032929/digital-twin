from collections import Counter

from fastapi import APIRouter, HTTPException, Query, Request, status

from services.api.app.dependencies import (
    ProfessorAccountDependency,
    PublicationServiceDependency,
    SessionRepositoryDependency,
    SourceIngestionServiceDependency,
)
from services.api.app.schemas import (
    CourseSourceIngestionResponse,
    ReleaseCreateRequest,
    ReleaseEvaluationRequest,
)
from src.digital_twin.grounding import IngestionError, SourcePermissions
from src.digital_twin.student import (
    DigitalTwinRelease,
    PublicationError,
)
from src.digital_twin.tutor_policy import SourceLabel


router = APIRouter(prefix="/professor", tags=["professor-publication"])


@router.put(
    "/courses/{course_id}/sources/{artifact_id}",
    response_model=CourseSourceIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_course_source(
    course_id: str,
    artifact_id: str,
    request: Request,
    account_id: ProfessorAccountDependency,
    publication: PublicationServiceDependency,
    ingestion: SourceIngestionServiceDependency,
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
        result = ingestion.ingest_pdf(
            await request.body(),
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
):
    try:
        return service.record_evaluation(account_id, release_id, request.status)
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
