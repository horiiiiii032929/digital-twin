from datetime import UTC, datetime, timedelta
from threading import Event, Thread
import time

import pytest

from services.ingestion import IngestionJobError, IngestionJobService
from services.persistence import SQLiteIngestionJobRepository
from services.storage import FileSystemObjectStore
from src.digital_twin.grounding import LocalCourseSourceIngestionService
from src.digital_twin.operations import (
    IngestionJob,
    IngestionJobResult,
    IngestionJobStatus,
)
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


def test_filesystem_store_rejects_symbolic_link_substitution(tmp_path):
    store = FileSystemObjectStore(tmp_path / "objects")
    stored = store.put(
        b"%PDF-original",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    stored_path = store.root / stored.key
    stored_path.unlink()
    external = tmp_path / "external.pdf"
    external.write_bytes(b"outside object root")
    stored_path.symlink_to(external)

    with pytest.raises(RuntimeError, match="symbolic link"):
        store.read(stored.key)
    with pytest.raises(RuntimeError, match="symbolic link"):
        store.iter_keys()
    with pytest.raises(RuntimeError, match="symbolic link"):
        store.delete(stored.key)
    assert external.read_bytes() == b"outside object root"


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
    with pytest.raises(IngestionJobError, match="different upload"):
        service.enqueue_pdf(
            content,
            idempotency_key="upload-1",
            course_id=fixture.course_a_id,
            artifact_id="lecture-01",
            title="Changed title",
            version=1,
            professor_id=fixture.professor_id,
            display_allowed=True,
            source_label=SourceLabel.COURSE_APPROVED,
        )
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
    release_chunks = service.release_chunks_owned(
        fixture.professor_id, fixture.course_a_id, [queued.id]
    )
    assert release_chunks == completed.result.chunks


def test_release_chunks_require_completed_owned_course_jobs(tmp_path):
    service, _, _, _, fixture = _service(tmp_path)
    queued, _ = _enqueue(service, fixture, _pdf(tmp_path))

    with pytest.raises(IngestionJobError, match="finish ingestion"):
        service.release_chunks_owned(
            fixture.professor_id, fixture.course_a_id, [queued.id]
        )
    with pytest.raises(IngestionJobError, match="at least one"):
        service.release_chunks_owned(fixture.professor_id, fixture.course_a_id, [])


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


def test_running_job_cannot_be_cancelled_mid_write(tmp_path):
    service, jobs, _, _, fixture = _service(tmp_path)
    queued, _ = _enqueue(service, fixture, _pdf(tmp_path))
    claimed = jobs.claim("active-worker", lease_seconds=30)
    assert claimed is not None

    with pytest.raises(IngestionJobError, match="pending or failed"):
        service.cancel_owned(fixture.professor_id, queued.id)

    assert jobs.get(queued.id).status == IngestionJobStatus.RUNNING


def test_worker_renews_lease_during_slow_ingestion(tmp_path):
    service, jobs, _, _, fixture = _service(tmp_path)
    queued, _ = _enqueue(service, fixture, _pdf(tmp_path))
    delegate = service.ingestion
    started = Event()

    class SlowIngestion:
        def ingest_pdf(self, *args, **kwargs):
            started.set()
            time.sleep(0.35)
            return delegate.ingest_pdf(*args, **kwargs)

    service.ingestion = SlowIngestion()
    service.lease_seconds = 0.15
    worker = Thread(target=service.process_one, args=("slow-worker",))
    worker.start()
    assert started.wait(timeout=2)
    time.sleep(0.22)

    assert jobs.recover_expired(datetime.now(UTC).isoformat()) == 0

    worker.join(timeout=5)
    assert not worker.is_alive()
    assert jobs.get(queued.id).status == IngestionJobStatus.SUCCEEDED


def test_upload_validation_rejects_non_pdf_and_oversize(tmp_path):
    service, _, _, _, fixture = _service(tmp_path)
    with pytest.raises(IngestionJobError, match="valid PDF"):
        _enqueue(service, fixture, b"not-a-pdf")
    with pytest.raises(IngestionJobError, match="upload limit"):
        _enqueue(service, fixture, b"%PDF-" + b"x" * (1024 * 1024))


def test_ingestion_result_rejects_impossible_region_counts():
    with pytest.raises(ValueError, match="non-negative integers"):
        IngestionJobResult(
            source_artifact_id="artifact",
            source_version=1,
            source_checksum="a" * 64,
            document_id="document",
            chunk_count=0,
            region_count=0,
            region_kind_counts={"figure": -1},
        )


def test_ingestion_job_rejects_impossible_terminal_and_lease_states():
    now = datetime.now(UTC).isoformat()
    common = {
        "id": "job-invalid",
        "idempotency_key": "invalid",
        "course_id": "course",
        "artifact_id": "artifact",
        "title": "Artifact",
        "version": 1,
        "professor_id": "professor",
        "source_object_key": "course-sources/a.pdf",
        "source_checksum": "a" * 64,
        "created_at": now,
        "updated_at": now,
    }
    with pytest.raises(ValueError, match="require a lease"):
        IngestionJob(**common, status=IngestionJobStatus.RUNNING)
    with pytest.raises(ValueError, match="require a sanitized error"):
        IngestionJob(**common, status=IngestionJobStatus.FAILED)
    with pytest.raises(ValueError, match="cannot exceed"):
        IngestionJob(**common, attempts=4, max_attempts=3)


def test_expired_ingestion_lease_cannot_renew_complete_or_fail(tmp_path):
    service, jobs, _, _, fixture = _service(tmp_path)
    queued, _ = _enqueue(service, fixture, _pdf(tmp_path))
    claimed = jobs.claim("stale-worker", lease_seconds=30)
    assert claimed is not None
    expired_at = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with jobs._connection:
        jobs._connection.execute(
            "UPDATE ingestion_jobs SET lease_expires_at = ? WHERE id = ?",
            (expired_at, claimed.id),
        )
    result = IngestionJobResult(
        source_artifact_id=f"{fixture.course_a_id}:lecture-01",
        source_version=1,
        source_checksum=queued.source_checksum,
        document_id="document",
        chunk_count=0,
        region_count=0,
    )

    assert jobs.renew_lease(claimed.id, "stale-worker", lease_seconds=30) is False
    assert jobs.complete(
        claimed.id, "stale-worker", result.model_dump_json()
    ) is False
    assert jobs.fail(
        claimed.id,
        "stale-worker",
        error_code="stale",
        error_message="Safe stale-worker failure",
    ) is False
    assert jobs.recover_expired(datetime.now(UTC).isoformat()) == 1
    assert jobs.get(claimed.id).status == IngestionJobStatus.PENDING


def test_ingestion_completion_rejects_result_from_another_source(tmp_path):
    service, jobs, _, _, fixture = _service(tmp_path)
    queued, _ = _enqueue(service, fixture, _pdf(tmp_path))
    claimed = jobs.claim("worker", lease_seconds=30)
    assert claimed is not None
    mismatched = IngestionJobResult(
        source_artifact_id=f"{fixture.course_a_id}:different-artifact",
        source_version=1,
        source_checksum=queued.source_checksum,
        document_id="document",
        chunk_count=0,
        region_count=0,
    )

    with pytest.raises(ValueError, match="claimed source"):
        jobs.complete(claimed.id, "worker", mismatched.model_dump_json())
    assert jobs.get(claimed.id).status == IngestionJobStatus.RUNNING
    with pytest.raises(ValueError, match="timezone"):
        jobs.recover_expired("2026-08-20T00:00:00")


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"idempotency_key": "x" * 129}, "Idempotency-Key"),
        ({"artifact_id": "   "}, "metadata"),
        ({"title": "x" * 241}, "metadata"),
        ({"version": True}, "positive integer"),
    ),
)
def test_invalid_ingestion_metadata_is_rejected_before_storage(
    tmp_path, overrides, message
):
    service, _, objects, _, fixture = _service(tmp_path)
    arguments = {
        "idempotency_key": "valid-key",
        "course_id": fixture.course_a_id,
        "artifact_id": "lecture-01",
        "title": "Lecture 01",
        "version": 1,
        "professor_id": fixture.professor_id,
        "display_allowed": True,
        "source_label": SourceLabel.COURSE_APPROVED,
    }
    arguments.update(overrides)

    with pytest.raises(IngestionJobError, match=message):
        service.enqueue_pdf(_pdf(tmp_path), **arguments)

    assert objects.iter_keys() == []
