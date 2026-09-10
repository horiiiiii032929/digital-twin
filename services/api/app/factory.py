import math
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.digital_twin.clock import SystemUtcClock, UtcClock
from services.api.app.config import (
    AppSettings,
    AutonomyPlannerMode,
    EvidenceGateMode,
    GeneratorMode,
    RuntimeMode,
    StudentTutoringMode,
    VisualRetrievalMode,
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
from src.digital_twin.llm import LlmClient
from src.digital_twin.model_policy import (
    OPENAI_GPT_5_6_LUNA_MODEL,
    OPENAI_GPT_5_6_TERRA_MODEL,
    OPENAI_MODEL_PRICING_USD_PER_MILLION,
    OPENAI_PRODUCT_CANDIDATE_MODELS,
)
from src.digital_twin.generation import (
    BoundedPedagogicalPromptBuilder,
    LiveAtomicGroundedGenerator,
    DeterministicEvidenceSetGroundedGenerator,
    DeterministicActionRouterV3,
    DeterministicPolicyEnforcer,
    StrictEvidenceGroundedPromptBuilder,
)
from src.digital_twin.grounding import (
    AmbiguitySafeEvidenceGateV1,
    DominanceScopedAmbiguitySafeEvidenceGateV3,
    AtomicClaimEvidenceValidator,
    CanonicalSourceAtomicClaimVerifier,
    ContiguousQuoteAtomicClaimVerifier,
    LocalCourseSourceIngestionService,
    RetrievalIndexStoreV1,
    StructuredLexicalCoverageEvidenceGate,
    QuestionTargetedAtomicEvidenceGate,
    PersistentJinaQuotaLedgerV1,
    QuotaBoundJinaVisualQueryProviderV1,
    SyncVisualQueryProvider,
    VisualAwareRetrieverV1,
    VisualIndexStoreV1,
    VisualIndexUnavailableError,
    VisualIndexUnavailableRetrieverV1,
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
    LearningGapPseudonymizer,
    ReleaseLifecycleService,
    SQLiteStudentRepository,
    StudentRepository,
    TeachingProfileService,
)
from src.digital_twin.student.proactive import (
    DiscordWebhookDeliveryAdapter,
    ProactiveOutreachService,
)
from src.digital_twin.student.autonomy_runtime import (
    DETERMINISTIC_GENERATOR_MODEL,
    DETERMINISTIC_PLANNER_MODEL,
    GovernedAutonomousTutoringGraph,
    LiveAutonomousPlanner,
)
from src.digital_twin.student.autonomy_service import (
    BoundedStrategyGroundedWordingGenerator,
    GovernedAutonomyService,
    RepositoryGroundedWordingGenerator,
)
from src.digital_twin.student.planning_architectures import (
    GuardedPolicyValuePlanner,
    LlmHierarchicalPlanningProvider,
)
from src.digital_twin.student.service import StudentTutoringService
from src.digital_twin.student.tutoring_graph import LiveReactiveSemanticPlanner


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
    visual_index_store: VisualIndexStoreV1 | None = None,
    visual_query_provider: SyncVisualQueryProvider | None = None,
    learning_gap_pseudonymizer: LearningGapPseudonymizer | None = None,
    settings: AppSettings | None = None,
    clock: UtcClock | None = None,
    autonomy_planner_client: LlmClient | None = None,
    teaching_profile_context_enabled: bool = False,
    question_specific_generation_enabled: bool = False,
    bounded_generation_contract_enabled: bool = False,
    named_referent_context_enabled: bool = False,
    instructional_moves_enabled: bool = False,
    instructional_continuation_enabled: bool = False,
    instructional_request_coverage_enabled: bool = False,
    instructional_compact_response_enabled: bool = False,
    instructional_profile_authority_enabled: bool = False,
    instructional_typed_response_enabled: bool = False,
    instructional_evidence_strength_enabled: bool = False,
    instructional_factual_revision_enabled: bool = False,
    instructional_bounded_revision_enabled: bool = False,
    instructional_conditional_revision_enabled: bool = False,
    experimental_generation_model_id: str | None = None,
    experimental_final_audit_model_id: str | None = None,
    provider_max_concurrency: int = 1,
    post_report_learning_mode: str = "control",
    post_report_planner_mode: str = "configured",
    post_report_goal_recovery_enabled: bool = False,
    post_report_source_assessment_enabled: bool = False,
    post_report_model_assessment_enabled: bool = False,
    post_report_model_assessment_version: str = "v1",
    post_report_context_retrieval_enabled: bool = False,
    instructional_contract_repair_enabled: bool = False,
    instructional_final_audit_enabled: bool = False,
    instructional_source_state_context_enabled: bool = False,
) -> FastAPI:
    if instructional_source_state_context_enabled and not instructional_final_audit_enabled:
        raise ValueError("source-state context requires the explicit final-audit candidate")
    if post_report_model_assessment_version not in {"v1", "v2"}:
        raise ValueError("unknown post-report assessment version")
    if post_report_model_assessment_version != "v1" and not post_report_model_assessment_enabled:
        raise ValueError("assessment version requires model assessment")
    if post_report_learning_mode not in {"control", "assessed-count", "assessed-decay", "assessed-bkt", "assessed-pfa"}:
        raise ValueError("unknown post-report learning mode")
    if post_report_planner_mode not in {"configured", "rules", "analytic-only"}:
        raise ValueError("unknown post-report planner mode")
    if instructional_contract_repair_enabled and (not instructional_evidence_strength_enabled or instructional_factual_revision_enabled):
        raise ValueError("contract repair requires evidence-strength generation and excludes factual revision")
    if instructional_final_audit_enabled and not instructional_contract_repair_enabled:
        raise ValueError("final audit requires the explicit contract-repair candidate")
    if instructional_conditional_revision_enabled and (not instructional_factual_revision_enabled or instructional_bounded_revision_enabled):
        raise ValueError("conditional revision requires factual revision and excludes bounded revision")
    if instructional_bounded_revision_enabled and not instructional_factual_revision_enabled:
        raise ValueError("bounded revision requires factual revision")
    if instructional_factual_revision_enabled and not instructional_evidence_strength_enabled:
        raise ValueError("factual revision requires evidence strength instruction")
    if instructional_evidence_strength_enabled and not instructional_typed_response_enabled:
        raise ValueError("evidence strength instruction requires typed instruction")
    if instructional_typed_response_enabled and not instructional_profile_authority_enabled:
        raise ValueError("typed instruction requires profile authority")
    if instructional_profile_authority_enabled and not instructional_compact_response_enabled:
        raise ValueError("profile authority requires compact instruction")
    if instructional_compact_response_enabled and (not named_referent_context_enabled or instructional_moves_enabled):
        raise ValueError("compact instruction requires named-referent context and excludes V5-V7 flags")
    if instructional_request_coverage_enabled and not instructional_continuation_enabled:
        raise ValueError("instructional request coverage requires continuation")
    if instructional_continuation_enabled and not instructional_moves_enabled:
        raise ValueError("instructional continuation requires instructional moves")
    if instructional_moves_enabled and not named_referent_context_enabled:
        raise ValueError("instructional moves require named-referent context")
    if named_referent_context_enabled and not bounded_generation_contract_enabled:
        raise ValueError("named referent context requires bounded generation contract")
    if bounded_generation_contract_enabled and not question_specific_generation_enabled:
        raise ValueError("bounded generation contract requires the explicit question-specific candidate")
    runtime_settings = settings or AppSettings()
    # An explicitly injected planner transport needs no OpenAI credential. Keep
    # credential checks for every other independently configured provider.
    runtime_settings.validate(
        require_provider_credentials=(
            autonomy_planner_client is None
            or runtime_settings.generator_mode != GeneratorMode.DETERMINISTIC
            or runtime_settings.visual_retrieval_mode != VisualRetrievalMode.TEXT_OCR_FALLBACK
        )
    )
    runtime_clock = clock or SystemUtcClock()
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
        entry
        for entry in profile.components
        if entry.component == ComponentKind.RETRIEVER
    )
    chunker = next(
        entry
        for entry in profile.components
        if entry.component == ComponentKind.CHUNKER
    )
    configured_generator, provider_budget = _configured_generator(
        runtime_settings,
        profile,
    )
    configured_evidence_gate = (
        student_evidence_gate
        if student_evidence_gate is not None
        else _configured_evidence_gate(runtime_settings)
    )
    active_generator = student_generator or configured_generator
    governed_v2 = bool(
        runtime_settings.student_tutoring_mode
        == StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
    )
    autonomy_provider_model = _autonomy_provider_model(runtime_settings)
    live_autonomy_planner = bool(governed_v2 and autonomy_provider_model is not None)
    active_generator_model = (
        provider_budget.client.model
        if provider_budget is not None
        else (
            "deterministic/evidence-set-v2"
            if isinstance(active_generator, DeterministicEvidenceSetGroundedGenerator)
            else DETERMINISTIC_GENERATOR_MODEL
        )
    )
    active_claim_validator = student_claim_evidence_validator
    if active_claim_validator is None and governed_v2:
        verifier = (
            CanonicalSourceAtomicClaimVerifier()
            if isinstance(active_generator, DeterministicEvidenceSetGroundedGenerator)
            else ContiguousQuoteAtomicClaimVerifier()
        )
        active_claim_validator = AtomicClaimEvidenceValidator(
            verifier,
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
            maximum_claims=8,
            evidence_limit=5,
        )
    app.state.provider_budget = provider_budget
    visual_retriever_decorator = None
    if (
        runtime_settings.visual_retrieval_mode
        == VisualRetrievalMode.JINA_V4_LATE_INTERACTION
    ):
        component_ledger_sha256 = runtime_settings.visual_component_ledger_sha256
        if component_ledger_sha256 is None:
            raise ValueError("qualified visual component ledger hash is unavailable")
        active_visual_index_store = visual_index_store or VisualIndexStoreV1(
            runtime_settings.visual_index_root
        )
        active_visual_query_provider = visual_query_provider
        if active_visual_query_provider is None:
            quota = PersistentJinaQuotaLedgerV1(
                runtime_settings.visual_quota_database_path,
                imported_ledger_sha256=component_ledger_sha256,
            )
            active_visual_query_provider = QuotaBoundJinaVisualQueryProviderV1(
                api_key=os.environ["JINA_API_KEY"],
                quota_ledger=quota,
                timeout_seconds=runtime_settings.visual_query_timeout_seconds,
            )
            app.state.visual_quota_ledger = quota
        app.state.visual_index_store = active_visual_index_store
        app.state.visual_query_provider = active_visual_query_provider

        def decorate_visual_retriever(text_retriever, release):
            try:
                manifest, index = active_visual_index_store.load_bound(
                    course_id=release.course_id,
                    release_id=release.id,
                    profile_id=release.profile_id,
                    profile_version=release.profile_version,
                    source_ledger_sha256=component_ledger_sha256,
                    chunks=release.chunks,
                )
            except VisualIndexUnavailableError:
                return VisualIndexUnavailableRetrieverV1(text_retriever)
            return VisualAwareRetrieverV1(
                text_retriever=text_retriever,
                query_provider=active_visual_query_provider,
                index=index,
                course_id=release.course_id,
                chunks=release.chunks,
                artifact_id=manifest.artifact_id,
            )

        visual_retriever_decorator = decorate_visual_retriever
    autonomy_planner_budget = None
    live_proactive_planner = None
    reactive_semantic_planner = None
    if live_autonomy_planner:
        assert autonomy_provider_model is not None
        autonomy_planner_budget = BudgetedLlmClient(
            autonomy_planner_client or OpenAiResponsesClient(
                autonomy_provider_model,
                timeout_seconds=30,
                max_output_tokens=500,
                reasoning_effort="low",
                input_price_usd_per_million=(
                    OPENAI_MODEL_PRICING_USD_PER_MILLION[autonomy_provider_model][0]
                ),
                output_price_usd_per_million=(
                    OPENAI_MODEL_PRICING_USD_PER_MILLION[autonomy_provider_model][1]
                ),
            ),
            max_calls=runtime_settings.provider_max_calls_per_process,
            max_cost_usd=runtime_settings.provider_cost_cap_usd,
            max_concurrency=provider_max_concurrency,
        )
        live_proactive_planner = (
            GuardedPolicyValuePlanner(
                proposal_provider=LlmHierarchicalPlanningProvider(
                    autonomy_planner_budget,
                    model_id=autonomy_provider_model,
                )
            )
            if runtime_settings.autonomy_planner_mode
            == AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE
            else LiveAutonomousPlanner(
                autonomy_planner_budget,
                model_id=autonomy_provider_model,
            )
        )
        reactive_semantic_planner = LiveReactiveSemanticPlanner(
            autonomy_planner_budget,
            model_id=autonomy_provider_model,
        )
    if experimental_final_audit_model_id is not None and (
        not instructional_final_audit_enabled
        or experimental_final_audit_model_id not in {"gpt-5.6-luna", "gpt-5.6-sol"}
    ):
        raise ValueError("audit model requires a declared final-audit composition")
    if experimental_generation_model_id is not None and (
        not instructional_typed_response_enabled
        or experimental_generation_model_id not in {"gpt-5.6-luna", "gpt-5.6-sol"}
    ):
        raise ValueError("generation model override requires the explicit typed candidate and approved model")
    if question_specific_generation_enabled:
        if autonomy_planner_budget is None or student_generator is not None:
            raise ValueError("question-specific candidate requires configured planner transport and no generator override")
        from src.digital_twin.generation.question_specific import (
            QuestionSpecificProfileGroundedGenerator, AsyncAnswerabilityAdmissionGateV1,
            BOUNDED_CONTRACT_CANDIDATE_ID, CANDIDATE_ID, NAMED_REFERENT_CANDIDATE_ID,
        )
        if student_evidence_gate is not None:
            raise ValueError("question-specific candidate requires its explicit async admission gate")
        configured_evidence_gate = AsyncAnswerabilityAdmissionGateV1()
        generator_class = QuestionSpecificProfileGroundedGenerator
        if instructional_moves_enabled:
            if student_claim_evidence_validator is not None:
                raise ValueError("instructional candidate requires its explicit source-binding validator")
            from src.digital_twin.generation.instructional import (
                EvidenceLinkedInstructionalGenerator, InstructionalSourceBindingValidator,
            )
            generator_class = EvidenceLinkedInstructionalGenerator
            active_claim_validator = InstructionalSourceBindingValidator()
            if instructional_continuation_enabled:
                from src.digital_twin.generation.continuation import InstructionalContinuationGenerator
                generator_class = InstructionalContinuationGenerator
                if instructional_request_coverage_enabled:
                    from src.digital_twin.generation.request_coverage import RequestCoverageInstructionalGenerator
                    generator_class = RequestCoverageInstructionalGenerator
        if instructional_compact_response_enabled:
            if student_claim_evidence_validator is not None:
                raise ValueError("compact instruction requires its explicit source-association validator")
            from src.digital_twin.generation.compact_instruction import CompactInstructionalGenerator
            from src.digital_twin.generation.instructional import InstructionalSourceBindingValidator
            generator_class = CompactInstructionalGenerator
            if instructional_profile_authority_enabled:
                from src.digital_twin.generation.profile_authority import ProfileAuthorityInstructionalGenerator
                generator_class = ProfileAuthorityInstructionalGenerator
                if instructional_typed_response_enabled:
                    from src.digital_twin.generation.typed_instruction import TypedInstructionalGenerator
                    generator_class = TypedInstructionalGenerator
                    if instructional_evidence_strength_enabled:
                        from src.digital_twin.generation.evidence_strength import EvidenceStrengthInstructionalGenerator
                        generator_class = EvidenceStrengthInstructionalGenerator
                        if instructional_factual_revision_enabled:
                            from src.digital_twin.generation.factual_revision import FactualRevisionInstructionalGenerator
                            generator_class = FactualRevisionInstructionalGenerator
                            if instructional_bounded_revision_enabled:
                                from src.digital_twin.generation.bounded_revision import BoundedRevisionInstructionalGenerator
                                generator_class = BoundedRevisionInstructionalGenerator
                            if instructional_conditional_revision_enabled:
                                from src.digital_twin.generation.conditional_revision import ConditionalRevisionInstructionalGenerator
                                generator_class = ConditionalRevisionInstructionalGenerator
                        if instructional_contract_repair_enabled:
                            from src.digital_twin.generation.contract_repair import ContractRepairInstructionalGenerator
                            generator_class = ContractRepairInstructionalGenerator
                            if instructional_final_audit_enabled:
                                from src.digital_twin.generation.audited_instruction import AuditedInstructionalGenerator
                                generator_class = AuditedInstructionalGenerator
                                if instructional_source_state_context_enabled:
                                    from src.digital_twin.generation.instructional_source_state import SourceStateInstructionalGenerator
                                    generator_class = SourceStateInstructionalGenerator
            active_claim_validator = InstructionalSourceBindingValidator()
        app.state.experimental_generation_configuration = {
            "candidate_id": "question-specific-profile-grounded-v14" if instructional_conditional_revision_enabled else "question-specific-profile-grounded-v13" if instructional_bounded_revision_enabled else "question-specific-profile-grounded-v12" if instructional_factual_revision_enabled else "question-specific-profile-grounded-v11" if instructional_evidence_strength_enabled else "question-specific-profile-grounded-v10" if instructional_typed_response_enabled else "question-specific-profile-grounded-v9" if instructional_profile_authority_enabled else "question-specific-profile-grounded-v8" if instructional_compact_response_enabled else "question-specific-profile-grounded-v7" if instructional_request_coverage_enabled else ("question-specific-profile-grounded-v6" if instructional_continuation_enabled else ("question-specific-profile-grounded-v5" if instructional_moves_enabled else (NAMED_REFERENT_CANDIDATE_ID if named_referent_context_enabled else (BOUNDED_CONTRACT_CANDIDATE_ID if bounded_generation_contract_enabled else CANDIDATE_ID)))),
            "admission_gate": configured_evidence_gate.implementation_id,
            "retriever": "selected-profile-unchanged",
            "semantic_support": "model-assessed-not-proven-by-spans",
        }
        generation_model = experimental_generation_model_id or autonomy_provider_model
        if instructional_contract_repair_enabled:
            app.state.experimental_generation_configuration["candidate_id"] = (
                "question-specific-profile-grounded-v19" if instructional_source_state_context_enabled
                else "question-specific-profile-grounded-v18" if instructional_final_audit_enabled
                else "question-specific-profile-grounded-v17")
        active_generator = generator_class(autonomy_planner_budget,
            **({"audit_model": experimental_final_audit_model_id or "gpt-5.6-sol"} if instructional_final_audit_enabled else {}),
            model_id=generation_model, bounded_contract_enabled=bounded_generation_contract_enabled,
            named_referent_context_enabled=named_referent_context_enabled,
            policy_enforcer=DeterministicPolicyEnforcer(action_router=DeterministicActionRouterV3()))
        if instructional_final_audit_enabled:
            app.state.experimental_generation_configuration["audit_model"] = active_generator.audit_model
        active_generator_model = generation_model
        if experimental_generation_model_id is not None:
            app.state.experimental_generation_configuration.update(generation_model=generation_model, planner_model=autonomy_provider_model)
        if instructional_moves_enabled or instructional_compact_response_enabled:
            app.state.experimental_generation_configuration["claim_validation"] = "experimental-source-binding-only; semantic-support-unverified"
    app.state.autonomy_planner_budget = autonomy_planner_budget
    source_bound_model_assessor = None
    if post_report_model_assessment_enabled:
        if not governed_v2 or autonomy_planner_budget is None:
            raise ValueError("model assessment requires a governed bounded provider composition")
        from src.digital_twin.student.model_assessment import SourceBoundModelAssessor
        source_bound_model_assessor = SourceBoundModelAssessor(autonomy_planner_budget, autonomy_provider_model,
            version=post_report_model_assessment_version)
    app.state.student_service = StudentTutoringService(
        app.state.student_repository,
        profile_path=resolved_student_profile_path,
        embedder=student_embedder,
        generator=active_generator,
        evidence_gate=configured_evidence_gate,
        claim_evidence_validator=active_claim_validator,
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
        learning_gap_pseudonymizer=(
            learning_gap_pseudonymizer
            or (
                LearningGapPseudonymizer(runtime_settings.learning_gap_hmac_secret)
                if runtime_settings.learning_gap_hmac_secret is not None
                else None
            )
        ),
        autonomy_planner_model=(
            autonomy_provider_model
            if live_autonomy_planner
            else DETERMINISTIC_PLANNER_MODEL
        ),
        autonomy_generator_model=active_generator_model,
        reactive_semantic_planner=reactive_semantic_planner,
        teaching_profile_context_enabled=teaching_profile_context_enabled,
        source_bound_assessment_enabled=post_report_source_assessment_enabled,
        source_bound_model_assessor=source_bound_model_assessor,
        conversation_retrieval_enabled=post_report_context_retrieval_enabled,
        retriever_decorator=visual_retriever_decorator,
        clock=runtime_clock,
    )
    app.state.proactive_outreach_service = ProactiveOutreachService(
        app.state.student_repository,
        clock=runtime_clock,
    )
    post_report_goal_manager = None
    if (post_report_learning_mode != "control" or post_report_goal_recovery_enabled
        or post_report_planner_mode != "configured" or post_report_source_assessment_enabled
        or post_report_context_retrieval_enabled or post_report_model_assessment_enabled):
        if not governed_v2:
            raise ValueError("post-report learning requires governed tutoring")
        from src.digital_twin.student.post_report_learning import (
            AnalyticOnlyPlanner, AssessedPlanningStateResolver, RecoveryAwareGoalManager,
            ScopedObservationReader, learning_estimator,
        )
        from src.digital_twin.student.planning_architectures import default_planning_state_card
        from src.digital_twin.student.autonomy_runtime import DeterministicAutonomousPlanner
        pseudonymizer = app.state.student_service.learning_gap_pseudonymizer
        if pseudonymizer is None:
            raise ValueError("assessed learning requires a learner-key pseudonymizer")
        observation_reader = ScopedObservationReader(app.state.student_repository, pseudonymizer)
        state_resolver = (AssessedPlanningStateResolver(observation_reader,
            learning_estimator(post_report_learning_mode))
            if post_report_learning_mode != "control" else default_planning_state_card)
        if post_report_planner_mode == "analytic-only":
            live_proactive_planner = AnalyticOnlyPlanner(state_resolver)
        elif post_report_planner_mode == "rules":
            live_proactive_planner = DeterministicAutonomousPlanner()
        elif post_report_learning_mode != "control":
            if not isinstance(live_proactive_planner, GuardedPolicyValuePlanner):
                raise ValueError("assessed input requires guarded, analytic-only or explicit rules planning")
            live_proactive_planner.state_card_resolver = state_resolver
        if post_report_goal_recovery_enabled:
            post_report_goal_manager = RecoveryAwareGoalManager(observation_reader, runtime_clock)
            app.state.student_service.autonomy_goal_manager = post_report_goal_manager
        if live_proactive_planner is not None:
            app.state.student_service.autonomy_planner_model = live_proactive_planner.model_id
        app.state.post_report_learning_configuration = {
            "input": post_report_learning_mode,
            "estimator": getattr(getattr(state_resolver, "estimator", None), "implementation_id", None),
            "planner": post_report_planner_mode,
            "goal_completion": "objective-scoped-recovery-v1" if post_report_goal_recovery_enabled else "cumulative-control",
            "status": "experimental-not-promoted",
            "assessment": (source_bound_model_assessor.implementation_id if post_report_model_assessment_enabled
                else "source-bound-literal-v1" if post_report_source_assessment_enabled else "lexical-control"),
            "assessment_model": source_bound_model_assessor.model_id if source_bound_model_assessor else None,
            "retrieval_context": "previous-student-query-v1" if post_report_context_retrieval_enabled else "current-message-only",
        }
    autonomy_graph = None
    if governed_v2:
        autonomy_wording_generator = (
            BoundedStrategyGroundedWordingGenerator(
                app.state.student_repository,
                autonomy_planner_budget,
                model_id=OPENAI_GPT_5_6_LUNA_MODEL,
                claim_validator=active_claim_validator,
            )
            if runtime_settings.autonomy_planner_mode
            == AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE
            and autonomy_planner_budget is not None
            else RepositoryGroundedWordingGenerator(
                app.state.student_repository,
                active_generator,
                model_id=active_generator_model,
                claim_validator=active_claim_validator,
            )
        )
        autonomy_graph = GovernedAutonomousTutoringGraph(
            planner=live_proactive_planner,
            generator=autonomy_wording_generator,
            checkpoint_database_path=str(runtime_settings.database_path),
        )
    app.state.governed_autonomy_service = GovernedAutonomyService(
        app.state.student_repository,
        app.state.proactive_outreach_service,
        graph=autonomy_graph,
        teaching_profile_context_enabled=teaching_profile_context_enabled,
        clock=runtime_clock,
        goal_manager=post_report_goal_manager,
    )
    app.state.teaching_profile_service = TeachingProfileService(
        app.state.student_repository
    )

    def scan_evidence_recovery_after_publish(
        professor_id: str,
        course_id: str,
    ) -> None:
        app.state.governed_autonomy_service.observe_evidence_recovery(
            professor_id,
            course_id,
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
        evidence_sufficiency_ready=configured_evidence_gate is not None,
        teaching_profile_required=(
            runtime_settings.student_tutoring_mode
            in {
                StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
                StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
            }
        ),
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
    # Capture construction inputs only in memory; artifacts receive a whitelist
    # of public configuration fields, never clients, settings secrets or handles.
    import inspect
    from services.api.app.generated_preview import attach_generated_preview
    local_parameters = locals()
    preview_parameters = {key: local_parameters[key] for key in inspect.signature(create_app).parameters}
    attach_generated_preview(app, factory=create_app, factory_parameters=preview_parameters,
        parent_budget=autonomy_planner_budget)
    return app


def _configured_generator(
    settings: AppSettings,
    profile: SystemReleaseProfile,
):
    if settings.generator_mode == GeneratorMode.DETERMINISTIC:
        if (
            settings.student_tutoring_mode
            == StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
        ):
            return _deterministic_governed_generator(), None
        return None, None
    if settings.generator_mode not in {
        GeneratorMode.OPENAI_GPT_5_4_MINI,
        GeneratorMode.OPENAI_PROFILE_SELECTED,
    }:
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
        or not generator.implementation.implementation_id.startswith(
            "openai-responses-"
        )
        or not generator.implementation.implementation_id.endswith("-atomic-v1")
        or prompt.status != ComponentStatus.SELECTED
        or prompt.implementation is None
        or prompt.implementation.implementation_id
        != "strict-evidence-grounded-prompt-v3"
    ):
        raise ValueError("active profile does not select the supported live generator")
    configuration = generator.implementation.configuration
    provider_model = _required_profile_string(configuration, "provider_model")
    if provider_model not in OPENAI_PRODUCT_CANDIDATE_MODELS:
        raise ValueError("active profile generator model is unsupported")
    reasoning_effort = configuration.get("reasoning_effort")
    if reasoning_effort not in {"none", "low"}:
        raise ValueError("active profile generator reasoning effort is unsupported")
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
            reasoning_effort=str(reasoning_effort),
            input_price_usd_per_million=(
                OPENAI_MODEL_PRICING_USD_PER_MILLION[provider_model][0]
            ),
            output_price_usd_per_million=(
                OPENAI_MODEL_PRICING_USD_PER_MILLION[provider_model][1]
            ),
        ),
        max_calls=settings.provider_max_calls_per_process,
        max_cost_usd=settings.provider_cost_cap_usd,
    )
    prompt_builder = (
        BoundedPedagogicalPromptBuilder()
        if settings.student_tutoring_mode
        in {
            StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
            StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
        }
        else StrictEvidenceGroundedPromptBuilder()
    )
    return (
        LiveAtomicGroundedGenerator(
            client,
            prompt_builder=prompt_builder,
            policy_enforcer=DeterministicPolicyEnforcer(
                action_router=DeterministicActionRouterV3()
            ),
        ),
        client,
    )


