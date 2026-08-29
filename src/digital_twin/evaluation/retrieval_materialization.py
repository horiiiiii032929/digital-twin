"""Idempotent local retrieval-index materialization for authorized evaluations."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from services.embeddings import Qwen3TextEmbedder
from src.digital_twin.grounding import (
    DocumentChunk,
    RetrievalIndexStoreV1,
    build_retrieval_index_binding,
)


class RetrievalMaterializationError(RuntimeError):
    """Raised when a frozen local index cannot be built or verified."""


def materialize_retrieval_indexes(
    *,
    chunks_by_course: dict[str, list[DocumentChunk]],
    profile: dict[str, Any],
    model_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Build or verify one immutable index per course with a pinned local model."""

    retriever = next(
        row for row in profile["components"] if row["component"] == "retriever"
    )["implementation"]["configuration"]
    chunker = next(
        row for row in profile["components"] if row["component"] == "chunker"
    )["implementation"]
    revision = str(retriever["embedding_revision"])
    snapshot = model_root / revision
    if not snapshot.is_dir():
        raise RetrievalMaterializationError(
            "pinned Qwen query/document embedding snapshot is unavailable"
        )
    source_region_count = sum(len(rows) for rows in chunks_by_course.values())
    if source_region_count != 2_100:
        raise RetrievalMaterializationError(
            "R1 evaluation index requires exactly 2,100 public source regions"
        )
    embedder = Qwen3TextEmbedder(
        snapshot,
        instruction=str(retriever["query_instruction"]),
        device=str(retriever["device"]),
        dtype=str(retriever["dtype"]),
        batch_size=int(retriever["embedding_batch_size"]),
        max_length=int(retriever["embedding_max_length"]),
        model_revision=revision,
    )
    store = RetrievalIndexStoreV1(output_root)
    started = time.perf_counter()
    manifests: dict[str, str] = {}
    for course_id, chunks in sorted(chunks_by_course.items()):
        binding = build_retrieval_index_binding(
            course_id=course_id,
            release_id=f"{course_id}-academic-open-release",
            profile_id=str(profile["profile_id"]),
            profile_version=str(profile["profile_version"]),
            chunker_id=str(chunker["implementation_id"]),
            chunker_version=str(chunker["version"]),
            chunks=chunks,
            configuration=retriever,
        )
        manifest = store.build(binding, chunks, embedder)
        store.verify_bound(binding)
        manifests[course_id] = manifest.artifact_id
    return {
        "status": "completed",
        "course_count": len(manifests),
        "source_region_count": source_region_count,
        "artifact_ids": manifests,
        "elapsed_seconds": time.perf_counter() - started,
        "local_model": str(retriever["embedding_model"]),
        "local_model_revision": revision,
        "provider_calls": 0,
        "cost_usd": 0.0,
    }
