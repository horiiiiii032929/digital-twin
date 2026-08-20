"""Provider-independent retrieval reranking."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.retrieval import retrieval_text


class PairwiseReranker(Protocol):
    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        """Return one relevance probability per query-document pair."""


class RerankingRetriever:
    """Rerank a bounded first-stage candidate set and preserve provenance."""

    def __init__(
        self,
        retriever: Retriever,
        reranker: PairwiseReranker,
        *,
        candidate_limit: int = 40,
    ) -> None:
        if isinstance(candidate_limit, bool) or candidate_limit < 1:
            raise ValueError("candidate_limit must be at least 1")
        self.retriever = retriever
        self.reranker = reranker
        self.candidate_limit = candidate_limit

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be at least 1")
        candidates = self.retriever.retrieve(
            query,
            limit=max(limit, self.candidate_limit),
        )[: max(limit, self.candidate_limit)]
        if not candidates:
            return []
        identifiers = [candidate.chunk.id for candidate in candidates]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("reranking candidates must have unique chunk identifiers")
        scores = self.reranker.score(
            query,
            [retrieval_text(candidate.chunk) for candidate in candidates],
        )
        if len(scores) != len(candidates):
            raise ValueError("reranker returned the wrong number of scores")
        normalized_scores = [float(score) for score in scores]
        if any(
            not math.isfinite(score) or not 0 <= score <= 1
            for score in normalized_scores
        ):
            raise ValueError("reranker scores must be finite and between 0 and 1")
        ranked = sorted(
            zip(candidates, normalized_scores, strict=True),
            key=lambda item: (-item[1], item[0].chunk.id),
        )
        return [
            RetrievalHit(
                chunk=candidate.chunk,
                relevance_score=score,
                raw_score=score,
            )
            for candidate, score in ranked[:limit]
        ]
