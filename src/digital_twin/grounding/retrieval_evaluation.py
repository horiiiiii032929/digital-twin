import math
import re
import time
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.protocols import Retriever


class RetrievalCaseCategory(StrEnum):
    DIRECT = "direct"
    MISCONCEPTION = "misconception"
    INTEGRITY_BOUNDARY = "integrity-boundary"
    AMBIGUOUS = "ambiguous"
    NO_EVIDENCE = "no-evidence"
    EXACT = "exact"
    PARAPHRASE = "paraphrase"
    MULTI_EVIDENCE = "multi-evidence"
    DISTRACTOR = "distractor"
    PERMISSION_VERSION = "permission-version"


class RetrievalFailureCause(StrEnum):
    SOURCE = "source"
    CHUNKING = "chunking"
    QUERY = "query"
    RANKING = "ranking"


class RelevantChunkReference(BaseModel):
    source_artifact_id: str = Field(min_length=1)
    text_contains: str = Field(min_length=1)


class RetrievalEvaluationCase(BaseModel):
    id: str = Field(min_length=1)
    category: RetrievalCaseCategory
    query: str = Field(min_length=1)
    relevant: list[RelevantChunkReference] = Field(default_factory=list)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def evidence_expectation_matches_category(self) -> "RetrievalEvaluationCase":
        if self.category == RetrievalCaseCategory.NO_EVIDENCE and self.relevant:
            raise ValueError("no-evidence cases cannot declare relevant chunks")
        if self.category != RetrievalCaseCategory.NO_EVIDENCE and not self.relevant:
            raise ValueError("evidence cases require at least one relevant chunk")
        return self


class RetrievalEvaluationSet(BaseModel):
    version: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    cases: list[RetrievalEvaluationCase] = Field(min_length=20)

    @model_validator(mode="after")
    def case_identifiers_must_be_unique(self) -> "RetrievalEvaluationSet":
        identifiers = [case.id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("evaluation case identifiers must be unique")
        return self


class RetrievalBenchmarkCorpus(BaseModel):
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    synthetic_only: bool
    chunks: list[DocumentChunk] = Field(min_length=20)

    @model_validator(mode="after")
    def chunk_identifiers_must_be_unique(self) -> "RetrievalBenchmarkCorpus":
        identifiers = [chunk.id for chunk in self.chunks]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("benchmark chunk identifiers must be unique")
        return self


class RetrievalEvaluationHit(BaseModel):
    rank: int = Field(ge=1)
    chunk_id: str
    document_id: str
    source_artifact_id: str
    source_version: int
    locator: str
    relevance_score: float


class RetrievalCaseResult(BaseModel):
    case_id: str
    category: RetrievalCaseCategory
    query: str
    recall_at_1: float | None = Field(default=None, ge=0, le=1)
    recall_at_3: float | None = Field(default=None, ge=0, le=1)
    recall_at_5: float | None = Field(default=None, ge=0, le=1)
    precision_at_1: float | None = Field(default=None, ge=0, le=1)
    precision_at_3: float | None = Field(default=None, ge=0, le=1)
    precision_at_5: float | None = Field(default=None, ge=0, le=1)
    ndcg_at_3: float | None = Field(default=None, ge=0, le=1)
    reciprocal_rank: float | None = Field(default=None, ge=0, le=1)
    no_evidence_correct: bool | None = None
    failure_cause: RetrievalFailureCause | None = None
    latency_ms: float = Field(ge=0)
    hits: list[RetrievalEvaluationHit] = Field(default_factory=list)


class RetrievalEvaluationSummary(BaseModel):
    retriever: str
    dataset_version: str
    corpus_version: str
    case_count: int = Field(ge=0)
    evidence_case_count: int = Field(ge=0)
    no_evidence_case_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0, le=1)
    recall_at_3: float = Field(ge=0, le=1)
    recall_at_5: float = Field(ge=0, le=1)
    precision_at_1: float = Field(ge=0, le=1)
    precision_at_3: float = Field(ge=0, le=1)
    precision_at_5: float = Field(ge=0, le=1)
    ndcg_at_3: float = Field(ge=0, le=1)
    mean_reciprocal_rank: float = Field(ge=0, le=1)
    no_evidence_accuracy: float = Field(ge=0, le=1)
    mean_latency_ms: float = Field(ge=0)
    p95_latency_ms: float = Field(ge=0)
    safety_violation_count: int = Field(ge=0)
    peak_memory_bytes: int | None = Field(default=None, ge=0)
    failures_by_cause: dict[str, int] = Field(default_factory=dict)
    metrics_by_category: dict[str, dict[str, float]] = Field(default_factory=dict)
    cases: list[RetrievalCaseResult]


