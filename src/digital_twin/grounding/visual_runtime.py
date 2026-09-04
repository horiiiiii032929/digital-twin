"""Persistent, quota-bounded visual retrieval for the local R1 product."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
from typing import Literal, Protocol
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.grounding.models import DocumentChunk, RegionKind, RetrievalHit
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.region_retrieval import (
    RegionRoute,
    classify_region_query,
)
from src.digital_twin.grounding.visual_late_interaction import (
    JINA_EMBEDDING_ENDPOINT,
    JINA_INPUT_TOKEN_PRICE_USD,
    JINA_MAX_INPUT_TOKENS,
    JINA_VISUAL_MODEL,
    VisualEmbeddingResultV1,
    VisualLateInteractionError,
    VisualLateInteractionIndexV1,
    VisualRegionEmbeddingV1,
    validated_multivector,
)


VISUAL_RUNTIME_SCHEMA_VERSION = "1.0.0"
JINA_ACCOUNT_TOKEN_LIMIT = 10_000_000
JINA_IMPORTED_COMPONENT_TOKENS = 144_639
_VISUAL_KINDS = {
    RegionKind.TABLE,
    RegionKind.FIGURE,
    RegionKind.DIAGRAM,
    RegionKind.EQUATION,
    RegionKind.SCREENSHOT,
}


class VisualRuntimeError(RuntimeError):
    """Raised when product visual retrieval cannot preserve its frozen binding."""


class VisualIndexUnavailableError(VisualRuntimeError):
    """Raised when a release has no materialized visual index."""


class VisualProviderUnavailableError(RuntimeError):
    """Raised for a transient or malformed provider response that permits fallback."""


class VisualProviderIdentityDriftError(VisualRuntimeError):
    """Raised when the provider does not return the frozen visual model identity."""


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _visual_chunk_rows(chunks: Sequence[DocumentChunk]) -> list[dict[str, object]]:
    rows = [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "source_artifact_id": chunk.source_artifact_id,
            "source_version": chunk.source_version,
            "source_checksum": chunk.source_checksum,
            "region_id": chunk.region_id,
            "region_kind": chunk.region_kind.value if chunk.region_kind else None,
            "region_checksum": chunk.region_checksum,
            "bounding_box": chunk.bounding_box,
            "crop_ref": chunk.crop_ref,
            "retrieval_allowed": chunk.retrieval_allowed,
            "display_allowed": chunk.display_allowed,
        }
        for chunk in chunks
        if chunk.region_kind in _VISUAL_KINDS
    ]
    rows.sort(key=lambda row: (str(row["region_id"]), str(row["chunk_id"])))
    return rows


def visual_source_set_sha256(chunks: Sequence[DocumentChunk]) -> str:
    return _canonical_sha256(_visual_chunk_rows(chunks))


class VisualIndexManifestV1(BaseModel):
    """Immutable binding between provider vectors and one published release."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = VISUAL_RUNTIME_SCHEMA_VERSION
    artifact_id: str = Field(min_length=1)
    implementation_id: Literal["jina-v4-late-interaction"] = "jina-v4-late-interaction"
    model: Literal["jina-embeddings-v4"] = JINA_VISUAL_MODEL
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    source_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_ledger_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: int = Field(ge=1)
    imported_account_tokens: int = Field(ge=0)
    created_at: str

    @model_validator(mode="after")
    def identity_is_content_addressed(self) -> "VisualIndexManifestV1":
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        expected = f"visual-index-{_canonical_sha256(payload)[:24]}"
        if self.artifact_id != expected:
            raise ValueError("visual index artifact ID does not match its content")
        return self


class JinaQuotaSnapshotV1(BaseModel):
    token_limit: int
    imported_tokens: int
    completed_tokens: int
    reserved_tokens: int
    accounted_tokens: int
    remaining_tokens: int
    calls: int


