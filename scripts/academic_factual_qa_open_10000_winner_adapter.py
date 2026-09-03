#!/usr/bin/env python3
"""Bind the confirmation-024 winner to the sealed 10,000+1,000 known benchmark.

Program 011 ran the T0 product against this package through
``academic_factual_qa_open_10000_t0_adapter``. That module is frozen: the
recorded Program 011 result depends on its behaviour, so nothing here edits it.
Shared, condition-neutral helpers are imported from it instead.

What this module adds is the wiring Program 011 never had:

* ``SourceSemanticEvidenceAtomGateV3`` -- the selected grounding architecture
* ``SourceSemanticEvidenceAtomRetrieverV1`` -- BM25 over atom projections, so
  retrieval is local and no embedder or query-vector cache is required
* ``DeterministicEvidenceSetGroundedGenerator`` -- the authoritative factual
  generator named by the confirmation-024 manifest
* ``DeterministicActionRouterV3`` -- the request-intent contract

The candidate arm therefore reaches no provider at all. A reactive semantic
planner may be injected for the provider-backed arm; the factual answer stays
deterministic either way, exactly as it did in confirmation 024.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.academic_factual_qa_open_10000_t0_adapter import (  # noqa: E402
    PROFILE_PATH,
    _CURRENT_CASE_ID,
    _chunks_by_course,
    _evaluation_citation,
    _RecordingGate,
    _RecordingGenerator,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_adapters import (  # noqa: E402
    StudentTutoringServiceAdapterV1,
)
from src.digital_twin.generation import (  # noqa: E402
    DeterministicEvidenceSetGroundedGenerator,
    DeterministicPolicyEnforcer,
)
from src.digital_twin.grounding import (  # noqa: E402
    AnyHitEvidenceGate,
    AtomicClaimEvidenceValidator,
    CanonicalSourceAtomicClaimVerifier,
    SourceSemanticEvidenceAtomGateV3,
    SourceSemanticEvidenceAtomGateV4,
    SourceSemanticEvidenceAtomRetrieverV1,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.action_router import DeterministicActionRouterV3  # noqa: E402
from src.digital_twin.student import (  # noqa: E402
    Account,
    AccountRole,
    CanonicalSourceRangeV1,
    Course,
    CourseConceptV1,
    CourseDomainModelV1,
    CourseMembership,
    CourseObjectiveV1,
    DigitalTwinRelease,
    LearningGapPseudonymizer,
    MembershipRole,
    ReleaseEvaluationStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    approved_synthetic_policy,
)
from src.digital_twin.student.tutoring_graph import TutoringMode  # noqa: E402


WINNER_FLOW_ID = "academic-factual-qa-open-10000-winner-v1"
CANDIDATE_EVIDENCE_GATE = "pedagogy-aware-source-semantic-evidence-atoms-v3"
# The successor corrects V3's claim-class contest so that a strictly dominant
# leader resolves instead of failing closed. See
# tests/test_source_semantic_evidence_atom_gate_v4.py.
SUCCESSOR_EVIDENCE_GATE = "dominance-scoped-source-semantic-evidence-atoms-v4"
CONTROL_EVIDENCE_GATE = "any-hit-evidence-gate-v1"
# What services/api/app/factory.py actually ships today, so a gate selection can
# compare the evaluated line against the incumbent rather than against itself.
PRODUCT_STRUCTURED_LEXICAL_GATE = "structured-lexical-v1"
WINNER_GENERATOR_ID = "deterministic-evidence-set-grounded-generator-v2"
WINNER_RETRIEVER_ID = "source-semantic-evidence-atom-retriever-v1"
WINNER_POLICY_ID = "deterministic-tutor-action-router-v3"
RETRIEVAL_CANDIDATE_LIMIT = 30
PROFESSOR_ID = "academic-open-professor"
STUDENT_ID = "academic-open-student"
PSEUDONYMIZATION_SECRET = b"academic-open-10000-winner-secret-32"


class WinnerAdapterError(RuntimeError):
    """Raised when the requested binding is not the confirmation-024 winner."""


def winner_profile_sha256() -> str:
    """Hash the release profile the winner arms run against."""

    import hashlib

    return hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()


class _ProviderCallCounter:
    """Count every provider call the arm makes, so preflight can assert zero."""

    def __init__(self) -> None:
        self.count = 0

    def wrap(self, planner: Any) -> Any:
        if planner is None:
            return None
        counter = self

        class _CountingPlanner:
            def __getattr__(self, name: str) -> Any:
                return getattr(planner, name)

            async def plan(self, *args: Any, **kwargs: Any) -> Any:
                counter.count += 1
                return await planner.plan(*args, **kwargs)

        return _CountingPlanner()


class WinnerEvaluationAdapterV1(StudentTutoringServiceAdapterV1):
    """Lifecycle wrapper that also exposes the bound identities for auditing."""

    def __init__(
        self,
        *,
        repository: SQLiteStudentRepository,
        condition: str,
        conversation_scope: str,
        evidence_gate_id: str,
        retriever_id: str,
        generator_id: str,
        tutoring_mode: str,
        provider_counter: _ProviderCallCounter,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.repository = repository
        self.condition = condition
        self.conversation_scope = conversation_scope
        self.evidence_gate_id = evidence_gate_id
        self.retriever_id = retriever_id
        self.generator_id = generator_id
        self.tutoring_mode = tutoring_mode
        self._provider_counter = provider_counter
        self._closed = False

    @property
    def provider_call_count(self) -> int:
        return self._provider_counter.count

    def validate_completion(self) -> None:
        return None

    def finalize(self) -> None:
        if not self._closed:
            self.repository.close()
            self._closed = True

    def interrupt(self) -> None:
        self.finalize()


MAXIMUM_CONCEPTS = 256
MAXIMUM_CONCEPT_RANGES = 16
MAXIMUM_OBJECTIVE_CONCEPTS = 32
MAXIMUM_DESCRIPTION = 1_000
MAXIMUM_LABEL = 200


def _concept_for_family(family_id: str, regions: list[Any]) -> CourseConceptV1:
    """One approved concept per source family, the benchmark's analysis unit."""

    ordered = sorted(regions, key=lambda row: (row.locator, row.id))
    label = str(ordered[0].metadata.get("title") or family_id)[:MAXIMUM_LABEL]
    described = " ".join(
        str(row.metadata.get("search_description") or row.text) for row in ordered
    )
    return CourseConceptV1(
        concept_id=family_id,
        label=label,
        description=described[:MAXIMUM_DESCRIPTION] or label,
        canonical_ranges=[
            CanonicalSourceRangeV1(
                source_artifact_id=row.source_artifact_id or row.document_id,
                source_version=row.source_version,
                source_sha256=row.source_checksum,
                locator=row.locator,
                char_start=int(row.metadata["char_start"]),
                char_end=int(row.metadata["char_end"]),
            )
            for row in ordered[:MAXIMUM_CONCEPT_RANGES]
        ],
    )


