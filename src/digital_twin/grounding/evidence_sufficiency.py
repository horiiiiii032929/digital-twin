"""Swappable, inspectable gates between retrieval and generation."""

import time
from collections.abc import Sequence

from pydantic import BaseModel, Field

from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.grounding.retrieval import lexical_tokens
from src.digital_twin.grounding.retrieval_evaluation import (
    RetrievalCaseCategory,
    RetrievalEvaluationSet,
    RetrievalEvaluationSummary,
    evaluate_retriever,
)


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "should",
    "the",
    "to",
    "what",
    "when",
    "which",
    "why",
    "with",
}


class EvidenceSufficiencyDecision(BaseModel):
    sufficient: bool
    score: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1)
    features: dict[str, float | int | bool] = Field(default_factory=dict)


class EvidenceSufficiencyCaseResult(BaseModel):
    case_id: str
    category: RetrievalCaseCategory
    expected_answerable: bool
    predicted_answerable: bool
    score: float = Field(ge=0, le=1)
    reason: str
    features: dict[str, float | int | bool]


class EvidenceSufficiencyEvaluationSummary(BaseModel):
    candidate: str
    dataset_version: str
    case_count: int = Field(ge=0)
    answerable_case_count: int = Field(ge=0)
    no_evidence_case_count: int = Field(ge=0)
    answerable_recall: float = Field(ge=0, le=1)
    no_evidence_accuracy: float = Field(ge=0, le=1)
    balanced_accuracy: float = Field(ge=0, le=1)
    false_answer_count: int = Field(ge=0)
    false_abstention_count: int = Field(ge=0)
    unconditional_recall_at_3: float = Field(ge=0, le=1)
    unconditional_ndcg_at_3: float = Field(ge=0, le=1)
    conditional_recall_at_3: float = Field(ge=0, le=1)
    conditional_ndcg_at_3: float = Field(ge=0, le=1)
    mean_gate_latency_ms: float = Field(ge=0)
    safety_violation_count: int = Field(ge=0)
    answerability_by_category: dict[str, dict[str, float | int]]
    decisions: list[EvidenceSufficiencyCaseResult]
    retrieval: RetrievalEvaluationSummary


class AnyHitEvidenceGate:
    """Control representing the current behavior: any ranked hit permits use."""

    implementation_id = "any-hit-evidence-gate"

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        del query
        return EvidenceSufficiencyDecision(
            sufficient=bool(hits),
            score=1.0 if hits else 0.0,
            reason="at least one eligible hit exists" if hits else "no hit exists",
            features={"hit_count": len(hits)},
        )


class MinimumRawScoreEvidenceGate:
    """Require the ranker's absolute top score to clear a calibrated cutoff."""

    implementation_id = "minimum-raw-score-evidence-gate"

    def __init__(self, minimum_raw_score: float) -> None:
        if minimum_raw_score < 0:
            raise ValueError("minimum_raw_score cannot be negative")
        self.minimum_raw_score = minimum_raw_score

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        del query
        top_score = hits[0].raw_score if hits else None
        comparable_score = float(top_score or 0.0)
        sufficient = top_score is not None and top_score >= self.minimum_raw_score
        normalized = (
            min(1.0, comparable_score / self.minimum_raw_score)
            if self.minimum_raw_score > 0
            else float(bool(hits))
        )
        return EvidenceSufficiencyDecision(
            sufficient=sufficient,
            score=normalized,
            reason=(
                "top raw score clears the calibrated cutoff"
                if sufficient
                else "top raw score is below the calibrated cutoff"
            ),
            features={
                "hit_count": len(hits),
                "top_raw_score": comparable_score,
                "minimum_raw_score": self.minimum_raw_score,
            },
        )


