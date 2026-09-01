"""Concrete live T0 adapter for the flow-independent open benchmark."""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any

from services.embeddings import Qwen3TextEmbedder
from src.digital_twin.evaluation.factual_qa_adapters import (
    StudentTutoringServiceAdapterV1,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.cross_engine_program import ProductEngineBindingV1
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    OpenAiCompatibleJsonTransport,
    ProviderCallLedgerV1,
)
from src.digital_twin.generation import (
    DeterministicGroundedGenerator,
    DeterministicPolicyEnforcer,
    ExtractiveBoundaryGroundedPromptBuilder,
    LiveAtomicGroundedGenerator,
    LiveExtractiveBoundaryGroundedGenerator,
    LiveQuestionTargetedAtomicGroundedGenerator,
    LiveQuestionTargetedExtractionGroundedGenerator,
    QuestionTargetedAtomicPromptBuilder,
    QuestionTargetedExtractionPromptBuilder,
    StrictEvidenceGroundedPromptBuilder,
)
from src.digital_twin.action_router import (
    DeterministicActionRouterV1,
    DeterministicActionRouterV2,
)
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    AtomicClaimEvidenceValidator,
    CaseBoundPrecomputedRetriever,
    ContiguousQuoteAtomicClaimVerifier,
    DocumentChunk,
    LocalNliCrossEncoderBackend,
    NliAtomicClaimVerifier,
    QuestionTargetedAtomicEvidenceGate,
    RetrievalHit,
    RetrievalIndexStoreV1,
    SourceSemanticEvidenceAtomGateV1,
    SourceSemanticEvidenceAtomGateV2,
    StructuredHierarchicalCoverageEvidenceGate,
    StructuredLexicalCoverageEvidenceGate,
    build_retrieval_index_binding,
)
from src.digital_twin.grounding.models import (
    AtomicAnswerClaim,
    GenerationUsage,
    TutorAnswer,
)
from src.digital_twin.llm import LlmMessage, LlmResponse, LlmUnavailableError
from src.digital_twin.student import (
    Account,
    AccountRole,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    MembershipRole,
    ReleaseEvaluationStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    approved_synthetic_policy,
)
from src.digital_twin.tutor_policy import SourceLabel
from src.digital_twin.model_policy import (
    OPENAI_MODEL_PRICING_USD_PER_MILLION,
    OPENAI_PRODUCT_CANDIDATE_MODELS,
    OPENAI_SEMANTIC_REVIEW_MODEL,
)


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_INDEX_ROOT = Path(
    os.getenv(
        "ACADEMIC_EVAL_INDEX_ROOT",
        str(
            ROOT
            / "reports/generated/academic-factual-qa-open-10000-v1-retrieval-indexes-001"
        ),
    )
)
PROFILE_PATH = (
    ROOT / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)
SOURCE_PLAN_PATH = Path(
    os.getenv(
        "ACADEMIC_EVAL_SOURCE_PLAN_PATH",
        str(ROOT / "data/processed/academic_factual_qa_open_10000_v1_sources.json"),
    )
)
HISTORICAL_BINDING_PATH = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_provider_binding_003.json"
)
OPENAI_BINDING_PATH = (
    ROOT / "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_002.json"
)
PRODUCT_MAXIMUM_CALLS = {"candidate": 500, "control": 100}
PRODUCT_MAXIMUM_COST_USD = {"candidate": 8.0, "control": 2.0}
ATOMIC_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim_id", "text", "citation_ids"],
                "properties": {
                    "claim_id": {"type": "string"},
                    "text": {"type": "string"},
                    "citation_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 5,
                        "items": {"type": "string"},
                    },
                },
            },
        }
    },
}
EXTRACTIVE_BOUNDARY_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["action", "claims"],
    "properties": {
        "action": {"type": "string", "enum": ["answer", "abstain", "clarify"]},
        "claims": {
            "type": "array",
            "minItems": 0,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim_id", "text", "citation_ids"],
                "properties": {
                    "claim_id": {
                        "type": "string",
                        "pattern": "^claim-[a-z0-9-]+$",
                    },
                    "text": {"type": "string"},
                    "citation_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 5,
                        "items": {"type": "string", "pattern": "^S[1-9][0-9]*$"},
                    },
                },
            },
        },
    },
}


class LiveT0AdapterError(RuntimeError):
    """Raised when the concrete T0 runtime violates its frozen manifest."""


