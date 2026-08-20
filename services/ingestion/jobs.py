"""Enqueue and execute recoverable offline source-ingestion jobs."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import hashlib
import math
from threading import Event, Thread
from uuid import uuid4

from src.digital_twin.grounding import (
    DocumentChunk,
    LocalCourseSourceIngestionService,
    SourcePermissions,
)
from src.digital_twin.operations import (
    IngestionJob,
    IngestionJobRepository,
    IngestionJobResult,
    IngestionJobStatus,
    ObjectStore,
)
from src.digital_twin.tutor_policy import SourceLabel


class IngestionJobError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class IngestionJobService:
    def __init__(
        self,
        repository: IngestionJobRepository,
        object_store: ObjectStore,
        ingestion: LocalCourseSourceIngestionService,
        *,
        max_upload_bytes: int,
        max_attempts: int = 3,
        lease_seconds: int = 300,
    ) -> None:
        integer_limits = (max_upload_bytes, max_attempts)
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
            for value in integer_limits
        ) or (
            isinstance(lease_seconds, bool)
            or not isinstance(lease_seconds, (int, float))
            or not math.isfinite(lease_seconds)
            or lease_seconds <= 0
        ):
            raise ValueError("upload, attempt, and lease limits must be positive")
        self.repository = repository
        self.object_store = object_store
        self.ingestion = ingestion
        self.max_upload_bytes = max_upload_bytes
        self.max_attempts = max_attempts
        self.lease_seconds = lease_seconds

    def enqueue_pdf(
        self,
        content: bytes,
        *,
        idempotency_key: str,
        course_id: str,
        artifact_id: str,
        title: str,
        version: int,
        professor_id: str,
        display_allowed: bool,
        source_label: SourceLabel,
    ) -> tuple[IngestionJob, bool]:
        normalized_key = idempotency_key.strip()
        normalized_course_id = course_id.strip()
        normalized_artifact_id = artifact_id.strip()
        normalized_title = title.strip()
        normalized_professor_id = professor_id.strip()
        if not normalized_key or len(normalized_key) > 128:
            raise IngestionJobError(
                "idempotency_key_required",
                "A valid Idempotency-Key header is required.",
            )
        if (
            any(
                not value or len(value) > 128
                for value in (
                    normalized_course_id,
                    normalized_artifact_id,
                    normalized_professor_id,
                )
            )
            or not normalized_title
            or len(normalized_title) > 240
        ):
            raise IngestionJobError(
                "source_metadata_invalid",
                "Course, source, title, and professor metadata are invalid.",
            )
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise IngestionJobError(
                "source_version_invalid", "Source version must be a positive integer."
            )
        if len(content) > self.max_upload_bytes:
            raise IngestionJobError(
                "source_too_large", "The PDF exceeds the configured upload limit."
            )
        if not content.startswith(b"%PDF-"):
            raise IngestionJobError(
                "invalid_pdf_signature", "The uploaded file is not a valid PDF."
            )
        existing = self.repository.get_by_idempotency_key(
            normalized_professor_id, normalized_course_id, normalized_key
        )
        checksum = hashlib.sha256(content).hexdigest()
        if existing is not None:
            if any(
                (
                    existing.artifact_id != normalized_artifact_id,
                    existing.title != normalized_title,
                    existing.version != version,
                    existing.source_checksum != checksum,
                    existing.display_allowed != display_allowed,
                    existing.source_label != source_label,
                )
            ):
                raise IngestionJobError(
                    "idempotency_conflict",
                    "The Idempotency-Key is already bound to a different upload.",
                )
            return existing, False
        try:
            stored = self.object_store.put(
                content,
                namespace="course-sources",
                suffix=".pdf",
                mime_type="application/pdf",
            )
        except ValueError as error:
            if "quota" not in str(error).casefold():
                raise
            raise IngestionJobError(
                "storage_quota_exceeded",
                "The course source storage quota has been reached.",
            ) from error
        now = _timestamp()
        requested = IngestionJob(
            id=f"ingestion-{uuid4()}",
            idempotency_key=normalized_key,
            course_id=normalized_course_id,
            artifact_id=normalized_artifact_id,
            title=normalized_title,
            version=version,
            professor_id=normalized_professor_id,
            display_allowed=display_allowed,
            source_label=source_label,
            source_object_key=stored.key,
            source_checksum=stored.checksum,
            max_attempts=self.max_attempts,
            created_at=now,
            updated_at=now,
        )
        saved, created = self.repository.enqueue(requested)
        if not created and any(
            (
                saved.artifact_id != requested.artifact_id,
                saved.title != requested.title,
                saved.version != requested.version,
                saved.source_checksum != requested.source_checksum,
                saved.display_allowed != requested.display_allowed,
                saved.source_label != requested.source_label,
            )
        ):
            raise IngestionJobError(
                "idempotency_conflict",
                "The Idempotency-Key is already bound to a different upload.",
            )
        return saved, created

    def get_owned(self, professor_id: str, job_id: str) -> IngestionJob:
        job = self.repository.get(job_id)
        if job is None or job.professor_id != professor_id:
            raise IngestionJobError("job_not_found", "The ingestion job was not found.")
        return job

    def list_owned(self, professor_id: str, course_id: str) -> list[IngestionJob]:
        return self.repository.list_for_course(professor_id, course_id)

    def release_chunks_owned(
        self,
        professor_id: str,
        course_id: str,
        job_ids: list[str],
    ) -> list[DocumentChunk]:
        """Resolve immutable release evidence from completed server-side jobs."""
        normalized_ids = [job_id.strip() for job_id in job_ids]
        if not normalized_ids or any(not job_id for job_id in normalized_ids):
            raise IngestionJobError(
                "release_sources_required",
                "Select at least one completed source-ingestion job.",
            )
        if len(normalized_ids) != len(set(normalized_ids)):
            raise IngestionJobError(
                "duplicate_release_source",
                "Each source-ingestion job may be selected only once.",
            )
        chunks: list[DocumentChunk] = []
        chunk_ids: set[str] = set()
        for job_id in normalized_ids:
            job = self.get_owned(professor_id, job_id)
            if job.course_id != course_id:
                raise IngestionJobError(
                    "job_not_found", "The ingestion job was not found."
                )
            if job.status != IngestionJobStatus.SUCCEEDED or job.result is None:
                raise IngestionJobError(
                    "release_source_not_ready",
                    "Every selected source must finish ingestion successfully.",
                )
            result = job.result
            if (
                result.source_checksum != job.source_checksum
                or result.chunk_count != len(result.chunks)
                or not result.chunks
            ):
                raise IngestionJobError(
                    "release_source_invalid",
                    "A selected source has inconsistent ingestion evidence.",
                )
            for chunk in result.chunks:
                if (
                    chunk.id in chunk_ids
                    or chunk.metadata.get("course_id") != course_id
                    or chunk.source_artifact_id != result.source_artifact_id
                    or chunk.source_version != result.source_version
                    or chunk.source_checksum != result.source_checksum
                ):
                    raise IngestionJobError(
                        "release_source_invalid",
                        "A selected source has inconsistent ingestion evidence.",
                    )
                chunk_ids.add(chunk.id)
                chunks.append(chunk.model_copy(deep=True))
        return chunks

    def cancel_owned(self, professor_id: str, job_id: str) -> IngestionJob:
        current = self.get_owned(professor_id, job_id)
        if current.status not in {
            IngestionJobStatus.PENDING,
            IngestionJobStatus.FAILED,
        }:
            raise IngestionJobError(
                "job_not_cancellable",
                "Only pending or failed ingestion jobs can be cancelled.",
            )
        job = self.repository.cancel(job_id)
        if job is None or job.status != IngestionJobStatus.CANCELLED:
            raise IngestionJobError(
                "job_not_cancellable", "The job could not be cancelled safely."
            )
        return job

    def retry_owned(self, professor_id: str, job_id: str) -> IngestionJob:
        current = self.get_owned(professor_id, job_id)
        retried = self.repository.retry(job_id)
        if retried is None or retried.status == current.status:
            raise IngestionJobError(
                "job_not_retryable", "The job is not eligible for another retry."
            )
        return retried

    def process_one(self, worker_id: str) -> IngestionJob | None:
        job = self.repository.claim(worker_id, lease_seconds=self.lease_seconds)
        if job is None:
            return None
        heartbeat = _LeaseHeartbeat(
            self.repository,
            job.id,
            worker_id,
            lease_seconds=self.lease_seconds,
        )
        heartbeat.start()
        try:
            try:
                content = self.object_store.read(job.source_object_key)
                if self.object_store.checksum(job.source_object_key) != job.source_checksum:
                    raise RuntimeError("stored source checksum mismatch")
                output = self.ingestion.ingest_pdf(
                    content,
                    course_id=job.course_id,
                    artifact_id=job.artifact_id,
                    title=job.title,
                    version=job.version,
                    professor_id=job.professor_id,
                    permissions=SourcePermissions(
                        processing_allowed=True,
                        tutoring_allowed=True,
                        display_allowed=job.display_allowed,
                    ),
                    source_label=job.source_label,
                )
                result = IngestionJobResult(
                    source_artifact_id=output.source.id,
                    source_version=output.source.version,
                    source_checksum=output.source.checksum,
                    document_id=output.bundle.document.id,
                    chunk_count=len(output.chunks),
                    region_count=len(output.bundle.regions),
                    region_kind_counts=dict(
                        sorted(
                            Counter(
                                region.kind.value for region in output.bundle.regions
                            ).items()
                        )
                    ),
                    processing_warnings=output.bundle.processing_warnings,
                    chunks=output.chunks,
                    derived_storage_refs=[
                        output.stored_source_ref,
                        *[region.crop_ref for region in output.bundle.regions],
                        *[figure.image_ref for figure in output.bundle.figures],
                    ],
                )
                self.repository.complete(job.id, worker_id, result.model_dump_json())
            except Exception as error:
                self.repository.fail(
                    job.id,
                    worker_id,
                    error_code=type(error).__name__,
                    error_message=_safe_error_message(error),
                )
        finally:
            heartbeat.stop()
        return self.repository.get(job.id)


class _LeaseHeartbeat:
    def __init__(self, repository, job_id, worker_id, *, lease_seconds: int) -> None:
        self.repository = repository
        self.job_id = job_id
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self._stop = Event()
        self._thread = Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=max(1.0, self.lease_seconds))

    def _run(self) -> None:
        interval = max(0.1, self.lease_seconds / 3)
        while not self._stop.wait(interval):
            try:
                renewed = self.repository.renew_lease(
                    self.job_id,
                    self.worker_id,
                    lease_seconds=self.lease_seconds,
                )
            except Exception:
                return
            if not renewed:
                return


def _safe_error_message(error: Exception) -> str:
    if isinstance(error, IngestionJobError):
        return error.message
    if isinstance(error, RuntimeError) and "checksum" in str(error).casefold():
        return "Stored source integrity verification failed."
    return "Source ingestion failed during parsing; inspect the job type and source validity."


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
