"""Inspectable evidence-support verifiers for the open-set release gate.

The verifiers in this module emit bounded advisory signals only.  The
deterministic :class:`CalibratedOpenSetEvidenceGate` remains the sole owner of
the final answer/abstain decision and validates every referenced hit ID.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from src.digital_twin.grounding.evidence_sufficiency import (
    EvidenceSupportSignals,
)
from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.grounding.retrieval import lexical_tokens


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


def _probability(value: float, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or not 0 <= numeric <= 1:
        raise ValueError(f"{name} must be a finite probability")
    return numeric


def _informative_terms(text: str) -> set[str]:
    return {token for token in lexical_tokens(text) if token not in _STOP_WORDS}


def _coverage(query: str, evidence: str) -> float:
    query_terms = _informative_terms(query)
    if not query_terms:
        return 0.0
    return len(query_terms & set(lexical_tokens(evidence))) / len(query_terms)


def _score_margin_ambiguity(scores: Sequence[float]) -> float:
    """Conservative ambiguity proxy based on competing high-scoring hits."""

    ranked = sorted((_probability(score, "support score") for score in scores), reverse=True)
    if len(ranked) < 2 or ranked[1] < 0.5:
        return 0.0
    return min(1.0, ranked[1] * (1.0 - (ranked[0] - ranked[1])))


class PairScoreBackend(Protocol):
    implementation_id: str
    version: str

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        """Return one finite probability for each text pair."""


@dataclass(frozen=True)
class NliProbabilities:
    contradiction: float
    entailment: float
    neutral: float

    def __post_init__(self) -> None:
        values = (
            _probability(self.contradiction, "contradiction"),
            _probability(self.entailment, "entailment"),
            _probability(self.neutral, "neutral"),
        )
        if not math.isclose(sum(values), 1.0, rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError("NLI probabilities must sum to one")


class NliScoreBackend(Protocol):
    implementation_id: str
    version: str

    def score_pairs(
        self,
        pairs: Sequence[tuple[str, str]],
    ) -> list[NliProbabilities]:
        """Return contradiction, entailment, and neutral probabilities."""


class LocalCrossEncoderBackend:
    """Lazy, revision-pinned Sentence Transformers cross-encoder adapter."""

    def __init__(
        self,
        *,
        model_id: str,
        revision: str,
        max_length: int = 512,
        batch_size: int = 8,
        local_files_only: bool = False,
    ) -> None:
        if not model_id or not revision:
            raise ValueError("model_id and revision are required")
        if max_length < 1 or batch_size < 1:
            raise ValueError("max_length and batch_size must be positive")
        self.model_id = model_id
        self.revision = revision
        self.max_length = max_length
        self.batch_size = batch_size
        self.local_files_only = local_files_only
        self.implementation_id = f"sentence-transformers-cross-encoder:{model_id}"
        self.version = revision
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self.model_id,
                revision=self.revision,
                max_length=self.max_length,
                local_files_only=self.local_files_only,
                trust_remote_code=False,
            )
        return self._model

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        scores = self._load().predict(
            list(pairs),
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        flattened = [float(value) for value in scores.reshape(-1).tolist()]
        if len(flattened) != len(pairs):
            raise ValueError("cross-encoder returned the wrong number of scores")
        return [_probability(value, "cross-encoder score") for value in flattened]


class LocalNliCrossEncoderBackend(LocalCrossEncoderBackend):
    """Revision-pinned NLI adapter with the model card's fixed label order."""

    def score_pairs(
        self,
        pairs: Sequence[tuple[str, str]],
    ) -> list[NliProbabilities]:
        if not pairs:
            return []
        rows = self._load().predict(
            list(pairs),
            batch_size=self.batch_size,
            show_progress_bar=False,
            apply_softmax=True,
            convert_to_numpy=True,
        )
        if len(rows) != len(pairs):
            raise ValueError("NLI model returned the wrong number of scores")
        probabilities: list[NliProbabilities] = []
        for row in rows.tolist():
            if len(row) != 3:
                raise ValueError("NLI model must return exactly three labels")
            probabilities.append(
                NliProbabilities(
                    contradiction=float(row[0]),
                    entailment=float(row[1]),
                    neutral=float(row[2]),
                )
            )
        return probabilities


