from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from services.api.app.config import AppSettings, RuntimeMode
from services.ingestion import IngestionJobService
from src.digital_twin.identity import IdentityError, IdentityService
from src.digital_twin.grounding import LocalCourseSourceIngestionService
from src.digital_twin.onboarding import ScopedSessionRepository, SessionRepository
from src.digital_twin.student import AccountRole
from src.digital_twin.student import ReleaseLifecycleService, StudentTutoringService


def get_session_repository(request: Request) -> SessionRepository:
    repository: SessionRepository = request.app.state.session_repository
    settings: AppSettings = request.app.state.settings
    if settings.mode != RuntimeMode.STAGING:
        return repository
    token = request.cookies.get(settings.session_cookie_name, "")
    try:
        principal = request.app.state.identity_service.authenticate(token)
    except IdentityError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": error.code, "message": error.message},
        ) from error
    if principal.role != AccountRole.PROFESSOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "professor_role_required",
                "message": "A professor account is required.",
            },
        )
    return ScopedSessionRepository(repository, principal.account_id)


SessionRepositoryDependency = Annotated[
    SessionRepository,
    Depends(get_session_repository),
]


def get_student_service(request: Request) -> StudentTutoringService:
    return request.app.state.student_service


def get_publication_service(request: Request) -> ReleaseLifecycleService:
    return request.app.state.publication_service


def get_source_ingestion_service(request: Request) -> LocalCourseSourceIngestionService:
    return request.app.state.source_ingestion_service


def get_identity_service(request: Request) -> IdentityService:
    return request.app.state.identity_service


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def get_ingestion_job_service(request: Request) -> IngestionJobService:
    return request.app.state.ingestion_job_service


def get_current_account_id(
    request: Request,
    identity: Annotated[IdentityService, Depends(get_identity_service)],
    account_id: Annotated[str | None, Header(alias="X-Account-ID")] = None,
) -> str:
    settings: AppSettings = request.app.state.settings
    if settings.mode in {RuntimeMode.DEMO, RuntimeMode.TEST}:
        if account_id is not None and account_id.strip():
            return account_id.strip()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "account_header_required",
                "message": "X-Account-ID is required for the synthetic local session.",
            },
        )
    if account_id is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "synthetic_identity_disabled",
                "message": "Synthetic account headers are disabled in staging.",
            },
        )
    token = request.cookies.get(settings.session_cookie_name, "")
    try:
        return identity.authenticate(token).account_id
    except IdentityError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": error.code, "message": error.message},
        ) from error


StudentServiceDependency = Annotated[
    StudentTutoringService,
    Depends(get_student_service),
]
StudentAccountDependency = Annotated[str, Depends(get_current_account_id)]
ProfessorAccountDependency = Annotated[str, Depends(get_current_account_id)]
AdminAccountDependency = Annotated[str, Depends(get_current_account_id)]
CurrentAccountDependency = Annotated[str, Depends(get_current_account_id)]
PublicationServiceDependency = Annotated[
    ReleaseLifecycleService,
    Depends(get_publication_service),
]
SourceIngestionServiceDependency = Annotated[
    LocalCourseSourceIngestionService,
    Depends(get_source_ingestion_service),
]
IdentityServiceDependency = Annotated[IdentityService, Depends(get_identity_service)]
SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
IngestionJobServiceDependency = Annotated[
    IngestionJobService,
    Depends(get_ingestion_job_service),
]
