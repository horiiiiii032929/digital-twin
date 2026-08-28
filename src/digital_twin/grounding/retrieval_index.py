"""Immutable, release-bound retrieval indexes for product runtime loading."""

from __future__ import annotations

import array
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.protocols import Retriever, TextEmbedder
from src.digital_twin.grounding.retrieval import (
    BM25Retriever,
    DenseRetriever,
    ReciprocalRankFusionRetriever,
    lexical_tokens,
    retrieval_text,
)


_SHA256_LENGTH = 64
_ARTIFACT_FILES = frozenset(
    {"chunks.json", "lexical.json", "dense.json", "dense.f32"}
)


class RetrievalIndexError(RuntimeError):
    """Sanitized base error for index lifecycle failures."""


class RetrievalIndexBindingError(RetrievalIndexError):
    pass


class RetrievalIndexCorruptionError(RetrievalIndexError):
    pass


class RetrievalIndexUnavailableError(RetrievalIndexError):
    pass


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _is_sha256(value: str) -> bool:
    return len(value) == _SHA256_LENGTH and all(
        character in "0123456789abcdef" for character in value
    )


def source_set_sha256(chunks: Sequence[DocumentChunk]) -> str:
    """Hash ordered authoritative chunk content and lineage."""

    ordered = sorted(chunks, key=lambda chunk: chunk.id)
    identifiers = [chunk.id for chunk in ordered]
    if len(identifiers) != len(set(identifiers)):
        raise RetrievalIndexBindingError("release chunk identifiers must be unique")
    if not ordered or any(not chunk.retrieval_allowed for chunk in ordered):
        raise RetrievalIndexBindingError(
            "retrieval indexes require approved retrieval-eligible chunks"
        )
    return _sha256_bytes(
        _canonical_bytes(
            [chunk.model_dump(mode="json", exclude_none=False) for chunk in ordered]
        )
    )


