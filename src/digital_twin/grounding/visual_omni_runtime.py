"""Current Jina omni visual retrieval successor with deterministic authority.

The historical v4 late-interaction implementation remains unchanged.  This
module adds a single-vector v5 successor and a conservative product decorator
that never treats provider vectors as source truth.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
import hashlib
import json
import math
import time
from typing import Any, Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.grounding.models import DocumentChunk, RegionKind, RetrievalHit
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.region_retrieval import RegionRoute, classify_region_query
from src.digital_twin.grounding.visual_late_interaction import (
    JINA_EMBEDDING_ENDPOINT,
    VisualEmbeddingResultV1,
    VisualEmbeddingUsageV1,
    VisualLateInteractionError,
    VisualLateInteractionIndexV1,
    validated_multivector,
)
from src.digital_twin.grounding.visual_runtime import (
    PersistentJinaQuotaLedgerV1,
    VisualProviderIdentityDriftError,
    VisualProviderUnavailableError,
    VisualRuntimeError,
)


JINA_OMNI_MODEL = "jina-embeddings-v5-omni-small"
JINA_OMNI_DIMENSIONS = 1024
JINA_OMNI_MAX_IMAGE_BYTES = 5 * 1024 * 1024
JINA_CUMULATIVE_PRIOR_TOKENS = 144_752
_VISUAL_KINDS = {
    RegionKind.TABLE,
    RegionKind.FIGURE,
    RegionKind.DIAGRAM,
    RegionKind.EQUATION,
    RegionKind.SCREENSHOT,
}


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


class VisualOmniBindingV1(BaseModel):
    """Immutable public binding for one v5 omni retrieval index."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = "1.0.0"
    implementation_id: Literal["jina-v5-omni-single-vector-v1"] = (
        "jina-v5-omni-single-vector-v1"
    )
    model: Literal["jina-embeddings-v5-omni-small"] = JINA_OMNI_MODEL
    dimensions: Literal[1024] = JINA_OMNI_DIMENSIONS
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_metadata_verified_at: str = Field(min_length=1)


