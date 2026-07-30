"""Build the shared M0-M3 ladder inside explicit course scopes."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Any

from src.digital_twin.evaluation.retrieval_qualification import (
    CourseScopedRetriever,
    RetrievalLadderConfig,
    RetrievalMethod,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.protocols import TextEmbedder
from src.digital_twin.grounding.reranking import (
    PairwiseReranker,
    RerankingRetriever,
)
from src.digital_twin.grounding.retrieval import (
    BM25Retriever,
    DenseRetriever,
    ReciprocalRankFusionRetriever,
)


def build_course_scoped_ladders(
    chunks_by_course: Mapping[str, Sequence[DocumentChunk]],
    *,
    embedder: TextEmbedder,
    reranker: PairwiseReranker,
    config: RetrievalLadderConfig,
) -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
    if not chunks_by_course:
        raise ValueError("at least one course scope is required")

    all_chunk_ids: list[str] = []
    for course_id, chunks in chunks_by_course.items():
        if not course_id.strip():
            raise ValueError("course ID is required")
        if not chunks:
            raise ValueError(f"{course_id} has no chunks")
        all_chunk_ids.extend(chunk.id for chunk in chunks)
    if len(all_chunk_ids) != len(set(all_chunk_ids)):
        raise ValueError("a chunk cannot belong to multiple course scopes")

    runtimes: dict[str, dict[str, Any]] = {}
    index_seconds: dict[str, float] = {}
    for course_id in sorted(chunks_by_course):
        chunks = list(chunks_by_course[course_id])
        started = time.perf_counter()
        bm25 = BM25Retriever(
            chunks,
            k1=config.bm25_k1,
            b=config.bm25_b,
        )
        dense = DenseRetriever(
            chunks,
            embedder,
            minimum_similarity=-1.0,
        )
        hybrid = ReciprocalRankFusionRetriever(
            [bm25, dense],
            rank_constant=config.fusion_rank_constant,
            candidate_limit=config.fusion_candidate_limit,
        )
        reranked = RerankingRetriever(
            hybrid,
            reranker,
            candidate_limit=config.rerank_candidate_limit,
        )
        raw = {
            RetrievalMethod.M0.value: bm25,
            RetrievalMethod.M1.value: dense,
            RetrievalMethod.M2.value: hybrid,
            RetrievalMethod.M3.value: reranked,
        }
        runtimes[course_id] = {
            method: CourseScopedRetriever(
                course_id,
                retriever,
                chunks,
            )
            for method, retriever in raw.items()
        }
        index_seconds[course_id] = time.perf_counter() - started
    return runtimes, index_seconds
