from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.routers.onboarding import router as onboarding_router
from src.digital_twin.onboarding import (
    InMemorySessionRepository,
    SessionRepository,
)


def create_app(repository: SessionRepository | None = None) -> FastAPI:
    app = FastAPI(title="Digital Twin Prototype API")
    app.state.session_repository = repository or InMemorySessionRepository()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(onboarding_router, prefix="/api")
    return app
