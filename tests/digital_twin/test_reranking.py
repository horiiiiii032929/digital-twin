from __future__ import annotations

import pytest

from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.reranking import RerankingRetriever
from services.reranking.qwen3_client import left_pad_token_sequences


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


def test_qwen_reranker_left_padding_preserves_prompt_tokens() -> None:
    input_ids, attention_masks = left_pad_token_sequences(
        [[11, 12, 13], [21]],
        pad_token_id=0,
    )

    assert input_ids == [[11, 12, 13], [0, 0, 21]]
    assert attention_masks == [[1, 1, 1], [0, 0, 1]]


@pytest.mark.parametrize(
    ("sequences", "pad_token_id"),
    (([[1, True]], 0), ([[1]], True), ([[-1]], 0)),
)
def test_qwen_reranker_padding_rejects_invalid_token_ids(
    sequences, pad_token_id
) -> None:
    with pytest.raises(ValueError):
        left_pad_token_sequences(sequences, pad_token_id=pad_token_id)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -0.1, 1.1])
def test_reranking_rejects_invalid_provider_scores(score: float) -> None:
    class InvalidReranker:
        def score(self, query, documents):
            del query
            return [score for _ in documents]

    retriever = RerankingRetriever(_StaticRetriever(), InvalidReranker())

    with pytest.raises(ValueError, match="finite and between 0 and 1"):
        retriever.retrieve("synthetic query")
