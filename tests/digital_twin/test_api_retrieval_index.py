from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.digital_twin.evaluation.retrieval_qualification import ProviderUsage
from src.digital_twin.grounding import (
    ApiRetrievalIndexBindingV2,
    DocumentChunk,
    RetrievalIndexBindingError,
    RetrievalIndexCorruptionError,
    RetrievalIndexUnavailableError,
    StreamingRetrievalIndexMaterializerV2,
    source_set_sha256,
)


DIMENSION = 1_536


def _chunks(count: int = 5) -> list[DocumentChunk]:
    return [
        DocumentChunk(
            id=f"chunk-{index:02d}",
            document_id=f"document-{index:02d}",
            text=f"Public source text about concept {index}.",
            ordinal=0,
            source_artifact_id=f"source-{index:02d}",
            source_version=1,
            retrieval_allowed=True,
            metadata={"course_id": "course-a", "title": f"Concept {index}"},
        )
        for index in range(count)
    ]


def _binding(
    chunks: list[DocumentChunk],
    *,
    batch_size: int = 2,
    request_token_limit: int = 50_000,
):
    return ApiRetrievalIndexBindingV2(
        instrument_id="api-first-retrieval-selection-001",
        course_id="course-a",
        release_id="release-a",
        profile_id="api-retrieval-successor",
        profile_version="v1",
        chunker_id="source-range-clusterer",
        chunker_version="v1",
        source_set_sha256=source_set_sha256(chunks),
        chunk_count=len(chunks),
        embedding_model="text-embedding-3-small",
        embedding_dimensions=DIMENSION,
        embedding_batch_size=batch_size,
        embedding_request_token_limit=request_token_limit,
        input_price_usd_per_million=0.02,
        metadata_verified_at=datetime(2026, 8, 30, tzinfo=UTC),
        bm25_k1=1.2,
        bm25_b=0.75,
        fusion_rank_constant=60,
        fusion_candidate_limit=30,
    )


class FakeApiEmbedder:
    provider_id = "openai"
    model_name = "text-embedding-3-small"
    dimensions = DIMENSION
    batch_size = 2
    request_token_limit = 50_000
    endpoint = "https://api.openai.com/v1/embeddings"

    def __init__(self, *, fail_on_call: int | None = None) -> None:
        self.calls = 0
        self.fail_on_call = fail_on_call
        self._usage = ProviderUsage()

    def embed_documents(self, texts):
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise RuntimeError("synthetic interruption")
        self._usage = self._usage.model_copy(
            update={
                "request_count": self._usage.request_count + 1,
                "input_items": self._usage.input_items + len(texts),
                "input_characters": self._usage.input_characters
                + sum(len(text) for text in texts),
                "input_tokens": self._usage.input_tokens + len(texts),
                "approximate_cost_usd": self._usage.approximate_cost_usd
                + len(texts) * 0.02 / 1_000_000,
            }
        )
        vectors = []
        for text in texts:
            values = [0.0] * DIMENSION
            values[sum(ord(character) for character in text) % DIMENSION] = 1.0
            vectors.append(values)
        return vectors

    def embed_query(self, text):
        return self.embed_documents([text])[0]

    def usage_snapshot(self):
        return self._usage


def test_streamed_materialization_is_bounded_immutable_and_loadable(tmp_path: Path):
    chunks = _chunks()
    binding = _binding(chunks)
    store = StreamingRetrievalIndexMaterializerV2(tmp_path / "indexes")
    embedder = FakeApiEmbedder()

    manifest = store.materialize(binding, chunks, embedder)
    artifact_path = store.artifacts_root / manifest.artifact_id[:2] / manifest.artifact_id

    assert embedder.calls == 3
    assert manifest.materialization["batch_count"] == 3
    assert manifest.materialization["peak_retained_vector_count"] == 2
    assert (artifact_path / "dense.f32").stat().st_size == len(chunks) * DIMENSION * 4
    assert store.verify(manifest.artifact_id, expected_binding=binding) == manifest

    no_reembed = FakeApiEmbedder(fail_on_call=1)
    assert store.materialize(binding, list(reversed(chunks)), no_reembed) == manifest
    assert no_reembed.calls == 0

    loaded = store.load(
        manifest.artifact_id,
        expected_binding=binding,
        embedder=FakeApiEmbedder(),
    )
    assert loaded.retriever.retrieve("concept 2", limit=2)


def test_streamed_materialization_resumes_after_completed_batch(tmp_path: Path):
    chunks = _chunks()
    binding = _binding(chunks)
    store = StreamingRetrievalIndexMaterializerV2(tmp_path / "indexes")

    with pytest.raises(RuntimeError, match="interruption"):
        store.materialize(
            binding,
            chunks,
            FakeApiEmbedder(fail_on_call=2),
        )

    resumed = FakeApiEmbedder()
    manifest = store.materialize(binding, chunks, resumed, resume=True)

    assert resumed.calls == 2
    assert manifest.materialization["batch_count"] == 3


def test_streamed_materialization_splits_batches_by_token_limit(tmp_path: Path):
    chunks = _chunks(4)
    chunks = [
        chunk.model_copy(update={"text": "x" * 30})
        for chunk in chunks
    ]
    binding = _binding(chunks, batch_size=4, request_token_limit=15)
    store = StreamingRetrievalIndexMaterializerV2(tmp_path / "indexes")
    embedder = FakeApiEmbedder()
    embedder.batch_size = 4
    embedder.request_token_limit = 15

    manifest = store.materialize(binding, chunks, embedder)

    assert embedder.calls == 4
    assert manifest.materialization["batch_count"] == 4


def test_streamed_materialization_rejects_resume_binding_drift(tmp_path: Path):
    chunks = _chunks()
    binding = _binding(chunks)
    store = StreamingRetrievalIndexMaterializerV2(tmp_path / "indexes")
    with pytest.raises(RuntimeError):
        store.materialize(binding, chunks, FakeApiEmbedder(fail_on_call=2))

    changed = binding.model_copy(update={"release_id": "release-b"})
    with pytest.raises(RetrievalIndexUnavailableError, match="resume"):
        store.materialize(changed, chunks, FakeApiEmbedder(), resume=True)


def test_streamed_materialization_rejects_embedder_and_artifact_drift(tmp_path: Path):
    chunks = _chunks()
    binding = _binding(chunks)
    store = StreamingRetrievalIndexMaterializerV2(tmp_path / "indexes")
    wrong = FakeApiEmbedder()
    wrong.model_name = "text-embedding-3-large"

    with pytest.raises(RetrievalIndexBindingError, match="model_name"):
        store.materialize(binding, chunks, wrong)

    manifest = store.materialize(binding, chunks, FakeApiEmbedder())
    dense = store.artifacts_root / manifest.artifact_id[:2] / manifest.artifact_id / "dense.f32"
    dense.write_bytes(dense.read_bytes() + b"x")
    with pytest.raises(RetrievalIndexCorruptionError, match="checksum"):
        store.verify(manifest.artifact_id, expected_binding=binding)
