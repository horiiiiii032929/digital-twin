from fastapi import APIRouter, HTTPException, status

from services.api.app.dependencies import (
    ProfessorAccountDependency,
    PublicationServiceDependency,
    SessionRepositoryDependency,
)
from services.api.app.schemas import ReleaseCreateRequest, ReleaseEvaluationRequest
from src.digital_twin.student import (
    DigitalTwinRelease,
    PublicationError,
)


router = APIRouter(prefix="/professor", tags=["professor-publication"])


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
