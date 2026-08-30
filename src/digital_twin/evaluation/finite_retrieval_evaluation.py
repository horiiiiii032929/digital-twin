"""Leakage-safe retrieval comparison for the finite evaluation program."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import time

from src.digital_twin.evaluation.factual_qa_contract import (
    CanonicalEvidenceRefV1,
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
    evidence_ranges_overlap,
)
from src.digital_twin.grounding.hierarchical_retrieval import (
    StructuredHierarchicalRetriever,
    deterministic_boundary_action,
    p95,
)
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.protocols import Retriever


class FiniteRetrievalEvaluationError(ValueError):
    """Raised when a retrieval comparison leaks or drifts from its package."""


@dataclass(frozen=True)
class RetrievalCaseObservation:
    case_id: str
    method_id: str
    action: str
    hit_ids: tuple[str, ...]
    evidence_at_3: bool
    evidence_recall_at_5: float
    severe_release: bool
    course_violation: bool
    source_version_violation: bool
    latency_ms: float
    reranking_applied: bool = False


@dataclass(frozen=True)
class RetrievalMethodSummary:
    method_id: str
    case_count: int
    complete_evidence_at_3: float
    evidence_recall_at_5: float
    boundary_accuracy: float
    severe_release_count: int
    course_violation_count: int
    source_version_violation_count: int
    latency_p95_ms: float
    reranked_case_count: int
    passed: bool


def validate_exact_reference_matchability(
    *,
    gold: list[EvaluationGoldV1],
    chunks: list[DocumentChunk],
) -> dict[str, int]:
    """Fail before ranking unless every answerable reference exists exactly."""

    references = {
        (
            chunk.source_artifact_id or chunk.document_id,
            chunk.source_version,
            chunk.source_checksum,
            int(chunk.metadata.get("char_start", -1)),
            int(chunk.metadata.get("char_end", -1)),
            chunk.region_id,
        )
        for chunk in chunks
    }
    required = [
        reference
        for row in gold
        if row.expected_action == EvaluationAction.ANSWER
        for claim in row.claims
        for reference in claim.evidence_refs
    ]
    missing = [
        reference
        for reference in required
        if (
            reference.source_artifact_id,
            reference.source_version,
            reference.source_sha256,
            reference.char_start,
            reference.char_end,
            reference.region_id,
        )
        not in references
    ]
    if missing:
        raise FiniteRetrievalEvaluationError(
            f"registered corpus cannot exactly match {len(missing)} gold references"
        )
    return {
        "required_reference_count": len(required),
        "matched_reference_count": len(required),
        "missing_reference_count": 0,
    }


def select_untouched_retrieval_cases(
    cases: list[EvaluationCaseV1], *, known_count: int = 200
) -> list[EvaluationCaseV1]:
    """Freeze 300 cases without reading gold or provider output."""

    if len(cases) != 500 or known_count != 200:
        raise FiniteRetrievalEvaluationError("retrieval split requires 500 minus 200")
    ordered = sorted(
        cases,
        key=lambda row: hashlib.sha256(
            f"finite-retrieval-v1:{row.case_id}".encode("utf-8")
        ).hexdigest(),
    )
    selected = ordered[known_count:]
    if len(selected) != 300 or len({row.case_id for row in selected}) != 300:
        raise FiniteRetrievalEvaluationError("untouched retrieval split drifted")
    return selected


def _hit_reference(hit: RetrievalHit) -> CanonicalEvidenceRefV1 | None:
    metadata = hit.chunk.metadata
    try:
        return CanonicalEvidenceRefV1(
            source_artifact_id=hit.chunk.source_artifact_id or hit.chunk.document_id,
            source_version=hit.chunk.source_version,
            source_sha256=hit.chunk.source_checksum,
            char_start=int(metadata["char_start"]),
            char_end=int(metadata["char_end"]),
            region_id=hit.chunk.region_id,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _covered(required: CanonicalEvidenceRefV1, hits: list[RetrievalHit]) -> bool:
    return any(
        reference is not None and evidence_ranges_overlap(required, reference)
        for reference in (_hit_reference(hit) for hit in hits)
    )


def evaluate_retrieval_method(
    *,
    method_id: str,
    cases: list[EvaluationCaseV1],
    hidden_gold: Mapping[str, EvaluationGoldV1],
    retrievers_by_course: Mapping[str, Retriever],
    hierarchical: bool = False,
    semantic_ranker: Callable[[str, list[RetrievalHit]], list[str]] | None = None,
) -> tuple[list[RetrievalCaseObservation], RetrievalMethodSummary]:
    """Execute retrieval first; join hidden gold only after rankings exist."""

    public_ids = [row.case_id for row in cases]
    if len(public_ids) != len(set(public_ids)) or set(public_ids) != set(hidden_gold):
        raise FiniteRetrievalEvaluationError("public and hidden retrieval IDs drifted")
    persisted: list[tuple[EvaluationCaseV1, list[RetrievalHit], float, bool, str]] = []
    for case in cases:
        retriever = retrievers_by_course.get(case.course_id)
        if retriever is None:
            raise FiniteRetrievalEvaluationError("case references an unknown course")
        started = time.perf_counter()
        reranked = False
        if hierarchical:
            if not isinstance(retriever, StructuredHierarchicalRetriever):
                raise FiniteRetrievalEvaluationError("hierarchical method binding drifted")
            initial = retriever.plan(case.question, limit=5)
            ranked_ids = None
            if initial.reranking_eligible and semantic_ranker is not None:
                ranked_ids = semantic_ranker(case.question, list(initial.hits))
            plan = retriever.plan(
                case.question,
                limit=5,
                allow_semantic_reranking=ranked_ids is not None,
                ranked_ids=ranked_ids,
            )
            hits = list(plan.hits)
            reranked = plan.reranking_applied
            action = plan.deterministic_action or "answer"
        else:
            hits = retriever.retrieve(case.question, limit=5)
            action = deterministic_boundary_action(case.question) or (
                "answer" if hits else "abstain"
            )
        latency = (time.perf_counter() - started) * 1000
        persisted.append((case, hits, latency, reranked, action))

    observations: list[RetrievalCaseObservation] = []
    for case, hits, latency, reranked, action in persisted:
        gold = hidden_gold[case.case_id]
        required = [
            reference for claim in gold.claims for reference in claim.evidence_refs
        ]
        top3_complete = bool(required) and all(
            _covered(reference, hits[:3]) for reference in required
        )
        recall5 = (
            sum(_covered(reference, hits[:5]) for reference in required) / len(required)
            if required
            else 1.0
        )
        boundary = gold.expected_action != EvaluationAction.ANSWER
        severe = boundary and action == EvaluationAction.ANSWER.value
        course_violation = any(
            hit.chunk.metadata.get("course_id") != case.course_id for hit in hits
        )
        required_versions = {
            reference.source_artifact_id: reference.source_version for reference in required
        }
        version_violation = any(
            reference is None
            or (
                reference.source_artifact_id in required_versions
                and required_versions[reference.source_artifact_id]
                != reference.source_version
            )
            for reference in (_hit_reference(hit) for hit in hits)
        )
        observations.append(
            RetrievalCaseObservation(
                case_id=case.case_id,
                method_id=method_id,
                action=action,
                hit_ids=tuple(hit.chunk.id for hit in hits),
                evidence_at_3=top3_complete if required else True,
                evidence_recall_at_5=recall5,
                severe_release=severe,
                course_violation=course_violation,
                source_version_violation=version_violation,
                latency_ms=latency,
                reranking_applied=reranked,
            )
        )

    answerable = [
        row
        for row in observations
        if hidden_gold[row.case_id].expected_action == EvaluationAction.ANSWER
    ]
    boundary_rows = [row for row in observations if row not in answerable]
    complete = sum(row.evidence_at_3 for row in answerable) / len(answerable)
    recall = sum(row.evidence_recall_at_5 for row in answerable) / len(answerable)
    boundary_accuracy = (
        sum(
            row.action == hidden_gold[row.case_id].expected_action.value
            for row in boundary_rows
        )
        / len(boundary_rows)
    )
    summary = RetrievalMethodSummary(
        method_id=method_id,
        case_count=len(observations),
        complete_evidence_at_3=complete,
        evidence_recall_at_5=recall,
        boundary_accuracy=boundary_accuracy,
        severe_release_count=sum(row.severe_release for row in observations),
        course_violation_count=sum(row.course_violation for row in observations),
        source_version_violation_count=sum(
            row.source_version_violation for row in observations
        ),
        latency_p95_ms=p95([row.latency_ms for row in observations]),
        reranked_case_count=sum(row.reranking_applied for row in observations),
        passed=(
            complete >= 0.90
            and recall >= 0.95
            and boundary_accuracy >= 0.98
            and not any(row.severe_release for row in observations)
            and not any(row.course_violation for row in observations)
            and not any(row.source_version_violation for row in observations)
            and p95([row.latency_ms for row in observations]) <= 2_000
        ),
    )
    return observations, summary


def select_retrieval_successor(
    summaries: list[RetrievalMethodSummary],
) -> RetrievalMethodSummary | None:
    by_id = {row.method_id: row for row in summaries}
    deterministic = by_id.get("hierarchical-deterministic-v1")
    assisted = by_id.get("hierarchical-nano-rerank-v1")
    passing = [row for row in summaries if row.passed]
    if not passing:
        return None
    if deterministic and deterministic.passed and assisted and assisted.passed:
        if assisted.complete_evidence_at_3 - deterministic.complete_evidence_at_3 <= 0.02:
            return deterministic
    return max(
        passing,
        key=lambda row: (
            row.complete_evidence_at_3,
            row.evidence_recall_at_5,
            -row.latency_p95_ms,
        ),
    )
