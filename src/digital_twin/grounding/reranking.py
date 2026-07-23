"""Provider-independent retrieval reranking."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.grounding.protocols import Retriever


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
        if candidate_limit < 1:
            raise ValueError("candidate_limit must be at least 1")
        self.retriever = retriever
        self.reranker = reranker
        self.candidate_limit = candidate_limit

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        candidates = self.retriever.retrieve(
            query,
            limit=max(limit, self.candidate_limit),
        )
        if not candidates:
            return []
        scores = self.reranker.score(
            query,
            [candidate.chunk.text for candidate in candidates],
        )
        if len(scores) != len(candidates):
            raise ValueError("reranker returned the wrong number of scores")
        ranked = sorted(
            zip(candidates, scores, strict=True),
            key=lambda item: (-item[1], item[0].chunk.id),
        )
        return [
            RetrievalHit(
                chunk=candidate.chunk,
                relevance_score=max(0.0, min(1.0, float(score))),
                raw_score=max(0.0, float(score)),
            )
            for candidate, score in ranked[:limit]
        ]

