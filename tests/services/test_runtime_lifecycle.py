import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from services.operations import (
    delete_account_data,
    delete_course_data,
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
            source_artifact_id="source-synthetic",
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
