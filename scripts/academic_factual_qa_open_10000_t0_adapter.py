"""Concrete live T0 adapter for the flow-independent open benchmark."""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from services.embeddings import Qwen3TextEmbedder
from src.digital_twin.evaluation.factual_qa_adapters import (
    StudentTutoringServiceAdapterV1,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    OpenAiCompatibleJsonTransport,
    ProviderCallLedgerV1,
)
from src.digital_twin.generation import (
    LiveAtomicGroundedGenerator,
    StrictEvidenceGroundedPromptBuilder,
)
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    AtomicClaimEvidenceValidator,
    DocumentChunk,
    LocalNliCrossEncoderBackend,
    NliAtomicClaimVerifier,
    RetrievalHit,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.grounding.models import GenerationUsage, TutorAnswer
from src.digital_twin.llm import LlmMessage, LlmResponse
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


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = (
    ROOT
    / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)
SOURCE_PLAN_PATH = ROOT / "data/processed/academic_factual_qa_open_10000_v1_sources.json"
HISTORICAL_BINDING_PATH = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_provider_binding_003.json"
)
OPENAI_BINDING_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
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
        raise LiveT0AdapterError("retrieved chunk lacks canonical character lineage") from error
    return EvaluationCitationV1(
        source_artifact_id=chunk.source_artifact_id or chunk.document_id,
        source_version=chunk.source_version,
        source_sha256=chunk.source_checksum,
        char_start=char_start,
        char_end=char_end,
        region_id=chunk.region_id,
    )


