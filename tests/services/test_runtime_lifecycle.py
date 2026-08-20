import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from services.operations import (
    delete_account_data,
    delete_course_data,
    drain_storage_deletions,
    export_account_data,
    prune_runtime_data,
)
from services.persistence import SQLiteIngestionJobRepository
from services.storage import FileSystemObjectStore
from src.digital_twin.identity import IdentityService, SQLiteIdentityRepository
from src.digital_twin.operations import (
    IngestionJob,
    IngestionJobResult,
    IngestionJobStatus,
)
from src.digital_twin.student import (
    AccountRole,
    SQLiteStudentRepository,
    seed_synthetic_student_workflow,
)


def _runtime(tmp_path):
    database = tmp_path / "runtime.sqlite3"
    students = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(students)
    identities = SQLiteIdentityRepository(database)
    identity = IdentityService(identities, students)
    identity.provision_account(
        account_id=fixture.student_a_id,
        email="student@example.test",
        display_name="Synthetic Student",
        role=AccountRole.STUDENT,
        password="Student-password-42",
    )
    identity.provision_account(
        account_id=fixture.professor_id,
        email="professor@example.test",
        display_name="Synthetic Professor",
        role=AccountRole.PROFESSOR,
        password="Professor-password-42",
    )
    return database, students, identities, identity, fixture


class DeleteOnceFailingObjectStore(FileSystemObjectStore):
    def __init__(self, root):
        super().__init__(root)
        self._fail_next_delete = True

    def delete(self, key: str) -> bool:
        if self._fail_next_delete:
            self._fail_next_delete = False
            raise OSError("synthetic object deletion failure")
        return super().delete(key)


def test_account_export_excludes_credentials_and_student_delete_is_scoped(tmp_path):
    database, students, identities, _, fixture = _runtime(tmp_path)
    output = tmp_path / "exports" / "student.json"

    payload = export_account_data(database, fixture.student_a_id, output)

    serialized = output.read_text()
    assert payload["account"]["email"] == "student@example.test"
    assert payload["memberships"]
    assert "password_hash" not in serialized
    assert "token_digest" not in serialized
    assert os.stat(output).st_mode & 0o777 == 0o600

    identities.close()
    students.close()
    deleted = delete_account_data(database, fixture.student_a_id)
    assert deleted.target_type == "account"
    reopened = SQLiteStudentRepository(database)
    try:
        assert reopened.get_account(fixture.student_a_id) is None
        assert reopened.get_account(fixture.professor_id) is not None
    finally:
        reopened.close()


