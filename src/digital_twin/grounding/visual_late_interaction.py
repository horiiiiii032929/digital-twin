"""Hash-bound late-interaction retrieval for visual document regions.

The module implements the retrieval boundary used by the prospective
ColPali-style visual successor.  Provider embeddings are advisory ranking
features: source permission, version, and citation authority always remain on
the original visual region.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import math
from typing import Any, Protocol, Sequence

import httpx

from src.digital_twin.evaluation.multimodal_retrieval import validated_bbox


JINA_EMBEDDING_ENDPOINT = "https://api.jina.ai/v1/embeddings"
JINA_VISUAL_MODEL = "jina-embeddings-v4"
JINA_MAX_INPUT_BYTES = 8 * 1024 * 1024
JINA_MAX_INPUT_TOKENS = 32_768
JINA_INPUT_TOKEN_PRICE_USD = 0.00000005


class VisualLateInteractionError(ValueError):
    """Raised when a visual embedding or its lineage is invalid."""


MultiVector = tuple[tuple[float, ...], ...]


def _validated_sha256(value: str, *, label: str) -> str:
    normalized = value.casefold()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise VisualLateInteractionError(f"{label} must be a lowercase SHA-256 digest")
    return normalized


def validated_multivector(value: object) -> MultiVector:
    """Return one finite, rectangular, non-empty multi-vector."""

    if not isinstance(value, list) or not value:
        raise VisualLateInteractionError("multi-vector must be a non-empty list")
    rows: list[tuple[float, ...]] = []
    dimension: int | None = None
    for raw_row in value:
        if not isinstance(raw_row, list) or not raw_row:
            raise VisualLateInteractionError("multi-vector rows must be non-empty lists")
        row: list[float] = []
        for raw_component in raw_row:
            if isinstance(raw_component, bool) or not isinstance(raw_component, (int, float)):
                raise VisualLateInteractionError("embedding components must be numeric")
            component = float(raw_component)
            if not math.isfinite(component):
                raise VisualLateInteractionError("embedding components must be finite")
            row.append(component)
        if dimension is None:
            dimension = len(row)
        elif len(row) != dimension:
            raise VisualLateInteractionError("multi-vector rows must have one dimension")
        rows.append(tuple(row))
    if len(rows) > 8192 or (dimension or 0) > 4096:
        raise VisualLateInteractionError("multi-vector exceeds the bounded retrieval contract")
    return tuple(rows)


def _unit_rows(vectors: MultiVector) -> MultiVector:
    result: list[tuple[float, ...]] = []
    for row in vectors:
        norm = math.sqrt(sum(component * component for component in row))
        if norm == 0:
            raise VisualLateInteractionError("embedding rows must not be zero vectors")
        result.append(tuple(component / norm for component in row))
    return tuple(result)


def maxsim_score(query_vectors: MultiVector, document_vectors: MultiVector) -> float:
    """Compute length-normalized ColBERT/ColPali MaxSim similarity."""

    if not query_vectors or not document_vectors:
        raise VisualLateInteractionError("MaxSim inputs must not be empty")
    if len(query_vectors[0]) != len(document_vectors[0]):
        raise VisualLateInteractionError("query and document dimensions differ")
    query = _unit_rows(query_vectors)
    document = _unit_rows(document_vectors)
    total = 0.0
    for query_row in query:
        total += max(
            sum(left * right for left, right in zip(query_row, document_row, strict=True))
            for document_row in document
        )
    return total / len(query)


@dataclass(frozen=True)
class VisualRegionEmbeddingV1:
    """One embedded crop with immutable original-region authority."""

    record_id: str
    course_id: str
    source_artifact_id: str
    source_version: str
    source_sha256: str
    asset_id: str
    region_id: str
    render_sha256: str
    bbox: tuple[float, float, float, float]
    modality: str
    vectors: MultiVector

    def __post_init__(self) -> None:
        for label, value in (
            ("record_id", self.record_id),
            ("course_id", self.course_id),
            ("source_artifact_id", self.source_artifact_id),
            ("source_version", self.source_version),
            ("asset_id", self.asset_id),
            ("region_id", self.region_id),
            ("modality", self.modality),
        ):
            if not value.strip():
                raise VisualLateInteractionError(f"{label} must not be blank")
        _validated_sha256(self.source_sha256, label="source_sha256")
        _validated_sha256(self.render_sha256, label="render_sha256")
        validated_bbox(self.bbox)
        if self.modality not in {"table", "equation", "diagram", "chart", "figure", "screenshot"}:
            raise VisualLateInteractionError("unsupported visual modality")
        validated_multivector([list(row) for row in self.vectors])


@dataclass(frozen=True)
class VisualEmbeddingUsageV1:
    total_tokens: int

    def __post_init__(self) -> None:
        if isinstance(self.total_tokens, bool) or self.total_tokens < 0:
            raise VisualLateInteractionError("embedding token accounting is invalid")


@dataclass(frozen=True)
class VisualEmbeddingResultV1:
    model: str
    vectors: MultiVector
    usage: VisualEmbeddingUsageV1


class VisualMultiVectorProvider(Protocol):
    """Provider-neutral query/image multi-vector contract."""

    implementation_id: str

    async def embed_query(self, query: str) -> VisualEmbeddingResultV1: ...

    async def embed_image(self, image_bytes: bytes, *, mime_type: str) -> VisualEmbeddingResultV1: ...


class JinaVisualMultiVectorProvider:
    """Strict, no-retry Jina Embeddings v4 API transport."""

    implementation_id = "jina-embeddings-v4-multivector-api-v1"

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = JINA_EMBEDDING_ENDPOINT,
        model: str = JINA_VISUAL_MODEL,
        timeout_seconds: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise VisualLateInteractionError("JINA_API_KEY is required")
        if endpoint != JINA_EMBEDDING_ENDPOINT:
            raise VisualLateInteractionError("only the first-party Jina endpoint is allowed")
        if model != JINA_VISUAL_MODEL:
            raise VisualLateInteractionError("visual embedding model identity drifted")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise VisualLateInteractionError("provider timeout must be positive")
        self._api_key = api_key
        self._endpoint = endpoint
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def _payload(self, *, value: dict[str, str], task: str) -> dict[str, Any]:
        if task not in {"retrieval.query", "retrieval.passage"}:
            raise VisualLateInteractionError("unsupported visual retrieval task")
        return {
            "model": self._model,
            "input": [value],
            "task": task,
            "embedding_type": "float",
            "return_multivector": True,
            "truncate": False,
        }

    def query_payload(self, query: str) -> dict[str, Any]:
        normalized = " ".join(query.split())
        if not normalized:
            raise VisualLateInteractionError("visual retrieval query must not be blank")
        return self._payload(value={"text": normalized}, task="retrieval.query")

    def image_payload(self, image_bytes: bytes, *, mime_type: str) -> dict[str, Any]:
        if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise VisualLateInteractionError("visual embedding input must be a supported raster image")
        if not image_bytes or len(image_bytes) > JINA_MAX_INPUT_BYTES:
            raise VisualLateInteractionError("visual embedding image size is invalid")
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return self._payload(value={"image": encoded}, task="retrieval.passage")

    @staticmethod
    def parse_response(payload: object) -> VisualEmbeddingResultV1:
        if not isinstance(payload, dict):
            raise VisualLateInteractionError("embedding response must be an object")
        model = payload.get("model")
        if model != JINA_VISUAL_MODEL:
            raise VisualLateInteractionError("returned visual embedding model identity drifted")
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise VisualLateInteractionError("embedding response must contain exactly one item")
        if data[0].get("index") != 0:
            raise VisualLateInteractionError("embedding response index drifted")
        vectors = validated_multivector(data[0].get("embeddings"))
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            raise VisualLateInteractionError("embedding response usage is missing")
        total_tokens = usage.get("total_tokens")
        if isinstance(total_tokens, bool) or not isinstance(total_tokens, int) or total_tokens < 0:
            raise VisualLateInteractionError("embedding response token accounting is invalid")
        return VisualEmbeddingResultV1(
            model=model,
            vectors=vectors,
            usage=VisualEmbeddingUsageV1(total_tokens=total_tokens),
        )

    async def _embed(self, payload: dict[str, Any]) -> VisualEmbeddingResultV1:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            transport=self._transport,
        ) as client:
            response = await client.post(self._endpoint, headers=headers, json=payload)
        if response.status_code != 200:
            raise VisualLateInteractionError(
                f"Jina embedding request failed with HTTP {response.status_code}"
            )
        try:
            body = response.json()
        except ValueError as error:
            raise VisualLateInteractionError("Jina embedding response is not JSON") from error
        return self.parse_response(body)

    async def embed_query(self, query: str) -> VisualEmbeddingResultV1:
        return await self._embed(self.query_payload(query))

    async def embed_image(self, image_bytes: bytes, *, mime_type: str) -> VisualEmbeddingResultV1:
        return await self._embed(self.image_payload(image_bytes, mime_type=mime_type))


class VisualLateInteractionIndexV1:
    """Small course-isolated MaxSim index for the local research release."""

    implementation_id = "visual-late-interaction-maxsim-v1"

    def __init__(self, records: Sequence[VisualRegionEmbeddingV1]) -> None:
        materialized = tuple(records)
        if not materialized:
            raise VisualLateInteractionError("visual index requires at least one region")
        identifiers = [record.record_id for record in materialized]
        if len(identifiers) != len(set(identifiers)):
            raise VisualLateInteractionError("visual index record IDs must be unique")
        self._records = materialized

    def retrieve(
        self,
        *,
        course_id: str,
        query_vectors: MultiVector,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        if not course_id.strip():
            raise VisualLateInteractionError("course scope is required")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise VisualLateInteractionError("visual retrieval limit must be positive")
        query = validated_multivector([list(row) for row in query_vectors])
        ranked = [
            (maxsim_score(query, record.vectors), record)
            for record in self._records
            if record.course_id == course_id
        ]
        ranked.sort(key=lambda item: (-item[0], item[1].record_id))
        return [
            {
                "record_id": record.record_id,
                "course_id": record.course_id,
                "source_artifact_id": record.source_artifact_id,
                "source_version": record.source_version,
                "source_sha256": record.source_sha256,
                "asset_id": record.asset_id,
                "region_id": record.region_id,
                "render_sha256": record.render_sha256,
                "bbox": list(record.bbox),
                "modality": record.modality,
                "score": score,
            }
            for score, record in ranked[:limit]
        ]
