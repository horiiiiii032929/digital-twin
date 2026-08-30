"""Resumable, memory-bounded API embedding index materialization.

This prospective v2 lifecycle is intentionally separate from the historical
Qwen-bound v1 artifacts.  Source truth and ranking artifacts remain local;
only bounded text batches cross the registered embedding API boundary.
"""

from __future__ import annotations

import array
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.protocols import Retriever, TextEmbedder
from src.digital_twin.grounding.retrieval import (
    BM25Retriever,
    DenseRetriever,
    ReciprocalRankFusionRetriever,
    lexical_tokens,
    retrieval_text,
)
from src.digital_twin.grounding.retrieval_index import (
    RetrievalIndexBindingError,
    RetrievalIndexCorruptionError,
    RetrievalIndexUnavailableError,
    source_set_sha256,
)


_ARTIFACT_FILES = frozenset(
    {"chunks.json", "lexical.json", "dense.json", "dense.f32"}
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _normalized_vector_bytes(vector: Sequence[float], *, dimension: int) -> bytes:
    try:
        values = [float(value) for value in vector]
    except (TypeError, ValueError) as error:
        raise RetrievalIndexBindingError("embedding vectors must be numeric") from error
    if len(values) != dimension:
        raise RetrievalIndexBindingError("embedding vector dimension drifted")
    if any(not math.isfinite(value) for value in values):
        raise RetrievalIndexBindingError("embedding vectors must be finite")
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude == 0:
        raise RetrievalIndexBindingError("embedding vectors cannot have zero magnitude")
    packed = array.array("f", (value / magnitude for value in values))
    if sys.byteorder != "little":
        packed.byteswap()
    return packed.tobytes()


def _write_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _estimated_input_tokens(text: str) -> int:
    """Match the direct embedding adapter's conservative request estimate."""

    return max(1, math.ceil(len(text) / 3))


def _bounded_embedding_batches(
    chunks: Sequence[DocumentChunk],
    *,
    maximum_items: int,
    maximum_tokens: int,
) -> Iterator[tuple[int, list[DocumentChunk]]]:
    """Yield stable batches bounded by both provider items and estimated tokens."""

    start = 0
    batch: list[DocumentChunk] = []
    tokens = 0
    for chunk in chunks:
        chunk_tokens = _estimated_input_tokens(retrieval_text(chunk))
        if chunk_tokens > maximum_tokens:
            raise RetrievalIndexBindingError(
                "one retrieval chunk exceeds the embedding request token limit"
            )
        if batch and (
            len(batch) >= maximum_items or tokens + chunk_tokens > maximum_tokens
        ):
            yield start, batch
            start += len(batch)
            batch = []
            tokens = 0
        batch.append(chunk)
        tokens += chunk_tokens
    if batch:
        yield start, batch


class ApiRetrievalIndexBindingV2(BaseModel):
    """Exact prospective provider/source/materialization identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2] = 2
    instrument_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    chunker_id: str = Field(min_length=1)
    chunker_version: str = Field(min_length=1)
    retriever_implementation_id: Literal["api-dense-bm25-index-v2"] = (
        "api-dense-bm25-index-v2"
    )
    source_set_sha256: str
    chunk_count: int = Field(ge=1)
    embedding_provider: Literal["openai"] = "openai"
    embedding_endpoint: Literal["https://api.openai.com/v1/embeddings"] = (
        "https://api.openai.com/v1/embeddings"
    )
    embedding_model: Literal["text-embedding-3-small", "text-embedding-3-large"]
    returned_model_identity_required: Literal[True] = True
    embedding_dimensions: int = Field(ge=1)
    embedding_batch_size: int = Field(ge=1, le=64)
    embedding_request_token_limit: int = Field(ge=1, le=300_000)
    input_price_usd_per_million: float = Field(ge=0, allow_inf_nan=False)
    metadata_verified_at: datetime
    retention_boundary: Literal[
        "no-application-state-standard-abuse-monitoring-up-to-30-days"
    ] = "no-application-state-standard-abuse-monitoring-up-to-30-days"
    bm25_k1: float = Field(gt=0, allow_inf_nan=False)
    bm25_b: float = Field(ge=0, le=1, allow_inf_nan=False)
    fusion_rank_constant: int = Field(ge=1)
    fusion_candidate_limit: int = Field(ge=1)

    @field_validator("source_set_sha256")
    @classmethod
    def source_hash_must_be_sha256(cls, value: str) -> str:
        value = value.lower()
        if not _is_sha256(value):
            raise ValueError("source_set_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def dimensions_and_price_must_match_candidate(self) -> "ApiRetrievalIndexBindingV2":
        expected = {
            "text-embedding-3-small": (1_536, 0.02),
            "text-embedding-3-large": (3_072, 0.13),
        }[self.embedding_model]
        if (self.embedding_dimensions, self.input_price_usd_per_million) != expected:
            raise ValueError("embedding dimensions or price drifted")
        return self

    @property
    def binding_sha256(self) -> str:
        return _sha256_bytes(_canonical_bytes(self.model_dump(mode="json")))


class ApiRetrievalIndexManifestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2] = 2
    artifact_id: str
    binding: ApiRetrievalIndexBindingV2
    dense_dimension: int = Field(ge=1)
    files: dict[str, str]
    materialization: dict[str, int | float]

    @field_validator("artifact_id")
    @classmethod
    def artifact_must_be_sha256(cls, value: str) -> str:
        value = value.lower()
        if not _is_sha256(value):
            raise ValueError("artifact_id must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def artifact_must_be_complete(self) -> "ApiRetrievalIndexManifestV2":
        if set(self.files) != _ARTIFACT_FILES or any(
            not _is_sha256(value) for value in self.files.values()
        ):
            raise ValueError("API retrieval index files are incomplete")
        expected = _sha256_bytes(
            _canonical_bytes(
                {
                    "binding": self.binding.model_dump(mode="json"),
                    "dense_dimension": self.dense_dimension,
                    "files": dict(sorted(self.files.items())),
                }
            )
        )
        if self.artifact_id != expected:
            raise ValueError("API retrieval artifact identifier is inconsistent")
        return self


@dataclass(frozen=True)
class LoadedApiRetrievalIndexV2:
    manifest: ApiRetrievalIndexManifestV2
    retriever: Retriever
    artifact_path: Path
    lexical_retriever: Retriever
    dense_retriever: Retriever


class StreamingRetrievalIndexMaterializerV2:
    """Persist one bounded vector batch at a time before immutable publication."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.artifacts_root = self.root / "artifacts-v2"
        self.work_root = self.root / "work-v2"
        self.bindings_root = self.root / "bindings-v2"
        for path in (self.artifacts_root, self.work_root, self.bindings_root):
            path.mkdir(parents=True, exist_ok=True)

    def materialize(
        self,
        binding: ApiRetrievalIndexBindingV2,
        chunks: Sequence[DocumentChunk],
        embedder: TextEmbedder,
        *,
        resume: bool = False,
    ) -> ApiRetrievalIndexManifestV2:
        ordered = sorted(chunks, key=lambda chunk: chunk.id)
        self._validate_binding(binding, ordered)
        self._validate_embedder(binding, embedder)
        existing = self._load_pointer(binding)
        if existing is not None:
            return self.verify(existing, expected_binding=binding)

        ledger_path = self.work_root / f"{binding.binding_sha256}.sqlite3"
        if resume and not ledger_path.is_file():
            raise RetrievalIndexUnavailableError("materialization resume ledger is unavailable")
        if not resume and ledger_path.exists():
            raise RetrievalIndexBindingError(
                "materialization ledger exists; use an explicit resume"
            )
        connection = self._open_ledger(
            ledger_path,
            binding=binding,
            chunks=ordered,
            resume=resume,
        )
        started = time.perf_counter()
        try:
            for batch_index, (start, batch) in enumerate(
                _bounded_embedding_batches(
                    ordered,
                    maximum_items=binding.embedding_batch_size,
                    maximum_tokens=binding.embedding_request_token_limit,
                )
            ):
                if self._batch_complete(
                    connection,
                    batch_index=batch_index,
                    start=start,
                    chunks=batch,
                ):
                    continue
                usage_before = _usage_snapshot(embedder)
                batch_started = time.perf_counter()
                vectors = embedder.embed_documents(
                    [retrieval_text(chunk) for chunk in batch]
                )
                elapsed = time.perf_counter() - batch_started
                usage_after = _usage_snapshot(embedder)
                if len(vectors) != len(batch):
                    raise RetrievalIndexBindingError(
                        "embedder returned the wrong document vector count"
                    )
                packed = [
                    _normalized_vector_bytes(
                        vector,
                        dimension=binding.embedding_dimensions,
                    )
                    for vector in vectors
                ]
                self._record_batch(
                    connection,
                    batch_index=batch_index,
                    start=start,
                    chunks=batch,
                    packed_vectors=packed,
                    elapsed_seconds=elapsed,
                    usage_before=usage_before,
                    usage_after=usage_after,
                )
            manifest = self._publish(
                connection,
                binding=binding,
                chunks=ordered,
                elapsed_seconds=time.perf_counter() - started,
            )
            connection.execute(
                "UPDATE metadata SET value = ? WHERE key = 'status'",
                ("completed",),
            )
            self._write_pointer(manifest)
            return manifest
        finally:
            connection.close()

    def verify(
        self,
        artifact_id: str,
        *,
        expected_binding: ApiRetrievalIndexBindingV2 | None = None,
    ) -> ApiRetrievalIndexManifestV2:
        if not _is_sha256(artifact_id):
            raise RetrievalIndexBindingError("artifact identifier must be SHA-256")
        artifact_path = self.artifacts_root / artifact_id[:2] / artifact_id
        manifest_path = artifact_path / "manifest.json"
        if not manifest_path.is_file() or manifest_path.is_symlink():
            raise RetrievalIndexUnavailableError("API retrieval artifact is unavailable")
        try:
            manifest = ApiRetrievalIndexManifestV2.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, ValueError) as error:
            raise RetrievalIndexCorruptionError(
                "API retrieval manifest is malformed"
            ) from error
        if manifest.artifact_id != artifact_id:
            raise RetrievalIndexCorruptionError("API retrieval artifact path drifted")
        if expected_binding is not None and manifest.binding != expected_binding:
            raise RetrievalIndexBindingError("API retrieval binding drifted")
        for name, expected_hash in manifest.files.items():
            path = artifact_path / name
            if not path.is_file() or path.is_symlink() or _sha256_file(path) != expected_hash:
                raise RetrievalIndexCorruptionError(
                    "API retrieval artifact checksum mismatch"
                )
        return manifest

    def load(
        self,
        artifact_id: str,
        *,
        expected_binding: ApiRetrievalIndexBindingV2,
        embedder: TextEmbedder,
    ) -> LoadedApiRetrievalIndexV2:
        manifest = self.verify(artifact_id, expected_binding=expected_binding)
        self._validate_embedder(expected_binding, embedder)
        artifact_path = self.artifacts_root / artifact_id[:2] / artifact_id
        try:
            chunks_payload = json.loads(
                (artifact_path / "chunks.json").read_text(encoding="utf-8")
            )
            lexical_payload = json.loads(
                (artifact_path / "lexical.json").read_text(encoding="utf-8")
            )
            dense_payload = json.loads(
                (artifact_path / "dense.json").read_text(encoding="utf-8")
            )
            chunks = [DocumentChunk.model_validate(row) for row in chunks_payload["chunks"]]
            chunk_ids = [chunk.id for chunk in chunks]
            if lexical_payload["chunk_ids"] != chunk_ids or dense_payload["chunk_ids"] != chunk_ids:
                raise ValueError("index ordering drifted")
            frequencies = dict(
                zip(chunk_ids, lexical_payload["term_frequencies"], strict=True)
            )
            lengths = dict(
                zip(chunk_ids, lexical_payload["document_lengths"], strict=True)
            )
            raw = (artifact_path / "dense.f32").read_bytes()
            expected_bytes = len(chunk_ids) * expected_binding.embedding_dimensions * 4
            if len(raw) != expected_bytes:
                raise ValueError("dense byte length drifted")
            values = array.array("f")
            values.frombytes(raw)
            if sys.byteorder != "little":
                values.byteswap()
            vectors = {
                chunk_id: list(values[offset : offset + expected_binding.embedding_dimensions])
                for chunk_id, offset in zip(
                    chunk_ids,
                    range(0, len(values), expected_binding.embedding_dimensions),
                    strict=True,
                )
            }
            lexical = BM25Retriever.from_index(
                chunks,
                term_frequencies=frequencies,
                document_lengths=lengths,
                document_frequencies=lexical_payload["document_frequencies"],
                average_document_length=lexical_payload["average_document_length"],
                k1=expected_binding.bm25_k1,
                b=expected_binding.bm25_b,
            )
            dense = DenseRetriever.from_index(chunks, embedder, vectors=vectors)
            retriever = ReciprocalRankFusionRetriever(
                [lexical, dense],
                rank_constant=expected_binding.fusion_rank_constant,
                candidate_limit=expected_binding.fusion_candidate_limit,
            )
        except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise RetrievalIndexCorruptionError(
                "API retrieval artifact payload is malformed"
            ) from error
        return LoadedApiRetrievalIndexV2(
            manifest,
            retriever,
            artifact_path,
            lexical,
            dense,
        )

    def _open_ledger(
        self,
        path: Path,
        *,
        binding: ApiRetrievalIndexBindingV2,
        chunks: Sequence[DocumentChunk],
        resume: bool,
    ) -> sqlite3.Connection:
        if not resume:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS batches (
                batch_index INTEGER PRIMARY KEY,
                start_index INTEGER NOT NULL,
                item_count INTEGER NOT NULL,
                chunk_ids_sha256 TEXT NOT NULL,
                vector_sha256 TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                latency_seconds REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vectors (
                chunk_index INTEGER PRIMARY KEY,
                chunk_id TEXT NOT NULL UNIQUE,
                vector_blob BLOB NOT NULL,
                vector_sha256 TEXT NOT NULL
            );
            """
        )
        expected = {
            "schema_version": "2",
            "binding_sha256": binding.binding_sha256,
            "source_set_sha256": binding.source_set_sha256,
            "chunk_ids_sha256": _sha256_bytes(
                _canonical_bytes([chunk.id for chunk in chunks])
            ),
            "status": "running",
        }
        existing = dict(connection.execute("SELECT key, value FROM metadata"))
        if resume:
            for key, value in expected.items():
                if key != "status" and existing.get(key) != value:
                    connection.close()
                    raise RetrievalIndexBindingError(
                        "materialization resume binding drifted"
                    )
            if existing.get("status") != "running":
                connection.close()
                raise RetrievalIndexBindingError(
                    "completed materialization cannot be resumed"
                )
        else:
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)", expected.items()
            )
            connection.commit()
        return connection

    @staticmethod
    def _batch_complete(
        connection: sqlite3.Connection,
        *,
        batch_index: int,
        start: int,
        chunks: Sequence[DocumentChunk],
    ) -> bool:
        row = connection.execute(
            "SELECT start_index, item_count, chunk_ids_sha256 FROM batches WHERE batch_index = ?",
            (batch_index,),
        ).fetchone()
        if row is None:
            return False
        expected = (
            start,
            len(chunks),
            _sha256_bytes(_canonical_bytes([chunk.id for chunk in chunks])),
        )
        if tuple(row) != expected:
            raise RetrievalIndexCorruptionError("completed materialization batch drifted")
        count = connection.execute(
            "SELECT COUNT(*) FROM vectors WHERE chunk_index >= ? AND chunk_index < ?",
            (start, start + len(chunks)),
        ).fetchone()[0]
        if count != len(chunks):
            raise RetrievalIndexCorruptionError("completed batch vector rows are incomplete")
        return True

    @staticmethod
    def _record_batch(
        connection: sqlite3.Connection,
        *,
        batch_index: int,
        start: int,
        chunks: Sequence[DocumentChunk],
        packed_vectors: Sequence[bytes],
        elapsed_seconds: float,
        usage_before: Any,
        usage_after: Any,
    ) -> None:
        input_tokens = usage_after.input_tokens - usage_before.input_tokens
        cost_usd = usage_after.approximate_cost_usd - usage_before.approximate_cost_usd
        if input_tokens < 0 or cost_usd < 0:
            raise RetrievalIndexBindingError("provider usage accounting regressed")
        vector_sha256 = _sha256_bytes(b"".join(packed_vectors))
        with connection:
            connection.executemany(
                "INSERT INTO vectors(chunk_index, chunk_id, vector_blob, vector_sha256) VALUES (?, ?, ?, ?)",
                [
                    (start + offset, chunk.id, packed, _sha256_bytes(packed))
                    for offset, (chunk, packed) in enumerate(
                        zip(chunks, packed_vectors, strict=True)
                    )
                ],
            )
            connection.execute(
                "INSERT INTO batches(batch_index, start_index, item_count, chunk_ids_sha256, vector_sha256, input_tokens, cost_usd, latency_seconds) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    batch_index,
                    start,
                    len(chunks),
                    _sha256_bytes(_canonical_bytes([chunk.id for chunk in chunks])),
                    vector_sha256,
                    input_tokens,
                    cost_usd,
                    elapsed_seconds,
                ),
            )

    def _publish(
        self,
        connection: sqlite3.Connection,
        *,
        binding: ApiRetrievalIndexBindingV2,
        chunks: Sequence[DocumentChunk],
        elapsed_seconds: float,
    ) -> ApiRetrievalIndexManifestV2:
        if connection.execute("SELECT COUNT(*) FROM vectors").fetchone()[0] != len(chunks):
            raise RetrievalIndexCorruptionError("materialization vectors are incomplete")
        temporary = Path(tempfile.mkdtemp(prefix=".building-v2-", dir=self.artifacts_root))
        try:
            chunk_ids = [chunk.id for chunk in chunks]
            frequencies = [
                dict(sorted(Counter(lexical_tokens(retrieval_text(chunk))).items()))
                for chunk in chunks
            ]
            lengths = [sum(row.values()) for row in frequencies]
            document_frequencies: Counter[str] = Counter()
            for row in frequencies:
                document_frequencies.update(row.keys())
            _write_bytes(
                temporary / "chunks.json",
                _canonical_bytes(
                    {
                        "schema_version": 2,
                        "chunks": [
                            chunk.model_dump(mode="json", exclude_none=False)
                            for chunk in chunks
                        ],
                    }
                )
                + b"\n",
            )
            _write_bytes(
                temporary / "lexical.json",
                _canonical_bytes(
                    {
                        "schema_version": 2,
                        "chunk_ids": chunk_ids,
                        "term_frequencies": frequencies,
                        "document_lengths": lengths,
                        "average_document_length": sum(lengths) / len(lengths),
                        "document_frequencies": dict(sorted(document_frequencies.items())),
                    }
                )
                + b"\n",
            )
            _write_bytes(
                temporary / "dense.json",
                _canonical_bytes(
                    {
                        "schema_version": 2,
                        "chunk_ids": chunk_ids,
                        "dimension": binding.embedding_dimensions,
                        "format": "float32-little-endian-row-major-unit-normalized",
                    }
                )
                + b"\n",
            )
            with (temporary / "dense.f32").open("xb") as stream:
                expected_index = 0
                for chunk_index, chunk_id, vector_blob, vector_sha256 in connection.execute(
                    "SELECT chunk_index, chunk_id, vector_blob, vector_sha256 FROM vectors ORDER BY chunk_index"
                ):
                    if (
                        chunk_index != expected_index
                        or chunk_id != chunks[expected_index].id
                        or _sha256_bytes(vector_blob) != vector_sha256
                    ):
                        raise RetrievalIndexCorruptionError(
                            "materialization vector ordering or checksum drifted"
                        )
                    stream.write(vector_blob)
                    expected_index += 1
                if expected_index != len(chunks):
                    raise RetrievalIndexCorruptionError("materialization vector stream is incomplete")
                stream.flush()
                os.fsync(stream.fileno())
            file_hashes = {
                name: _sha256_file(temporary / name) for name in sorted(_ARTIFACT_FILES)
            }
            artifact_id = _sha256_bytes(
                _canonical_bytes(
                    {
                        "binding": binding.model_dump(mode="json"),
                        "dense_dimension": binding.embedding_dimensions,
                        "files": file_hashes,
                    }
                )
            )
            totals = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(input_tokens), 0), COALESCE(SUM(cost_usd), 0), COALESCE(SUM(latency_seconds), 0) FROM batches"
            ).fetchone()
            manifest = ApiRetrievalIndexManifestV2(
                artifact_id=artifact_id,
                binding=binding,
                dense_dimension=binding.embedding_dimensions,
                files=file_hashes,
                materialization={
                    "batch_count": int(totals[0]),
                    "input_tokens": int(totals[1]),
                    "cost_usd": float(totals[2]),
                    "provider_latency_seconds": float(totals[3]),
                    "wall_seconds": elapsed_seconds,
                    "peak_retained_vector_count": binding.embedding_batch_size,
                },
            )
            _write_bytes(
                temporary / "manifest.json",
                _canonical_bytes(manifest.model_dump(mode="json")) + b"\n",
            )
            final_path = self.artifacts_root / artifact_id[:2] / artifact_id
            final_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.rename(temporary, final_path)
            except OSError:
                if not final_path.exists():
                    raise
                existing = self.verify(artifact_id, expected_binding=binding)
                if existing != manifest:
                    raise RetrievalIndexCorruptionError(
                        "concurrent API index publication disagreed"
                    )
            return self.verify(artifact_id, expected_binding=binding)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    @staticmethod
    def _validate_binding(
        binding: ApiRetrievalIndexBindingV2,
        chunks: Sequence[DocumentChunk],
    ) -> None:
        if binding.chunk_count != len(chunks) or source_set_sha256(chunks) != binding.source_set_sha256:
            raise RetrievalIndexBindingError("API retrieval source binding drifted")
        if any(
            chunk.metadata.get("course_id") != binding.course_id
            or not chunk.retrieval_allowed
            for chunk in chunks
        ):
            raise RetrievalIndexBindingError("API retrieval index crossed its course boundary")

    @staticmethod
    def _validate_embedder(
        binding: ApiRetrievalIndexBindingV2,
        embedder: TextEmbedder,
    ) -> None:
        expected = {
            "provider_id": binding.embedding_provider,
            "model_name": binding.embedding_model,
            "dimensions": binding.embedding_dimensions,
            "batch_size": binding.embedding_batch_size,
            "request_token_limit": binding.embedding_request_token_limit,
            "endpoint": binding.embedding_endpoint,
        }
        mismatches = [
            name for name, value in expected.items() if getattr(embedder, name, None) != value
        ]
        if mismatches:
            raise RetrievalIndexBindingError(
                "API embedder does not match its binding: " + ", ".join(sorted(mismatches))
            )

    def _load_pointer(self, binding: ApiRetrievalIndexBindingV2) -> str | None:
        path = self.bindings_root / f"{binding.binding_sha256}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RetrievalIndexCorruptionError("API retrieval pointer is malformed") from error
        if payload.get("binding_sha256") != binding.binding_sha256:
            raise RetrievalIndexBindingError("API retrieval pointer binding drifted")
        artifact_id = str(payload.get("artifact_id", ""))
        if not _is_sha256(artifact_id):
            raise RetrievalIndexCorruptionError("API retrieval pointer artifact drifted")
        return artifact_id

    def _write_pointer(self, manifest: ApiRetrievalIndexManifestV2) -> None:
        path = self.bindings_root / f"{manifest.binding.binding_sha256}.json"
        payload = _canonical_bytes(
            {
                "schema_version": 2,
                "binding_sha256": manifest.binding.binding_sha256,
                "artifact_id": manifest.artifact_id,
            }
        ) + b"\n"
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()


def _usage_snapshot(embedder: TextEmbedder) -> Any:
    reporter = getattr(embedder, "usage_snapshot", None)
    if not callable(reporter):
        raise RetrievalIndexBindingError("API embedder does not expose usage accounting")
    usage = reporter()
    required = ("input_tokens", "approximate_cost_usd")
    if any(not hasattr(usage, name) for name in required):
        raise RetrievalIndexBindingError("API embedder usage accounting is malformed")
    return usage


__all__ = [
    "ApiRetrievalIndexBindingV2",
    "ApiRetrievalIndexManifestV2",
    "LoadedApiRetrievalIndexV2",
    "StreamingRetrievalIndexMaterializerV2",
]