def _domain_model_for_course(
    *,
    course_id: str,
    release: DigitalTwinRelease,
    chunks: list[Any],
) -> CourseDomainModelV1:
    """Derive the approved course semantics from the sealed public corpus.

    The corpus is public input. Nothing here reads gold, so building the domain
    model cannot leak the answer key into the system under test.
    """

    # Prefer the benchmark's own analysis unit, then fall back to progressively
    # coarser lineage so a corpus that predates source families still yields an
    # approved domain model within the 256-concept schema ceiling.
    def group_by(key: str) -> dict[str, list[Any]] | None:
        grouped: dict[str, list[Any]] = {}
        for chunk in chunks:
            if key == "document_id":
                value = str(chunk.source_artifact_id or chunk.document_id)
            else:
                value = str(chunk.metadata.get(key) or "")
            if not value:
                return None
            grouped.setdefault(value, []).append(chunk)
        return grouped if len(grouped) <= MAXIMUM_CONCEPTS else None

    families: dict[str, list[Any]] | None = None
    for key in ("source_family_id", "parent_cluster_id", "document_id"):
        families = group_by(key)
        if families is not None:
            break
    if families is None:
        raise WinnerAdapterError(
            f"{course_id} has no lineage that yields at most {MAXIMUM_CONCEPTS} "
            "approved domain-model concepts"
        )

    concepts = [
        _concept_for_family(family_id, regions)
        for family_id, regions in sorted(families.items())
    ]
    concept_ids = [concept.concept_id for concept in concepts]
    objectives = [
        CourseObjectiveV1(
            objective_id=f"objective-{course_id}-{index:03d}",
            statement=(
                f"Answer questions about approved {course_id.replace('-', ' ')} "
                f"sources, group {index + 1}, only from released evidence."
            ),
            concept_ids=concept_ids[start : start + MAXIMUM_OBJECTIVE_CONCEPTS],
        )
        for index, start in enumerate(
            range(0, len(concept_ids), MAXIMUM_OBJECTIVE_CONCEPTS)
        )
    ]
    return CourseDomainModelV1(
        domain_model_id=f"domain-{course_id}",
        course_id=course_id,
        release_id=release.id,
        release_sha256=hashlib.sha256(
            release.model_dump_json().encode("utf-8")
        ).hexdigest(),
        version=1,
        objectives=objectives,
        concepts=concepts,
        approved_by=PROFESSOR_ID,
    )


