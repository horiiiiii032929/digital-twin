"""Direct OpenAI embedding adapter for the API-first retrieval successor."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from services.retrieval_provider import (
    PostJson,
    RetrievalProviderError,
    RetrievalUsageLedger,
    bearer_headers,
    estimate_input_tokens,
    post_json,
    require_https_endpoint,
)
from src.digital_twin.evaluation.retrieval_qualification import ProviderUsage
from src.digital_twin.model_policy import (
    OPENAI_EMBEDDING_PRICING_USD_PER_MILLION,
    OPENAI_TEXT_EMBEDDING_SMALL_MODEL,
    require_registered_current_model,
)


DEFAULT_MODEL = OPENAI_TEXT_EMBEDDING_SMALL_MODEL
DEFAULT_ENDPOINT = "https://api.openai.com/v1/embeddings"
MAX_PROVIDER_INPUTS = 2_048
MAX_PROVIDER_TOKENS_PER_INPUT = 8_192
MAX_PROVIDER_TOKENS_PER_REQUEST = 300_000


class OpenAITextEmbedder:
    """Embed text with exact identity, shape, usage, and budget validation."""

    provider_id = "openai"
    execution = "hosted-api"

    def __init__(
        self,
        api_key: str,
        *,
        ledger: RetrievalUsageLedger,
        model: str = DEFAULT_MODEL,
        endpoint: str = DEFAULT_ENDPOINT,
        dimensions: int = 1_536,
        batch_size: int = 64,
        request_token_limit: int = 50_000,
        timeout_seconds: float = 60,
        transport: PostJson = post_json,
    ) -> None:
        require_registered_current_model(model)
        if model not in OPENAI_EMBEDDING_PRICING_USD_PER_MILLION:
            raise ValueError("OpenAI embedding model is not prospectively registered")
        if isinstance(dimensions, bool) or not isinstance(dimensions, int) or dimensions < 1:
            raise ValueError("dimensions must be a positive integer")
        if (
            isinstance(batch_size, bool)
            or not isinstance(batch_size, int)
            or not 1 <= batch_size <= min(64, MAX_PROVIDER_INPUTS)
        ):
            raise ValueError("batch_size must be between 1 and 64")
        if (
            isinstance(request_token_limit, bool)
            or not isinstance(request_token_limit, int)
            or not 1 <= request_token_limit <= MAX_PROVIDER_TOKENS_PER_REQUEST
        ):
            raise ValueError("request_token_limit exceeds the provider boundary")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        require_https_endpoint(endpoint)
        self._headers = bearer_headers(api_key)
        self.ledger = ledger
        self.model = model
        self.model_name = model
        self.model_revision = model
        self.endpoint = endpoint
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.request_token_limit = request_token_limit
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(list(texts))

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed([text])
        if len(vectors) != 1:
            raise RetrievalProviderError(
                "OpenAI returned an unexpected query vector count"
            )
        return vectors[0]

    def usage_snapshot(self) -> ProviderUsage:
        return self.ledger.usage_snapshot()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("embedding inputs must be non-empty strings")
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            per_input = [estimate_input_tokens(value) for value in batch]
            if any(value > MAX_PROVIDER_TOKENS_PER_INPUT for value in per_input):
                raise RetrievalProviderError(
                    "embedding input exceeds the local per-input token boundary"
                )
            estimated_tokens = sum(per_input)
            if estimated_tokens > self.request_token_limit:
                raise RetrievalProviderError(
                    "embedding batch exceeds the local request token boundary"
                )
            self.ledger.require_capacity(estimated_tokens)
            try:
                response = self._transport(
                    self.endpoint,
                    self._headers,
                    {
                        "model": self.model,
                        "input": batch,
                        "encoding_format": "float",
                        "dimensions": self.dimensions,
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
            if response.get("model") != self.model:
                self.ledger.record_failure()
                raise RetrievalProviderError("OpenAI embedding model identity drifted")
            data = response.get("data")
            if not isinstance(data, list) or len(data) != len(batch):
                self.ledger.record_failure()
                raise RetrievalProviderError(
                    "OpenAI returned the wrong embedding count"
                )
            try:
                ordered = sorted(data, key=_response_index)
                indices = [_response_index(item) for item in ordered]
                batch_vectors = [
                    _embedding(item, self.dimensions) for item in ordered
                ]
            except RetrievalProviderError:
                self.ledger.record_failure()
                raise
            if indices != list(range(len(batch))):
                self.ledger.record_failure()
                raise RetrievalProviderError(
                    "OpenAI returned invalid embedding indexes"
                )
            vectors.extend(batch_vectors)
        return vectors


def _response_index(item: Any) -> int:
    if (
        not isinstance(item, dict)
        or isinstance(item.get("index"), bool)
        or not isinstance(item.get("index"), int)
    ):
        raise RetrievalProviderError(
            "OpenAI embedding response is missing an index"
        )
    return item["index"]


def _embedding(item: Any, expected_dimensions: int) -> list[float]:
    if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
        raise RetrievalProviderError(
            "OpenAI embedding response is missing a vector"
        )
    try:
        vector = [float(value) for value in item["embedding"]]
    except (TypeError, ValueError) as error:
        raise RetrievalProviderError(
            "OpenAI embedding vector is not numeric"
        ) from error
    if len(vector) != expected_dimensions:
        raise RetrievalProviderError(
            "OpenAI returned an embedding with unexpected dimensions"
        )
    if any(not math.isfinite(value) for value in vector):
        raise RetrievalProviderError(
            "OpenAI returned a non-finite embedding vector"
        )
    return vector


__all__ = [
    "DEFAULT_ENDPOINT",
    "DEFAULT_MODEL",
    "MAX_PROVIDER_INPUTS",
    "MAX_PROVIDER_TOKENS_PER_INPUT",
    "MAX_PROVIDER_TOKENS_PER_REQUEST",
    "OpenAITextEmbedder",
]