class RetrievalIndexBindingV1(BaseModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    chunker_id: str = Field(min_length=1)
    chunker_version: str = Field(min_length=1)
    retriever_implementation_id: str = Field(min_length=1)
    source_set_sha256: str
    chunk_count: int = Field(ge=1)
    embedding_provider: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    embedding_revision: str = Field(min_length=1)
    query_instruction_sha256: str
    device: str = Field(min_length=1)
    dtype: str = Field(min_length=1)
    embedding_max_length: int = Field(ge=32)
    embedding_batch_size: int = Field(ge=1)
    bm25_k1: float = Field(gt=0, allow_inf_nan=False)
    bm25_b: float = Field(ge=0, le=1, allow_inf_nan=False)
    fusion_rank_constant: int = Field(ge=1)
    fusion_candidate_limit: int = Field(ge=1)

    @field_validator("source_set_sha256", "query_instruction_sha256")
    @classmethod
    def hashes_must_be_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _is_sha256(normalized):
            raise ValueError("retrieval index hashes must be lowercase SHA-256")
        return normalized

    @model_validator(mode="after")
    def selected_retriever_must_be_supported(self) -> "RetrievalIndexBindingV1":
        if self.retriever_implementation_id != "qwen3-hybrid-v1":
            raise ValueError("only the selected qwen3 hybrid index is supported")
        return self

    @property
    def binding_sha256(self) -> str:
        return _sha256_bytes(_canonical_bytes(self.model_dump(mode="json")))


def build_retrieval_index_binding(
    *,
    course_id: str,
    release_id: str,
    profile_id: str,
    profile_version: str,
    chunker_id: str,
    chunker_version: str,
    chunks: Sequence[DocumentChunk],
    configuration: Mapping[str, str | int | float | bool],
) -> RetrievalIndexBindingV1:
    """Create the exact immutable binding from a selected retrieval profile."""

    def required(name: str) -> str | int | float | bool:
        if name not in configuration:
            raise RetrievalIndexBindingError(
                f"retrieval configuration is missing {name}"
            )
        return configuration[name]

    def required_int(name: str) -> int:
        value = required(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise RetrievalIndexBindingError(
                f"retrieval configuration {name} must be an integer"
            )
        return value

    def required_number(name: str) -> float:
        value = required(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RetrievalIndexBindingError(
                f"retrieval configuration {name} must be numeric"
            )
        return float(value)

    query_instruction = str(required("query_instruction"))
    return RetrievalIndexBindingV1(
        course_id=course_id,
        release_id=release_id,
        profile_id=profile_id,
        profile_version=profile_version,
        chunker_id=chunker_id,
        chunker_version=chunker_version,
        retriever_implementation_id="qwen3-hybrid-v1",
        source_set_sha256=source_set_sha256(chunks),
        chunk_count=len(chunks),
        embedding_provider=str(required("embedding_provider")),
        embedding_model=str(required("embedding_model")),
        embedding_revision=str(required("embedding_revision")),
        query_instruction_sha256=_sha256_bytes(query_instruction.encode("utf-8")),
        device=str(required("device")),
        dtype=str(required("dtype")),
        embedding_max_length=required_int("embedding_max_length"),
        embedding_batch_size=required_int("embedding_batch_size"),
        bm25_k1=required_number("bm25_k1"),
        bm25_b=required_number("bm25_b"),
        fusion_rank_constant=required_int("fusion_rank_constant"),
        fusion_candidate_limit=required_int("fusion_candidate_limit"),
    )


class RetrievalIndexManifestV1(BaseModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    artifact_id: str
    binding: RetrievalIndexBindingV1
    dense_dimension: int = Field(ge=1)
    files: dict[str, str]

    @field_validator("artifact_id")
    @classmethod
    def artifact_id_must_be_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _is_sha256(normalized):
            raise ValueError("artifact_id must be a lowercase SHA-256")
        return normalized

    @model_validator(mode="after")
    def files_must_be_complete(self) -> "RetrievalIndexManifestV1":
        if set(self.files) != _ARTIFACT_FILES:
            raise ValueError("retrieval index manifest files are incomplete")
        if any(not _is_sha256(value) for value in self.files.values()):
            raise ValueError("retrieval index file hashes must be SHA-256")
        expected = _artifact_id(
            self.binding,
            dense_dimension=self.dense_dimension,
            files=self.files,
        )
        if self.artifact_id != expected:
            raise ValueError("retrieval index artifact identifier is inconsistent")
        return self


class PublishedRetrievalIndexV1(BaseModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    artifact_id: str
    binding_sha256: str

    @field_validator("artifact_id", "binding_sha256")
    @classmethod
    def values_must_be_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _is_sha256(normalized):
            raise ValueError("published index identifiers must be SHA-256")
        return normalized


@dataclass(frozen=True)
class LoadedRetrievalIndexV1:
    manifest: RetrievalIndexManifestV1
    retriever: Retriever
    artifact_path: Path


def _artifact_id(
    binding: RetrievalIndexBindingV1,
    *,
    dense_dimension: int,
    files: Mapping[str, str],
) -> str:
    return _sha256_bytes(
        _canonical_bytes(
            {
                "binding": binding.model_dump(mode="json"),
                "dense_dimension": dense_dimension,
                "files": dict(sorted(files.items())),
            }
        )
    )


def _normalized_vector(vector: Sequence[float]) -> list[float]:
    try:
        values = [float(value) for value in vector]
    except (TypeError, ValueError) as error:
        raise RetrievalIndexBindingError("embedding vectors must be numeric") from error
    if not values or any(not math.isfinite(value) for value in values):
        raise RetrievalIndexBindingError(
            "embedding vectors must be finite and non-empty"
        )
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude == 0:
        raise RetrievalIndexBindingError("embedding vectors cannot have zero magnitude")
    return [value / magnitude for value in values]


def _write_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, value: Any) -> None:
    _write_bytes(path, _canonical_bytes(value) + b"\n")


def _atomic_write_json(path: Path, value: Any) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_bytes(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_json(path: Path) -> Any:
    if not path.is_file() or path.is_symlink():
        raise RetrievalIndexCorruptionError("retrieval index file is unavailable")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RetrievalIndexCorruptionError(
            "retrieval index contains malformed JSON"
        ) from error


def _encode_vectors(vectors: Sequence[Sequence[float]]) -> bytes:
    values = array.array("f")
    for vector in vectors:
        values.extend(vector)
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes()


def _decode_vectors(
    content: bytes,
    *,
    chunk_ids: Sequence[str],
    dimension: int,
) -> dict[str, list[float]]:
    expected_bytes = len(chunk_ids) * dimension * 4
    if len(content) != expected_bytes:
        raise RetrievalIndexCorruptionError("dense index byte length is inconsistent")
    values = array.array("f")
    values.frombytes(content)
    if sys.byteorder != "little":
        values.byteswap()
    return {
        identifier: list(values[offset : offset + dimension])
        for identifier, offset in zip(
            chunk_ids,
            range(0, len(values), dimension),
            strict=True,
        )
    }


class RetrievalIndexStoreV1:
    """Build, publish, verify, and load immutable release index artifacts."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.artifacts_root = self.root / "artifacts"
        self.active_root = self.root / "active"
        self.bindings_root = self.root / "bindings"
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        self.active_root.mkdir(parents=True, exist_ok=True)
        self.bindings_root.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        binding: RetrievalIndexBindingV1,
        chunks: Sequence[DocumentChunk],
        embedder: TextEmbedder,
    ) -> RetrievalIndexManifestV1:
        ordered = sorted(chunks, key=lambda chunk: chunk.id)
        self._validate_binding(binding, ordered)
        self._validate_embedder(binding, embedder)

        existing = self._load_binding_pointer(binding)
        if existing is not None:
            return self.verify(existing.artifact_id, expected_binding=binding)

        vectors = embedder.embed_documents(
            [retrieval_text(chunk) for chunk in ordered]
        )
        if len(vectors) != len(ordered):
            raise RetrievalIndexBindingError(
                "embedder returned the wrong document vector count"
            )
        normalized = [_normalized_vector(vector) for vector in vectors]
        dimensions = {len(vector) for vector in normalized}
        if len(dimensions) != 1:
            raise RetrievalIndexBindingError(
                "embedder returned inconsistent document dimensions"
            )
        dimension = next(iter(dimensions))
        chunk_ids = [chunk.id for chunk in ordered]

        term_frequencies = [
            dict(sorted(Counter(lexical_tokens(retrieval_text(chunk))).items()))
            for chunk in ordered
        ]
        document_lengths = [sum(frequencies.values()) for frequencies in term_frequencies]
        document_frequencies: Counter[str] = Counter()
        for frequencies in term_frequencies:
            document_frequencies.update(frequencies.keys())

        chunks_payload = {
            "schema_version": 1,
            "chunks": [
                chunk.model_dump(mode="json", exclude_none=False) for chunk in ordered
            ],
        }
        lexical_payload = {
            "schema_version": 1,
            "chunk_ids": chunk_ids,
            "term_frequencies": term_frequencies,
            "document_lengths": document_lengths,
            "average_document_length": (
                sum(document_lengths) / len(document_lengths)
            ),
            "document_frequencies": dict(sorted(document_frequencies.items())),
        }
        dense_payload = {
            "schema_version": 1,
            "chunk_ids": chunk_ids,
            "dimension": dimension,
            "format": "float32-little-endian-row-major",
        }
        contents = {
            "chunks.json": _canonical_bytes(chunks_payload) + b"\n",
            "lexical.json": _canonical_bytes(lexical_payload) + b"\n",
            "dense.json": _canonical_bytes(dense_payload) + b"\n",
            "dense.f32": _encode_vectors(normalized),
        }
        file_hashes = {
            name: _sha256_bytes(content) for name, content in contents.items()
        }
        artifact_id = _artifact_id(
            binding,
            dense_dimension=dimension,
            files=file_hashes,
        )
        manifest = RetrievalIndexManifestV1(
            artifact_id=artifact_id,
            binding=binding,
            dense_dimension=dimension,
            files=file_hashes,
        )
        final_path = self._artifact_path(artifact_id)
        if final_path.exists():
            existing = self.verify(artifact_id, expected_binding=binding)
            if existing != manifest:
                raise RetrievalIndexCorruptionError(
                    "existing immutable retrieval index does not match"
                )
            self._write_binding_pointer(existing)
            return existing

        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(
            tempfile.mkdtemp(prefix=".building-", dir=self.artifacts_root)
        )
        try:
            for name, content in contents.items():
                _write_bytes(temporary / name, content)
            _write_json(temporary / "manifest.json", manifest.model_dump(mode="json"))
            try:
                os.rename(temporary, final_path)
            except OSError:
                if not final_path.exists():
                    raise
                existing = self.verify(artifact_id, expected_binding=binding)
                if existing != manifest:
                    raise RetrievalIndexCorruptionError(
                        "concurrent immutable index publication disagreed"
                    )
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        verified = self.verify(artifact_id, expected_binding=binding)
        self._write_binding_pointer(verified)
        return verified

    def verify(
        self,
        artifact_id: str,
        *,
        expected_binding: RetrievalIndexBindingV1 | None = None,
    ) -> RetrievalIndexManifestV1:
        artifact_path = self._artifact_path(artifact_id)
        if not artifact_path.is_dir() or artifact_path.is_symlink():
            raise RetrievalIndexUnavailableError("retrieval index artifact is unavailable")
        try:
            manifest = RetrievalIndexManifestV1.model_validate(
                _read_json(artifact_path / "manifest.json")
            )
        except ValueError as error:
            raise RetrievalIndexCorruptionError(
                "retrieval index manifest is invalid"
            ) from error
        if manifest.artifact_id != artifact_id:
            raise RetrievalIndexCorruptionError(
                "retrieval index path does not match its manifest"
            )
        if expected_binding is not None and manifest.binding != expected_binding:
            raise RetrievalIndexBindingError(
                "retrieval index binding does not match the requested release"
            )
        for name, expected_hash in manifest.files.items():
            path = artifact_path / name
            if not path.is_file() or path.is_symlink():
                raise RetrievalIndexCorruptionError(
                    "retrieval index artifact file is unavailable"
                )
            if _sha256_bytes(path.read_bytes()) != expected_hash:
                raise RetrievalIndexCorruptionError(
                    "retrieval index artifact checksum mismatch"
                )
        return manifest

    def publish(self, manifest: RetrievalIndexManifestV1) -> PublishedRetrievalIndexV1:
        verified = self.verify(
            manifest.artifact_id,
            expected_binding=manifest.binding,
        )
        pointer = PublishedRetrievalIndexV1(
            course_id=verified.binding.course_id,
            release_id=verified.binding.release_id,
            artifact_id=verified.artifact_id,
            binding_sha256=verified.binding.binding_sha256,
        )
        path = self._active_path(verified.binding.course_id)
        _atomic_write_json(path, pointer.model_dump(mode="json"))
        return pointer

    def load_published(
        self,
        expected_binding: RetrievalIndexBindingV1,
        embedder: TextEmbedder,
    ) -> LoadedRetrievalIndexV1:
        pointer_path = self._active_path(expected_binding.course_id)
        if not pointer_path.is_file() or pointer_path.is_symlink():
            raise RetrievalIndexUnavailableError(
                "published retrieval index pointer is unavailable"
            )
        try:
            pointer = PublishedRetrievalIndexV1.model_validate(
                _read_json(pointer_path)
            )
        except ValueError as error:
            raise RetrievalIndexCorruptionError(
                "published retrieval index pointer is invalid"
            ) from error
        if (
            pointer.course_id != expected_binding.course_id
            or pointer.release_id != expected_binding.release_id
            or pointer.binding_sha256 != expected_binding.binding_sha256
        ):
            raise RetrievalIndexBindingError(
                "published retrieval index does not match the requested release"
            )
        return self.load(
            pointer.artifact_id,
            expected_binding=expected_binding,
            embedder=embedder,
        )

    def load_bound(
        self,
        expected_binding: RetrievalIndexBindingV1,
        embedder: TextEmbedder,
    ) -> LoadedRetrievalIndexV1:
        """Load the immutable artifact registered for an exact release binding."""

        pointer = self._load_binding_pointer(expected_binding)
        if pointer is None:
            raise RetrievalIndexUnavailableError(
                "release retrieval index binding is unavailable"
            )
        return self.load(
            pointer.artifact_id,
            expected_binding=expected_binding,
            embedder=embedder,
        )

    def verify_bound(
        self,
        expected_binding: RetrievalIndexBindingV1,
    ) -> RetrievalIndexManifestV1:
        """Verify the exact registered artifact without loading query runtime."""

        pointer = self._load_binding_pointer(expected_binding)
        if pointer is None:
            raise RetrievalIndexUnavailableError(
                "release retrieval index binding is unavailable"
            )
        return self.verify(
            pointer.artifact_id,
            expected_binding=expected_binding,
        )

    def load(
        self,
        artifact_id: str,
        *,
        expected_binding: RetrievalIndexBindingV1,
        embedder: TextEmbedder,
    ) -> LoadedRetrievalIndexV1:
        manifest = self.verify(artifact_id, expected_binding=expected_binding)
        self._validate_embedder(expected_binding, embedder)
        artifact_path = self._artifact_path(artifact_id)
        try:
            chunks_payload = _read_json(artifact_path / "chunks.json")
            lexical_payload = _read_json(artifact_path / "lexical.json")
            dense_payload = _read_json(artifact_path / "dense.json")
            chunks = [
                DocumentChunk.model_validate(value)
                for value in chunks_payload["chunks"]
            ]
            chunk_ids = [chunk.id for chunk in chunks]
            if (
                chunks_payload.get("schema_version") != 1
                or lexical_payload.get("schema_version") != 1
                or dense_payload.get("schema_version") != 1
                or lexical_payload["chunk_ids"] != chunk_ids
                or dense_payload["chunk_ids"] != chunk_ids
                or dense_payload["dimension"] != manifest.dense_dimension
                or dense_payload["format"] != "float32-little-endian-row-major"
                or source_set_sha256(chunks) != expected_binding.source_set_sha256
                or len(chunks) != expected_binding.chunk_count
            ):
                raise RetrievalIndexCorruptionError(
                    "retrieval index payload lineage is inconsistent"
                )
            frequencies = dict(
                zip(
                    chunk_ids,
                    lexical_payload["term_frequencies"],
                    strict=True,
                )
            )
            lengths = dict(
                zip(
                    chunk_ids,
                    lexical_payload["document_lengths"],
                    strict=True,
                )
            )
            vectors = _decode_vectors(
                (artifact_path / "dense.f32").read_bytes(),
                chunk_ids=chunk_ids,
                dimension=manifest.dense_dimension,
            )
        except RetrievalIndexError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise RetrievalIndexCorruptionError(
                "retrieval index payload is malformed"
            ) from error

        try:
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
        except (KeyError, TypeError, ValueError) as error:
            raise RetrievalIndexCorruptionError(
                "retrieval index payload invariants are invalid"
            ) from error
        return LoadedRetrievalIndexV1(
            manifest=manifest,
            retriever=retriever,
            artifact_path=artifact_path,
        )

    def _validate_binding(
        self,
        binding: RetrievalIndexBindingV1,
        chunks: Sequence[DocumentChunk],
    ) -> None:
        if binding.chunk_count != len(chunks):
            raise RetrievalIndexBindingError(
                "retrieval index chunk count does not match the binding"
            )
        if source_set_sha256(chunks) != binding.source_set_sha256:
            raise RetrievalIndexBindingError(
                "retrieval index source set does not match the binding"
            )
        if any(
            chunk.metadata.get("course_id") != binding.course_id for chunk in chunks
        ):
            raise RetrievalIndexBindingError(
                "retrieval index cannot cross course boundaries"
            )
        versions_by_source: dict[str, set[int]] = {}
        for chunk in chunks:
            source_id = chunk.source_artifact_id or chunk.document_id
            versions_by_source.setdefault(source_id, set()).add(chunk.source_version)
        if any(len(versions) != 1 for versions in versions_by_source.values()):
            raise RetrievalIndexBindingError(
                "retrieval index cannot contain multiple versions of one source"
            )

    def _validate_embedder(
        self,
        binding: RetrievalIndexBindingV1,
        embedder: TextEmbedder,
    ) -> None:
        expected = {
            "provider_id": binding.embedding_provider,
            "model_name": binding.embedding_model,
            "model_revision": binding.embedding_revision,
            "device": binding.device,
            "dtype": binding.dtype,
            "max_length": binding.embedding_max_length,
            "batch_size": binding.embedding_batch_size,
        }
        mismatches = [
            name for name, value in expected.items() if getattr(embedder, name, None) != value
        ]
        instruction = str(getattr(embedder, "instruction", ""))
        if _sha256_bytes(instruction.encode("utf-8")) != binding.query_instruction_sha256:
            mismatches.append("instruction")
        if mismatches:
            raise RetrievalIndexBindingError(
                "embedder does not match retrieval index binding: "
                + ", ".join(sorted(mismatches))
            )

    def _artifact_path(self, artifact_id: str) -> Path:
        if not _is_sha256(artifact_id):
            raise RetrievalIndexBindingError("artifact identifier must be SHA-256")
        return self.artifacts_root / artifact_id[:2] / artifact_id

    def _binding_path(self, binding_sha256: str) -> Path:
        if not _is_sha256(binding_sha256):
            raise RetrievalIndexBindingError("binding identifier must be SHA-256")
        return self.bindings_root / f"{binding_sha256}.json"

    def _load_binding_pointer(
        self,
        binding: RetrievalIndexBindingV1,
    ) -> PublishedRetrievalIndexV1 | None:
        path = self._binding_path(binding.binding_sha256)
        if not path.exists():
            return None
        if not path.is_file() or path.is_symlink():
            raise RetrievalIndexCorruptionError(
                "retrieval index binding pointer is unavailable"
            )
        try:
            pointer = PublishedRetrievalIndexV1.model_validate(_read_json(path))
        except ValueError as error:
            raise RetrievalIndexCorruptionError(
                "retrieval index binding pointer is invalid"
            ) from error
        if (
            pointer.course_id != binding.course_id
            or pointer.release_id != binding.release_id
            or pointer.binding_sha256 != binding.binding_sha256
        ):
            raise RetrievalIndexBindingError(
                "retrieval index binding pointer does not match"
            )
        return pointer

    def _write_binding_pointer(self, manifest: RetrievalIndexManifestV1) -> None:
        binding = manifest.binding
        pointer = PublishedRetrievalIndexV1(
            course_id=binding.course_id,
            release_id=binding.release_id,
            artifact_id=manifest.artifact_id,
            binding_sha256=binding.binding_sha256,
        )
        _atomic_write_json(
            self._binding_path(binding.binding_sha256),
            pointer.model_dump(mode="json"),
        )

    def _active_path(self, course_id: str) -> Path:
        identifier = _sha256_bytes(course_id.encode("utf-8"))
        return self.active_root / f"{identifier}.json"


__all__ = [
    "LoadedRetrievalIndexV1",
    "PublishedRetrievalIndexV1",
    "RetrievalIndexBindingError",
    "RetrievalIndexBindingV1",
    "RetrievalIndexCorruptionError",
    "RetrievalIndexError",
    "RetrievalIndexManifestV1",
    "RetrievalIndexStoreV1",
    "RetrievalIndexUnavailableError",
    "build_retrieval_index_binding",
    "source_set_sha256",
]
