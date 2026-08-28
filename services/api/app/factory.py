import math
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.config import (
    AppSettings,
    GeneratorMode,
    RuntimeMode,
    StudentTutoringMode,
)
from services.api.app.middleware import (
    OriginGuardMiddleware,
    RateLimitMiddleware,
    RequestObservabilityMiddleware,
    UploadSizeGuardMiddleware,
)
from services.api.app.observability import OperationalMetrics
from services.api.app.routers.auth import router as auth_router
from src.digital_twin.evaluation import (
    ComponentKind,
    ComponentStatus,
    SystemReleaseProfile,
    load_release_profile,
)
from services.api.app.routers.onboarding import router as onboarding_router
from services.api.app.routers.operations import router as operations_router
from services.api.app.routers.publication import router as publication_router
from services.api.app.routers.student import router as student_router
from services.ingestion import IngestionJobService
from services.persistence import SQLiteIngestionJobRepository
from services.storage import FileSystemObjectStore
from services.llm import BudgetedLlmClient, OpenAiResponsesClient
from src.digital_twin.generation import (
    BoundedPedagogicalPromptBuilder,
    LiveAtomicGroundedGenerator,
    StrictEvidenceGroundedPromptBuilder,
)
from src.digital_twin.grounding import (
    LocalCourseSourceIngestionService,
    RetrievalIndexStoreV1,
    build_retrieval_index_binding,
)
from src.digital_twin.grounding.protocols import (
    EvidenceSufficiencyGate,
    OCRProvider,
    PostGenerationClaimValidator,
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
from src.digital_twin.student.proactive import (
    DiscordWebhookDeliveryAdapter,
    EvidenceRecoveryMode,
    ProactiveOutreachService,
)
from src.digital_twin.student.service import StudentTutoringService


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STUDENT_PROFILE = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
DEFAULT_REGION_CROP_ROOT = ROOT / "data/interim/multimodal-region-crops"
DEFAULT_SOURCE_ROOT = ROOT / "data/interim/course-sources"


def create_app(
    repository: SessionRepository | None = None,
    *,
    student_repository: StudentRepository | None = None,
    student_embedder: TextEmbedder | None = None,
    student_generator: TutorGenerator | None = None,
    student_evidence_gate: EvidenceSufficiencyGate | None = None,
    student_claim_evidence_validator: PostGenerationClaimValidator | None = None,
    student_profile_path: Path | None = None,
    region_crop_root: Path | None = None,
    source_root: Path | None = None,
    source_ocr_provider: OCRProvider | None = None,
    source_description_provider: RegionDescriptionProvider | None = None,
    identity_repository: IdentityRepository | None = None,
    retrieval_index_store: RetrievalIndexStoreV1 | None = None,
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
    app.state.object_store = FileSystemObjectStore(
        runtime_settings.object_root,
        max_bytes=runtime_settings.max_object_store_bytes,
    )
    app.state.ingestion_job_repository = SQLiteIngestionJobRepository(job_database_path)
    app.state.ingestion_job_service = IngestionJobService(
        app.state.ingestion_job_repository,
        app.state.object_store,
        app.state.source_ingestion_service,
        max_upload_bytes=runtime_settings.max_upload_bytes,
    )
    resolved_student_profile_path = (
        student_profile_path or runtime_settings.student_profile_path
    )
    profile = load_release_profile(resolved_student_profile_path)
    retriever = next(
        entry for entry in profile.components if entry.component == ComponentKind.RETRIEVER
    )
    chunker = next(
        entry for entry in profile.components if entry.component == ComponentKind.CHUNKER
    )
    configured_generator, provider_budget = _configured_generator(
        runtime_settings,
        profile,
    )
    app.state.provider_budget = provider_budget
    app.state.student_service = StudentTutoringService(
        app.state.student_repository,
        profile_path=resolved_student_profile_path,
        embedder=student_embedder,
        generator=student_generator or configured_generator,
        evidence_gate=student_evidence_gate,
        claim_evidence_validator=student_claim_evidence_validator,
        tutoring_mode=runtime_settings.student_tutoring_mode.value,
        retrieval_index_store=retrieval_index_store,
        retrieval_index_chunker_id=(
            chunker.implementation.implementation_id
            if chunker.implementation is not None
            else "page-bounded-heading-paragraph-chunker"
        ),
        retrieval_index_chunker_version=(
            chunker.implementation.version
            if chunker.implementation is not None
            else "v1"
        ),
    )
    app.state.proactive_outreach_service = ProactiveOutreachService(
        app.state.student_repository
    )

    def scan_evidence_recovery_after_publish(
        professor_id: str,
        course_id: str,
    ) -> None:
        app.state.proactive_outreach_service.scan_evidence_recovery(
            professor_id,
            course_id,
            mode=EvidenceRecoveryMode.SHADOW,
        )

    app.state.discord_delivery_adapter = DiscordWebhookDeliveryAdapter(enabled=False)
    def release_index_binding(release):
        if retriever.implementation is None or chunker.implementation is None:
            raise ValueError("release profile lacks an indexable retrieval selection")
        return build_retrieval_index_binding(
            course_id=release.course_id,
            release_id=release.id,
            profile_id=release.profile_id,
            profile_version=release.profile_version,
            chunker_id=chunker.implementation.implementation_id,
            chunker_version=chunker.implementation.version,
            chunks=release.chunks,
            configuration=retriever.implementation.configuration,
        )

    def retrieval_index_ready(release) -> bool:
        if retrieval_index_store is None:
            return True
        retrieval_index_store.verify_bound(release_index_binding(release))
        return True

    def prepare_retrieval_index(release) -> None:
        if retrieval_index_store is None:
            return
        if student_embedder is None:
            raise ValueError("retrieval index preparation requires an embedder")
        retrieval_index_store.build(
            release_index_binding(release),
            release.chunks,
            student_embedder,
        )

    app.state.publication_service = ReleaseLifecycleService(
        app.state.student_repository,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        evidence_sufficiency_ready=student_evidence_gate is not None,
        post_publish_hook=scan_evidence_recovery_after_publish,
        retrieval_index_ready=(
            retrieval_index_ready if retrieval_index_store is not None else None
        ),
        retrieval_index_preparer=(
            prepare_retrieval_index if retrieval_index_store is not None else None
        ),
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


def _configured_generator(
    settings: AppSettings,
    profile: SystemReleaseProfile,
):
    if settings.generator_mode == GeneratorMode.DETERMINISTIC:
        return None, None
    if settings.generator_mode != GeneratorMode.OPENAI_GPT_5_4_MINI:
        raise ValueError("historical generator modes cannot be selected for R1")
    generator = next(
        entry
        for entry in profile.components
        if entry.component == ComponentKind.GENERATOR
    )
    prompt = next(
        entry for entry in profile.components if entry.component == ComponentKind.PROMPT
    )
    if (
        generator.status != ComponentStatus.SELECTED
        or generator.implementation is None
        or generator.implementation.implementation_id
        != "openai-responses-gpt-5-4-mini-atomic-v1"
        or prompt.status != ComponentStatus.SELECTED
        or prompt.implementation is None
        or prompt.implementation.implementation_id
        != "strict-evidence-grounded-prompt-v3"
    ):
        raise ValueError("active profile does not select the supported live generator")
    configuration = generator.implementation.configuration
    provider_model = _required_profile_string(configuration, "provider_model")
    if provider_model != "gpt-5.4-mini-2026-03-17":
        raise ValueError("active profile generator model is unsupported")
    if configuration.get("reasoning_effort") != "none":
        raise ValueError("active profile generator must use reasoning effort none")
    if configuration.get("max_attempts") != 1:
        raise ValueError("active profile generator must use one attempt")
    timeout_seconds = _required_profile_number(configuration, "timeout_seconds")
    max_output_tokens = _required_profile_integer(
        configuration,
        "max_output_tokens",
    )
    client = BudgetedLlmClient(
        OpenAiResponsesClient(
            provider_model,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            reasoning_effort="none",
        ),
        max_calls=settings.provider_max_calls_per_process,
        max_cost_usd=settings.provider_cost_cap_usd,
    )
    prompt_builder = (
        BoundedPedagogicalPromptBuilder()
        if settings.student_tutoring_mode
        == StudentTutoringMode.BOUNDED_TUTORING_GRAPH
        else StrictEvidenceGroundedPromptBuilder()
    )
    return (
        LiveAtomicGroundedGenerator(
            client,
            prompt_builder=prompt_builder,
        ),
        client,
    )


def _required_profile_string(
    configuration: dict[str, str | int | float | bool],
    name: str,
) -> str:
    value = configuration.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"active profile generator {name} is invalid")
    return value.strip()


def _required_profile_number(
    configuration: dict[str, str | int | float | bool],
    name: str,
) -> float:
    value = configuration.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"active profile generator {name} is invalid")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"active profile generator {name} is invalid")
    return numeric


def _required_profile_integer(
    configuration: dict[str, str | int | float | bool],
    name: str,
) -> int:
    value = configuration.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"active profile generator {name} is invalid")
    return value
