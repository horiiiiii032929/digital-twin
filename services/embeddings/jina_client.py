"""Hosted Jina text-embedding adapter for retrieval experiments."""

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
from src.digital_twin.model_policy import require_registered_current_model


DEFAULT_MODEL = "jina-embeddings-v5-text-small"


class JinaTextEmbedder:
    """Embed passages and queries with task-specific retrieval adapters."""

    def __init__(
        self,
        api_key: str,
        *,
        ledger: RetrievalUsageLedger,
        model: str = DEFAULT_MODEL,
        endpoint: str = "https://api.jina.ai/v1/embeddings",
        dimensions: int = 1024,
        batch_size: int = 64,
        timeout_seconds: float = 60,
        transport: PostJson = post_json,
    ) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        require_registered_current_model(model)
        self._headers = bearer_headers(api_key)
        self.ledger = ledger
        self.model = model
        self.endpoint = endpoint
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(list(texts), task="retrieval.passage")

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed([text], task="retrieval.query")
        if len(vectors) != 1:
            raise RetrievalProviderError(
                "Jina returned an unexpected query vector count"
            )
        return vectors[0]

    def usage_snapshot(self) -> ProviderUsage:
        return self.ledger.usage_snapshot()

    def _embed(self, texts: list[str], *, task: str) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            estimated_tokens = estimate_input_tokens(*batch)
            self.ledger.require_capacity(estimated_tokens)
            try:
                response = self._transport(
                    self.endpoint,
                    self._headers,
                    {
                        "model": self.model,
                        "input": batch,
                        "task": task,
                        "dimensions": self.dimensions,
                        "normalized": True,
                        "truncate": False,
                    },
                    self.timeout_seconds,
                )
            except RetrievalProviderError:
                self.ledger.record_failure()
                raise
            self.ledger.record(
                values=batch,
                estimated_input_tokens=estimated_tokens,
                response=response,
            )
            data = response.get("data")
            if not isinstance(data, list) or len(data) != len(batch):
                self.ledger.record_failure()
                raise RetrievalProviderError("Jina returned the wrong embedding count")
            try:
                ordered = sorted(data, key=_response_index)
                indices = [_response_index(item) for item in ordered]
            except RetrievalProviderError:
                self.ledger.record_failure()
                raise
            if indices != list(range(len(batch))):
                self.ledger.record_failure()
                raise RetrievalProviderError("Jina returned invalid embedding indexes")
            vectors.extend(_embedding(item) for item in ordered)
        return vectors


def _response_index(item: Any) -> int:
    if not isinstance(item, dict) or not isinstance(item.get("index"), int):
        raise RetrievalProviderError("Jina embedding response is missing an index")
    return item["index"]


def _embedding(item: Any) -> list[float]:
    if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
        raise RetrievalProviderError("Jina embedding response is missing a vector")
    try:
        vector = [float(value) for value in item["embedding"]]
    except (TypeError, ValueError) as error:
        raise RetrievalProviderError("Jina embedding vector is not numeric") from error
    if not vector:
        raise RetrievalProviderError("Jina returned an empty embedding vector")
    return vector
