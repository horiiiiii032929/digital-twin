from __future__ import annotations

from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.reranking import RerankingRetriever


def _approved_chunk(identifier: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        id=identifier,
        document_id=f"document-{identifier}",
        text=text,
        ordinal=0,
        retrieval_allowed=True,
    )


class _StaticRetriever:
    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        del query
        chunks = [
            _approved_chunk("first", "First synthetic passage."),
            _approved_chunk("second", "Second synthetic passage."),
        ]
        return [
            RetrievalHit(chunk=chunk, relevance_score=1 - index * 0.1)
            for index, chunk in enumerate(chunks[:limit])
        ]


class _ReverseReranker:
    def score(self, query: str, documents: list[str]) -> list[float]:
        del query
        return [0.1 if document.startswith("First") else 0.9 for document in documents]


def test_reranking_reorders_candidates_and_preserves_chunks() -> None:
    retriever = RerankingRetriever(
        _StaticRetriever(),
        _ReverseReranker(),
        candidate_limit=2,
    )

    hits = retriever.retrieve("synthetic query", limit=2)

    assert [hit.chunk.text for hit in hits] == [
        "Second synthetic passage.",
        "First synthetic passage.",
    ]
    assert [hit.raw_score for hit in hits] == [0.9, 0.1]
