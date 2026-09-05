"""Actual-product adapter for the final fresh cross-method comparison.

Historical adapters remain unchanged.  This successor differs only in making
the retriever and release profile explicit so that the measured manifest cannot
claim Qwen hybrid retrieval while the product silently runs its BM25 fallback.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Sequence

from services.embeddings import Qwen3TextEmbedder
from scripts import academic_factual_qa_open_10000_winner_adapter as historical
from scripts.academic_factual_qa_open_10000_t0_adapter import (
    _CURRENT_CASE_ID,
    _RecordingGate,
    _RecordingGenerator,
    _evaluation_citation,
)
from src.digital_twin.action_router import DeterministicActionRouterV3
from src.digital_twin.evaluation import ComponentKind, load_release_profile
from src.digital_twin.evaluation.factual_qa_adapters import (
    StudentTutoringServiceAdapterV1,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.generation import (
    DeterministicEvidenceSetGroundedGenerator,
    DeterministicPolicyEnforcer,
)
from src.digital_twin.grounding import (
    AmbiguitySafeEvidenceGateV1,
    AnyHitEvidenceGate,
    AtomicClaimEvidenceValidator,
    BM25Retriever,
    CanonicalSourceAtomicClaimVerifier,
    DominanceScopedAmbiguitySafeEvidenceGateV3,
    QuestionTargetedAtomicEvidenceGate,
    StructuredLexicalCoverageEvidenceGate,
    build_selected_retriever,
)
from src.digital_twin.student import (
    Account,
    AccountRole,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    LearningGapPseudonymizer,
    MembershipRole,
    ReleaseEvaluationStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    approved_synthetic_policy,
)
from src.digital_twin.student.tutoring_graph import TutoringMode


ROOT = Path(__file__).resolve().parents[1]
FLOW_ID = "final-cross-method-factual-confirmation-001"
PROFILE_PATH = (
    ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-candidate-v3.json"
)
GENERATOR_ID = "deterministic-evidence-set-grounded-generator-v2"
POLICY_ID = "deterministic-tutor-action-router-v3"
BM25_RETRIEVER_ID = "bm25-v1"
QWEN_RETRIEVER_ID = "qwen3-hybrid-v1"
ANY_HIT_GATE = "any-hit-evidence-gate-v1"
QUESTION_TARGETED_GATE = "question-targeted-ambiguity-safe-v2"
DOMINANCE_GATE = "dominance-scoped-ambiguity-safe-v3"
PROFESSOR_ID = "final-confirmation-professor"
STUDENT_ID = "final-confirmation-student"
PSEUDONYMIZATION_SECRET = b"final-confirmation-public-only-32"


class FinalCrossMethodAdapterError(RuntimeError):
    """Raised when an evaluated product binding drifts from its manifest."""


def profile_sha256(path: Path = PROFILE_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FinalCrossMethodAdapter(StudentTutoringServiceAdapterV1):
    def __init__(
        self,
        *,
        repository: SQLiteStudentRepository,
        retriever_id: str,
        evidence_gate_id: str,
        generator_id: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.repository = repository
        self.retriever_id = retriever_id
        self.evidence_gate_id = evidence_gate_id
        self.generator_id = generator_id
        self._closed = False

    def validate_completion(self) -> None:
        return None

    def finalize(self) -> None:
        if not self._closed:
            self.repository.close()
            self._closed = True

    def interrupt(self) -> None:
        self.finalize()


def _install_courses(
    repository: SQLiteStudentRepository,
    chunks_by_course: dict[str, list[Any]],
    *,
    profile_path: Path,
) -> None:
    profile = load_release_profile(profile_path)
    repository.save_account(Account(id=PROFESSOR_ID, role=AccountRole.PROFESSOR))
    repository.save_account(Account(id=STUDENT_ID, role=AccountRole.STUDENT))
    for course_id, chunks in sorted(chunks_by_course.items()):
        repository.save_course(
            Course(
                id=course_id,
                title=course_id.replace("-", " ").title(),
                owner_professor_id=PROFESSOR_ID,
            )
        )
        repository.save_membership(
            CourseMembership(
                account_id=PROFESSOR_ID,
                course_id=course_id,
                role=MembershipRole.PROFESSOR,
            )
        )
        repository.save_membership(
            CourseMembership(
                account_id=STUDENT_ID,
                course_id=course_id,
                role=MembershipRole.STUDENT,
            )
        )
        release = DigitalTwinRelease(
            id=f"{course_id}-final-confirmation-release",
            course_id=course_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            policy_version=1,
            policy=approved_synthetic_policy(),
            chunks=chunks,
            status=StudentReleaseStatus.PUBLISHED,
            evaluation_status=ReleaseEvaluationStatus.PASSED,
        )
        repository.save_release(release)
        repository.save_course_domain_model(
            historical._domain_model_for_course(
                course_id=course_id,
                release=release,
                chunks=chunks,
            )
        )


def _evidence_gate(identifier: str) -> Any:
    base = QuestionTargetedAtomicEvidenceGate(
        base_gate=StructuredLexicalCoverageEvidenceGate(
            minimum_content_matching_terms=2,
            evidence_limit=5,
        )
    )
    if identifier == QUESTION_TARGETED_GATE:
        return AmbiguitySafeEvidenceGateV1(base, evidence_limit=5)
    if identifier == DOMINANCE_GATE:
        return DominanceScopedAmbiguitySafeEvidenceGateV3(base, evidence_limit=5)
    if identifier == ANY_HIT_GATE:
        return AnyHitEvidenceGate()
    raise FinalCrossMethodAdapterError(f"unsupported evidence gate: {identifier}")


def _qwen_embedder(profile_path: Path) -> Qwen3TextEmbedder:
    profile = load_release_profile(profile_path)
    selection = next(
        entry for entry in profile.components if entry.component == ComponentKind.RETRIEVER
    )
    implementation = selection.implementation
    if implementation is None:
        raise FinalCrossMethodAdapterError("profile has no selected retriever")
    configuration = implementation.configuration
    revision = str(configuration["embedding_revision"])
    model_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_QWEN_MODEL_ROOT",
            str(
                ROOT
                / "data/external/huggingface/hub/"
                "models--Qwen--Qwen3-Embedding-0.6B/snapshots"
            ),
        )
    )
    model_path = model_root / revision
    if not model_path.is_dir():
        raise FinalCrossMethodAdapterError(
            f"pinned Qwen embedding snapshot is unavailable: {model_path}"
        )
    return Qwen3TextEmbedder(
        model_path,
        instruction=str(configuration["query_instruction"]),
        device=str(configuration["device"]),
        dtype=str(configuration["dtype"]),
        batch_size=int(configuration["embedding_batch_size"]),
        max_length=int(configuration["embedding_max_length"]),
        model_revision=revision,
    )


def build_final_cross_method_adapter(
    *,
    manifest: SystemUnderTestManifestV1,
    cases: Sequence[EvaluationCaseV1],
    runtime: dict[str, Any],
) -> FinalCrossMethodAdapter:
    del cases
    if manifest.flow_id != FLOW_ID:
        raise FinalCrossMethodAdapterError(f"flow identity drifted: {manifest.flow_id}")
    if manifest.generator != GENERATOR_ID or manifest.policy != POLICY_ID:
        raise FinalCrossMethodAdapterError("generator or policy identity drifted")
    profile_path = Path(str(runtime.get("profile_path", PROFILE_PATH)))
    if manifest.profile_sha256 != profile_sha256(profile_path):
        raise FinalCrossMethodAdapterError("profile hash drifted")
    if manifest.retriever not in {BM25_RETRIEVER_ID, QWEN_RETRIEVER_ID}:
        raise FinalCrossMethodAdapterError(
            f"unsupported retriever binding: {manifest.retriever}"
        )

    source_path = Path(str(runtime["source_package_path"]))
    chunks_by_course, chunks_by_id = historical.load_corpus_with_atom_lineage(
        source_path
    )
    generator = _RecordingGenerator(
        DeterministicEvidenceSetGroundedGenerator(
            policy_enforcer=DeterministicPolicyEnforcer(
                action_router=DeterministicActionRouterV3()
            )
        )
    )
    gate_impl = _evidence_gate(manifest.evidence_gate)
    gate = _RecordingGate(gate_impl)
    validator = AtomicClaimEvidenceValidator(
        CanonicalSourceAtomicClaimVerifier(),
        minimum_entailment=1.0,
        maximum_contradiction=0.0,
        maximum_claims=8,
        evidence_limit=5,
    )
    embedder = _qwen_embedder(profile_path) if manifest.retriever == QWEN_RETRIEVER_ID else None
    profile = load_release_profile(profile_path)
    selection = next(
        entry for entry in profile.components if entry.component == ComponentKind.RETRIEVER
    )

    def retriever_factory(chunks: Sequence[Any], active_versions: Any) -> Any:
        if manifest.retriever == BM25_RETRIEVER_ID:
            return BM25Retriever(chunks, active_source_versions=active_versions)
        return build_selected_retriever(
            selection,
            chunks,
            active_source_versions=active_versions,
            embedder=embedder,
            allow_control_fallback=False,
        )

    repository = SQLiteStudentRepository(Path(runtime["state_path"]))
    _install_courses(repository, chunks_by_course, profile_path=profile_path)
    service = StudentTutoringService(
        repository,
        profile_path=profile_path,
        generator=generator,
        evidence_gate=gate,
        claim_evidence_validator=validator,
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(PSEUDONYMIZATION_SECRET),
        retriever_factory=retriever_factory,
    )
    conversations: dict[str, str] = {}

    def conversation_for(case: EvaluationCaseV1) -> str:
        identifier = conversations.get(case.case_id)
        if identifier is None:
            identifier = service.create_conversation(STUDENT_ID, case.course_id).id
            conversations[case.case_id] = identifier
        return identifier

    async def execute_turn(case: EvaluationCaseV1) -> Any:
        token = _CURRENT_CASE_ID.set(case.case_id)
        try:
            return await service.submit_message(
                STUDENT_ID,
                conversation_for(case),
                content=case.question,
                client_request_id=f"{FLOW_ID}:{case.case_id}",
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
            raise FinalCrossMethodAdapterError(
                "released citation cannot map to one canonical source range"
            )
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
        answer = generator.answers_by_case.get(case.case_id)
        if answer is None:
            raise FinalCrossMethodAdapterError("answer lacks recorded atomic claims")
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

    return FinalCrossMethodAdapter(
        flow_id=FLOW_ID,
        execute_turn=execute_turn,
        resolve_citation=resolve_citation,
        resolve_claims=resolve_claims,
        resolve_retrieved=resolve_retrieved,
        repository=repository,
        retriever_id=manifest.retriever,
        evidence_gate_id=gate_impl.implementation_id,
        generator_id=GENERATOR_ID,
    )