class PersistentJinaQuotaLedgerV1:
    """Cross-restart quota accounting with conservative failed-call charging."""

    def __init__(
        self,
        path: Path,
        *,
        token_limit: int = JINA_ACCOUNT_TOKEN_LIMIT,
        imported_tokens: int = JINA_IMPORTED_COMPONENT_TOKENS,
        imported_ledger_sha256: str,
    ) -> None:
        if token_limit != JINA_ACCOUNT_TOKEN_LIMIT:
            raise VisualRuntimeError(
                "Jina account token ceiling must remain 10,000,000"
            )
        if imported_tokens < 0 or imported_tokens >= token_limit:
            raise VisualRuntimeError("imported Jina token accounting is invalid")
        if len(imported_ledger_sha256) != 64:
            raise VisualRuntimeError("imported Jina ledger hash is invalid")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.token_limit = token_limit
        self.imported_tokens = imported_tokens
        self.imported_ledger_sha256 = imported_ledger_sha256
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS visual_quota_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS visual_query_calls (
                    request_id TEXT PRIMARY KEY,
                    request_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('reserved', 'completed', 'failed')),
                    reserved_tokens INTEGER NOT NULL,
                    actual_tokens INTEGER NOT NULL DEFAULT 0,
                    accounted_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL DEFAULT 0,
                    latency_ms REAL NOT NULL DEFAULT 0,
                    failure_type TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );
                """
            )
            expected = {
                "schema_version": VISUAL_RUNTIME_SCHEMA_VERSION,
                "token_limit": str(self.token_limit),
                "imported_tokens": str(self.imported_tokens),
                "imported_ledger_sha256": self.imported_ledger_sha256,
            }
            existing = dict(
                connection.execute(
                    "SELECT key, value FROM visual_quota_metadata"
                ).fetchall()
            )
            if existing and existing != expected:
                raise VisualRuntimeError("persisted Jina quota binding drifted")
            if not existing:
                connection.executemany(
                    "INSERT INTO visual_quota_metadata (key, value) VALUES (?, ?)",
                    expected.items(),
                )

    def snapshot(self) -> JinaQuotaSnapshotV1:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT
                       COALESCE(SUM(CASE WHEN status = 'completed' THEN actual_tokens ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN status = 'reserved' THEN reserved_tokens ELSE 0 END), 0),
                       COALESCE(SUM(accounted_tokens), 0),
                       COUNT(*)
                   FROM visual_query_calls"""
            ).fetchone()
        completed, reserved, accounted, calls = (int(value) for value in row)
        total = self.imported_tokens + accounted
        return JinaQuotaSnapshotV1(
            token_limit=self.token_limit,
            imported_tokens=self.imported_tokens,
            completed_tokens=completed,
            reserved_tokens=reserved,
            accounted_tokens=accounted,
            remaining_tokens=max(0, self.token_limit - total),
            calls=calls,
        )

    def reserve(self, *, request_id: str, request_sha256: str) -> None:
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT COALESCE(SUM(accounted_tokens), 0) FROM visual_query_calls"
            ).fetchone()
            accounted = self.imported_tokens + int(row[0])
            if accounted + JINA_MAX_INPUT_TOKENS > self.token_limit:
                raise VisualRuntimeError("Jina 10M-token account ceiling reached")
            try:
                connection.execute(
                    """INSERT INTO visual_query_calls
                       (request_id, request_sha256, status, reserved_tokens,
                        accounted_tokens, created_at)
                       VALUES (?, ?, 'reserved', ?, ?, ?)""",
                    (
                        request_id,
                        request_sha256,
                        JINA_MAX_INPUT_TOKENS,
                        JINA_MAX_INPUT_TOKENS,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise VisualRuntimeError(
                    "duplicate visual provider request ID"
                ) from error

    def complete(
        self,
        *,
        request_id: str,
        actual_tokens: int,
        latency_ms: float,
    ) -> None:
        if actual_tokens < 0 or actual_tokens > JINA_MAX_INPUT_TOKENS:
            raise VisualRuntimeError("Jina returned invalid token accounting")
        completed_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE visual_query_calls
                   SET status = 'completed', actual_tokens = ?, accounted_tokens = ?,
                       cost_usd = ?, latency_ms = ?, completed_at = ?
                   WHERE request_id = ? AND status = 'reserved'""",
                (
                    actual_tokens,
                    actual_tokens,
                    actual_tokens * JINA_INPUT_TOKEN_PRICE_USD,
                    latency_ms,
                    completed_at,
                    request_id,
                ),
            )
            if cursor.rowcount != 1:
                raise VisualRuntimeError("visual quota reservation is missing")

    def fail(self, *, request_id: str, failure_type: str, latency_ms: float) -> None:
        completed_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE visual_query_calls
                   SET status = 'failed', latency_ms = ?, failure_type = ?, completed_at = ?
                   WHERE request_id = ? AND status = 'reserved'""",
                (latency_ms, failure_type[:128], completed_at, request_id),
            )
            if cursor.rowcount != 1:
                raise VisualRuntimeError("visual quota reservation is missing")


class SyncVisualQueryProvider(Protocol):
    implementation_id: str

    def embed_query(self, query: str) -> VisualEmbeddingResultV1: ...


class QuotaBoundJinaVisualQueryProviderV1:
    """First-party Jina query transport with no retry and durable accounting."""

    implementation_id = "jina-embeddings-v4-query-api-quota-bound-v1"

    def __init__(
        self,
        *,
        api_key: str,
        quota_ledger: PersistentJinaQuotaLedgerV1,
        timeout_seconds: float = 8.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise VisualRuntimeError("JINA_API_KEY is required")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise VisualRuntimeError("visual query timeout must be positive")
        self._api_key = api_key
        self._quota = quota_ledger
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def embed_query(self, query: str) -> VisualEmbeddingResultV1:
        from src.digital_twin.grounding.visual_late_interaction import (
            JinaVisualMultiVectorProvider,
        )

        payload = JinaVisualMultiVectorProvider(api_key="payload-only").query_payload(
            query
        )
        request_sha256 = _canonical_sha256(payload)
        request_id = f"visual-query-{uuid4()}"
        self._quota.reserve(
            request_id=request_id,
            request_sha256=request_sha256,
        )
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
                    f"Jina visual query failed with HTTP {response.status_code}"
                )
            try:
                body = response.json()
                if isinstance(body, dict) and body.get("model") != JINA_VISUAL_MODEL:
                    raise VisualProviderIdentityDriftError(
                        "returned visual embedding model identity drifted"
                    )
                result = JinaVisualMultiVectorProvider.parse_response(body)
            except (ValueError, VisualLateInteractionError) as error:
                raise VisualProviderUnavailableError(
                    "Jina visual query response is invalid"
                ) from error
        except httpx.HTTPError as error:
            latency_ms = (time.perf_counter() - started) * 1000
            self._quota.fail(
                request_id=request_id,
                failure_type=type(error).__name__,
                latency_ms=latency_ms,
            )
            raise VisualProviderUnavailableError(
                "Jina visual query transport failed"
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


class VisualIndexStoreV1:
    """SQLite-backed ignored artifact store for release-bound visual vectors."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, release_id: str) -> Path:
        digest = hashlib.sha256(release_id.encode("utf-8")).hexdigest()[:24]
        return self.root / f"visual-index-{digest}.sqlite3"

    def materialize_from_component_ledger(
        self,
        *,
        source_ledger_path: Path,
        dataset_path: Path,
        course_id: str,
        release_id: str,
        profile_id: str,
        profile_version: str,
        chunks: Sequence[DocumentChunk],
    ) -> VisualIndexManifestV1:
        target = self.path_for(release_id)
        if target.exists():
            raise VisualRuntimeError("visual index output already exists")
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        dataset_sha256 = dataset.get("content_sha256")
        content_without_hash = {
            key: value for key, value in dataset.items() if key != "content_sha256"
        }
        if dataset_sha256 != _canonical_sha256(content_without_hash):
            raise VisualRuntimeError("visual dataset hash drifted")
        assets = [
            asset
            for asset in dataset.get("assets", [])
            if asset.get("course_id") == course_id
        ]
        if not assets:
            raise VisualRuntimeError("visual dataset has no assets for this course")
        chunk_by_region: dict[str, DocumentChunk] = {}
        for chunk in chunks:
            if chunk.region_id is None:
                continue
            if chunk.region_id in chunk_by_region:
                raise VisualRuntimeError("visual release contains duplicate region IDs")
            chunk_by_region[chunk.region_id] = chunk
        source_ledger_sha256 = _file_sha256(source_ledger_path)
        created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        manifest_payload = {
            "schema_version": VISUAL_RUNTIME_SCHEMA_VERSION,
            "implementation_id": "jina-v4-late-interaction",
            "model": JINA_VISUAL_MODEL,
            "course_id": course_id,
            "release_id": release_id,
            "profile_id": profile_id,
            "profile_version": profile_version,
            "source_set_sha256": visual_source_set_sha256(chunks),
            "source_ledger_sha256": source_ledger_sha256,
            "dataset_sha256": dataset_sha256,
            "record_count": len(assets),
            "imported_account_tokens": JINA_IMPORTED_COMPONENT_TOKENS,
            "created_at": created_at,
        }
        manifest = VisualIndexManifestV1(
            artifact_id=f"visual-index-{_canonical_sha256(manifest_payload)[:24]}",
            **manifest_payload,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            source = sqlite3.connect(
                f"{source_ledger_path.resolve().as_uri()}?mode=ro",
                uri=True,
            )
            destination = sqlite3.connect(target)
            try:
                destination.execute("PRAGMA journal_mode = WAL")
                destination.executescript(
                    """
                    CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE visual_records (
                        record_id TEXT PRIMARY KEY,
                        metadata_json TEXT NOT NULL,
                        vectors_json TEXT NOT NULL
                    );
                    """
                )
                destination.execute(
                    "INSERT INTO metadata (key, value) VALUES ('manifest', ?)",
                    (manifest.model_dump_json(),),
                )
                for asset in assets:
                    region = asset["region_lineage"][0]
                    chunk = chunk_by_region.get(region["region_id"])
                    if chunk is None:
                        raise VisualRuntimeError(
                            f"release is missing visual region {region['region_id']}"
                        )
                    if (
                        not chunk.retrieval_allowed
                        or not chunk.display_allowed
                        or chunk.source_artifact_id != asset["source_artifact_id"]
                        or chunk.source_checksum != asset["source_sha256"]
                        or chunk.region_checksum != asset["render_sha256"]
                        or list(chunk.bounding_box or ()) != region["bbox"]
                        or not chunk.crop_ref
                    ):
                        raise VisualRuntimeError(
                            "visual release lineage does not match dataset"
                        )
                    row = source.execute(
                        """SELECT status, response_json FROM calls
                           WHERE request_key = ?""",
                        (f"image:{asset['asset_id']}",),
                    ).fetchone()
                    if row is None or row[0] != "completed" or not row[1]:
                        raise VisualRuntimeError(
                            "component ledger lacks an image embedding"
                        )
                    response = json.loads(row[1])
                    if response.get("provider_model") != JINA_VISUAL_MODEL:
                        raise VisualRuntimeError(
                            "component image model identity drifted"
                        )
                    vectors = validated_multivector(response["content"]["vectors"])
                    record = VisualRegionEmbeddingV1(
                        record_id=region["region_id"],
                        course_id=course_id,
                        source_artifact_id=asset["source_artifact_id"],
                        source_version=str(chunk.source_version),
                        source_sha256=asset["source_sha256"],
                        asset_id=asset["asset_id"],
                        region_id=region["region_id"],
                        render_sha256=asset["render_sha256"],
                        bbox=tuple(region["bbox"]),
                        modality=asset["modality"],
                        vectors=vectors,
                    )
                    record_metadata = {
                        key: value
                        for key, value in record.__dict__.items()
                        if key != "vectors"
                    }
                    destination.execute(
                        """INSERT INTO visual_records
                           (record_id, metadata_json, vectors_json) VALUES (?, ?, ?)""",
                        (
                            record.record_id,
                            json.dumps(record_metadata, sort_keys=True),
                            json.dumps([list(vector) for vector in vectors]),
                        ),
                    )
                destination.commit()
            finally:
                destination.close()
                source.close()
        except Exception:
            target.unlink(missing_ok=True)
            Path(f"{target}-wal").unlink(missing_ok=True)
            Path(f"{target}-shm").unlink(missing_ok=True)
            raise
        return manifest

    def load_bound(
        self,
        *,
        course_id: str,
        release_id: str,
        profile_id: str,
        profile_version: str,
        source_ledger_sha256: str,
        chunks: Sequence[DocumentChunk],
    ) -> tuple[VisualIndexManifestV1, VisualLateInteractionIndexV1]:
        path = self.path_for(release_id)
        if not path.is_file():
            raise VisualIndexUnavailableError("release visual index is unavailable")
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            manifest_row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'manifest'"
            ).fetchone()
            if manifest_row is None:
                raise VisualRuntimeError("visual index manifest is missing")
            manifest = VisualIndexManifestV1.model_validate_json(manifest_row[0])
            if (
                manifest.course_id != course_id
                or manifest.release_id != release_id
                or manifest.profile_id != profile_id
                or manifest.profile_version != profile_version
                or manifest.source_ledger_sha256 != source_ledger_sha256
                or manifest.source_set_sha256 != visual_source_set_sha256(chunks)
            ):
                raise VisualRuntimeError("visual index release binding drifted")
            records: list[VisualRegionEmbeddingV1] = []
            for metadata_json, vectors_json in connection.execute(
                "SELECT metadata_json, vectors_json FROM visual_records ORDER BY record_id"
            ):
                metadata = json.loads(metadata_json)
                records.append(
                    VisualRegionEmbeddingV1(
                        **metadata,
                        vectors=validated_multivector(json.loads(vectors_json)),
                    )
                )
            if len(records) != manifest.record_count:
                raise VisualRuntimeError("visual index record count drifted")
            return manifest, VisualLateInteractionIndexV1(records)
        finally:
            connection.close()


class VisualAwareRetrieverV1:
    """Use late interaction only for visual queries and fail back to text/OCR."""

    implementation_id = "jina-v4-late-interaction-with-text-ocr-fallback-v1"
    primary_implementation_id = "jina-v4-late-interaction"

    def __init__(
        self,
        *,
        text_retriever: Retriever,
        query_provider: SyncVisualQueryProvider,
        index: VisualLateInteractionIndexV1,
        course_id: str,
        chunks: Sequence[DocumentChunk],
        artifact_id: str,
    ) -> None:
        self._text_retriever = text_retriever
        self._query_provider = query_provider
        self._index = index
        self._course_id = course_id
        self._artifact_id = artifact_id
        self._chunks_by_region: dict[str, DocumentChunk] = {}
        for chunk in chunks:
            if chunk.region_id is not None:
                if chunk.region_id in self._chunks_by_region:
                    raise VisualRuntimeError(
                        "release contains duplicate visual region IDs"
                    )
                self._chunks_by_region[chunk.region_id] = chunk
        self.fallback_count = 0
        self.primary_available = True
        self.last_failure_type: str | None = None
        self.last_route = RegionRoute.GENERAL
        self.last_hits: list[RetrievalHit] = []

    @property
    def fallback_implementation_id(self) -> str:
        return getattr(
            self._text_retriever,
            "implementation_id",
            "text-ocr-fallback",
        )

    @property
    def artifact_id(self) -> str:
        return self._artifact_id

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        self.last_route = classify_region_query(query)
        if self.last_route == RegionRoute.GENERAL:
            self.last_hits = self._text_retriever.retrieve(query, limit=limit)
            return self.last_hits
        try:
            result = self._query_provider.embed_query(query)
            ranked = self._index.retrieve(
                course_id=self._course_id,
                query_vectors=result.vectors,
                limit=limit,
            )
            hits: list[RetrievalHit] = []
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
                        "visual result cannot map to release authority"
                    )
                score = max(-1.0, min(1.0, float(item["score"])))
                hits.append(
                    RetrievalHit(
                        chunk=chunk,
                        relevance_score=(score + 1.0) / 2.0,
                        raw_score=max(0.0, score),
                    )
                )
            self.primary_available = True
            self.last_failure_type = None
            self.last_hits = hits
            return self.last_hits
        except VisualProviderUnavailableError as error:
            self.fallback_count += 1
            self.primary_available = False
            self.last_failure_type = type(error).__name__
            self.last_hits = self._text_retriever.retrieve(query, limit=limit)
            return self.last_hits


class VisualIndexUnavailableRetrieverV1:
    """Expose a visible visual fallback when a release has no bound index."""

    implementation_id = "visual-index-unavailable-with-text-ocr-fallback-v1"
    primary_implementation_id = "jina-v4-late-interaction"

    def __init__(self, text_retriever: Retriever) -> None:
        self._text_retriever = text_retriever
        self.fallback_count = 0
        self.primary_available = True
        self.last_failure_type: str | None = None
        self.last_route = RegionRoute.GENERAL

    @property
    def fallback_implementation_id(self) -> str:
        return getattr(
            self._text_retriever,
            "implementation_id",
            "text-ocr-fallback",
        )

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        self.last_route = classify_region_query(query)
        if self.last_route == RegionRoute.GENERAL:
            self.primary_available = True
            self.last_failure_type = None
        else:
            self.primary_available = False
            self.fallback_count += 1
            self.last_failure_type = "VisualIndexUnavailable"
        return self._text_retriever.retrieve(query, limit=limit)