_CURRENT_CASE_ID: ContextVar[str | None] = ContextVar(
    "academic_factual_qa_open_current_case", default=None
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _evaluation_citation(chunk: DocumentChunk) -> EvaluationCitationV1:
    try:
        char_start = int(chunk.metadata["char_start"])
        char_end = int(chunk.metadata["char_end"])
    except (KeyError, TypeError, ValueError) as error:
        raise LiveT0AdapterError(
            "retrieved chunk lacks canonical character lineage"
        ) from error
    return EvaluationCitationV1(
        source_artifact_id=chunk.source_artifact_id or chunk.document_id,
        source_version=chunk.source_version,
        source_sha256=chunk.source_checksum,
        char_start=char_start,
        char_end=char_end,
        region_id=chunk.region_id,
    )


def _chunks_by_course(
    source_path: Path | None = None,
) -> tuple[dict[str, list[DocumentChunk]], dict[str, DocumentChunk]]:
    plan = _load(source_path or SOURCE_PLAN_PATH)
    if "chunks" in plan:
        chunks = [DocumentChunk.model_validate(row) for row in plan["chunks"]]
        grouped: dict[str, list[DocumentChunk]] = {}
        by_id: dict[str, DocumentChunk] = {}
        for chunk in chunks:
            course_id = str(chunk.metadata.get("course_id", ""))
            if not course_id:
                raise LiveT0AdapterError("registered chunk lacks course identity")
            if chunk.id in by_id:
                raise LiveT0AdapterError("registered chunk identity is duplicated")
            grouped.setdefault(course_id, []).append(chunk)
            by_id[chunk.id] = chunk
        if len(grouped) != 4 or not chunks:
            raise LiveT0AdapterError("registered source package has invalid coverage")
        return grouped, by_id
    grouped: dict[str, list[DocumentChunk]] = {}
    by_id: dict[str, DocumentChunk] = {}
    ordinals: dict[str, int] = {}
    for row in plan["clusters"]:
        course_id = str(row["course_id"])
        ordinal = ordinals.get(course_id, 0)
        ordinals[course_id] = ordinal + 1
        locator = (
            f"{row['source_path']} characters {row['char_start']}–{row['char_end']}"
        )
        chunk = DocumentChunk(
            id=str(row["cluster_id"]),
            document_id=str(row["source_artifact_id"]),
            text=str(row["text"]),
            ordinal=ordinal,
            source_artifact_id=str(row["source_artifact_id"]),
            source_version=int(row["source_version"]),
            source_label=SourceLabel.COURSE_APPROVED,
            locator=locator,
            source_checksum=str(row["source_sha256"]),
            retrieval_allowed=True,
            display_allowed=True,
            metadata={
                "title": str(row["section_heading"]),
                "course_id": course_id,
                "char_start": str(row["char_start"]),
                "char_end": str(row["char_end"]),
                "source_path": str(row["source_path"]),
            },
        )
        grouped.setdefault(course_id, []).append(chunk)
        by_id[chunk.id] = chunk
    return grouped, by_id


class _BoundedProductLlmClient:
    def __init__(
        self,
        *,
        transport: OpenAiCompatibleJsonTransport | DirectProviderJsonTransport,
        ledger: ProviderCallLedgerV1,
        flow_id: str,
        response_schema: dict[str, Any] | None = None,
        quarantine_failures: bool = False,
        forced_failure_case_ids: set[str] | None = None,
    ) -> None:
        self.transport = transport
        self.ledger = ledger
        self.flow_id = flow_id
        self.response_schema = response_schema or ATOMIC_RESPONSE_SCHEMA
        self.quarantine_failures = quarantine_failures
        self.forced_failure_case_ids = forced_failure_case_ids or set()

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        case_id = _CURRENT_CASE_ID.get()
        if not case_id:
            raise LiveT0AdapterError("provider call escaped the active evaluation case")
        if case_id in self.forced_failure_case_ids:
            raise LlmUnavailableError("frozen provider-failure injection")
        system = (
            "\n\n".join(row.content for row in messages if row.role == "system")
            or "Return only the requested grounded JSON object."
        )
        prompt = "\n\n".join(row.content for row in messages if row.role != "system")
        response = await self.transport.call_with_ledger(
            ledger=self.ledger,
            request_key=f"{self.flow_id}:{case_id}:generator",
            provider_role="product-generator",
            system=system,
            prompt=prompt,
            task=task,
            schema=self.response_schema,
            quarantine_failures=self.quarantine_failures,
        )
        return LlmResponse(
            content=json.dumps(response.content, sort_keys=True),
            provider_model=response.provider_model,
            provider_revision=response.provider_revision,
            usage=GenerationUsage(
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.input_tokens + response.output_tokens,
                approximate_cost_usd=response.cost_usd,
            ),
        )


def _generator_transport(
    manifest: SystemUnderTestManifestV1,
    runtime: dict[str, Any] | None = None,
) -> tuple[
    dict[str, Any],
    OpenAiCompatibleJsonTransport | DirectProviderJsonTransport,
]:
    """Resolve only an explicitly manifested historical or direct generator."""

    runtime = runtime or {}

    cross_engine_payload = runtime.get("product_engine_binding")
    if cross_engine_payload is not None:
        engine = ProductEngineBindingV1.model_validate(cross_engine_payload)
        if engine.provider == "deterministic":
            raise LiveT0AdapterError(
                "deterministic engine does not construct a provider transport"
            )
        model = engine.generator_model
        binding = {
            "binding_id": f"cross-engine-010-{engine.engine_id}-generator",
            "provider": "openai" if engine.provider == "openai-direct" else "deepseek",
            "provider_display_name": (
                "OpenAI" if engine.provider == "openai-direct" else "DeepSeek"
            ),
            "first_party_endpoint": True,
            "api_url": (
                "https://api.openai.com/v1/responses"
                if engine.provider == "openai-direct"
                else "https://api.deepseek.com/chat/completions"
            ),
            "credential_environment_variable": engine.credential_environment_variable,
            "provider_model": model,
            "documented_revision": engine.returned_identity_must_equal or model,
            "expected_provider_revision": (
                engine.returned_identity_must_equal
                if engine.provider == "openai-direct"
                else None
            ),
            "require_provider_revision": True,
            "reasoning_effort": engine.generator_reasoning_effort,
            "max_output_tokens": engine.maximum_output_tokens,
            "temperature": 0,
            "timeout_seconds": 45,
            "maximum_transport_retries": 0,
            "provider_user_id": "course-digital-twin-public-evaluation",
            "pricing_usd_per_million_input_tokens": (
                engine.input_price_usd_per_million
            ),
            "pricing_usd_per_million_output_tokens": (
                engine.output_price_usd_per_million
            ),
        }
        if engine.provider == "openai-direct":
            return binding, DirectProviderJsonTransport(binding)
        return binding, OpenAiCompatibleJsonTransport(binding)

    if manifest.generator == "deepseek-v4-flash-live-atomic":
        provider_binding = _load(HISTORICAL_BINDING_PATH)
        binding = deepcopy(provider_binding["providers"]["deepseek-v4-flash"])
        binding.update(
            {
                "binding_id": f"{binding['binding_id']}-product",
                "max_output_tokens": 600,
                "timeout_seconds": 15,
            }
        )
        return binding, OpenAiCompatibleJsonTransport(binding)
    if manifest.generator in {
        "openai-gpt-5.4-mini-live-atomic",
        "openai-gpt-5.4-mini-live-extractive-boundary",
        "openai-gpt-5.4-mini-question-targeted-atomic-v1",
        "openai-gpt-5.4-question-targeted-extraction-v2",
        "openai-responses-live-atomic-v2",
    }:
        candidate = runtime.get("model_candidate_manifest")
        if candidate is None:
            provider_binding = _load(OPENAI_BINDING_PATH)
            binding = deepcopy(provider_binding["providers"]["high-volume-generator"])
        else:
            if not isinstance(candidate, dict):
                raise LiveT0AdapterError("model candidate manifest is invalid")
            provider_model = str(candidate.get("provider_model", ""))
            allowed_models = OPENAI_PRODUCT_CANDIDATE_MODELS
            if manifest.generator == "openai-gpt-5.4-question-targeted-extraction-v2":
                allowed_models = (*allowed_models, OPENAI_SEMANTIC_REVIEW_MODEL)
            if provider_model not in allowed_models:
                raise LiveT0AdapterError("model candidate is not allowlisted")
            input_price, output_price = OPENAI_MODEL_PRICING_USD_PER_MILLION[
                provider_model
            ]
            binding = {
                "binding_id": f"r1-cascade-v2-{candidate['candidate_id']}",
                "provider": "openai",
                "provider_display_name": "OpenAI",
                "first_party_endpoint": True,
                "api_url": "https://api.openai.com/v1/responses",
                "credential_environment_variable": "OPENAI_API_KEY",
                "provider_model": provider_model,
                "documented_revision": provider_model,
                "reasoning_effort": candidate["reasoning_effort"],
                "max_output_tokens": int(candidate["max_output_tokens"]),
                "temperature": 0,
                "seed": 20260829,
                "timeout_seconds": 45,
                "maximum_transport_retries": 1,
                "pricing_usd_per_million_input_tokens": input_price,
                "pricing_usd_per_million_output_tokens": output_price,
            }
        if (
            not isinstance(binding.get("binding_id"), str)
            or not binding["binding_id"].strip()
        ):
            raise LiveT0AdapterError(
                "OpenAI generator binding lacks a nested binding_id"
            )
        binding.update(
            {
                "binding_id": f"{binding['binding_id']}-product",
                "max_output_tokens": int(binding.get("max_output_tokens", 600)),
                "timeout_seconds": float(binding.get("timeout_seconds", 30)),
            }
        )
        return binding, DirectProviderJsonTransport(binding)
    raise LiveT0AdapterError("system manifest generator drifted")


class _RecordingGate:
    def __init__(self, gate: Any) -> None:
        self.gate = gate
        self.implementation_id = gate.implementation_id
        self.hits_by_case: dict[str, list[RetrievalHit]] = {}

    def assess(self, query: str, hits: list[RetrievalHit]):
        case_id = _CURRENT_CASE_ID.get()
        if case_id:
            self.hits_by_case[case_id] = list(hits)
        return self.gate.assess(query, hits)


class _RecordingGenerator:
    implementation_id = "recording-live-atomic-grounded-generator-v1"
    version = "v1"

    def __init__(self, generator: Any) -> None:
        self.generator = generator
        self.answers_by_case: dict[str, TutorAnswer] = {}

    async def generate(
        self, question: str, hits: list[RetrievalHit], policy: Any
    ) -> TutorAnswer:
        answer = await self.generator.generate(question, hits, policy)
        case_id = _CURRENT_CASE_ID.get()
        if case_id:
            self.answers_by_case[case_id] = answer.model_copy(deep=True)
        return answer

    async def generate_for_intent(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: Any,
        *,
        intent: str,
        help_level: int,
        repair_reason: str | None = None,
    ) -> TutorAnswer:
        generate = getattr(self.generator, "generate_for_intent", None)
        if not callable(generate):
            raise LiveT0AdapterError("T1 generator lacks intent-aware generation")
        answer = await generate(
            question,
            hits,
            policy,
            intent=intent,
            help_level=help_level,
            repair_reason=repair_reason,
        )
        case_id = _CURRENT_CASE_ID.get()
        if case_id:
            self.answers_by_case[case_id] = answer.model_copy(deep=True)
        return answer


class _DeterministicAtomicGenerator:
    """Deterministic E0 baseline with explicit exact-quote claim lineage."""

    implementation_id = "deterministic-atomic-grounded-generator-v1"
    version = "v1"

    def __init__(self, *, policy_enforcer: DeterministicPolicyEnforcer) -> None:
        self.delegate = DeterministicGroundedGenerator(
            prompt_builder=ExtractiveBoundaryGroundedPromptBuilder(),
            policy_enforcer=policy_enforcer,
        )

    async def generate(self, question, hits, policy):
        return self._attach(await self.delegate.generate(question, hits, policy), hits)

    async def generate_for_intent(
        self,
        question,
        hits,
        policy,
        *,
        intent,
        help_level,
        repair_reason=None,
    ):
        answer = await self.delegate.generate_for_intent(
            question,
            hits,
            policy,
            intent=intent,
            help_level=help_level,
            repair_reason=repair_reason,
        )
        return self._attach(answer, hits)

    @staticmethod
    def _attach(answer: TutorAnswer, hits: list[RetrievalHit]) -> TutorAnswer:
        if answer.atomic_claims or not hits or answer.trace is None:
            return answer
        if answer.trace.policy_action != "answer":
            return answer
        return answer.model_copy(
            update={
                "atomic_claims": [
                    AtomicAnswerClaim(
                        claim_id="claim-deterministic-evidence",
                        text=hits[0].chunk.text,
                        evidence_hit_ids=[hits[0].chunk.id],
                    )
                ]
            }
        )

class _ManagedAdapter(StudentTutoringServiceAdapterV1):
    def __init__(
        self,
        *,
        provider_ledger: ProviderCallLedgerV1,
        repository: SQLiteStudentRepository,
        maximum_quarantined_failures: int | None = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.provider_ledger = provider_ledger
        self.repository = repository
        self.maximum_quarantined_failures = maximum_quarantined_failures
        self._closed = False

    def validate_completion(self) -> None:
        snapshot = self.provider_ledger.snapshot()
        too_many_failures = (
            self.maximum_quarantined_failures is not None
            and int(snapshot.get("failed_calls", 0)) > self.maximum_quarantined_failures
        )
        if snapshot.get("status") != "running" or too_many_failures:
            raise LiveT0AdapterError(
                "product provider ledger is not valid for completion"
            )

    def finalize(self) -> None:
        self.provider_ledger.mark_complete()
        self.provider_ledger.close()
        self.repository.close()
        self._closed = True

    def interrupt(self) -> None:
        if self._closed:
            return
        try:
            if self.provider_ledger.snapshot().get("status") == "running":
                self.provider_ledger.mark_interrupted()
        finally:
            self.provider_ledger.close()
            self.repository.close()
            self._closed = True


class _ManagedDeterministicAdapter(StudentTutoringServiceAdapterV1):
    """Lifecycle wrapper for the zero-provider E0 factual baseline."""

    def __init__(self, *, repository: SQLiteStudentRepository, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.repository = repository
        self._closed = False

    def validate_completion(self) -> None:
        return None

    def finalize(self) -> None:
        if not self._closed:
            self.repository.close()
            self._closed = True

    def interrupt(self) -> None:
        self.finalize()


def _setup_service(
    *,
    chunks_by_course: dict[str, list[DocumentChunk]],
    generator: _RecordingGenerator,
    gate: _RecordingGate,
    database_path: Path,
    index_root: Path,
    claim_evidence_validator: Any,
    tutoring_mode: str = "grounded-assistant",
    conversation_courses: dict[str, str] | None = None,
) -> tuple[SQLiteStudentRepository, StudentTutoringService, dict[str, str]]:
    repository = SQLiteStudentRepository(database_path)
    profile = _load(PROFILE_PATH)
    professor_id = "academic-open-professor"
    student_id = "academic-open-student"
    repository.save_account(Account(id=professor_id, role=AccountRole.PROFESSOR))
    repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
    for course_id, chunks in chunks_by_course.items():
        repository.save_course(
            Course(
                id=course_id,
                title=course_id.replace("-", " ").title(),
                owner_professor_id=professor_id,
            )
        )
        repository.save_membership(
            CourseMembership(
                account_id=professor_id,
                course_id=course_id,
                role=MembershipRole.PROFESSOR,
            )
        )
        repository.save_membership(
            CourseMembership(
                account_id=student_id,
                course_id=course_id,
                role=MembershipRole.STUDENT,
            )
        )
        repository.save_release(
            DigitalTwinRelease(
                id=f"{course_id}-academic-open-release",
                course_id=course_id,
                profile_id=str(profile["profile_id"]),
                profile_version=str(profile["profile_version"]),
                policy_version=1,
                policy=approved_synthetic_policy(),
                chunks=chunks,
                status=StudentReleaseStatus.PUBLISHED,
                evaluation_status=ReleaseEvaluationStatus.PASSED,
            )
        )
    retriever = next(
        row for row in profile["components"] if row["component"] == "retriever"
    )["implementation"]["configuration"]
    revision = str(retriever["embedding_revision"])
    chunker = next(
        row for row in profile["components"] if row["component"] == "chunker"
    )["implementation"]
    index_store = RetrievalIndexStoreV1(index_root)
    for course_id, course_chunks in chunks_by_course.items():
        release_id = f"{course_id}-academic-open-release"
        index_binding = build_retrieval_index_binding(
            course_id=course_id,
            release_id=release_id,
            profile_id=str(profile["profile_id"]),
            profile_version=str(profile["profile_version"]),
            chunker_id=str(chunker["implementation_id"]),
            chunker_version=str(chunker["version"]),
            chunks=course_chunks,
            configuration=retriever,
        )
        index_store.verify_bound(index_binding)
    model_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_QWEN_MODEL_ROOT",
            str(
                ROOT / "data/external/huggingface/hub/"
                "models--Qwen--Qwen3-Embedding-0.6B/snapshots"
            ),
        )
    )
    embedder = Qwen3TextEmbedder(
        model_root / revision,
        instruction=str(retriever["query_instruction"]),
        device=str(retriever["device"]),
        dtype=str(retriever["dtype"]),
        batch_size=int(retriever["embedding_batch_size"]),
        max_length=int(retriever["embedding_max_length"]),
        model_revision=revision,
    )
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        embedder=embedder,
        generator=generator,
        evidence_gate=gate,
        claim_evidence_validator=claim_evidence_validator,
        tutoring_mode=tutoring_mode,
        retrieval_index_store=index_store,
        retrieval_index_chunker_id=str(chunker["implementation_id"]),
        retrieval_index_chunker_version=str(chunker["version"]),
    )
    requested = conversation_courses or {
        course_id: course_id for course_id in chunks_by_course
    }
    conversations = {
        key: service.create_conversation(student_id, course_id).id
        for key, course_id in sorted(requested.items())
    }
    return repository, service, conversations


