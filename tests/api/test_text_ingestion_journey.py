"""Synthetic source bytes traverse approval, release, dialogue and withdrawal."""
import hashlib

import pytest

from tests.api.test_publication_api import _client, _headers
from tests.services.test_ingestion_jobs import _service
from src.digital_twin.tutor_policy import SourceLabel


@pytest.mark.parametrize("mime,content", [
    ("text/plain", "Cache coherence keeps replicated processor data consistent.\n".encode()),
    ("text/markdown", "# Cache coherence\n\nQ: Why coordinate replicas?\n\nA: Cache coherence keeps replicated processor data consistent.\n".encode()),
])
def test_utf8_source_to_student_citation_and_withdrawal(tmp_path, mime, content):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    headers = _headers(fixture.professor_id)
    upload = client.put(f"/api/professor/courses/{fixture.course_a_id}/sources/new-notes",
        params={"title": "Anonymized forum transcript", "display_allowed": True, "deidentified_reviewed": True},
        headers={**headers, "Content-Type": mime}, content=content)
    assert upload.status_code == 201, upload.text
    payload = upload.json()
    assert payload["source_checksum"] == hashlib.sha256(content).hexdigest()
    assert payload["chunks"]
    assert all(chunk["metadata"]["deidentified_reviewed"] == "true" for chunk in payload["chunks"])
    assert all(chunk["locator"] and chunk["retrieval_allowed"] for chunk in payload["chunks"])
    draft = client.post(f"/api/professor/courses/{fixture.course_a_id}/releases", headers=headers,
        json={"session_id": "onboarding-release-synthetic", "profile_id": "student-tutor",
            "profile_version": "v1", "release_id": "release-new-text", "chunks": payload["chunks"]})
    assert draft.status_code == 201, draft.text
    preflight = client.post("/api/professor/releases/release-new-text/preflight", headers=headers)
    assert preflight.status_code == 200 and preflight.json()["passed"] is True
    assert client.post("/api/professor/releases/release-new-text/publish", headers=headers).status_code == 200
    student = _headers(fixture.student_a_id)
    conversation = client.post(f"/api/student/courses/{fixture.course_a_id}/conversations", headers=student)
    assert conversation.status_code == 201
    endpoint = f"/api/student/conversations/{conversation.json()['id']}/messages"
    turn = client.post(endpoint, headers=student,
        json={"content": "What does cache coherence do?", "request_id": "fresh-text-1"})
    assert turn.status_code == 200, turn.text
    assert turn.json()["citations"]
    assert client.post("/api/professor/releases/release-new-text/withdraw", headers=headers).status_code == 200
    after = client.post(endpoint, headers=student,
        json={"content": "Explain cache coherence again.", "request_id": "fresh-text-2"})
    assert after.status_code == 409


@pytest.mark.parametrize("mime,suffix", [("text/plain", ".txt"), ("text/markdown", ".md")])
def test_utf8_job_worker_preserves_format_and_provenance(tmp_path, mime, suffix):
    service, jobs, objects, students, fixture = _service(tmp_path)
    kwargs = dict(course_id=fixture.course_a_id, artifact_id="notes", title="Anonymized forum notes", deidentified_reviewed=True,
        version=1, professor_id=fixture.professor_id, display_allowed=True,
        source_label=SourceLabel.COURSE_APPROVED, idempotency_key="fresh-text")
    content = b"# Consistency\n\nCache coherence keeps replicas consistent.\n"
    job, created = service.enqueue_source(content, mime_type=mime, **kwargs)
    assert created and job.source_object_key.endswith(suffix)
    assert jobs.get(job.id).deidentified_reviewed is True
    assert service.enqueue_source(content, mime_type=mime, **kwargs)[1] is False
    with pytest.raises(ValueError):
        service.enqueue_source(content, mime_type="text/markdown" if mime == "text/plain" else "text/plain", **kwargs)
    completed = service.process_one("utf8-worker")
    assert completed.status.value == "succeeded", completed.error_message
    assert completed.result.source_checksum == hashlib.sha256(content).hexdigest()
    assert service.release_chunks_owned(fixture.professor_id, fixture.course_a_id, [job.id])


@pytest.mark.parametrize("content", [b"", b"\xff", b"binary\x00content", b" \n "])
def test_invalid_text_rejected_before_objects_written(tmp_path, content):
    service, jobs, objects, students, fixture = _service(tmp_path)
    with pytest.raises(ValueError):
        service.enqueue_source(content, mime_type="text/plain", idempotency_key="invalid",
            course_id=fixture.course_a_id, artifact_id="notes", title="Notes", version=1,
            professor_id=fixture.professor_id, display_allowed=True, source_label=SourceLabel.COURSE_APPROVED)
    assert objects.iter_keys() == []


@pytest.mark.parametrize("reviewed,label", [(False, SourceLabel.COURSE_APPROVED), (True, SourceLabel.UNAPPROVED_EXTERNAL)])
def test_attestation_does_not_approve_unapproved_sources(tmp_path, reviewed, label):
    service, jobs, objects, students, fixture = _service(tmp_path)
    with pytest.raises(ValueError):
        service.enqueue_source(b"# Forum\n\nAn anonymous conceptual question.", mime_type="text/markdown",
            deidentified_reviewed=reviewed, idempotency_key="review", course_id=fixture.course_a_id,
            artifact_id="forum", title="Forum notes", version=1, professor_id=fixture.professor_id,
            display_allowed=True, source_label=label)
    assert objects.iter_keys() == []


def test_review_does_not_override_processing_permission(tmp_path):
    from src.digital_twin.grounding import SourcePermissions
    service, jobs, objects, students, fixture = _service(tmp_path)
    with pytest.raises(ValueError, match="processing permission"):
        service.ingestion.ingest_source(b"Anonymized conceptual discussion.", mime_type="text/plain",
            deidentified_reviewed=True, course_id=fixture.course_a_id, artifact_id="forum",
            title="Anonymized forum", version=1, professor_id=fixture.professor_id,
            permissions=SourcePermissions(processing_allowed=False, tutoring_allowed=True))
    assert not list((tmp_path / "sources").glob("source-*"))


def test_migration_preserves_existing_jobs_as_unreviewed(tmp_path):
    import sqlite3
    from src.digital_twin.student.migrations import apply_migrations, DEFAULT_MIGRATIONS
    connection = sqlite3.connect(tmp_path / "upgrade.sqlite3")
    apply_migrations(connection, DEFAULT_MIGRATIONS[:-1])
    connection.execute("""INSERT INTO ingestion_jobs
        (id,idempotency_key,course_id,artifact_id,title,version,professor_id,display_allowed,
        source_label,source_object_key,source_checksum,status,attempts,max_attempts,created_at,updated_at)
        VALUES ('old','old','c','a','Notes',1,'p',0,'course-approved','source.pdf',?,'pending',0,3,'now','now')""", ("a" * 64,))
    connection.commit()
    apply_migrations(connection)
    assert connection.execute("SELECT deidentified_reviewed FROM ingestion_jobs WHERE id='old'").fetchone()[0] == 0
    connection.close()