def test_professor_delete_requires_explicit_owned_course_deletion(tmp_path):
    database, students, identities, _, fixture = _runtime(tmp_path)
    store = FileSystemObjectStore(tmp_path / "objects")
    stored = store.put(
        b"%PDF-synthetic",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    jobs = SQLiteIngestionJobRepository(database)
    now = datetime.now(UTC).isoformat()
    jobs.enqueue(
        IngestionJob(
            id="job-delete-course",
            idempotency_key="delete-course",
            course_id=fixture.course_a_id,
            artifact_id="lecture-01",
            title="Lecture 01",
            version=1,
            professor_id=fixture.professor_id,
            source_object_key=stored.key,
            source_checksum=stored.checksum,
            created_at=now,
            updated_at=now,
        )
    )
    source_root = tmp_path / "derived" / "course-sources"
    crop_root = tmp_path / "derived" / "region-crops"
    source_root.mkdir(parents=True)
    (crop_root / "figures").mkdir(parents=True)
    (source_root / "source-synthetic.pdf").write_bytes(b"derived source")
    (crop_root / "region-synthetic.png").write_bytes(b"derived region")
    (crop_root / "figures" / "figure-synthetic.png").write_bytes(b"derived figure")
    claimed = jobs.claim("lifecycle-worker", lease_seconds=30)
    assert claimed is not None
    assert jobs.complete(
        claimed.id,
        "lifecycle-worker",
        IngestionJobResult(
                source_artifact_id=f"{fixture.course_a_id}:lecture-01",
            source_version=1,
            source_checksum=stored.checksum,
            document_id="document-synthetic",
            chunk_count=0,
            region_count=0,
            derived_storage_refs=[
                "source://source-synthetic.pdf",
                "region://region-synthetic.png",
                "figure://figure-synthetic.png",
            ],
        ).model_dump_json(),
    )
    jobs.close()
    identities.close()
    students.close()

    with pytest.raises(ValueError, match="delete owned courses"):
        delete_account_data(database, fixture.professor_id)

    result = delete_course_data(
        database,
        store,
        fixture.course_a_id,
        source_root=source_root,
        region_crop_root=crop_root,
    )
    assert result.target_type == "course"
    assert result.objects_deleted == 4
    assert not store.exists(stored.key)
    assert not (source_root / "source-synthetic.pdf").exists()
    assert not (crop_root / "region-synthetic.png").exists()
    assert not (crop_root / "figures" / "figure-synthetic.png").exists()
    assert result.storage_deletions_pending == 0


def test_failed_course_object_cleanup_is_durable_and_retryable(tmp_path):
    database, students, identities, _, fixture = _runtime(tmp_path)
    store = DeleteOnceFailingObjectStore(tmp_path / "objects")
    stored = store.put(
        b"%PDF-retryable-delete",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    jobs = SQLiteIngestionJobRepository(database)
    now = datetime.now(UTC).isoformat()
    jobs.enqueue(
        IngestionJob(
            id="job-retryable-delete",
            idempotency_key="retryable-delete",
            course_id=fixture.course_a_id,
            artifact_id="lecture-retry",
            title="Retry lecture",
            version=1,
            professor_id=fixture.professor_id,
            source_object_key=stored.key,
            source_checksum=stored.checksum,
            created_at=now,
            updated_at=now,
        )
    )
    jobs.close()
    identities.close()
    students.close()

    deleted = delete_course_data(database, store, fixture.course_a_id)

    assert deleted.storage_deletions_pending == 1
    assert store.exists(stored.key)
    with sqlite3.connect(database) as connection:
        queued = connection.execute(
            "SELECT attempts, last_error FROM storage_deletion_queue"
        ).fetchone()
    assert queued[0] == 1
    assert "synthetic object deletion failure" in queued[1]

    retried = drain_storage_deletions(database, store)

    assert retried.objects_deleted == 1
    assert retried.deletions_pending == 0
    assert not store.exists(stored.key)


def test_course_cleanup_preserves_storage_shared_by_a_remaining_job(tmp_path):
    database, students, identities, _, fixture = _runtime(tmp_path)
    store = FileSystemObjectStore(tmp_path / "objects")
    stored = store.put(
        b"%PDF-shared-object",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    source_root = tmp_path / "derived" / "course-sources"
    source_root.mkdir(parents=True)
    shared_source = source_root / "shared-source.pdf"
    shared_source.write_bytes(b"shared derived source")
    jobs = SQLiteIngestionJobRepository(database)
    now = datetime.now(UTC).isoformat()
    for suffix, course_id in (("a", fixture.course_a_id), ("b", fixture.course_b_id)):
        job, _ = jobs.enqueue(
            IngestionJob(
                id=f"job-shared-{suffix}",
                idempotency_key=f"shared-{suffix}",
                course_id=course_id,
                artifact_id=f"lecture-shared-{suffix}",
                title="Shared lecture",
                version=1,
                professor_id=fixture.professor_id,
                source_object_key=stored.key,
                source_checksum=stored.checksum,
                created_at=now,
                updated_at=now,
            )
        )
        claimed = jobs.claim(f"worker-{suffix}", lease_seconds=30)
        assert claimed is not None and claimed.id == job.id
        assert jobs.complete(
            claimed.id,
            f"worker-{suffix}",
            IngestionJobResult(
                    source_artifact_id=f"{course_id}:lecture-shared-{suffix}",
                source_version=1,
                source_checksum=stored.checksum,
                document_id=f"document-{suffix}",
                chunk_count=0,
                region_count=0,
                derived_storage_refs=["source://shared-source.pdf"],
            ).model_dump_json(),
        )
    jobs.close()
    identities.close()
    students.close()

    first = delete_course_data(
        database,
        store,
        fixture.course_a_id,
        source_root=source_root,
    )

    assert first.objects_deleted == 0
    assert store.exists(stored.key)
    assert shared_source.exists()

    second = delete_course_data(
        database,
        store,
        fixture.course_b_id,
        source_root=source_root,
    )

    assert second.objects_deleted == 2
    assert not store.exists(stored.key)
    assert not shared_source.exists()


def test_retention_prunes_only_expired_and_terminal_records(tmp_path):
    database, students, identities, identity, fixture = _runtime(tmp_path)
    store = FileSystemObjectStore(tmp_path / "objects")
    expired = identity.login("student@example.test", "Student-password-42")
    active = identity.login("professor@example.test", "Professor-password-42")
    stored = store.put(
        b"%PDF-retention",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    jobs = SQLiteIngestionJobRepository(database)
    old = datetime.now(UTC) - timedelta(days=60)
    job, _ = jobs.enqueue(
        IngestionJob(
            id="job-old-terminal",
            idempotency_key="old-terminal",
            course_id=fixture.course_a_id,
            artifact_id="lecture-old",
            title="Old lecture",
            version=1,
            professor_id=fixture.professor_id,
            source_object_key=stored.key,
            source_checksum=stored.checksum,
            created_at=old.isoformat(),
            updated_at=old.isoformat(),
        )
    )
    assert job.status == IngestionJobStatus.PENDING
    jobs.close()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE identity_sessions SET expires_at = ? WHERE account_id = ?",
            ((datetime.now(UTC) - timedelta(days=1)).isoformat(), fixture.student_a_id),
        )
        connection.execute(
            """UPDATE ingestion_jobs SET status = 'cancelled', updated_at = ?
               WHERE id = 'job-old-terminal'""",
            (old.isoformat(),),
        )
        connection.execute(
            """INSERT INTO audit_events
               (id, event_type, account_id, details_json, created_at)
               VALUES ('audit-old', 'test.old', ?, '{}', ?)""",
            (fixture.student_a_id, (datetime.now(UTC) - timedelta(days=400)).isoformat()),
        )
    identities.close()
    students.close()

    result = prune_runtime_data(database, store)

    assert result.expired_sessions_deleted == 1
    assert result.terminal_jobs_deleted == 1
    assert result.audit_events_deleted == 1
    assert result.unreferenced_objects_deleted == 1
    connection = sqlite3.connect(database)
    try:
        active_sessions = connection.execute(
            "SELECT COUNT(*) FROM identity_sessions WHERE account_id = ?",
            (fixture.professor_id,),
        ).fetchone()[0]
        assert active_sessions == 1
        assert json.loads(active.model_dump_json())["token"]
        assert expired.token
    finally:
        connection.close()


def test_retention_reconciles_old_unreferenced_raw_and_derived_artifacts(tmp_path):
    database, students, identities, _, _ = _runtime(tmp_path)
    store = FileSystemObjectStore(tmp_path / "objects")
    orphan = store.put(
        b"%PDF-orphan",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    source_root = tmp_path / "derived" / "course-sources"
    crop_root = tmp_path / "derived" / "region-crops"
    source_root.mkdir(parents=True)
    (crop_root / "figures").mkdir(parents=True)
    derived = [
        source_root / "orphan-source.pdf",
        crop_root / "orphan-region.png",
        crop_root / "figures" / "orphan-figure.png",
    ]
    for path in derived:
        path.write_bytes(b"orphan")
    old_timestamp = (datetime.now(UTC) - timedelta(hours=2)).timestamp()
    os.utime(store.root / orphan.key, (old_timestamp, old_timestamp))
    for path in derived:
        os.utime(path, (old_timestamp, old_timestamp))
    identities.close()
    students.close()

    result = prune_runtime_data(
        database,
        store,
        source_root=source_root,
        region_crop_root=crop_root,
        orphan_grace_minutes=60,
    )

    assert result.unreferenced_objects_deleted == 4
    assert result.storage_deletions_pending == 0
    assert not store.exists(orphan.key)
    assert all(not path.exists() for path in derived)
