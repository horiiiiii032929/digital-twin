from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.config import AppSettings, GeneratorMode, RuntimeMode
from services.api.app.middleware import (
    OriginGuardMiddleware,
    RateLimitMiddleware,
    RequestObservabilityMiddleware,
    UploadSizeGuardMiddleware,
)
from services.api.app.observability import OperationalMetrics
from services.api.app.routers.auth import router as auth_router
from src.digital_twin.evaluation import load_release_profile
from services.api.app.routers.onboarding import router as onboarding_router
from services.api.app.routers.operations import router as operations_router
from services.api.app.routers.publication import router as publication_router
from services.api.app.routers.student import router as student_router
from services.ingestion import IngestionJobService
from services.persistence import SQLiteIngestionJobRepository
from services.storage import FileSystemObjectStore
from services.llm import BudgetedLlmClient, LiteLlmClient
from src.digital_twin.generation import (
    LiveGroundedGenerator,
    StrictEvidenceGroundedPromptBuilder,
)
from src.digital_twin.grounding import LocalCourseSourceIngestionService
from src.digital_twin.grounding.protocols import (
    OCRProvider,
    RegionDescriptionProvider,
    TextEmbedder,
    TutorGenerator,
)
from src.digital_twin.onboarding import (
    InMemorySessionRepository,
    SessionRepository,
    SQLiteSessionRepository,
)
from src.digital_twin.identity import (
    IdentityRepository,
    IdentityService,
    SQLiteIdentityRepository,
)
from src.digital_twin.student import (
    ReleaseLifecycleService,
    SQLiteStudentRepository,
    StudentRepository,
)
from src.digital_twin.student.service import StudentTutoringService


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STUDENT_PROFILE = (
    ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
)
DEFAULT_REGION_CROP_ROOT = ROOT / "data/interim/multimodal-region-crops"
DEFAULT_SOURCE_ROOT = ROOT / "data/interim/course-sources"


def create_app(
    repository: SessionRepository | None = None,
    *,
    student_repository: StudentRepository | None = None,
    student_embedder: TextEmbedder | None = None,
    student_generator: TutorGenerator | None = None,
    student_profile_path: Path = DEFAULT_STUDENT_PROFILE,
    region_crop_root: Path | None = None,
    source_root: Path | None = None,
    source_ocr_provider: OCRProvider | None = None,
    source_description_provider: RegionDescriptionProvider | None = None,
    identity_repository: IdentityRepository | None = None,
    settings: AppSettings | None = None,
) -> FastAPI:
    runtime_settings = settings or AppSettings()
    runtime_settings.validate()
    app = FastAPI(
        title=(
            "Course Digital Twin API"
            if runtime_settings.mode == RuntimeMode.STAGING
            else "Digital Twin Prototype API"
        )
    )
    app.state.settings = runtime_settings
    app.state.operational_metrics = OperationalMetrics()
    app.state.session_repository = repository or (
        SQLiteSessionRepository(runtime_settings.database_path)
        if runtime_settings.mode == RuntimeMode.STAGING
        else InMemorySessionRepository()
    )
    app.state.student_repository = student_repository or SQLiteStudentRepository(
        runtime_settings.database_path
        if runtime_settings.mode == RuntimeMode.STAGING
        else ":memory:"
    )
    identity_path = getattr(app.state.student_repository, "path", ":memory:")
    app.state.identity_repository = identity_repository or SQLiteIdentityRepository(
        identity_path
    )
    app.state.identity_service = IdentityService(
        app.state.identity_repository,
        app.state.student_repository,
        session_ttl_seconds=runtime_settings.session_ttl_seconds,
    )
    resolved_region_root = region_crop_root or (
        runtime_settings.region_crop_root
        if runtime_settings.mode == RuntimeMode.STAGING
        else DEFAULT_REGION_CROP_ROOT
    )
    resolved_source_root = source_root or (
        runtime_settings.source_root
        if runtime_settings.mode == RuntimeMode.STAGING
        else DEFAULT_SOURCE_ROOT
    )
    app.state.region_crop_root = resolved_region_root
    app.state.source_ingestion_service = LocalCourseSourceIngestionService(
        resolved_source_root,
        resolved_region_root,
        ocr_provider=source_ocr_provider,
        description_provider=source_description_provider,
        max_source_bytes=runtime_settings.max_upload_bytes,
    )
    job_database_path = getattr(
        app.state.student_repository, "path", runtime_settings.database_path
    )
    if job_database_path == ":memory:":
        job_database_path = runtime_settings.database_path
    app.state.object_store = FileSystemObjectStore(
        runtime_settings.object_root,
        max_bytes=runtime_settings.max_object_store_bytes,
    )
    app.state.ingestion_job_repository = SQLiteIngestionJobRepository(
        job_database_path
    )
    app.state.ingestion_job_service = IngestionJobService(
        app.state.ingestion_job_repository,
        app.state.object_store,
        app.state.source_ingestion_service,
        max_upload_bytes=runtime_settings.max_upload_bytes,
    )
    configured_generator, provider_budget = _configured_generator(runtime_settings)
    app.state.provider_budget = provider_budget
    app.state.student_service = StudentTutoringService(
        app.state.student_repository,
        profile_path=student_profile_path,
        embedder=student_embedder,
        generator=student_generator or configured_generator,
    )
    profile = load_release_profile(student_profile_path)
    app.state.publication_service = ReleaseLifecycleService(
        app.state.student_repository,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime_settings.allowed_origins),
        allow_origin_regex=(
            r"^http://(localhost|127\.0\.0\.1):\d+$"
            if runtime_settings.mode in {RuntimeMode.DEMO, RuntimeMode.TEST}
            else None
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(OriginGuardMiddleware, settings=runtime_settings)
    app.add_middleware(UploadSizeGuardMiddleware, settings=runtime_settings)
    app.add_middleware(RateLimitMiddleware, settings=runtime_settings)
    app.add_middleware(
        RequestObservabilityMiddleware,
        metrics=app.state.operational_metrics,
    )
    app.include_router(auth_router, prefix="/api")
    app.include_router(operations_router, prefix="/api")
    app.include_router(onboarding_router, prefix="/api")
    app.include_router(publication_router, prefix="/api")
    app.include_router(student_router, prefix="/api")
    return app


def _configured_generator(settings: AppSettings):
    if settings.generator_mode == GeneratorMode.DETERMINISTIC:
        return None, None
    client = BudgetedLlmClient(
        LiteLlmClient(
            "deepseek/deepseek-v4-flash",
            timeout_seconds=15,
            max_output_tokens=600,
            temperature=0,
            response_format={"type": "json_object"},
            provider_options={
                "extra_body": {
                    "thinking": {"type": "disabled"},
                    "user_id": "course-digital-twin-staging",
                }
            },
        ),
        max_calls=settings.provider_max_calls_per_process,
        max_cost_usd=settings.provider_cost_cap_usd,
    )
    return (
        LiveGroundedGenerator(
            client,
            prompt_builder=StrictEvidenceGroundedPromptBuilder(),
        ),
        client,
    )