def _install_courses(
    repository: SQLiteStudentRepository,
    chunks_by_course: dict[str, list[Any]],
) -> None:
    import json

    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
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
        repository.save_release(release)
        repository.save_course_domain_model(
            _domain_model_for_course(
                course_id=course_id,
                release=release,
                chunks=chunks,
            )
        )


def load_corpus_with_atom_lineage(
    source_path: Path | None = None,
) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    """Load a corpus and fill in whatever atom lineage it does not already carry.

    The sealed package ships regions that already declare ``region_id``,
    ``parent_cluster_id``, and ``source_family_id``. The older cluster format
    declares none of them, so the semantic atom line cannot read it at all.
    Each cluster span is itself the citable region, so the cluster identity is
    the region identity and its own relation group, and its recorded character
    span is the range.

    A corpus that already supplies a field keeps it. This defers to
    ``_chunks_by_course`` for parsing so the frozen adapter stays the single
    reader of both corpus formats.
    """

    grouped, by_id = _chunks_by_course(source_path)
    repaired_groups: dict[str, list[Any]] = {}
    repaired_by_id: dict[str, Any] = {}
    for course_id, chunks in grouped.items():
        rows = []
        for chunk in chunks:
            metadata = dict(chunk.metadata)
            metadata.setdefault("parent_cluster_id", chunk.id)
            metadata.setdefault("source_family_id", chunk.source_artifact_id or chunk.document_id)
            if "char_start" not in metadata or "char_end" not in metadata:
                start = int(metadata.get("char_start", 0))
                metadata["char_start"] = str(start)
                metadata["char_end"] = str(start + len(chunk.text))
            row = chunk.model_copy(
                update={
                    "metadata": metadata,
                    "region_id": chunk.region_id or chunk.id,
                }
            )
            rows.append(row)
            repaired_by_id[row.id] = row
        repaired_groups[course_id] = rows
    return repaired_groups, repaired_by_id


