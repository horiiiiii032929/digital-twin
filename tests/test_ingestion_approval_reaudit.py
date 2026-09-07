"""Regression cases for authoritative profile scope and ingestion ownership."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from src.digital_twin.student import (
    SQLiteStudentRepository,
    seed_synthetic_student_workflow,
)
from src.digital_twin.student.teaching_profile import (
    TeachingProfileError,
    TeachingProfileService,
)
from tests.api.test_publication_api import _teaching_profile_payload
from tests.services.test_ingestion_jobs import _service, _enqueue, _pdf


@pytest.mark.parametrize(
    "injected",
    [
        {"course_id": "other-course"},
        {"version": 50},
        {"status": "withdrawn", "withdrawn_at": "now"},
    ],
)
def test_profile_preferences_cannot_override_authoritative_fields(tmp_path, injected):
    repo = SQLiteStudentRepository(tmp_path / "scope.db")
    fixture = seed_synthetic_student_workflow(repo)
    if "course_id" in injected:
        injected = {"course_id": fixture.course_b_id}
    try:
        with pytest.raises(TeachingProfileError, match="preference"):
            TeachingProfileService(repo).create_draft(
                fixture.professor_id,
                fixture.course_a_id,
                {**_teaching_profile_payload(), **injected},
            )
        assert repo.list_teaching_profiles(fixture.course_a_id) == []
    finally:
        repo.close()


def test_concurrent_profile_drafts_allocate_distinct_versions(tmp_path):
    path = tmp_path / "concurrent.db"
    first = SQLiteStudentRepository(path)
    fixture = seed_synthetic_student_workflow(first)
    second = SQLiteStudentRepository(path)
    barrier = Barrier(2)
    # Reproduce the legacy read/read/write race. Atomic allocation does not use
    # this nontransactional service-level list operation.
    for repo in (first, second):
        original = repo.list_teaching_profiles

        def simultaneous_read(course_id, original=original):
            result = original(course_id)
            barrier.wait(timeout=3)
            return result

        repo.list_teaching_profiles = simultaneous_read
    try:

        def create(repo):
            return TeachingProfileService(repo).create_draft(
                fixture.professor_id, fixture.course_a_id, _teaching_profile_payload()
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            profiles = list(pool.map(create, (first, second)))
        assert sorted(p.version for p in profiles) == [1, 2]
    finally:
        first.close()
        second.close()


def test_ingestion_checks_the_bytes_it_actually_parses(tmp_path, monkeypatch):
    service, jobs, objects, students, fixture = _service(tmp_path)
    try:
        job, _ = _enqueue(service, fixture, _pdf(tmp_path))
        monkeypatch.setattr(objects, "read", lambda key: b"%PDF-corrupted-read")
        # A second store read could see restored bytes: checksum must bind the
        # buffer sent to the parser, not a separate read of the same object key.
        monkeypatch.setattr(objects, "checksum", lambda key: job.source_checksum)
        parsed = []
        monkeypatch.setattr(
            service.ingestion, "ingest_pdf", lambda *a, **kw: parsed.append(a)
        )
        finished = service.process_one("worker")
        assert not parsed
        assert finished.status.value == "failed"
        assert finished.error_message == "Stored source integrity verification failed."
    finally:
        jobs.close()
        students.close()


def test_reused_worker_name_cannot_fail_a_new_ingestion_attempt(tmp_path, monkeypatch):
    from threading import Event
    from services.ingestion import jobs as job_module

    service, jobs, objects, students, fixture = _service(tmp_path)
    first_entered, second_entered = Event(), Event()
    release_first, release_second = Event(), Event()

    class NoHeartbeat:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    monkeypatch.setattr(job_module, "_LeaseHeartbeat", NoHeartbeat)
    parse = service.ingestion.ingest_pdf
    entered = []

    def controlled_parse(*args, **kwargs):
        entered.append(1)
        if len(entered) == 1:
            first_entered.set()
            assert release_first.wait(5)
            raise ValueError("old failed attempt")
        second_entered.set()
        assert release_second.wait(5)
        return parse(*args, **kwargs)

    monkeypatch.setattr(service.ingestion, "ingest_pdf", controlled_parse)
    try:
        job, _ = _enqueue(service, fixture, _pdf(tmp_path))
        with ThreadPoolExecutor(max_workers=2) as pool:
            old = pool.submit(service.process_one, "same-worker")
            assert first_entered.wait(5)
            with jobs._lock, jobs._connection:
                jobs._connection.execute(
                    "UPDATE ingestion_jobs SET lease_expires_at = ? WHERE id = ?",
                    ("2000-01-01T00:00:00+00:00", job.id),
                )
            current = pool.submit(service.process_one, "same-worker")
            assert second_entered.wait(5)
            release_first.set()
            old.result(timeout=5)
            still_running = jobs.get(job.id).status.value
            release_second.set()
            final = current.result(timeout=5)
        assert still_running == "running"
        assert final.status.value == "succeeded"
        assert final.attempts == 2
    finally:
        release_first.set()
        release_second.set()
        jobs.close()
        students.close()


def test_withdrawn_profile_cannot_replace_a_working_published_release(tmp_path):
    from src.digital_twin.student.publication import (
        ReleaseLifecycleService,
        PublicationError,
    )
    from src.digital_twin.student.teaching_profile import TeachingProfileStatus
    from src.digital_twin.student.models import StudentReleaseStatus

    repo = SQLiteStudentRepository(tmp_path / "publish.db")
    fixture = seed_synthetic_student_workflow(repo)
    profiles = TeachingProfileService(repo)
    try:
        draft = profiles.create_draft(
            fixture.professor_id, fixture.course_a_id, _teaching_profile_payload()
        )
        approved = profiles.approve(
            fixture.professor_id,
            fixture.course_a_id,
            draft.profile_id,
            preview_sha256=profiles.preview(
                fixture.professor_id, fixture.course_a_id, draft.profile_id
            ).preview_sha256,
        )
        old = repo.get_release(fixture.release_a_id)
        candidate = old.model_copy(
            update={
                "id": "successor",
                "status": StudentReleaseStatus.DRAFT,
                "teaching_profile_id": approved.profile_id,
                "teaching_profile_sha256": approved.content_sha256,
            }
        )
        repo.save_release(candidate)
        publication = ReleaseLifecycleService(
            repo,
            profile_id=old.profile_id,
            profile_version=old.profile_version,
            evidence_sufficiency_ready=True,
        )
        publication.run_preflight(fixture.professor_id, candidate.id)

        # Force withdrawal after the service precheck, before the repository
        # transition. A stale preflight must not revoke the working predecessor.
        def withdraw_during_preparation(release):
            profiles.withdraw(
                fixture.professor_id, fixture.course_a_id, approved.profile_id
            )

        publication._prepare_retrieval_index = withdraw_during_preparation
        with pytest.raises(PublicationError, match="teaching profile"):
            publication.publish(fixture.professor_id, candidate.id)
        assert repo.get_release(old.id).status.value == "published"
        assert repo.get_release(candidate.id).status.value == "draft"
        assert (
            repo.get_teaching_profile(approved.profile_id).status
            == TeachingProfileStatus.WITHDRAWN
        )
    finally:
        repo.close()


def test_revoked_professor_cannot_manage_teaching_profile(tmp_path):
    from src.digital_twin.student.models import AccountStatus

    repo = SQLiteStudentRepository(tmp_path / "revoked.db")
    fixture = seed_synthetic_student_workflow(repo)
    try:
        account = repo.get_account(fixture.professor_id)
        repo.save_account(account.model_copy(update={"status": AccountStatus.REVOKED}))
        with pytest.raises(TeachingProfileError, match="owner"):
            TeachingProfileService(repo).create_draft(
                fixture.professor_id, fixture.course_a_id, _teaching_profile_payload()
            )
    finally:
        repo.close()