def _chunks_by_course() -> tuple[dict[str, list[DocumentChunk]], dict[str, DocumentChunk]]:
    plan = _load(SOURCE_PLAN_PATH)
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
    ) -> None:
        self.transport = transport
        self.ledger = ledger
        self.flow_id = flow_id

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        case_id = _CURRENT_CASE_ID.get()
        if not case_id:
            raise LiveT0AdapterError("provider call escaped the active evaluation case")
        system = "\n\n".join(
            row.content for row in messages if row.role == "system"
        ) or "Return only the requested grounded JSON object."
        prompt = "\n\n".join(
            row.content for row in messages if row.role != "system"
        )
        response = await self.transport.call_with_ledger(
            ledger=self.ledger,
            request_key=f"{self.flow_id}:{case_id}:generator",
            provider_role="product-generator",
            system=system,
            prompt=prompt,
            task=task,
            schema=ATOMIC_RESPONSE_SCHEMA,
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
) -> tuple[
    dict[str, Any],
    OpenAiCompatibleJsonTransport | DirectProviderJsonTransport,
]:
    """Resolve only an explicitly manifested historical or direct generator."""

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
    if manifest.generator == "openai-gpt-5.4-mini-live-atomic":
        provider_binding = _load(OPENAI_BINDING_PATH)
        binding = deepcopy(provider_binding["providers"]["high-volume-generator"])
        binding.update(
            {
                "binding_id": f"{binding['binding_id']}-product",
                "max_output_tokens": 600,
                "timeout_seconds": 30,
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

    def __init__(self, generator: LiveAtomicGroundedGenerator) -> None:
        self.generator = generator
        self.answers_by_case: dict[str, TutorAnswer] = {}

    async def generate(self, question: str, hits: list[RetrievalHit], policy: Any) -> TutorAnswer:
        answer = await self.generator.generate(question, hits, policy)
        case_id = _CURRENT_CASE_ID.get()
        if case_id:
            self.answers_by_case[case_id] = answer.model_copy(deep=True)
        return answer


class _ManagedAdapter(StudentTutoringServiceAdapterV1):
    def __init__(
        self,
        *,
        provider_ledger: ProviderCallLedgerV1,
        repository: SQLiteStudentRepository,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.provider_ledger = provider_ledger
        self.repository = repository
        self._closed = False

    def validate_completion(self) -> None:
        snapshot = self.provider_ledger.snapshot()
        if snapshot.get("status") != "running" or snapshot.get("failed_calls"):
            raise LiveT0AdapterError("product provider ledger is not valid for completion")

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


def _setup_service(
    *,
    chunks_by_course: dict[str, list[DocumentChunk]],
    generator: _RecordingGenerator,
    gate: _RecordingGate,
    database_path: Path,
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
    embedder = Qwen3TextEmbedder(
        ROOT
        / "data/external/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/snapshots"
        / revision,
        instruction=str(retriever["query_instruction"]),
        device=str(retriever["device"]),
        dtype=str(retriever["dtype"]),
        batch_size=int(retriever["embedding_batch_size"]),
        max_length=int(retriever["embedding_max_length"]),
        model_revision=revision,
    )
    validator = AtomicClaimEvidenceValidator(
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
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        embedder=embedder,
        generator=generator,
        evidence_gate=gate,
        claim_evidence_validator=validator,
        tutoring_mode="grounded-assistant",
    )
    conversations = {
        course_id: service.create_conversation(student_id, course_id).id
        for course_id in chunks_by_course
    }
    return repository, service, conversations


def build_live_t0_adapter(
    *,
    manifest: SystemUnderTestManifestV1,
    cases: list[EvaluationCaseV1],
    runtime: dict[str, Any],
) -> StudentTutoringServiceAdapterV1:
    del cases
    generator_binding, generator_transport = _generator_transport(manifest)
    flow_id = manifest.flow_id
    condition = "candidate" if "candidate" in flow_id else "control"
    maximum_calls = PRODUCT_MAXIMUM_CALLS[condition]
    maximum_cost = PRODUCT_MAXIMUM_COST_USD[condition]
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
    )
    client = _BoundedProductLlmClient(
        transport=generator_transport,
        ledger=provider_ledger,
        flow_id=flow_id,
    )
    recording_generator = _RecordingGenerator(
        LiveAtomicGroundedGenerator(
            client,
            prompt_builder=StrictEvidenceGroundedPromptBuilder(),
        )
    )
    gate = _RecordingGate(
        StructuredLexicalCoverageEvidenceGate()
        if "candidate" in flow_id
        else AnyHitEvidenceGate()
    )
    chunks_by_course, chunks_by_id = _chunks_by_course()
    state_path = Path(runtime["state_path"])
    repository, service, conversations = _setup_service(
        chunks_by_course=chunks_by_course,
        generator=recording_generator,
        gate=gate,
        database_path=state_path,
    )

    async def execute_turn(case: EvaluationCaseV1):
        if case.course_id not in conversations:
            raise LiveT0AdapterError("evaluation case references an unknown course")
        token = _CURRENT_CASE_ID.set(case.case_id)
        try:
            return await service.submit_message(
                "academic-open-student",
                conversations[case.course_id],
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

    def resolve_retrieved(case: EvaluationCaseV1, _turn: Any) -> list[EvaluationCitationV1]:
        return [_evaluation_citation(hit.chunk) for hit in gate.hits_by_case.get(case.case_id, [])]

    def resolve_claims(case: EvaluationCaseV1, turn: Any) -> list[EvaluationAtomicClaimV1]:
        if turn.tutor_message.action != "answer":
            return []
        answer = recording_generator.answers_by_case.get(case.case_id)
        if answer is None:
            raise LiveT0AdapterError("released answer lacks recorded atomic claims")
        return [
            EvaluationAtomicClaimV1(
                text=claim.text,
                citations=[_evaluation_citation(chunks_by_id[hit_id]) for hit_id in claim.evidence_hit_ids],
            )
            for claim in answer.atomic_claims
        ]

    return _ManagedAdapter(
        flow_id=flow_id,
        execute_turn=execute_turn,
        resolve_citation=resolve_citation,
        resolve_claims=resolve_claims,
        resolve_retrieved=resolve_retrieved,
        provider_ledger=provider_ledger,
        repository=repository,
    )
