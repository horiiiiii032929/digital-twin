from datetime import UTC, datetime, timedelta

import pytest

from services.ingestion import IngestionJobError, IngestionJobService
from services.persistence import SQLiteIngestionJobRepository
from services.storage import FileSystemObjectStore
from src.digital_twin.grounding import LocalCourseSourceIngestionService
from src.digital_twin.operations import IngestionJobStatus
from src.digital_twin.student import SQLiteStudentRepository, seed_synthetic_student_workflow
from src.digital_twin.tutor_policy import SourceLabel
from tests.fixtures.ingestion import write_synthetic_pdf


def _service(tmp_path):
    database = tmp_path / "runtime.sqlite3"
    students = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(students)
    jobs = SQLiteIngestionJobRepository(database)
    objects = FileSystemObjectStore(tmp_path / "objects")
    service = IngestionJobService(
        jobs,
        objects,
        LocalCourseSourceIngestionService(
            tmp_path / "sources", tmp_path / "crops"
        ),
        max_upload_bytes=1024 * 1024,
        lease_seconds=30,
    )
    return service, jobs, objects, students, fixture


def _pdf(tmp_path):
    path = tmp_path / "source.pdf"
    write_synthetic_pdf(path, with_text=True, with_figure=True)
    return path.read_bytes()


def _enqueue(service, fixture, content, key="upload-1"):
    return service.enqueue_pdf(
        content,
        idempotency_key=key,
        course_id=fixture.course_a_id,
        artifact_id="lecture-01",
        title="Lecture 01",
        version=1,
        professor_id=fixture.professor_id,
        display_allowed=True,
        source_label=SourceLabel.COURSE_APPROVED,
    )


def test_filesystem_store_is_content_addressed_atomic_and_path_safe(tmp_path):
    store = FileSystemObjectStore(tmp_path / "objects")
    first = store.put(
        b"%PDF-synthetic",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    second = store.put(
        b"%PDF-synthetic",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )

    assert first == second
    assert store.read(first.key) == b"%PDF-synthetic"
    assert store.checksum(first.key) == first.checksum
    assert store.iter_keys() == [first.key]
    with pytest.raises(ValueError, match="escapes|invalid"):
        store.read("../secret")


def test_filesystem_store_enforces_total_quota_but_allows_deduplication(tmp_path):
    store = FileSystemObjectStore(tmp_path / "objects", max_bytes=14)
    first = store.put(
        b"%PDF-synthetic",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    assert store.put(
        b"%PDF-synthetic",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    ) == first
    with pytest.raises(ValueError, match="quota"):
        store.put(
            b"%PDF-other",
            namespace="course-sources",
            suffix=".pdf",
            mime_type="application/pdf",
        )


def test_enqueue_is_idempotent_and_conflicting_reuse_fails(tmp_path):
    service, _, objects, _, fixture = _service(tmp_path)
    content = _pdf(tmp_path)

    first, created = _enqueue(service, fixture, content)
    duplicate, duplicate_created = _enqueue(service, fixture, content)

    assert created is True
    assert duplicate_created is False
    assert duplicate.id == first.id
    with pytest.raises(IngestionJobError, match="different upload"):
        _enqueue(service, fixture, content + b"changed")
    assert objects.iter_keys() == [first.source_object_key]


def test_worker_processes_pdf_and_persists_release_ready_result(tmp_path):
    service, jobs, objects, _, fixture = _service(tmp_path)
    queued, _ = _enqueue(service, fixture, _pdf(tmp_path))

    completed = service.process_one("worker-a")

    assert completed.id == queued.id
    assert completed.status == IngestionJobStatus.SUCCEEDED
    assert completed.result.chunk_count == len(completed.result.chunks)
    assert completed.result.source_checksum == queued.source_checksum
    assert objects.exists(queued.source_object_key)
    assert jobs.get(queued.id).result.chunks[0].metadata["course_id"] == (
        fixture.course_a_id
    )
    assert jobs.get(queued.id).result.derived_storage_refs
    assert any(
        ref.startswith("source://")
        for ref in jobs.get(queued.id).result.derived_storage_refs
    )


def test_failed_job_can_retry_and_expired_worker_lease_recovers(tmp_path):
    service, jobs, _, _, fixture = _service(tmp_path)
    queued, _ = _enqueue(service, fixture, _pdf(tmp_path))
    claimed = jobs.claim("crashed-worker", lease_seconds=30)
    assert claimed.status == IngestionJobStatus.RUNNING

    recovered = jobs.recover_expired(
        (datetime.now(UTC) + timedelta(seconds=31)).isoformat()
    )
    assert recovered == 1
    assert jobs.get(queued.id).status == IngestionJobStatus.PENDING

    claimed_again = jobs.claim("worker-b", lease_seconds=30)
    assert jobs.fail(
        claimed_again.id,
        "worker-b",
        error_code="synthetic-failure",
        error_message="safe diagnostic",
    )
    assert jobs.get(queued.id).status == IngestionJobStatus.FAILED
    assert service.retry_owned(fixture.professor_id, queued.id).status == (
        IngestionJobStatus.PENDING
    )


def test_cancelled_job_is_not_claimed(tmp_path):
    service, jobs, _, _, fixture = _service(tmp_path)
    queued, _ = _enqueue(service, fixture, _pdf(tmp_path))

    cancelled = service.cancel_owned(fixture.professor_id, queued.id)

    assert cancelled.status == IngestionJobStatus.CANCELLED
    assert jobs.claim("worker-a", lease_seconds=30) is None


def test_upload_validation_rejects_non_pdf_and_oversize(tmp_path):
    service, _, _, _, fixture = _service(tmp_path)
    with pytest.raises(IngestionJobError, match="valid PDF"):
        _enqueue(service, fixture, b"not-a-pdf")
    with pytest.raises(IngestionJobError, match="upload limit"):
        _enqueue(service, fixture, b"%PDF-" + b"x" * (1024 * 1024))
