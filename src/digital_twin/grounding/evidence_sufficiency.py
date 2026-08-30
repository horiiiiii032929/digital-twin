"""Swappable, inspectable gates between retrieval and generation."""

import math
import time
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.action_router import required_atomic_claim_count
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
_QUESTION_CONTEXT_WORDS = {
    "according",
    "answer",
    "approved",
    "assignment",
    "earlier",
    "explain",
    "full",
    "graded",
    "note",
    "notes",
    "only",
    "previous",
    "require",
    "requires",
    "rule",
    "say",
    "says",
    "using",
}


class EvidenceSufficiencyDecision(BaseModel):
    sufficient: bool
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    reason: str = Field(min_length=1)
    features: dict[str, float | int | bool] = Field(default_factory=dict)
    selected_hit_ids: list[str] = Field(default_factory=list)

    @field_validator("selected_hit_ids")
    @classmethod
    def selected_hit_ids_must_be_unique(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("selected_hit_ids cannot contain blank IDs")
        if len(values) != len(set(values)):
            raise ValueError("selected_hit_ids must be unique")
        return values


class EvidenceSufficiencyCaseResult(BaseModel):
    case_id: str
    category: RetrievalCaseCategory
    expected_answerable: bool
    predicted_answerable: bool
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
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


class EvidenceSupportSignals(BaseModel):
    """Provider-neutral semantic signals used by the open-set v2 gate.

    The verifier may score evidence, but it cannot return the final product
    decision. Referenced hit IDs are checked against the exact eligible hits
    supplied by retrieval before the signals can be used.
    """

    direct_support: float = Field(ge=0, le=1, allow_inf_nan=False)
    completeness: float = Field(ge=0, le=1, allow_inf_nan=False)
    contradiction: float = Field(ge=0, le=1, allow_inf_nan=False)
    ambiguity: float = Field(ge=0, le=1, allow_inf_nan=False)
    supporting_hit_ids: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)

    @field_validator("supporting_hit_ids")
    @classmethod
    def supporting_hit_ids_must_be_unique(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("supporting_hit_ids cannot contain blank IDs")
        if len(values) != len(set(values)):
            raise ValueError("supporting_hit_ids must be unique")
        return values


class EvidenceSupportVerifier(Protocol):
    """Score semantic support without owning the final answer/abstain policy."""

    implementation_id: str
    version: str

    def verify(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSupportSignals:
        """Return bounded support signals for the exact retrieved evidence."""


class CalibratedOpenSetEvidenceGate:
    """Fail-closed policy over independently calibrated support signals."""

    implementation_id = "calibrated-open-set-evidence-gate-v2"

    def __init__(
        self,
        verifier: EvidenceSupportVerifier,
        *,
        minimum_direct_support: float,
        minimum_completeness: float,
        maximum_contradiction: float,
        maximum_ambiguity: float,
        minimum_supporting_hits: int = 1,
        evidence_limit: int = 5,
    ) -> None:
        self._validate_probability(
            minimum_direct_support,
            "minimum_direct_support",
        )
        self._validate_probability(minimum_completeness, "minimum_completeness")
        self._validate_probability(maximum_contradiction, "maximum_contradiction")
        self._validate_probability(maximum_ambiguity, "maximum_ambiguity")
        if isinstance(minimum_supporting_hits, bool) or minimum_supporting_hits < 1:
            raise ValueError("minimum_supporting_hits must be at least 1")
        if isinstance(evidence_limit, bool) or evidence_limit < 1:
            raise ValueError("evidence_limit must be at least 1")
        if minimum_supporting_hits > evidence_limit:
            raise ValueError("minimum_supporting_hits cannot exceed evidence_limit")
        if not getattr(verifier, "implementation_id", ""):
            raise ValueError("verifier must declare implementation_id")
        if not getattr(verifier, "version", ""):
            raise ValueError("verifier must declare version")
        self.verifier = verifier
        self.minimum_direct_support = minimum_direct_support
        self.minimum_completeness = minimum_completeness
        self.maximum_contradiction = maximum_contradiction
        self.maximum_ambiguity = maximum_ambiguity
        self.minimum_supporting_hits = minimum_supporting_hits
        self.evidence_limit = evidence_limit

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        bounded_hits = list(hits[: self.evidence_limit])
        if not bounded_hits:
            return self._rejected(
                "no eligible evidence was retrieved",
                verifier_called=False,
                hit_count=0,
            )

        try:
            raw_signals = self.verifier.verify(query, bounded_hits)
            signals = EvidenceSupportSignals.model_validate(raw_signals)
        except Exception as error:  # The release boundary must fail closed.
            return self._rejected(
                "evidence verifier failed closed",
                verifier_called=True,
                hit_count=len(bounded_hits),
                verifier_error=True,
                verifier_error_type=type(error).__name__,
            )

        eligible_hit_ids = {hit.chunk.id for hit in bounded_hits}
        supporting_hit_ids = set(signals.supporting_hit_ids)
        if not supporting_hit_ids.issubset(eligible_hit_ids):
            return self._rejected(
                "evidence verifier referenced an unknown hit",
                verifier_called=True,
                hit_count=len(bounded_hits),
                verifier_output_valid=False,
            )

        checks = {
            "direct_support_passed": (
                signals.direct_support >= self.minimum_direct_support
            ),
            "completeness_passed": (
                signals.completeness >= self.minimum_completeness
            ),
            "contradiction_passed": (
                signals.contradiction <= self.maximum_contradiction
            ),
            "ambiguity_passed": signals.ambiguity <= self.maximum_ambiguity,
            "supporting_hits_passed": (
                len(supporting_hit_ids) >= self.minimum_supporting_hits
            ),
        }
        sufficient = all(checks.values())
        score = min(
            signals.direct_support,
            signals.completeness,
            1 - signals.contradiction,
            1 - signals.ambiguity,
        )
        return EvidenceSufficiencyDecision(
            sufficient=sufficient,
            score=score,
            reason=(
                "retrieved evidence passes calibrated open-set support checks"
                if sufficient
                else "retrieved evidence fails calibrated open-set support checks"
            ),
            features={
                "hit_count": len(bounded_hits),
                "direct_support": signals.direct_support,
                "completeness": signals.completeness,
                "contradiction": signals.contradiction,
                "ambiguity": signals.ambiguity,
                "supporting_hit_count": len(supporting_hit_ids),
                "minimum_direct_support": self.minimum_direct_support,
                "minimum_completeness": self.minimum_completeness,
                "maximum_contradiction": self.maximum_contradiction,
                "maximum_ambiguity": self.maximum_ambiguity,
                "minimum_supporting_hits": self.minimum_supporting_hits,
                "verifier_called": True,
                "verifier_error": False,
                "verifier_output_valid": True,
                **checks,
            },
            selected_hit_ids=(
                [
                    hit.chunk.id
                    for hit in bounded_hits
                    if hit.chunk.id in supporting_hit_ids
                ]
                if sufficient
                else []
            ),
        )

    @staticmethod
    def _validate_probability(value: float, name: str) -> None:
        if (
            isinstance(value, bool)
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError(f"{name} must be between 0 and 1")

    def _rejected(
        self,
        reason: str,
        *,
        verifier_called: bool,
        hit_count: int,
        verifier_error: bool = False,
        verifier_error_type: str | None = None,
        verifier_output_valid: bool = True,
    ) -> EvidenceSufficiencyDecision:
        features: dict[str, float | int | bool] = {
            "hit_count": hit_count,
            "verifier_called": verifier_called,
            "verifier_error": verifier_error,
            "verifier_output_valid": verifier_output_valid,
        }
        if verifier_error_type is not None:
            # Avoid leaking provider or exception text through product traces.
            features["verifier_error_type_known"] = bool(verifier_error_type)
        return EvidenceSufficiencyDecision(
            sufficient=False,
            score=0.0,
            reason=reason,
            features=features,
        )


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
        if (
            isinstance(minimum_raw_score, bool)
            or not math.isfinite(minimum_raw_score)
            or minimum_raw_score < 0
        ):
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
        if (
            isinstance(minimum_query_coverage, bool)
            or not math.isfinite(minimum_query_coverage)
            or not 0 <= minimum_query_coverage <= 1
        ):
            raise ValueError("minimum_query_coverage must be between 0 and 1")
        if isinstance(minimum_matching_terms, bool) or minimum_matching_terms < 1:
            raise ValueError("minimum_matching_terms must be at least 1")
        if isinstance(evidence_limit, bool) or evidence_limit < 1:
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


class StructuredLexicalCoverageEvidenceGate:
    """Select evidence using source aliases plus inspectable lexical support.

    This is a deterministic development control, not a semantic verifier. Source
    aliases must come from search metadata and never from evaluator labels.
    """

    implementation_id = "structured-lexical-coverage-evidence-gate-v1"

    def __init__(
        self,
        *,
        minimum_content_matching_terms: int = 2,
        evidence_limit: int = 5,
    ) -> None:
        if (
            isinstance(minimum_content_matching_terms, bool)
            or minimum_content_matching_terms < 1
        ):
            raise ValueError("minimum_content_matching_terms must be at least 1")
        if isinstance(evidence_limit, bool) or evidence_limit < 1:
            raise ValueError("evidence_limit must be at least 1")
        self.minimum_content_matching_terms = minimum_content_matching_terms
        self.evidence_limit = evidence_limit

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        query_terms = {
            token
            for token in lexical_tokens(query)
            if token not in _STOP_WORDS and token not in _QUESTION_CONTEXT_WORDS
        }
        alias_selected: list[RetrievalHit] = []
        content_selected: list[RetrievalHit] = []
        matched_terms: set[str] = set()
        for hit in hits[: self.evidence_limit]:
            content_overlap = query_terms & set(lexical_tokens(hit.chunk.text))
            alias_terms = set(
                lexical_tokens(hit.chunk.metadata.get("search_description", ""))
            )
            alias_overlap = query_terms & alias_terms
            if alias_overlap:
                alias_selected.append(hit)
                matched_terms.update(alias_overlap)
            elif len(content_overlap) >= self.minimum_content_matching_terms:
                content_selected.append(hit)
                matched_terms.update(content_overlap)
        selected = alias_selected or content_selected
        score = len(matched_terms) / len(query_terms) if query_terms else 0.0
        sufficient = bool(selected)
        return EvidenceSufficiencyDecision(
            sufficient=sufficient,
            score=score,
            reason=(
                "source aliases or content terms support the question"
                if sufficient
                else "no source alias or content-term support was found"
            ),
            features={
                "candidate_hit_count": min(len(hits), self.evidence_limit),
                "selected_hit_count": len(selected),
                "query_term_count": len(query_terms),
                "matching_term_count": len(matched_terms),
                "alias_match_count": len(alias_selected),
                "minimum_content_matching_terms": self.minimum_content_matching_terms,
                "evidence_limit": self.evidence_limit,
            },
            selected_hit_ids=[hit.chunk.id for hit in selected],
        )


class QuestionTargetedAtomicEvidenceGate:
    """Narrow supported evidence to the one or two facts requested by the question.

    The wrapped structured gate remains the answerability control. This successor
    changes only which already-approved atoms reach generation. It uses public
    question terms, immutable source text/search aliases, and retrieval scores;
    it cannot inspect evaluation labels or hidden gold.
    """

    implementation_id = "question-targeted-atomic-evidence-gate-v1"

    def __init__(
        self,
        *,
        base_gate: StructuredLexicalCoverageEvidenceGate | None = None,
    ) -> None:
        self.base_gate = base_gate or StructuredLexicalCoverageEvidenceGate()

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        decision = self.base_gate.assess(query, hits)
        if not decision.sufficient:
            return decision.model_copy(
                update={
                    "reason": "structured support failed before target selection",
                    "features": {
                        **decision.features,
                        "target_claim_count": required_atomic_claim_count(query),
                        "target_selection_applied": False,
                    },
                }
            )
        allowed = set(decision.selected_hit_ids)
        candidates = [
            (index, hit)
            for index, hit in enumerate(hits)
            if not allowed or hit.chunk.id in allowed
        ]
        query_terms = {
            token
            for token in lexical_tokens(query)
            if token not in _STOP_WORDS and token not in _QUESTION_CONTEXT_WORDS
        }

        def ranking_terms(value: str) -> set[str]:
            terms: set[str] = set()
            for token in lexical_tokens(value):
                normalized = token
                if len(normalized) > 4 and normalized.endswith("s"):
                    normalized = normalized[:-1]
                if len(normalized) > 4 and normalized.endswith("e"):
                    normalized = normalized[:-1]
                terms.add(normalized)
            return terms

        query_ranking_terms = ranking_terms(" ".join(sorted(query_terms)))

        def rank_key(row: tuple[int, RetrievalHit]) -> tuple[int, int, float, int, str]:
            index, hit = row
            content_overlap = len(
                query_ranking_terms & ranking_terms(hit.chunk.text)
            )
            alias_overlap = len(
                query_ranking_terms
                & ranking_terms(hit.chunk.metadata.get("search_description", ""))
            )
            return (
                -content_overlap,
                -alias_overlap,
                -hit.relevance_score,
                index,
                hit.chunk.id,
            )

        target_count = required_atomic_claim_count(query)
        selected = [hit for _, hit in sorted(candidates, key=rank_key)[:target_count]]
        sufficient = len(selected) == target_count
        return EvidenceSufficiencyDecision(
            sufficient=sufficient,
            score=decision.score if sufficient else 0.0,
            reason=(
                "question-targeted authoritative atoms selected"
                if sufficient
                else "insufficient distinct authoritative atoms for the requested answer"
            ),
            features={
                **decision.features,
                "target_claim_count": target_count,
                "target_selected_hit_count": len(selected),
                "target_selection_applied": True,
            },
            selected_hit_ids=[hit.chunk.id for hit in selected],
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
        if (
            isinstance(minimum_relevance_score, bool)
            or not math.isfinite(minimum_relevance_score)
            or not 0 <= minimum_relevance_score <= 1
        ):
            raise ValueError("minimum_relevance_score must be between 0 and 1")
        if isinstance(secondary_limit, bool) or secondary_limit < 1:
            raise ValueError("secondary_limit must be at least 1")
        if not isinstance(require_source_overlap, bool):
            raise ValueError("require_source_overlap must be a boolean")
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
            if (hit.chunk.source_artifact_id or hit.chunk.document_id)
            in primary_sources
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
        if isinstance(candidate_limit, bool) or candidate_limit < 1:
            raise ValueError("candidate_limit must be at least 1")
        self.retriever = retriever
        self.gate = gate
        self.candidate_limit = candidate_limit

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise ValueError("retrieval limit must be at least 1")
        hits = self.retriever.retrieve(
            query,
            limit=max(limit, self.candidate_limit),
        )
        decision = self.gate.assess(query, hits)
        return list(hits[:limit]) if decision.sufficient else []


class _CapturingEvidenceGatedRetriever(EvidenceGatedRetriever):
    """Capture the exact gate decision made during one evaluation retrieval."""

    def __init__(self, retriever, gate, *, candidate_limit: int) -> None:
        super().__init__(retriever, gate, candidate_limit=candidate_limit)
        self.captures: list[tuple[EvidenceSufficiencyDecision, float]] = []

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise ValueError("retrieval limit must be at least 1")
        hits = self.retriever.retrieve(
            query,
            limit=max(limit, self.candidate_limit),
        )
        started = time.perf_counter()
        decision = self.gate.assess(query, hits)
        latency_ms = (time.perf_counter() - started) * 1000
        self.captures.append((decision, latency_ms))
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
    gated = _CapturingEvidenceGatedRetriever(
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
    if len(gated.captures) != len(evaluation_set.cases):
        raise RuntimeError("evidence evaluation did not capture one decision per case")
    decisions: list[EvidenceSufficiencyCaseResult] = []
    gate_latencies: list[float] = []
    for case, (decision, latency_ms) in zip(
        evaluation_set.cases,
        gated.captures,
        strict=True,
    ):
        gate_latencies.append(latency_ms)
        decisions.append(
            EvidenceSufficiencyCaseResult(
                case_id=case.id,
                category=case.category,
                expected_answerable=case.category != RetrievalCaseCategory.NO_EVIDENCE,
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
        decision.case_id for decision in answerable if decision.predicted_answerable
    }
    accepted_retrieval = [
        result for result in retrieval_summary.cases if result.case_id in accepted_ids
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