def load_retrieval_evaluation_set(path: Path) -> RetrievalEvaluationSet:
    return RetrievalEvaluationSet.model_validate_json(path.read_text(encoding="utf-8"))


def load_retrieval_benchmark_corpus(path: Path) -> RetrievalBenchmarkCorpus:
    return RetrievalBenchmarkCorpus.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_retriever(
    name: str,
    retriever: Retriever,
    chunks: list[DocumentChunk],
    evaluation_set: RetrievalEvaluationSet,
) -> RetrievalEvaluationSummary:
    case_results = [
        _evaluate_case(retriever, chunks, case) for case in evaluation_set.cases
    ]
    evidence_results = [
        result
        for result in case_results
        if result.category != RetrievalCaseCategory.NO_EVIDENCE
    ]
    no_evidence_results = [
        result
        for result in case_results
        if result.category == RetrievalCaseCategory.NO_EVIDENCE
    ]
    failures: dict[str, int] = {}
    for result in case_results:
        if result.failure_cause is not None:
            key = result.failure_cause.value
            failures[key] = failures.get(key, 0) + 1

    return RetrievalEvaluationSummary(
        retriever=name,
        dataset_version=evaluation_set.version,
        corpus_version=evaluation_set.corpus_version,
        case_count=len(case_results),
        evidence_case_count=len(evidence_results),
        no_evidence_case_count=len(no_evidence_results),
        recall_at_1=_mean_metric(evidence_results, "recall_at_1"),
        recall_at_3=_mean_metric(evidence_results, "recall_at_3"),
        recall_at_5=_mean_metric(evidence_results, "recall_at_5"),
        precision_at_1=_mean_metric(evidence_results, "precision_at_1"),
        precision_at_3=_mean_metric(evidence_results, "precision_at_3"),
        precision_at_5=_mean_metric(evidence_results, "precision_at_5"),
        ndcg_at_3=_mean_metric(evidence_results, "ndcg_at_3"),
        mean_reciprocal_rank=_mean_metric(evidence_results, "reciprocal_rank"),
        no_evidence_accuracy=(
            sum(result.no_evidence_correct is True for result in no_evidence_results)
            / len(no_evidence_results)
            if no_evidence_results
            else 1.0
        ),
        mean_latency_ms=(
            sum(result.latency_ms for result in case_results) / len(case_results)
            if case_results
            else 0.0
        ),
        p95_latency_ms=_percentile(
            [result.latency_ms for result in case_results], 0.95
        ),
        safety_violation_count=_safety_violation_count(case_results, chunks),
        failures_by_cause=failures,
        metrics_by_category=_metrics_by_category(case_results),
        cases=case_results,
    )


def _evaluate_case(
    retriever: Retriever,
    chunks: list[DocumentChunk],
    case: RetrievalEvaluationCase,
) -> RetrievalCaseResult:
    started = time.perf_counter()
    hits = retriever.retrieve(case.query, limit=5)
    latency_ms = (time.perf_counter() - started) * 1000
    serialized_hits = [_serialize_hit(rank, hit) for rank, hit in enumerate(hits, 1)]

    if case.category == RetrievalCaseCategory.NO_EVIDENCE:
        correct = not hits
        return RetrievalCaseResult(
            case_id=case.id,
            category=case.category,
            query=case.query,
            no_evidence_correct=correct,
            failure_cause=None if correct else RetrievalFailureCause.QUERY,
            latency_ms=latency_ms,
            hits=serialized_hits,
        )

    source_ids = {chunk.source_artifact_id or chunk.document_id for chunk in chunks}
    missing_source = any(
        reference.source_artifact_id not in source_ids for reference in case.relevant
    )
    unresolved_chunk = any(
        not any(_chunk_matches(chunk, reference) for chunk in chunks)
        for reference in case.relevant
    )
    recall_at_1 = _recall_at(hits, case.relevant, 1)
    recall_at_3 = _recall_at(hits, case.relevant, 3)
    recall_at_5 = _recall_at(hits, case.relevant, 5)
    precision_at_1 = _precision_at(hits, case.relevant, 1)
    precision_at_3 = _precision_at(hits, case.relevant, 3)
    precision_at_5 = _precision_at(hits, case.relevant, 5)
    ndcg_at_3 = _ndcg_at(hits, case.relevant, 3)
    reciprocal_rank = _reciprocal_rank(hits, case.relevant)

    if missing_source:
        failure_cause = RetrievalFailureCause.SOURCE
    elif unresolved_chunk:
        failure_cause = RetrievalFailureCause.CHUNKING
    elif not hits:
        failure_cause = RetrievalFailureCause.QUERY
    elif recall_at_5 < 1:
        failure_cause = RetrievalFailureCause.RANKING
    else:
        failure_cause = None

    return RetrievalCaseResult(
        case_id=case.id,
        category=case.category,
        query=case.query,
        recall_at_1=recall_at_1,
        recall_at_3=recall_at_3,
        recall_at_5=recall_at_5,
        precision_at_1=precision_at_1,
        precision_at_3=precision_at_3,
        precision_at_5=precision_at_5,
        ndcg_at_3=ndcg_at_3,
        reciprocal_rank=reciprocal_rank,
        failure_cause=failure_cause,
        latency_ms=latency_ms,
        hits=serialized_hits,
    )