class LexicalCoverageEvidenceGate:
    """Require retrieved text to cover enough informative query terms."""

    implementation_id = "lexical-coverage-evidence-gate"

    def __init__(
        self,
        *,
        minimum_query_coverage: float,
        minimum_matching_terms: int,
        evidence_limit: int = 3,
    ) -> None:
        if not 0 <= minimum_query_coverage <= 1:
            raise ValueError("minimum_query_coverage must be between 0 and 1")
        if minimum_matching_terms < 1:
            raise ValueError("minimum_matching_terms must be at least 1")
        if evidence_limit < 1:
            raise ValueError("evidence_limit must be at least 1")
        self.minimum_query_coverage = minimum_query_coverage
        self.minimum_matching_terms = minimum_matching_terms
        self.evidence_limit = evidence_limit

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        query_terms = {
            token for token in lexical_tokens(query) if token not in _STOP_WORDS
        }
        evidence_terms = {
            token
            for hit in hits[: self.evidence_limit]
            for token in lexical_tokens(hit.chunk.text)
        }
        matching_terms = query_terms & evidence_terms
        coverage = len(matching_terms) / len(query_terms) if query_terms else 0.0
        sufficient = bool(hits) and (
            coverage >= self.minimum_query_coverage
            and len(matching_terms) >= self.minimum_matching_terms
        )
        return EvidenceSufficiencyDecision(
            sufficient=sufficient,
            score=coverage,
            reason=(
                "retrieved evidence covers the calibrated query-term minimum"
                if sufficient
                else "retrieved evidence lacks calibrated lexical support"
            ),
            features={
                "hit_count": len(hits),
                "query_term_count": len(query_terms),
                "matching_term_count": len(matching_terms),
                "query_coverage": coverage,
                "minimum_query_coverage": self.minimum_query_coverage,
                "minimum_matching_terms": self.minimum_matching_terms,
                "evidence_limit": self.evidence_limit,
            },
        )


class SecondaryRetrieverAgreementGate:
    """Require an independent retriever to support the primary evidence."""

    implementation_id = "secondary-retriever-agreement-gate"

    def __init__(
        self,
        secondary_retriever,
        *,
        minimum_relevance_score: float,
        secondary_limit: int = 5,
        require_source_overlap: bool = True,
    ) -> None:
        if not 0 <= minimum_relevance_score <= 1:
            raise ValueError("minimum_relevance_score must be between 0 and 1")
        if secondary_limit < 1:
            raise ValueError("secondary_limit must be at least 1")
        self.secondary_retriever = secondary_retriever
        self.minimum_relevance_score = minimum_relevance_score
        self.secondary_limit = secondary_limit
        self.require_source_overlap = require_source_overlap

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        secondary_hits = self.secondary_retriever.retrieve(
            query,
            limit=self.secondary_limit,
        )
        supported = [
            hit
            for hit in secondary_hits
            if hit.relevance_score >= self.minimum_relevance_score
        ]
        primary_sources = {
            hit.chunk.source_artifact_id or hit.chunk.document_id for hit in hits
        }
        agreeing = [
            hit
            for hit in supported
            if hit.chunk.source_artifact_id or hit.chunk.document_id in primary_sources
        ]
        evidence = agreeing if self.require_source_overlap else supported
        score = max((hit.relevance_score for hit in evidence), default=0.0)
        sufficient = bool(hits) and bool(evidence)
        return EvidenceSufficiencyDecision(
            sufficient=sufficient,
            score=score,
            reason=(
                "independent retrieval supports the primary evidence"
                if sufficient
                else "independent retrieval does not support the primary evidence"
            ),
            features={
                "primary_hit_count": len(hits),
                "secondary_hit_count": len(secondary_hits),
                "supported_secondary_hit_count": len(supported),
                "agreeing_source_count": len(
                    {
                        hit.chunk.source_artifact_id or hit.chunk.document_id
                        for hit in agreeing
                    }
                ),
                "minimum_relevance_score": self.minimum_relevance_score,
                "require_source_overlap": self.require_source_overlap,
            },
        )


class EvidenceGatedRetriever:
    """Return ranked hits only when the injected evidence gate accepts them."""

    def __init__(
        self,
        retriever,
        gate,
        *,
        candidate_limit: int = 20,
    ) -> None:
        if candidate_limit < 1:
            raise ValueError("candidate_limit must be at least 1")
        self.retriever = retriever
        self.gate = gate
        self.candidate_limit = candidate_limit

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if limit < 1:
            raise ValueError("retrieval limit must be at least 1")
        hits = self.retriever.retrieve(
            query,
            limit=max(limit, self.candidate_limit),
        )
        decision = self.gate.assess(query, hits)
        return list(hits[:limit]) if decision.sufficient else []