def _autonomy_provider_model(settings: AppSettings) -> str | None:
    return {
        AutonomyPlannerMode.DETERMINISTIC: None,
        AutonomyPlannerMode.OPENAI_GPT_5_6_TERRA: OPENAI_GPT_5_6_TERRA_MODEL,
        AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE: (
            OPENAI_GPT_5_6_LUNA_MODEL
        ),
    }[settings.autonomy_planner_mode]


def _deterministic_governed_generator() -> DeterministicEvidenceSetGroundedGenerator:
    """Build the one policy-bound deterministic generator used by governed R1."""

    return DeterministicEvidenceSetGroundedGenerator(
        policy_enforcer=DeterministicPolicyEnforcer(
            action_router=DeterministicActionRouterV3()
        )
    )


def _configured_evidence_gate(settings: AppSettings):
    if settings.evidence_gate_mode == EvidenceGateMode.UNSELECTED:
        return None
    if settings.evidence_gate_mode == EvidenceGateMode.STRUCTURED_LEXICAL_V1:
        return StructuredLexicalCoverageEvidenceGate(
            minimum_content_matching_terms=2,
            evidence_limit=3,
        )
    if (
        settings.evidence_gate_mode
        == EvidenceGateMode.AMBIGUITY_SAFE_STRUCTURED_LEXICAL_V1
    ):
        return AmbiguitySafeEvidenceGateV1(
            StructuredLexicalCoverageEvidenceGate(
                minimum_content_matching_terms=2,
                evidence_limit=3,
            ),
            evidence_limit=5,
        )
    if (
        settings.evidence_gate_mode
        == EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3
    ):
        # Selected by product-evidence-gate-selection-004: 50.00% fully
        # grounded factual success against the v2 gate's 36.80%, with severe
        # unsupported releases and operational failures zero in both arms.
        return DominanceScopedAmbiguitySafeEvidenceGateV3(
            QuestionTargetedAtomicEvidenceGate(
                base_gate=StructuredLexicalCoverageEvidenceGate(
                    minimum_content_matching_terms=2,
                    evidence_limit=5,
                )
            ),
            evidence_limit=5,
        )
    if (
        settings.evidence_gate_mode
        == EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2
    ):
        return AmbiguitySafeEvidenceGateV1(
            QuestionTargetedAtomicEvidenceGate(
                base_gate=StructuredLexicalCoverageEvidenceGate(
                    minimum_content_matching_terms=2,
                    evidence_limit=5,
                )
            ),
            evidence_limit=5,
        )
    raise ValueError("unsupported evidence gate mode")


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