def build_winner_adapter(
    *,
    manifest: SystemUnderTestManifestV1,
    cases: Sequence[EvaluationCaseV1],
    runtime: dict[str, Any],
) -> WinnerEvaluationAdapterV1:
    """Return an adapter bound to exactly one confirmation-024 condition."""

    if manifest.flow_id != WINNER_FLOW_ID:
        raise WinnerAdapterError(
            f"winner manifest flow identity drifted: {manifest.flow_id}"
        )
    if manifest.generator != WINNER_GENERATOR_ID:
        raise WinnerAdapterError(
            "the selected factual generator is deterministic/evidence-set-v2; "
            f"refusing generator {manifest.generator}"
        )
    if manifest.retriever != WINNER_RETRIEVER_ID:
        raise WinnerAdapterError(
            f"winner retriever identity drifted: {manifest.retriever}"
        )
    if manifest.evidence_gate == CANDIDATE_EVIDENCE_GATE:
        condition = "candidate"
        evidence_gate: Any = SourceSemanticEvidenceAtomGateV3()
    elif manifest.evidence_gate == SUCCESSOR_EVIDENCE_GATE:
        condition = "successor"
        evidence_gate = SourceSemanticEvidenceAtomGateV4()
    elif manifest.evidence_gate == PRODUCT_STRUCTURED_LEXICAL_GATE:
        condition = "incumbent"
        evidence_gate = StructuredLexicalCoverageEvidenceGate(
            minimum_content_matching_terms=2,
            evidence_limit=3,
        )
    elif manifest.evidence_gate == CONTROL_EVIDENCE_GATE:
        condition = "control"
        evidence_gate = AnyHitEvidenceGate()
    else:
        raise WinnerAdapterError(
            "winner evidence gate must be the selected v3 architecture, its "
            "v4 successor, or the any-hit rollback control; refusing "
            f"{manifest.evidence_gate}"
        )

    source_value = runtime.get("source_package_path")
    source_path = Path(str(source_value)) if source_value else None
    chunks_by_course, chunks_by_id = load_corpus_with_atom_lineage(source_path)

    counter = _ProviderCallCounter()
    reactive_planner = counter.wrap(runtime.get("reactive_semantic_planner"))

    generator = _RecordingGenerator(
        DeterministicEvidenceSetGroundedGenerator(
            policy_enforcer=DeterministicPolicyEnforcer(
                action_router=DeterministicActionRouterV3()
            )
        )
    )
    gate = _RecordingGate(evidence_gate)
    validator = AtomicClaimEvidenceValidator(
        CanonicalSourceAtomicClaimVerifier(),
        minimum_entailment=1.0,
        maximum_contradiction=0.0,
        maximum_claims=8,
        evidence_limit=5,
    )

    def retriever_factory(chunks: Sequence[Any], _active_versions: Any) -> Any:
        return SourceSemanticEvidenceAtomRetrieverV1(
            chunks,
            candidate_limit=RETRIEVAL_CANDIDATE_LIMIT,
        )

    repository = SQLiteStudentRepository(Path(runtime["state_path"]))
    _install_courses(repository, chunks_by_course)
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        generator=generator,
        evidence_gate=gate,
        claim_evidence_validator=validator,
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(PSEUDONYMIZATION_SECRET),
        reactive_semantic_planner=reactive_planner,
        retriever_factory=retriever_factory,
    )
    scope = str(runtime.get("conversation_scope", "case"))
    if scope not in {"case", "cluster", "course"}:
        raise WinnerAdapterError(f"unsupported conversation scope: {scope}")
    known_courses = set(chunks_by_course)
    conversations: dict[str, str] = {}

    def conversation_for(case: EvaluationCaseV1) -> str:
        # T1-v2 accumulates a learner belief state per conversation. Program 011
        # could share one conversation per course because T0 is stateless; here
        # a shared conversation would make each case depend on every earlier
        # case in the same course, so the default is one conversation per case.
        key = {
            "case": case.case_id,
            "cluster": case.cluster_id,
            "course": case.course_id,
        }[scope]
        identifier = conversations.get(key)
        if identifier is None:
            identifier = service.create_conversation(STUDENT_ID, case.course_id).id
            conversations[key] = identifier
        return identifier

    async def execute_turn(case: EvaluationCaseV1) -> Any:
        if case.course_id not in known_courses:
            raise WinnerAdapterError(
                f"evaluation case references an unknown course: {case.course_id}"
            )
        token = _CURRENT_CASE_ID.set(case.case_id)
        try:
            return await service.submit_message(
                STUDENT_ID,
                conversation_for(case),
                content=case.question,
                client_request_id=f"{WINNER_FLOW_ID}:{case.case_id}",
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
            raise WinnerAdapterError(
                "released citation cannot map to one source range"
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
            raise WinnerAdapterError("released answer lacks recorded atomic claims")
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

    return WinnerEvaluationAdapterV1(
        flow_id=WINNER_FLOW_ID,
        execute_turn=execute_turn,
        resolve_citation=resolve_citation,
        resolve_claims=resolve_claims,
        resolve_retrieved=resolve_retrieved,
        repository=repository,
        condition=condition,
        conversation_scope=scope,
        evidence_gate_id=evidence_gate.implementation_id,
        retriever_id=WINNER_RETRIEVER_ID,
        generator_id=WINNER_GENERATOR_ID,
        tutoring_mode=TutoringMode.T1_V2,
        provider_counter=counter,
    )
