"""Hosted Jina text-embedding adapter for retrieval experiments."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from services.jina_api import (
    JinaAPIError,
    JinaPostJson,
    JinaUsageLedger,
    estimate_input_tokens,
    jina_headers,
    post_json,
)


class JinaTextEmbedder:
    """Embed passages and queries with separate retrieval task adapters."""

    def __init__(
        self,
        api_key: str,
        *,
        ledger: JinaUsageLedger,
        model: str = "jina-embeddings-v3",
        endpoint: str = "https://api.jina.ai/v1/embeddings",
        dimensions: int = 1024,
        batch_size: int = 64,
        timeout_seconds: float = 60,
        transport: JinaPostJson = post_json,
    ) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._headers = jina_headers(api_key)
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
            raise JinaAPIError("Jina returned an unexpected query vector count")
        return vectors[0]

    def _embed(self, texts: list[str], *, task: str) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            estimated_tokens = estimate_input_tokens(*batch)
            self.ledger.require_capacity(estimated_tokens)
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
            self.ledger.record(response, estimated_tokens)
            data = response.get("data")
            if not isinstance(data, list) or len(data) != len(batch):
                raise JinaAPIError("Jina returned the wrong embedding count")
            ordered = sorted(data, key=_response_index)
            batch_vectors = [_embedding(item) for item in ordered]
            vectors.extend(batch_vectors)
        return vectors


def _response_index(item: Any) -> int:
    if not isinstance(item, dict) or not isinstance(item.get("index"), int):
        raise JinaAPIError("Jina embedding response is missing an index")
    return item["index"]


def _embedding(item: Any) -> list[float]:
    if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
        raise JinaAPIError("Jina embedding response is missing a vector")
    try:
        vector = [float(value) for value in item["embedding"]]
    except (TypeError, ValueError) as error:
        raise JinaAPIError("Jina embedding vector is not numeric") from error
    if not vector:
        raise JinaAPIError("Jina returned an empty embedding vector")
    return vector