def _chunk_matches(
    chunk: DocumentChunk,
    reference: RelevantChunkReference,
) -> bool:
    source_id = chunk.source_artifact_id or chunk.document_id
    return source_id == reference.source_artifact_id and _normalized_text(
        reference.text_contains
    ) in _normalized_text(chunk.text)


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _recall_at(
    hits: list[RetrievalHit],
    references: list[RelevantChunkReference],
    limit: int,
) -> float:
    matched = sum(
        any(_chunk_matches(hit.chunk, reference) for hit in hits[:limit])
        for reference in references
    )
    return matched / len(references)


def _reciprocal_rank(
    hits: list[RetrievalHit],
    references: list[RelevantChunkReference],
) -> float:
    for rank, hit in enumerate(hits, start=1):
        if any(_chunk_matches(hit.chunk, reference) for reference in references):
            return 1 / rank
    return 0.0


def _precision_at(
    hits: list[RetrievalHit],
    references: list[RelevantChunkReference],
    limit: int,
) -> float:
    relevant_hits = sum(
        any(_chunk_matches(hit.chunk, reference) for reference in references)
        for hit in hits[:limit]
    )
    return relevant_hits / limit


def _ndcg_at(
    hits: list[RetrievalHit],
    references: list[RelevantChunkReference],
    limit: int,
) -> float:
    gains = [
        1.0
        if any(_chunk_matches(hit.chunk, reference) for reference in references)
        else 0.0
        for hit in hits[:limit]
    ]
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, 1))
    ideal_count = min(len(references), limit)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal if ideal else 0.0


def _serialize_hit(rank: int, hit: RetrievalHit) -> RetrievalEvaluationHit:
    chunk = hit.chunk
    return RetrievalEvaluationHit(
        rank=rank,
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        source_artifact_id=chunk.source_artifact_id or chunk.document_id,
        source_version=chunk.source_version,
        locator=chunk.locator or f"chunk {chunk.ordinal + 1}",
        relevance_score=hit.relevance_score,
    )


def _mean_metric(results: list[RetrievalCaseResult], field: str) -> float:
    values = [getattr(result, field) for result in results]
    numeric = [value for value in values if value is not None]
    return sum(numeric) / len(numeric) if numeric else 0.0


def _percentile(values: list[float], proportion: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(proportion * len(ordered)) - 1)
    return ordered[index]


def _safety_violation_count(
    results: list[RetrievalCaseResult], chunks: list[DocumentChunk]
) -> int:
    active_versions: dict[str, int] = {}
    for chunk in chunks:
        if chunk.retrieval_allowed:
            source_id = chunk.source_artifact_id or chunk.document_id
            active_versions[source_id] = max(
                chunk.source_version,
                active_versions.get(source_id, 0),
            )
    chunks_by_id = {chunk.id: chunk for chunk in chunks}
    violations = 0
    for result in results:
        for hit in result.hits:
            chunk = chunks_by_id.get(hit.chunk_id)
            if chunk is None or not chunk.retrieval_allowed:
                violations += 1
                continue
            source_id = chunk.source_artifact_id or chunk.document_id
            if active_versions.get(source_id) != chunk.source_version:
                violations += 1
    return violations


def _metrics_by_category(
    results: list[RetrievalCaseResult],
) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[RetrievalCaseResult]] = {}
    for result in results:
        grouped.setdefault(result.category.value, []).append(result)
    metrics: dict[str, dict[str, float]] = {}
    for category, members in sorted(grouped.items()):
        if members[0].category == RetrievalCaseCategory.NO_EVIDENCE:
            metrics[category] = {
                "case_count": float(len(members)),
                "no_evidence_accuracy": sum(
                    member.no_evidence_correct is True for member in members
                )
                / len(members),
            }
        else:
            metrics[category] = {
                "case_count": float(len(members)),
                "recall_at_3": _mean_metric(members, "recall_at_3"),
                "ndcg_at_3": _mean_metric(members, "ndcg_at_3"),
                "mean_reciprocal_rank": _mean_metric(members, "reciprocal_rank"),
            }
    return metrics
