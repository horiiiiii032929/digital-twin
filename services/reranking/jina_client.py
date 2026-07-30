"""Hosted Jina reranking adapter for retrieval experiments."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from services.retrieval_provider import (
    PostJson,
    RetrievalProviderError,
    RetrievalUsageLedger,
    bearer_headers,
    estimate_input_tokens,
    post_json,
)
from src.digital_twin.evaluation.retrieval_qualification import ProviderUsage


class JinaReranker:
    """Return one hosted relevance score per query-document pair."""

    def __init__(
        self,
        api_key: str,
        *,
        ledger: RetrievalUsageLedger,
        model: str = "jina-reranker-v3",
        endpoint: str = "https://api.jina.ai/v1/rerank",
        timeout_seconds: float = 60,
        transport: PostJson = post_json,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._headers = bearer_headers(api_key)
        self.ledger = ledger
        self.model = model
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        if not documents:
            return []
        values = [query, *documents]
        estimated_tokens = estimate_input_tokens(
            *(query for _ in documents),
            *documents,
        )
        self.ledger.require_capacity(estimated_tokens)
        try:
            response = self._transport(
                self.endpoint,
                self._headers,
                {
                    "model": self.model,
                    "query": query,
                    "documents": list(documents),
                    "top_n": len(documents),
                    "return_documents": False,
                },
                self.timeout_seconds,
            )
        except RetrievalProviderError:
            self.ledger.record_failure()
            raise
        self.ledger.record(
            values=values,
            estimated_input_tokens=estimated_tokens,
            response=response,
        )
        results = response.get("results")
        if not isinstance(results, list) or len(results) != len(documents):
            self.ledger.record_failure()
            raise RetrievalProviderError(
                "Jina returned the wrong reranking result count"
            )
        scores = [0.0] * len(documents)
        seen: set[int] = set()
        for item in results:
            try:
                index, score = _reranking_item(item, len(documents))
            except RetrievalProviderError:
                self.ledger.record_failure()
                raise
            if index in seen:
                self.ledger.record_failure()
                raise RetrievalProviderError(
                    "Jina returned a duplicate reranking index"
                )
            seen.add(index)
            scores[index] = score
        return scores

    def usage_snapshot(self) -> ProviderUsage:
        return self.ledger.usage_snapshot()


def _reranking_item(item: Any, document_count: int) -> tuple[int, float]:
    if not isinstance(item, dict):
        raise RetrievalProviderError("Jina reranking result has an unexpected shape")
    index = item.get("index")
    score = item.get("relevance_score")
    if not isinstance(index, int) or not 0 <= index < document_count:
        raise RetrievalProviderError("Jina reranking result has an invalid index")
    if not isinstance(score, (int, float)):
        raise RetrievalProviderError("Jina reranking result has a non-numeric score")
    return index, float(score)