class InspectableFeatureSupportVerifier:
    """Deterministic lexical feature control with no learned model."""

    implementation_id = "inspectable-feature-classifier-v2"
    version = "2.0.0"

    def __init__(self, *, supporting_hit_threshold: float = 0.5) -> None:
        self.supporting_hit_threshold = _probability(
            supporting_hit_threshold,
            "supporting_hit_threshold",
        )

    def verify(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSupportSignals:
        if not hits:
            raise ValueError("at least one hit is required")
        scores = [_coverage(query, hit.chunk.text) for hit in hits]
        supporting = [
            hit.chunk.id
            for hit, score in zip(hits, scores, strict=True)
            if score >= self.supporting_hit_threshold
        ]
        aggregate = " ".join(hit.chunk.text for hit in hits)
        return EvidenceSupportSignals(
            direct_support=max(scores),
            completeness=_coverage(query, aggregate),
            contradiction=0.0,
            ambiguity=_score_margin_ambiguity(scores),
            supporting_hit_ids=supporting,
            reason="deterministic query-to-evidence lexical features",
        )


class CrossEncoderSupportVerifier:
    """Cross-encoder support scoring plus inspectable coverage features."""

    implementation_id = "cross-encoder-support-verifier-v2"
    version = "2.0.0"

    def __init__(
        self,
        backend: PairScoreBackend,
        *,
        supporting_hit_threshold: float,
    ) -> None:
        self.backend = backend
        self.supporting_hit_threshold = _probability(
            supporting_hit_threshold,
            "supporting_hit_threshold",
        )

    def verify(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSupportSignals:
        if not hits:
            raise ValueError("at least one hit is required")
        scores = self.backend.score_pairs([(query, hit.chunk.text) for hit in hits])
        if len(scores) != len(hits):
            raise ValueError("support backend returned the wrong number of scores")
        validated_scores = [_probability(score, "support score") for score in scores]
        supporting_pairs = [
            (hit, score)
            for hit, score in zip(hits, validated_scores, strict=True)
            if score >= self.supporting_hit_threshold
        ]
        supporting_text = " ".join(hit.chunk.text for hit, _ in supporting_pairs)
        direct_support = max(validated_scores)
        lexical_completeness = _coverage(query, supporting_text)
        completeness = max(
            lexical_completeness,
            direct_support if len(supporting_pairs) == 1 else 0.0,
        )
        return EvidenceSupportSignals(
            direct_support=direct_support,
            completeness=completeness,
            contradiction=0.0,
            ambiguity=_score_margin_ambiguity(validated_scores),
            supporting_hit_ids=[hit.chunk.id for hit, _ in supporting_pairs],
            reason=(
                "revision-pinned cross-encoder support with deterministic "
                "query coverage"
            ),
        )


class CrossEncoderNliCompletenessVerifier:
    """Support verifier augmented by pairwise evidence contradiction checks.

    NLI is intentionally not applied to the interrogative query.  It checks
    whether independently supporting evidence passages contradict one another;
    completeness remains an inspectable query-coverage signal.
    """

    implementation_id = "cross-encoder-nli-completeness-verifier-v2"
    version = "2.0.0"

    def __init__(
        self,
        support_verifier: CrossEncoderSupportVerifier,
        nli_backend: NliScoreBackend,
    ) -> None:
        self.support_verifier = support_verifier
        self.nli_backend = nli_backend

    def verify(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSupportSignals:
        support = self.support_verifier.verify(query, hits)
        by_id = {hit.chunk.id: hit for hit in hits}
        supporting_hits = [by_id[hit_id] for hit_id in support.supporting_hit_ids]
        pairs = [
            (left.chunk.text, right.chunk.text)
            for index, left in enumerate(supporting_hits)
            for right in supporting_hits[index + 1 :]
        ]
        nli_rows = self.nli_backend.score_pairs(pairs)
        if len(nli_rows) != len(pairs):
            raise ValueError("NLI backend returned the wrong number of scores")
        contradiction = max(
            (row.contradiction for row in nli_rows),
            default=0.0,
        )
        return support.model_copy(
            update={
                "contradiction": contradiction,
                "reason": (
                    "revision-pinned support scoring, deterministic query "
                    "coverage, and pairwise evidence NLI"
                ),
            }
        )