def evaluate_evidence_sufficiency(
    name: str,
    retriever,
    gate,
    chunks,
    evaluation_set: RetrievalEvaluationSet,
    *,
    candidate_limit: int = 20,
) -> EvidenceSufficiencyEvaluationSummary:
    gated = EvidenceGatedRetriever(
        retriever,
        gate,
        candidate_limit=candidate_limit,
    )
    retrieval_summary = evaluate_retriever(
        name,
        gated,
        chunks,
        evaluation_set,
    )
    decisions: list[EvidenceSufficiencyCaseResult] = []
    gate_latencies: list[float] = []
    for case in evaluation_set.cases:
        hits = retriever.retrieve(case.query, limit=candidate_limit)
        started = time.perf_counter()
        decision = gate.assess(case.query, hits)
        gate_latencies.append((time.perf_counter() - started) * 1000)
        decisions.append(
            EvidenceSufficiencyCaseResult(
                case_id=case.id,
                category=case.category,
                expected_answerable=case.category
                != RetrievalCaseCategory.NO_EVIDENCE,
                predicted_answerable=decision.sufficient,
                score=decision.score,
                reason=decision.reason,
                features=decision.features,
            )
        )

    answerable = [decision for decision in decisions if decision.expected_answerable]
    no_evidence = [
        decision for decision in decisions if not decision.expected_answerable
    ]
    accepted_ids = {
        decision.case_id
        for decision in answerable
        if decision.predicted_answerable
    }
    accepted_retrieval = [
        result
        for result in retrieval_summary.cases
        if result.case_id in accepted_ids
    ]
    answerable_recall = _ratio(
        sum(decision.predicted_answerable for decision in answerable),
        len(answerable),
    )
    no_evidence_accuracy = _ratio(
        sum(not decision.predicted_answerable for decision in no_evidence),
        len(no_evidence),
    )
    return EvidenceSufficiencyEvaluationSummary(
        candidate=name,
        dataset_version=evaluation_set.version,
        case_count=len(decisions),
        answerable_case_count=len(answerable),
        no_evidence_case_count=len(no_evidence),
        answerable_recall=answerable_recall,
        no_evidence_accuracy=no_evidence_accuracy,
        balanced_accuracy=(answerable_recall + no_evidence_accuracy) / 2,
        false_answer_count=sum(
            decision.predicted_answerable for decision in no_evidence
        ),
        false_abstention_count=sum(
            not decision.predicted_answerable for decision in answerable
        ),
        unconditional_recall_at_3=retrieval_summary.recall_at_3,
        unconditional_ndcg_at_3=retrieval_summary.ndcg_at_3,
        conditional_recall_at_3=_mean_case_metric(
            accepted_retrieval,
            "recall_at_3",
        ),
        conditional_ndcg_at_3=_mean_case_metric(
            accepted_retrieval,
            "ndcg_at_3",
        ),
        mean_gate_latency_ms=(
            sum(gate_latencies) / len(gate_latencies) if gate_latencies else 0.0
        ),
        safety_violation_count=retrieval_summary.safety_violation_count,
        answerability_by_category=_answerability_by_category(decisions),
        decisions=decisions,
        retrieval=retrieval_summary,
    )


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _mean_case_metric(results, field: str) -> float:
    values = [getattr(result, field) for result in results]
    numeric = [float(value) for value in values if value is not None]
    return sum(numeric) / len(numeric) if numeric else 0.0


def _answerability_by_category(
    decisions: Sequence[EvidenceSufficiencyCaseResult],
) -> dict[str, dict[str, float | int]]:
    categories: dict[str, list[EvidenceSufficiencyCaseResult]] = {}
    for decision in decisions:
        categories.setdefault(decision.category.value, []).append(decision)
    return {
        category: {
            "case_count": len(members),
            "accuracy": _ratio(
                sum(
                    member.expected_answerable == member.predicted_answerable
                    for member in members
                ),
                len(members),
            ),
            "false_answer_count": sum(
                not member.expected_answerable and member.predicted_answerable
                for member in members
            ),
            "false_abstention_count": sum(
                member.expected_answerable and not member.predicted_answerable
                for member in members
            ),
        }
        for category, members in sorted(categories.items())
    }
