from __future__ import annotations

import json

import httpx
import pytest

from src.digital_twin.grounding.visual_late_interaction import (
    JINA_EMBEDDING_ENDPOINT,
    JINA_MAX_INPUT_BYTES,
    JinaVisualMultiVectorProvider,
    VisualLateInteractionError,
    VisualLateInteractionIndexV1,
    VisualRegionEmbeddingV1,
    maxsim_score,
    validated_multivector,
)


def _record(*, record_id: str, course_id: str, vectors: tuple[tuple[float, ...], ...]):
    return VisualRegionEmbeddingV1(
        record_id=record_id,
        course_id=course_id,
        source_artifact_id=f"source-{record_id}",
        source_version="revision-1",
        source_sha256="a" * 64,
        asset_id=f"asset-{record_id}",
        region_id=f"region-{record_id}",
        render_sha256="b" * 64,
        bbox=(0.0, 0.0, 1.0, 1.0),
        modality="diagram",
        vectors=vectors,
    )


def test_maxsim_uses_query_to_patch_late_interaction() -> None:
    query = ((1.0, 0.0), (0.0, 1.0))
    complete = ((1.0, 0.0), (0.0, 1.0))
    partial = ((1.0, 0.0),)

    assert maxsim_score(query, complete) == pytest.approx(1.0)
    assert maxsim_score(query, partial) == pytest.approx(0.5)


def test_visual_index_is_course_scoped_and_returns_original_lineage() -> None:
    index = VisualLateInteractionIndexV1(
        [
            _record(record_id="match", course_id="course-a", vectors=((1.0, 0.0),)),
            _record(record_id="weak", course_id="course-a", vectors=((0.0, 1.0),)),
            _record(record_id="wrong-course", course_id="course-b", vectors=((1.0, 0.0),)),
        ]
    )

    hits = index.retrieve(course_id="course-a", query_vectors=((1.0, 0.0),), limit=3)

    assert [hit["record_id"] for hit in hits] == ["match", "weak"]
    assert hits[0]["region_id"] == "region-match"
    assert hits[0]["render_sha256"] == "b" * 64


def test_multivector_rejects_non_finite_ragged_and_zero_rows() -> None:
    with pytest.raises(VisualLateInteractionError, match="one dimension"):
        validated_multivector([[1.0, 0.0], [1.0]])
    with pytest.raises(VisualLateInteractionError, match="finite"):
        validated_multivector([[float("nan")]])
    with pytest.raises(VisualLateInteractionError, match="zero"):
        maxsim_score(((0.0, 0.0),), ((1.0, 0.0),))


def test_jina_payload_pins_multivector_model_task_and_no_truncation() -> None:
    provider = JinaVisualMultiVectorProvider(api_key="runtime-secret")

    query = provider.query_payload("  compare   both arrows ")
    image = provider.image_payload(b"png", mime_type="image/png")

    assert query == {
        "model": "jina-embeddings-v4",
        "input": [{"text": "compare both arrows"}],
        "task": "retrieval.query",
        "embedding_type": "float",
        "return_multivector": True,
        "truncate": False,
    }
    assert image["task"] == "retrieval.passage"
    assert image["return_multivector"] is True
    assert image["input"][0]["image"] == "cG5n"
    with pytest.raises(VisualLateInteractionError, match="size"):
        provider.image_payload(b"x" * (JINA_MAX_INPUT_BYTES + 1), mime_type="image/png")


@pytest.mark.asyncio
async def test_jina_transport_validates_identity_usage_and_request_headers() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers.get("authorization")
        seen["accept"] = request.headers.get("accept")
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "jina-embeddings-v4",
                "data": [{"index": 0, "embeddings": [[1.0, 0.0], [0.0, 1.0]]}],
                "usage": {"total_tokens": 12},
            },
        )

    provider = JinaVisualMultiVectorProvider(
        api_key="runtime-secret",
        transport=httpx.MockTransport(handler),
    )
    result = await provider.embed_query("Which node follows A?")

    assert seen["url"] == JINA_EMBEDDING_ENDPOINT
    assert seen["authorization"] == "Bearer runtime-secret"
    assert seen["accept"] == "application/json"
    assert result.model == "jina-embeddings-v4"
    assert result.usage.total_tokens == 12
    assert len(result.vectors) == 2


def test_jina_response_rejects_identity_drift_and_missing_accounting() -> None:
    with pytest.raises(VisualLateInteractionError, match="identity drifted"):
        JinaVisualMultiVectorProvider.parse_response(
            {
                "model": "mutable-alias",
                "data": [{"index": 0, "embeddings": [[1.0]]}],
                "usage": {"total_tokens": 1},
            }
        )
    with pytest.raises(VisualLateInteractionError, match="usage is missing"):
        JinaVisualMultiVectorProvider.parse_response(
            {"model": "jina-embeddings-v4", "data": [{"index": 0, "embeddings": [[1.0]]}]}
        )
    with pytest.raises(VisualLateInteractionError, match="index drifted"):
        JinaVisualMultiVectorProvider.parse_response(
            {
                "model": "jina-embeddings-v4",
                "data": [{"index": 1, "embeddings": [[1.0]]}],
                "usage": {"total_tokens": 1},
            }
        )
