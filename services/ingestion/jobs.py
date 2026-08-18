"""Enqueue and execute recoverable offline source-ingestion jobs."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import hashlib
from uuid import uuid4

from src.digital_twin.grounding import (
    LocalCourseSourceIngestionService,
    SourcePermissions,
)
from src.digital_twin.operations import (
    IngestionJob,
    IngestionJobRepository,
    IngestionJobResult,
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
        if not idempotency_key.strip():
            raise IngestionJobError(
                "idempotency_key_required", "An Idempotency-Key header is required."
            )
        if len(content) > self.max_upload_bytes:
            raise IngestionJobError(
                "source_too_large", "The PDF exceeds the configured upload limit."
            )
        if not content.startswith(b"%PDF-"):
            raise IngestionJobError(
                "invalid_pdf_signature", "The uploaded file is not a valid PDF."
            )
        normalized_key = idempotency_key.strip()
        existing = self.repository.get_by_idempotency_key(
            professor_id, course_id, normalized_key
        )
        checksum = hashlib.sha256(content).hexdigest()
        if existing is not None:
            if any(
                (
                    existing.artifact_id != artifact_id,
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
            course_id=course_id,
            artifact_id=artifact_id,
            title=title.strip(),
            version=version,
            professor_id=professor_id,
            display_allowed=display_allowed,
            source_label=source_label,
            source_object_key=stored.key,
            source_checksum=stored.checksum,
            max_attempts=self.max_attempts,
            created_at=now,
            updated_at=now,
        )
        saved, created = self.repository.enqueue(requested)
        return saved, created

    def get_owned(self, professor_id: str, job_id: str) -> IngestionJob:
        job = self.repository.get(job_id)
        if job is None or job.professor_id != professor_id:
            raise IngestionJobError("job_not_found", "The ingestion job was not found.")
        return job

    def list_owned(self, professor_id: str, course_id: str) -> list[IngestionJob]:
        return self.repository.list_for_course(professor_id, course_id)

    def cancel_owned(self, professor_id: str, job_id: str) -> IngestionJob:
        self.get_owned(professor_id, job_id)
        job = self.repository.cancel(job_id)
        if job is None:
            raise IngestionJobError("job_not_found", "The ingestion job was not found.")
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
        return self.repository.get(job.id)


def _safe_error_message(error: Exception) -> str:
    if isinstance(error, IngestionJobError):
        return error.message
    if isinstance(error, RuntimeError) and "checksum" in str(error).casefold():
        return "Stored source integrity verification failed."
    return "Source ingestion failed during parsing; inspect the job type and source validity."


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