def _setup_precomputed_service(
    *,
    chunks_by_course: dict[str, list[DocumentChunk]],
    generator: _RecordingGenerator,
    gate: _RecordingGate,
    database_path: Path,
    claim_evidence_validator: Any,
    tutoring_mode: str,
    conversation_courses: dict[str, str] | None,
) -> tuple[SQLiteStudentRepository, StudentTutoringService, dict[str, str]]:
    """Build a product service that consumes only precomputed retrieval rows."""

    repository = SQLiteStudentRepository(database_path)
    profile = _load(PROFILE_PATH)
    professor_id = "academic-open-professor"
    student_id = "academic-open-student"
    repository.save_account(Account(id=professor_id, role=AccountRole.PROFESSOR))
    repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
    for course_id, chunks in chunks_by_course.items():
        repository.save_course(
            Course(
                id=course_id,
                title=course_id.replace("-", " ").title(),
                owner_professor_id=professor_id,
            )
        )
        for account_id, role in (
            (professor_id, MembershipRole.PROFESSOR),
            (student_id, MembershipRole.STUDENT),
        ):
            repository.save_membership(
                CourseMembership(account_id=account_id, course_id=course_id, role=role)
            )
        repository.save_release(
            DigitalTwinRelease(
                id=f"{course_id}-academic-open-release",
                course_id=course_id,
                profile_id=str(profile["profile_id"]),
                profile_version=str(profile["profile_version"]),
                policy_version=1,
                policy=approved_synthetic_policy(),
                chunks=chunks,
                status=StudentReleaseStatus.PUBLISHED,
                evaluation_status=ReleaseEvaluationStatus.PASSED,
            )
        )
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        generator=generator,
        evidence_gate=gate,
        claim_evidence_validator=claim_evidence_validator,
        tutoring_mode=tutoring_mode,
    )
    requested = conversation_courses or {
        course_id: course_id for course_id in chunks_by_course
    }
    conversations = {
        key: service.create_conversation(student_id, course_id).id
        for key, course_id in sorted(requested.items())
    }
    return repository, service, conversations


