from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from src.digital_twin.onboarding import SessionRepository
from src.digital_twin.student import ReleaseLifecycleService, StudentTutoringService


def get_session_repository(request: Request) -> SessionRepository:
    return request.app.state.session_repository


SessionRepositoryDependency = Annotated[
    SessionRepository,
    Depends(get_session_repository),
]


def get_student_service(request: Request) -> StudentTutoringService:
    return request.app.state.student_service


def get_publication_service(request: Request) -> ReleaseLifecycleService:
    return request.app.state.publication_service


def get_synthetic_account_id(
    account_id: Annotated[str | None, Header(alias="X-Account-ID")] = None,
) -> str:
    if account_id is None or not account_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "account_header_required",
                "message": "X-Account-ID is required for the synthetic local session.",
            },
        )
    return account_id.strip()


StudentServiceDependency = Annotated[
    StudentTutoringService,
    Depends(get_student_service),
]
StudentAccountDependency = Annotated[str, Depends(get_synthetic_account_id)]
ProfessorAccountDependency = Annotated[str, Depends(get_synthetic_account_id)]
PublicationServiceDependency = Annotated[
    ReleaseLifecycleService,
    Depends(get_publication_service),
]
