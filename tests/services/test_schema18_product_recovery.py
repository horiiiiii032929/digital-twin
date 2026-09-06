"""Schema18/source-format recovery and in-process tutoring contracts, not capacity qualification."""

import hashlib

import httpx
import pytest

from scripts.tutoring_capacity_probe import StudentProbeSession, measure_tutoring_requests
from services.ingestion import IngestionJobService
from services.operations import create_runtime_backup, restore_runtime_backup, verify_runtime_backup
from services.persistence import SQLiteIngestionJobRepository
from services.storage import FileSystemObjectStore
from src.digital_twin.grounding import LocalCourseSourceIngestionService
from src.digital_twin.student import SQLiteStudentRepository
from src.digital_twin.student.models import Account, AccountRole, CourseMembership, MembershipRole
from src.digital_twin.tutor_policy import SourceLabel
from tests.api.test_student_api import KeywordEmbedder, _client, _headers
from tests.services.test_ingestion_jobs import _service


@pytest.mark.parametrize("mime,suffix", [("text/plain", ".txt"), ("text/markdown", ".md")])
def test_clean_restore_preserves_reviewed_text_job_and_release_ready_lineage(tmp_path, mime, suffix):
    original = tmp_path / "original"
    service, jobs, objects, students, fixture = _service(original)
    content = b"# Anonymized explanation\n\nCache coherence keeps replicas consistent.\n"
    job, _ = service.enqueue_source(content, mime_type=mime, deidentified_reviewed=True,
        idempotency_key="restore-input", course_id=fixture.course_a_id, artifact_id="forum-notes",
        title="Anonymized forum notes", version=1, professor_id=fixture.professor_id,
        display_allowed=True, source_label=SourceLabel.COURSE_APPROVED)
    completed = service.process_one("recovery-worker")
    assert completed.status.value == "succeeded"
    before = service.release_chunks_owned(fixture.professor_id, fixture.course_a_id, [job.id])
    jobs.close()
    students.close()
    archive = tmp_path / "fresh-backup.zip"
    manifest = create_runtime_backup(original / "runtime.sqlite3", original, archive)
    assert verify_runtime_backup(archive) == manifest
    restored = tmp_path / "empty-restore"
    restore_runtime_backup(archive, restored / "runtime.sqlite3", restored)
    restored_students = SQLiteStudentRepository(restored / "runtime.sqlite3")
    restored_jobs = SQLiteIngestionJobRepository(restored / "runtime.sqlite3")
    restored_objects = FileSystemObjectStore(restored / "objects")
    recovered = IngestionJobService(restored_jobs, restored_objects,
        LocalCourseSourceIngestionService(restored / "sources", restored / "crops"), max_upload_bytes=1024 * 1024)
    try:
        restored_job = restored_jobs.get(job.id)
        assert restored_job.deidentified_reviewed is True
        assert restored_job.source_object_key.endswith(suffix)
        assert restored_objects.read(restored_job.source_object_key) == content
        assert restored_job.source_checksum == hashlib.sha256(content).hexdigest()
        assert recovered.release_chunks_owned(fixture.professor_id, fixture.course_a_id, [job.id]) == before
        assert all(chunk.metadata["deidentified_reviewed"] == "true" for chunk in before)
        assert restored_students.get_published_release(fixture.course_a_id).id == fixture.release_a_id
        assert list((restored / "sources").glob(f"source-*{suffix}"))
    finally:
        restored_jobs.close()
        restored_students.close()


@pytest.mark.asyncio
async def test_probe_exercises_real_tutoring_posts_without_network_or_capacity_claim(tmp_path):
    app_client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())
    clients = []
    sessions = []
    try:
        for number in range(3):
            student_id = f"probe-synthetic-{number}"
            repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
            repository.save_membership(CourseMembership(account_id=student_id,
                course_id=fixture.course_a_id, role=MembershipRole.STUDENT))
            client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app_client.app),
                base_url="http://asgi-contract", headers=_headers(student_id))
            clients.append(client)
            conversation = await client.post(f"/api/student/courses/{fixture.course_a_id}/conversations")
            assert conversation.status_code == 201
            sessions.append(StudentProbeSession(client=client, conversation_id=conversation.json()["id"],
                course_id=fixture.course_a_id, release_id=fixture.release_a_id))
        result = await measure_tutoring_requests(sessions,
            ["What does cache coherence do?", "Explain cache coherence again."])
        assert result["request_count"] == 6
        assert result["failure_count"] == 0, result
        assert all(row["citation_count"] > 0 for row in result["requests"])
        assert result["quality_pass"] is None and result["deployment_qualified"] is False
        assert all(len(repository.list_messages(session.conversation_id)) == 4 for session in sessions)
    finally:
        for client in clients:
            await client.aclose()
        app_client.close()
        repository.close()