class JinaOmniEmbeddingProviderV1:
    """Strict first-party v5 omni transport with durable token accounting."""

    implementation_id = "jina-v5-omni-single-vector-api-v1"

    def __init__(
        self,
        *,
        api_key: str,
        quota_ledger: PersistentJinaQuotaLedgerV1,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise VisualRuntimeError("JINA_API_KEY is required")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise VisualRuntimeError("visual omni timeout must be positive")
        self._api_key = api_key
        self._quota = quota_ledger
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    @staticmethod
    def query_payload(query: str) -> dict[str, Any]:
        normalized = " ".join(query.split())
        if not normalized:
            raise VisualRuntimeError("visual omni query must not be blank")
        return {
            "model": JINA_OMNI_MODEL,
            "input": [{"text": normalized}],
            "task": "retrieval.query",
            "dimensions": JINA_OMNI_DIMENSIONS,
            "embedding_type": "float",
            "normalized": True,
            "truncate": False,
        }

    @staticmethod
    def image_payload(image_bytes: bytes, *, mime_type: str) -> dict[str, Any]:
        if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise VisualRuntimeError("visual omni input must be a supported raster image")
        if not image_bytes or len(image_bytes) > JINA_OMNI_MAX_IMAGE_BYTES:
            raise VisualRuntimeError("visual omni image size is invalid")
        return {
            "model": JINA_OMNI_MODEL,
            "input": [{"image": base64.b64encode(image_bytes).decode("ascii")}],
            "task": "retrieval.passage",
            "dimensions": JINA_OMNI_DIMENSIONS,
            "embedding_type": "float",
            "normalized": True,
            "truncate": False,
        }

    @staticmethod
    def parse_response(payload: object) -> VisualEmbeddingResultV1:
        if not isinstance(payload, dict):
            raise VisualLateInteractionError("omni embedding response must be an object")
        if payload.get("model") != JINA_OMNI_MODEL:
            raise VisualProviderIdentityDriftError(
                "returned visual omni model identity drifted"
            )
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise VisualLateInteractionError(
                "omni embedding response must contain exactly one item"
            )
        if data[0].get("index") != 0:
            raise VisualLateInteractionError("omni embedding response index drifted")
        vector = data[0].get("embedding")
        if not isinstance(vector, list) or len(vector) != JINA_OMNI_DIMENSIONS:
            raise VisualLateInteractionError("omni embedding dimension drifted")
        vectors = validated_multivector([vector])
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            raise VisualLateInteractionError("omni embedding usage is missing")
        total_tokens = usage.get("total_tokens")
        if (
            isinstance(total_tokens, bool)
            or not isinstance(total_tokens, int)
            or total_tokens < 0
        ):
            raise VisualLateInteractionError("omni token accounting is invalid")
        return VisualEmbeddingResultV1(
            model=JINA_OMNI_MODEL,
            vectors=vectors,
            usage=VisualEmbeddingUsageV1(total_tokens=total_tokens),
        )

    def _embed(self, payload: dict[str, Any]) -> VisualEmbeddingResultV1:
        request_sha256 = _canonical_sha256(payload)
        request_id = f"visual-omni-{uuid4()}"
        self._quota.reserve(request_id=request_id, request_sha256=request_sha256)
        started = time.perf_counter()
        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(
                    JINA_EMBEDDING_ENDPOINT,
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            if response.status_code != 200:
                raise VisualProviderUnavailableError(
                    f"Jina visual omni request failed with HTTP {response.status_code}"
                )
            try:
                result = self.parse_response(response.json())
            except VisualProviderIdentityDriftError:
                raise
            except (ValueError, VisualLateInteractionError) as error:
                raise VisualProviderUnavailableError(
                    "Jina visual omni response is invalid"
                ) from error
        except httpx.HTTPError as error:
            latency_ms = (time.perf_counter() - started) * 1000
            self._quota.fail(
                request_id=request_id,
                failure_type=type(error).__name__,
                latency_ms=latency_ms,
            )
            raise VisualProviderUnavailableError(
                "Jina visual omni transport failed"
            ) from error
        except Exception as error:
            latency_ms = (time.perf_counter() - started) * 1000
            self._quota.fail(
                request_id=request_id,
                failure_type=type(error).__name__,
                latency_ms=latency_ms,
            )
            raise
        latency_ms = (time.perf_counter() - started) * 1000
        self._quota.complete(
            request_id=request_id,
            actual_tokens=result.usage.total_tokens,
            latency_ms=latency_ms,
        )
        return result

    def embed_query(self, query: str) -> VisualEmbeddingResultV1:
        return self._embed(self.query_payload(query))

    def embed_image(
        self, image_bytes: bytes, *, mime_type: str
    ) -> VisualEmbeddingResultV1:
        return self._embed(self.image_payload(image_bytes, mime_type=mime_type))


class VisualAwareRetrieverV2:
    """Route visual evidence by release composition and deterministic confidence.

    V1 relied only on visual keywords.  V2 also invokes visual retrieval for an
    all-visual release and for a low-confidence text result.  High-confidence
    ordinary text queries retain the exact text path.
    """

    implementation_id = "jina-v5-omni-with-text-ocr-fallback-v2"
    primary_implementation_id = "jina-v5-omni-single-vector-v1"

    def __init__(
        self,
        *,
        text_retriever: Retriever,
        query_provider: JinaOmniEmbeddingProviderV1,
        index: VisualLateInteractionIndexV1,
        course_id: str,
        chunks: Sequence[DocumentChunk],
        artifact_id: str,
        text_confidence_threshold: float = 0.75,
        text_margin_threshold: float = 0.10,
    ) -> None:
        if not 0 <= text_confidence_threshold <= 1:
            raise ValueError("text confidence threshold must be in [0, 1]")
        if not 0 <= text_margin_threshold <= 1:
            raise ValueError("text margin threshold must be in [0, 1]")
        self._text_retriever = text_retriever
        self._query_provider = query_provider
        self._index = index
        self._course_id = course_id
        self._artifact_id = artifact_id
        self._text_confidence_threshold = text_confidence_threshold
        self._text_margin_threshold = text_margin_threshold
        self._chunks_by_region: dict[str, DocumentChunk] = {}
        visual_count = 0
        for chunk in chunks:
            if chunk.region_id is not None:
                if chunk.region_id in self._chunks_by_region:
                    raise VisualRuntimeError("release contains duplicate visual region IDs")
                self._chunks_by_region[chunk.region_id] = chunk
            if chunk.region_kind in _VISUAL_KINDS:
                visual_count += 1
        self._all_visual_release = bool(chunks) and visual_count == len(chunks)
        self.fallback_count = 0
        self.primary_available = True
        self.last_failure_type: str | None = None
        self.last_route = RegionRoute.GENERAL
        self.last_hits: list[RetrievalHit] = []
        self.visual_call_count = 0

    @property
    def artifact_id(self) -> str:
        return self._artifact_id

    @property
    def fallback_implementation_id(self) -> str:
        return getattr(self._text_retriever, "implementation_id", "text-ocr-fallback")

    def _requires_visual(
        self, *, route: RegionRoute, text_hits: Sequence[RetrievalHit]
    ) -> bool:
        if route != RegionRoute.GENERAL or self._all_visual_release:
            return True
        if not text_hits:
            return True
        top = text_hits[0].relevance_score
        second = text_hits[1].relevance_score if len(text_hits) > 1 else 0.0
        top_is_visual = text_hits[0].chunk.region_kind in _VISUAL_KINDS
        return top_is_visual and (
            top < self._text_confidence_threshold
            or top - second < self._text_margin_threshold
        )

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise ValueError("retrieval limit must be positive")
        candidate_limit = max(limit, 10)
        text_hits = self._text_retriever.retrieve(query, limit=candidate_limit)
        self.last_route = classify_region_query(query)
        if not self._requires_visual(route=self.last_route, text_hits=text_hits):
            self.last_hits = list(text_hits[:limit])
            return self.last_hits
        try:
            result = self._query_provider.embed_query(query)
            self.visual_call_count += 1
            ranked = self._index.retrieve(
                course_id=self._course_id,
                query_vectors=result.vectors,
                limit=candidate_limit,
            )
            visual_hits: list[RetrievalHit] = []
            for item in ranked:
                chunk = self._chunks_by_region.get(str(item["region_id"]))
                if chunk is None or (
                    chunk.source_artifact_id != item["source_artifact_id"]
                    or str(chunk.source_version) != item["source_version"]
                    or chunk.source_checksum != item["source_sha256"]
                    or chunk.region_checksum != item["render_sha256"]
                    or not chunk.retrieval_allowed
                ):
                    raise VisualRuntimeError(
                        "visual omni result cannot map to release authority"
                    )
                score = max(-1.0, min(1.0, float(item["score"])))
                visual_hits.append(
                    RetrievalHit(
                        chunk=chunk,
                        relevance_score=(score + 1.0) / 2.0,
                        raw_score=max(0.0, score),
                    )
                )
            self.primary_available = True
            self.last_failure_type = None
            self.last_hits = visual_hits[:limit]
            return self.last_hits
        except VisualProviderUnavailableError as error:
            self.fallback_count += 1
            self.primary_available = False
            self.last_failure_type = type(error).__name__
            self.last_hits = list(text_hits[:limit])
            return self.last_hits


__all__ = [
    "JINA_CUMULATIVE_PRIOR_TOKENS",
    "JINA_OMNI_DIMENSIONS",
    "JINA_OMNI_MODEL",
    "JinaOmniEmbeddingProviderV1",
    "VisualAwareRetrieverV2",
    "VisualOmniBindingV1",
]
