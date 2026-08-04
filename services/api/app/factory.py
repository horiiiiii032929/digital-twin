from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.routers.onboarding import router as onboarding_router
from services.api.app.routers.student import router as student_router
from src.digital_twin.grounding.protocols import TextEmbedder, TutorGenerator
from src.digital_twin.onboarding import (
    InMemorySessionRepository,
    SessionRepository,
)
from src.digital_twin.student import SQLiteStudentRepository, StudentRepository
from src.digital_twin.student.service import StudentTutoringService


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STUDENT_PROFILE = (
    ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
)


def create_app(
    repository: SessionRepository | None = None,
    *,
    student_repository: StudentRepository | None = None,
    student_embedder: TextEmbedder | None = None,
    student_generator: TutorGenerator | None = None,
    student_profile_path: Path = DEFAULT_STUDENT_PROFILE,
) -> FastAPI:
    app = FastAPI(title="Digital Twin Prototype API")
    app.state.session_repository = repository or InMemorySessionRepository()
    app.state.student_repository = student_repository or SQLiteStudentRepository()
    app.state.student_service = StudentTutoringService(
        app.state.student_repository,
        profile_path=student_profile_path,
        embedder=student_embedder,
        generator=student_generator,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(onboarding_router, prefix="/api")
    app.include_router(student_router, prefix="/api")
    return app
