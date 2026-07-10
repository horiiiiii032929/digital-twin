from typing import Annotated

from fastapi import Depends, Request

from src.digital_twin.onboarding import SessionRepository


def get_session_repository(request: Request) -> SessionRepository:
    return request.app.state.session_repository


SessionRepositoryDependency = Annotated[
    SessionRepository,
    Depends(get_session_repository),
]
