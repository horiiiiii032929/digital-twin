from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from src.digital_twin.grounding.models import DocumentChunk, RegionKind, RetrievalHit
from src.digital_twin.grounding.visual_late_interaction import (
    VisualEmbeddingResultV1,
    VisualEmbeddingUsageV1,
    VisualLateInteractionIndexV1,
    VisualRegionEmbeddingV1,
)
from src.digital_twin.grounding.visual_omni_runtime import (
    JINA_OMNI_DIMENSIONS,
    JINA_OMNI_MODEL,
    JinaOmniEmbeddingProviderV1,
    VisualAwareRetrieverV2,
)
from src.digital_twin.grounding.visual_runtime import (
    PersistentJinaQuotaLedgerV1,
    VisualProviderIdentityDriftError,
    VisualProviderUnavailableError,
)
from src.digital_twin.tutor_policy import SourceLabel


def _chunk(*, kind: RegionKind, score_text: str = "The diagram shows A then B.") -> DocumentChunk:
    visual = kind != RegionKind.TEXT
    return DocumentChunk(
        id=f"chunk-{kind.value}",
        document_id=f"source-{kind.value}",
        text=score_text,
        ordinal=0,
        source_artifact_id=f"source-{kind.value}",
        source_version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        source_checksum="a" * 64,
        region_id="region-1" if visual else None,
        region_kind=kind,
        bounding_box=(0.0, 0.0, 1.0, 1.0) if visual else None,
        crop_ref="crop.png" if visual else None,
        region_checksum="b" * 64 if visual else None,
        retrieval_allowed=True,
        display_allowed=True,
    )


def _record() -> VisualRegionEmbeddingV1:
    return VisualRegionEmbeddingV1(
        record_id="region-1",
        course_id="course-1",
        source_artifact_id="source-diagram",
        source_version="1",
        source_sha256="a" * 64,
        asset_id="asset-1",
        region_id="region-1",
        render_sha256="b" * 64,
        bbox=(0.0, 0.0, 1.0, 1.0),
        modality="diagram",
        vectors=((1.0, 0.0),),
    )


class _TextRetriever:
    implementation_id = "text-fixture"

    def __init__(self, hit: RetrievalHit) -> None:
        self.hit = hit

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        del query, limit
        return [self.hit]


class _QueryProvider:
    implementation_id = "query-fixture"

    def __init__(self, *, unavailable: bool = False) -> None:
        self.calls = 0
        self.unavailable = unavailable

    def embed_query(self, query: str) -> VisualEmbeddingResultV1:
        del query
        self.calls += 1
        if self.unavailable:
            raise VisualProviderUnavailableError("offline")
        return VisualEmbeddingResultV1(
            model=JINA_OMNI_MODEL,
            vectors=((1.0, 0.0),),
            usage=VisualEmbeddingUsageV1(total_tokens=2),
        )


def _retriever(
    *, text_chunk: DocumentChunk, provider: _QueryProvider
) -> VisualAwareRetrieverV2:
    return VisualAwareRetrieverV2(
        text_retriever=_TextRetriever(
            RetrievalHit(chunk=text_chunk, relevance_score=0.99, raw_score=8.0)
        ),
        query_provider=provider,  # type: ignore[arg-type]
        index=VisualLateInteractionIndexV1([_record()]),
        course_id="course-1",
        chunks=[text_chunk],
        artifact_id="visual-index-fixture",
    )


def test_omni_payload_matches_current_first_party_contract() -> None:
    query = JinaOmniEmbeddingProviderV1.query_payload("  packet   layout ")
    image = JinaOmniEmbeddingProviderV1.image_payload(
        b"png", mime_type="image/png"
    )

    assert query == {
        "model": JINA_OMNI_MODEL,
        "input": [{"text": "packet layout"}],
        "task": "retrieval.query",
        "dimensions": 1024,
        "embedding_type": "float",
        "normalized": True,
        "truncate": False,
    }
    assert image["model"] == JINA_OMNI_MODEL
    assert image["task"] == "retrieval.passage"
    assert set(image["input"][0]) == {"image"}
    assert "return_multivector" not in image


def test_omni_provider_checks_identity_dimensions_and_accounts_tokens(
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == JINA_OMNI_MODEL
        return httpx.Response(
            200,
            json={
                "model": JINA_OMNI_MODEL,
                "data": [{"index": 0, "embedding": [0.0] * JINA_OMNI_DIMENSIONS}],
                "usage": {"total_tokens": 7, "prompt_tokens": 7},
            },
        )

    quota = PersistentJinaQuotaLedgerV1(
        tmp_path / "quota.sqlite3",
        imported_tokens=10,
        imported_ledger_sha256="c" * 64,
    )
    provider = JinaOmniEmbeddingProviderV1(
        api_key="test",
        quota_ledger=quota,
        transport=httpx.MockTransport(handler),
    )

    result = provider.embed_query("packet layout")

    assert result.model == JINA_OMNI_MODEL
    assert len(result.vectors[0]) == JINA_OMNI_DIMENSIONS
    assert quota.snapshot().completed_tokens == 7
    assert quota.snapshot().remaining_tokens == 10_000_000 - 17


def test_omni_provider_rejects_returned_identity_drift(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "model": "different-model",
                "data": [{"index": 0, "embedding": [0.0] * JINA_OMNI_DIMENSIONS}],
                "usage": {"total_tokens": 7},
            },
        )
    )
    quota = PersistentJinaQuotaLedgerV1(
        tmp_path / "quota.sqlite3",
        imported_tokens=10,
        imported_ledger_sha256="d" * 64,
    )
    provider = JinaOmniEmbeddingProviderV1(
        api_key="test", quota_ledger=quota, transport=transport
    )

    with pytest.raises(VisualProviderIdentityDriftError):
        provider.embed_query("packet layout")
    assert quota.snapshot().calls == 1


def test_high_confidence_text_path_never_calls_visual_provider() -> None:
    provider = _QueryProvider()
    retriever = _retriever(text_chunk=_chunk(kind=RegionKind.TEXT), provider=provider)

    hits = retriever.retrieve("When are office hours?", limit=1)

    assert provider.calls == 0
    assert hits[0].chunk.region_kind == RegionKind.TEXT


def test_all_visual_release_uses_omni_and_preserves_region_authority() -> None:
    provider = _QueryProvider()
    retriever = _retriever(
        text_chunk=_chunk(kind=RegionKind.DIAGRAM), provider=provider
    )

    hits = retriever.retrieve("Which host returns the ACK?", limit=1)

    assert provider.calls == 1
    assert hits[0].chunk.region_id == "region-1"
    assert hits[0].chunk.source_checksum == "a" * 64


def test_transient_visual_failure_falls_back_to_text() -> None:
    provider = _QueryProvider(unavailable=True)
    retriever = _retriever(
        text_chunk=_chunk(kind=RegionKind.DIAGRAM), provider=provider
    )

    hits = retriever.retrieve("Which host returns the ACK?", limit=1)

    assert provider.calls == 1
    assert retriever.fallback_count == 1
    assert retriever.primary_available is False
    assert hits[0].chunk.id == "chunk-diagram"