def build_live_t0_adapter(
    *,
    manifest: SystemUnderTestManifestV1,
    cases: list[EvaluationCaseV1],
    runtime: dict[str, Any],
) -> StudentTutoringServiceAdapterV1:
    engine_payload = runtime.get("product_engine_binding")
    engine = (
        ProductEngineBindingV1.model_validate(engine_payload)
        if engine_payload is not None
        else None
    )
    deterministic_engine = engine is not None and engine.provider == "deterministic"
    generator_binding = None
    generator_transport = None
    if not deterministic_engine:
        generator_binding, generator_transport = _generator_transport(manifest, runtime)
    flow_id = manifest.flow_id
    if manifest.evidence_gate in {
        "structured-lexical-coverage-evidence-gate-v1",
        "structured-hierarchical-coverage-evidence-gate-v1",
        "question-targeted-atomic-evidence-gate-v1",
        "ambiguity-safe-source-semantic-evidence-atoms-v2",
    }:
        condition = "candidate"
    elif manifest.evidence_gate in {
        "any-hit-evidence-gate-v1",
        "source-semantic-evidence-atoms-v1",
    }:
        condition = "control"
    else:
        raise LiveT0AdapterError("system manifest evidence gate is unsupported")
    maximum_calls = int(runtime.get("maximum_calls", PRODUCT_MAXIMUM_CALLS[condition]))
    maximum_cost = float(
        runtime.get("maximum_cost_usd", PRODUCT_MAXIMUM_COST_USD[condition])
    )
    cascade_v2 = (
        runtime.get("model_candidate_manifest") is not None or engine is not None
    )
    targeted_generator = manifest.generator == (
        "openai-gpt-5.4-mini-question-targeted-atomic-v1"
    )
    extraction_generator = manifest.generator == (
        "openai-gpt-5.4-question-targeted-extraction-v2"
    )
    if extraction_generator:
        response_schema = ATOMIC_RESPONSE_SCHEMA
        live_generator = LiveQuestionTargetedExtractionGroundedGenerator
        prompt_builder = QuestionTargetedExtractionPromptBuilder()
        claim_evidence_validator = AtomicClaimEvidenceValidator(
            ContiguousQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
            maximum_claims=8,
            evidence_limit=5,
        )
    elif targeted_generator or manifest.generator in {
        "openai-gpt-5.4-mini-live-extractive-boundary",
        "openai-responses-live-atomic-v2",
        "cross-engine-live-extractive-boundary-v1",
    }:
        response_schema = EXTRACTIVE_BOUNDARY_RESPONSE_SCHEMA
        live_generator = LiveExtractiveBoundaryGroundedGenerator
        prompt_builder = ExtractiveBoundaryGroundedPromptBuilder()
        claim_evidence_validator = AtomicClaimEvidenceValidator(
            ContiguousQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
            maximum_claims=8,
            evidence_limit=5,
        )
    else:
        response_schema = ATOMIC_RESPONSE_SCHEMA
        live_generator = LiveAtomicGroundedGenerator
        prompt_builder = StrictEvidenceGroundedPromptBuilder()
        claim_evidence_validator = AtomicClaimEvidenceValidator(
            NliAtomicClaimVerifier(
                LocalNliCrossEncoderBackend(
                    model_id="cross-encoder/nli-deberta-v3-base",
                    revision="6c749ce3425cd33b46d187e45b92bbf96ee12ec7",
                    local_files_only=True,
                )
            ),
            minimum_entailment=0.8,
            maximum_contradiction=0.2,
            maximum_claims=8,
            evidence_limit=5,
        )
    provider_ledger = None
    action_router = (
        DeterministicActionRouterV2()
        if manifest.evidence_gate
        == "ambiguity-safe-source-semantic-evidence-atoms-v2"
        else DeterministicActionRouterV1()
    )
    if deterministic_engine:
        generator_impl = _DeterministicAtomicGenerator(
            policy_enforcer=DeterministicPolicyEnforcer(action_router=action_router)
        )
    else:
        if generator_binding is None or generator_transport is None:
            raise LiveT0AdapterError("provider-backed engine lacks transport binding")
        provider_ledger = ProviderCallLedgerV1(
            Path(runtime["provider_ledger_path"]),
            run_binding={
                "instrument_id": runtime["instrument_id"],
                "flow_id": flow_id,
                "manifest": manifest.model_dump(mode="json"),
                "binding": generator_binding,
                "cases_sha256": runtime["cases_sha256"],
                "code_revision": runtime["code_revision"],
            },
            maximum_calls=maximum_calls,
            maximum_cost_usd=maximum_cost,
            resume=bool(runtime["resume"]),
            maximum_transport_retries_total=(
                maximum_calls * 2 // 100 if cascade_v2 else None
            ),
        )
        client = _BoundedProductLlmClient(
            transport=generator_transport,
            ledger=provider_ledger,
            flow_id=flow_id,
            response_schema=response_schema,
            quarantine_failures=cascade_v2,
            forced_failure_case_ids=set(runtime.get("forced_failure_case_ids", [])),
        )
        if extraction_generator:
            generator_impl = LiveQuestionTargetedExtractionGroundedGenerator(
                client,
                prompt_builder=QuestionTargetedExtractionPromptBuilder(),
                policy_enforcer=DeterministicPolicyEnforcer(
                    action_router=action_router
                ),
            )
        elif targeted_generator:
            generator_impl = LiveQuestionTargetedAtomicGroundedGenerator(
                client,
                prompt_builder=QuestionTargetedAtomicPromptBuilder(),
                policy_enforcer=DeterministicPolicyEnforcer(
                    action_router=action_router
                ),
            )
        else:
            generator_impl = live_generator(
                client,
                prompt_builder=prompt_builder,
                policy_enforcer=DeterministicPolicyEnforcer(
                    action_router=action_router
                ),
            )
    recording_generator = _RecordingGenerator(generator_impl)
    if manifest.evidence_gate == "ambiguity-safe-source-semantic-evidence-atoms-v2":
        evidence_gate = SourceSemanticEvidenceAtomGateV2()
    elif manifest.evidence_gate == "source-semantic-evidence-atoms-v1":
        evidence_gate = SourceSemanticEvidenceAtomGateV1()
    elif manifest.evidence_gate == "question-targeted-atomic-evidence-gate-v1":
        evidence_gate = QuestionTargetedAtomicEvidenceGate()
    elif manifest.evidence_gate == "structured-hierarchical-coverage-evidence-gate-v1":
        evidence_gate = StructuredHierarchicalCoverageEvidenceGate()
    elif condition == "candidate":
        evidence_gate = StructuredLexicalCoverageEvidenceGate()
    else:
        evidence_gate = AnyHitEvidenceGate()
    gate = _RecordingGate(evidence_gate)
    source_path_value = runtime.get("source_package_path")
    source_path = Path(str(source_path_value)) if source_path_value else None
    chunks_by_course, chunks_by_id = _chunks_by_course(source_path)
    state_path = Path(runtime["state_path"])
    tutoring_mode = str(runtime.get("tutoring_mode", "grounded-assistant"))
    conversation_scope = str(runtime.get("conversation_scope", "course"))
    if conversation_scope not in {"course", "cluster"}:
        raise LiveT0AdapterError("unsupported evaluation conversation scope")
    conversation_courses = (
        {case.cluster_id: case.course_id for case in cases}
        if conversation_scope == "cluster"
        else None
    )
    precomputed_path_value = runtime.get("precomputed_retrieval_path")
    if precomputed_path_value is not None:
        repository, service, conversations = _setup_precomputed_service(
            chunks_by_course=chunks_by_course,
            generator=recording_generator,
            gate=gate,
            database_path=state_path,
            claim_evidence_validator=claim_evidence_validator,
            tutoring_mode=tutoring_mode,
            conversation_courses=conversation_courses,
        )
    else:
        repository, service, conversations = _setup_service(
            chunks_by_course=chunks_by_course,
            generator=recording_generator,
            gate=gate,
            database_path=state_path,
            index_root=RETRIEVAL_INDEX_ROOT,
            claim_evidence_validator=claim_evidence_validator,
            tutoring_mode=tutoring_mode,
            conversation_courses=conversation_courses,
        )
    if precomputed_path_value is not None:
        precomputed_path = Path(str(precomputed_path_value))
        payload = _load(precomputed_path)
        rankings = payload.get("ranked_chunk_ids")
        if (
            payload.get("schema_version") != 1
            or payload.get("program_id") != runtime["instrument_id"]
            or not isinstance(rankings, dict)
            or payload.get("content_sha256")
            != canonical_json_sha256(
                {
                    key: value
                    for key, value in payload.items()
                    if key != "content_sha256"
                }
            )
        ):
            raise LiveT0AdapterError("precomputed retrieval package is invalid")
        expected_case_ids = {case.case_id for case in cases}
        if set(rankings) != expected_case_ids:
            raise LiveT0AdapterError("precomputed retrieval case identities drifted")
        normalized_rankings: dict[str, list[str]] = {}
        for case_id, identifiers in rankings.items():
            if not isinstance(identifiers, list) or not all(
                isinstance(identifier, str) for identifier in identifiers
            ):
                raise LiveT0AdapterError("precomputed retrieval ranking is malformed")
            normalized_rankings[str(case_id)] = list(identifiers)
        for course_id, course_chunks in chunks_by_course.items():
            release_id = f"{course_id}-academic-open-release"
            scoped = {
                case.case_id: normalized_rankings[case.case_id]
                for case in cases
                if case.course_id == course_id
            }
            service._retrievers[release_id] = CaseBoundPrecomputedRetriever(
                chunks=course_chunks,
                ranked_chunk_ids=scoped,
                current_case_id=_CURRENT_CASE_ID.get,
            )

    async def execute_turn(case: EvaluationCaseV1):
        conversation_key = (
            case.cluster_id if conversation_scope == "cluster" else case.course_id
        )
        if conversation_key not in conversations:
            raise LiveT0AdapterError("evaluation case references an unknown course")
        token = _CURRENT_CASE_ID.set(case.case_id)
        try:
            return await service.submit_message(
                "academic-open-student",
                conversations[conversation_key],
                content=case.question,
                client_request_id=f"{flow_id}:{case.case_id}",
            )
        finally:
            _CURRENT_CASE_ID.reset(token)

    def resolve_citation(row: Any) -> EvaluationCitationV1:
        matching = [
            chunk
            for chunk in chunks_by_id.values()
            if chunk.source_artifact_id == row.source_artifact_id
            and chunk.locator == row.locator
        ]
        if len(matching) != 1:
            raise LiveT0AdapterError("released citation cannot map to one source range")
        return _evaluation_citation(matching[0])

    def resolve_retrieved(
        case: EvaluationCaseV1, _turn: Any
    ) -> list[EvaluationCitationV1]:
        return [
            _evaluation_citation(hit.chunk)
            for hit in gate.hits_by_case.get(case.case_id, [])
        ]

    def resolve_claims(
        case: EvaluationCaseV1, turn: Any
    ) -> list[EvaluationAtomicClaimV1]:
        if turn.tutor_message.action != "answer":
            return []
        answer = recording_generator.answers_by_case.get(case.case_id)
        if answer is None:
            raise LiveT0AdapterError("released answer lacks recorded atomic claims")
        return [
            EvaluationAtomicClaimV1(
                text=claim.text,
                citations=[
                    _evaluation_citation(chunks_by_id[hit_id])
                    for hit_id in claim.evidence_hit_ids
                ],
            )
            for claim in answer.atomic_claims
        ]

    adapter_kwargs = {
        "flow_id": flow_id,
        "execute_turn": execute_turn,
        "resolve_citation": resolve_citation,
        "resolve_claims": resolve_claims,
        "resolve_retrieved": resolve_retrieved,
        "repository": repository,
    }
    if deterministic_engine:
        return _ManagedDeterministicAdapter(**adapter_kwargs)
    if provider_ledger is None:
        raise LiveT0AdapterError("provider-backed adapter lacks a provider ledger")
    return _ManagedAdapter(
        provider_ledger=provider_ledger,
        **adapter_kwargs,
        # Evaluation-v2 persists every failed provider response as an explicit
        # operational-failure case. Completion and malformed-response rates are
        # quality metrics; an individual failure is not a corrupt execution.
        maximum_quarantined_failures=(None if cascade_v2 else 0),
    )
