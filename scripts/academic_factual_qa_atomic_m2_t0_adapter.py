"""Actual StudentTutoringService adapter over the selected atomic-M2 index."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from scripts import academic_factual_qa_open_10000_t0_adapter as base
from scripts.run_academic_factual_qa_api_retrieval_selection import (
    _CachedQueryEmbedder,
    _unpack_vector,
)
from src.digital_twin.evaluation.factual_qa_adapters import StudentTutoringServiceAdapterV1
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.action_router import DeterministicActionRouterV1
from src.digital_twin.generation import (
    DeterministicPolicyEnforcer,
    ExtractiveBoundaryGroundedPromptBuilder,
    LiveExtractiveBoundaryGroundedGenerator,
    LiveQuestionTargetedAtomicGroundedGenerator,
    QuestionTargetedAtomicPromptBuilder,
)
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    AtomicClaimEvidenceValidator,
    ContiguousQuoteAtomicClaimVerifier,
    DocumentChunk,
    QuestionTargetedAtomicEvidenceGate,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.grounding.api_retrieval_index import (
    ApiRetrievalIndexBindingV2,
    StreamingRetrievalIndexMaterializerV2,
)
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


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "research/05_evaluation/datasets/academic-factual-qa-atomic-m2-confirmation-001-sources.json"
RETRIEVAL_RUNTIME_PATH = ROOT / "research/05_evaluation/instruments/academic_factual_qa_atomic_m2_product_retrieval_runtime_001.json"
ACTION_ROUTER_SOURCE_PATH = ROOT / "research/05_evaluation/datasets/academic-factual-qa-action-router-confirmation-001-sources.json"
ACTION_ROUTER_RETRIEVAL_RUNTIME_PATH = ROOT / "reports/generated/academic-factual-qa-action-router-product-checkpoint-001/retrieval-runtime.json"
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"


class AtomicM2ProductAdapterError(RuntimeError):
    """Raised when the selected retrieval/product boundary drifts."""


def _load_hashed(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != expected:
        raise AtomicM2ProductAdapterError(f"content hash drifted: {path.name}")
    return payload


def _chunks_by_course(
    source_path: Path = SOURCE_PATH,
) -> tuple[dict[str, list[DocumentChunk]], dict[str, DocumentChunk]]:
    payload = _load_hashed(source_path)
    chunks = [DocumentChunk.model_validate(row) for row in payload["chunks"]]
    grouped: dict[str, list[DocumentChunk]] = {}
    by_id: dict[str, DocumentChunk] = {}
    for chunk in chunks:
        course_id = str(chunk.metadata.get("course_id", ""))
        if not course_id:
            raise AtomicM2ProductAdapterError("atomic chunk lacks course identity")
        grouped.setdefault(course_id, []).append(chunk)
        by_id[chunk.id] = chunk
    if len(chunks) != 300 or len(grouped) != 4 or len(by_id) != 300:
        raise AtomicM2ProductAdapterError("atomic source portfolio drifted")
    return grouped, by_id


def _query_embedder(
    cases: list[EvaluationCaseV1],
    runtime_path: Path = RETRIEVAL_RUNTIME_PATH,
) -> _CachedQueryEmbedder:
    runtime = _load_hashed(runtime_path)
    query_cache = ROOT / runtime["query_cache"]["path"]
    if hashlib.sha256(query_cache.read_bytes()).hexdigest() != runtime["query_cache"]["file_sha256"]:
        raise AtomicM2ProductAdapterError("atomic query cache file drifted")
    connection = sqlite3.connect(f"file:{query_cache}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        rows = list(
            connection.execute(
                "SELECT case_id,question_sha256,vector_blob,vector_sha256 "
                "FROM vectors ORDER BY case_id"
            )
        )
    finally:
        connection.close()
    if (
        metadata.get("schema_version") != "1"
        or metadata.get("model") != runtime["query_cache"]["model"]
        or metadata.get("dimensions") != str(runtime["query_cache"]["dimensions"])
        or len(rows) != runtime["query_cache"]["vector_count"]
    ):
        raise AtomicM2ProductAdapterError("atomic query cache binding drifted")
    question_by_id = {row.case_id: row.question for row in cases}
    vectors: dict[str, list[float]] = {}
    for case_id, question_sha256, vector_blob, vector_sha256 in rows:
        question = question_by_id.get(case_id)
        if question is None:
            continue
        if (
            hashlib.sha256(question.encode()).hexdigest() != question_sha256
            or hashlib.sha256(vector_blob).hexdigest() != vector_sha256
        ):
            raise AtomicM2ProductAdapterError("atomic query vector drifted")
        vectors[question] = _unpack_vector(vector_blob)
    if any(case.question not in vectors for case in cases):
        raise AtomicM2ProductAdapterError("product question escaped frozen query cache")
    return _CachedQueryEmbedder(
        model="text-embedding-3-small", dimensions=1536, vectors=vectors
    )


def _retrievers(
    *,
    chunks_by_course: dict[str, list[DocumentChunk]],
    embedder: _CachedQueryEmbedder,
    runtime_path: Path = RETRIEVAL_RUNTIME_PATH,
) -> dict[str, Any]:
    runtime = _load_hashed(runtime_path)
    index_root = ROOT / runtime["index_root"]
    store = StreamingRetrievalIndexMaterializerV2(index_root)
    loaded: dict[str, Any] = {}
    for course_id, chunks in sorted(chunks_by_course.items()):
        course = runtime["courses"].get(course_id)
        if not isinstance(course, dict):
            raise AtomicM2ProductAdapterError("atomic runtime course drifted")
        binding = ApiRetrievalIndexBindingV2.model_validate(course["binding"])
        loaded[course_id] = store.load(
            str(course["artifact_id"]), expected_binding=binding, embedder=embedder
        ).retriever
    return loaded


def _setup_service(
    *,
    chunks_by_course: dict[str, list[DocumentChunk]],
    retrievers: dict[str, Any],
    generator: base._RecordingGenerator,  # noqa: SLF001
    gate: base._RecordingGate,  # noqa: SLF001
    database_path: Path,
) -> tuple[SQLiteStudentRepository, StudentTutoringService, dict[str, str]]:
    repository = SQLiteStudentRepository(database_path)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    professor_id = "atomic-product-professor"
    student_id = "atomic-product-student"
    repository.save_account(Account(id=professor_id, role=AccountRole.PROFESSOR))
    repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
    for course_id, chunks in sorted(chunks_by_course.items()):
        repository.save_course(
            Course(id=course_id, title=course_id, owner_professor_id=professor_id)
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
                id=f"{course_id}-atomic-product-release",
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
        claim_evidence_validator=AtomicClaimEvidenceValidator(
            ContiguousQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
            maximum_claims=8,
            evidence_limit=5,
        ),
        tutoring_mode="grounded-assistant",
    )
    for course_id, retriever_instance in retrievers.items():
        service._retrievers[f"{course_id}-atomic-product-release"] = retriever_instance  # noqa: SLF001
    return repository, service, {"student_id": student_id}


def build_atomic_m2_t0_adapter(
    *,
    manifest: SystemUnderTestManifestV1,
    cases: list[EvaluationCaseV1],
    runtime: dict[str, Any],
) -> StudentTutoringServiceAdapterV1:
    historical_retriever = (
        "atomic-bm25-openai-small-rrf-v1@"
        "academic-factual-qa-atomic-m2-confirmation-001"
    )
    successor_retriever = (
        "atomic-bm25-openai-small-rrf-v1@"
        "academic-factual-qa-action-router-confirmation-001"
    )
    if manifest.retriever == historical_retriever:
        source_path = SOURCE_PATH
        runtime_path = RETRIEVAL_RUNTIME_PATH
        successor = False
    elif manifest.retriever == successor_retriever:
        source_path = ACTION_ROUTER_SOURCE_PATH
        runtime_path = ACTION_ROUTER_RETRIEVAL_RUNTIME_PATH
        successor = True
    else:
        raise AtomicM2ProductAdapterError("product retriever manifest drifted")
    if successor and manifest.evidence_gate == (
        "question-targeted-atomic-evidence-gate-v1"
    ):
        condition = "candidate"
        gate_impl = QuestionTargetedAtomicEvidenceGate()
        generator_kind = "targeted"
    elif successor and manifest.evidence_gate == (
        "atomic-structured-coverage-control-v1"
    ):
        condition = "control"
        gate_impl = StructuredLexicalCoverageEvidenceGate()
        generator_kind = "historical"
    elif not successor and manifest.evidence_gate == "atomic-structured-coverage-evidence-gate-v1":
        condition = "candidate"
        gate_impl = StructuredLexicalCoverageEvidenceGate()
        generator_kind = "historical"
    elif not successor and manifest.evidence_gate == "atomic-any-hit-evidence-gate-v1":
        condition = "control"
        gate_impl = AnyHitEvidenceGate()
        generator_kind = "historical"
    else:
        raise AtomicM2ProductAdapterError("product evidence gate drifted")
    generator_binding, generator_transport = base._generator_transport(manifest)  # noqa: SLF001
    maximum_calls = int(runtime.get("maximum_calls", 500 if condition == "candidate" else 100))
    maximum_cost = float(runtime.get("maximum_cost_usd", 5.5 if condition == "candidate" else 1.0))
    provider_ledger = base.ProviderCallLedgerV1(
        Path(runtime["provider_ledger_path"]),
        run_binding={
            "instrument_id": runtime["instrument_id"],
            "flow_id": manifest.flow_id,
            "manifest": manifest.model_dump(mode="json"),
            "binding": generator_binding,
            "cases_sha256": runtime["cases_sha256"],
            "code_revision": runtime["code_revision"],
        },
        maximum_calls=maximum_calls,
        maximum_cost_usd=maximum_cost,
        resume=bool(runtime["resume"]),
        maximum_transport_retries_total=0,
    )
    client = base._BoundedProductLlmClient(  # noqa: SLF001
        transport=generator_transport,
        ledger=provider_ledger,
        flow_id=manifest.flow_id,
        response_schema=base.EXTRACTIVE_BOUNDARY_RESPONSE_SCHEMA,
        quarantine_failures=True,
    )
    if generator_kind == "targeted":
        generator_impl: Any = LiveQuestionTargetedAtomicGroundedGenerator(
            client,
            prompt_builder=QuestionTargetedAtomicPromptBuilder(),
            policy_enforcer=DeterministicPolicyEnforcer(
                action_router=DeterministicActionRouterV1()
            ),
        )
    else:
        generator_impl = LiveExtractiveBoundaryGroundedGenerator(
            client, prompt_builder=ExtractiveBoundaryGroundedPromptBuilder()
        )
    recording_generator = base._RecordingGenerator(generator_impl)  # noqa: SLF001
    gate = base._RecordingGate(gate_impl)  # noqa: SLF001
    chunks_by_course, chunks_by_id = _chunks_by_course(source_path)
    embedder = _query_embedder(cases, runtime_path)
    retrievers = _retrievers(
        chunks_by_course=chunks_by_course,
        embedder=embedder,
        runtime_path=runtime_path,
    )
    repository, service, identities = _setup_service(
        chunks_by_course=chunks_by_course,
        retrievers=retrievers,
        generator=recording_generator,
        gate=gate,
        database_path=Path(runtime["state_path"]),
    )
    conversations = {
        case.case_id: service.create_conversation(
            identities["student_id"], case.course_id
        ).id
        for case in cases
    }

    async def execute_turn(case: EvaluationCaseV1):
        token = base._CURRENT_CASE_ID.set(case.case_id)  # noqa: SLF001
        try:
            return await service.submit_message(
                identities["student_id"],
                conversations[case.case_id],
                content=case.question,
                client_request_id=f"{manifest.flow_id}:{case.case_id}",
            )
        finally:
            base._CURRENT_CASE_ID.reset(token)  # noqa: SLF001

    def resolve_citation(row: Any) -> EvaluationCitationV1:
        matching = [
            chunk
            for chunk in chunks_by_id.values()
            if chunk.source_artifact_id == row.source_artifact_id
            and chunk.locator == row.locator
        ]
        if len(matching) != 1:
            raise AtomicM2ProductAdapterError("citation does not map to one atom")
        return base._evaluation_citation(matching[0])  # noqa: SLF001

    def resolve_retrieved(
        case: EvaluationCaseV1, _turn: Any
    ) -> list[EvaluationCitationV1]:
        return [
            base._evaluation_citation(hit.chunk)  # noqa: SLF001
            for hit in gate.hits_by_case.get(case.case_id, [])
        ]

    def resolve_claims(
        case: EvaluationCaseV1, turn: Any
    ) -> list[EvaluationAtomicClaimV1]:
        if turn.tutor_message.action != "answer":
            return []
        answer = recording_generator.answers_by_case.get(case.case_id)
        if answer is None:
            raise AtomicM2ProductAdapterError("answer lacks recorded atomic claims")
        return [
            EvaluationAtomicClaimV1(
                text=claim.text,
                citations=[
                    base._evaluation_citation(chunks_by_id[hit_id])  # noqa: SLF001
                    for hit_id in claim.evidence_hit_ids
                ],
            )
            for claim in answer.atomic_claims
        ]

    return base._ManagedAdapter(  # noqa: SLF001
        flow_id=manifest.flow_id,
        execute_turn=execute_turn,
        resolve_citation=resolve_citation,
        resolve_claims=resolve_claims,
        resolve_retrieved=resolve_retrieved,
        provider_ledger=provider_ledger,
        repository=repository,
        maximum_quarantined_failures=int(maximum_calls * 0.005),
    )
