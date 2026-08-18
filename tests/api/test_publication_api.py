from pathlib import Path

from fastapi.testclient import TestClient

from services.api.app.factory import create_app
from src.digital_twin.grounding import OCRTextRegion
from src.digital_twin.onboarding import InMemorySessionRepository, create_session
from src.digital_twin.student import (
    SQLiteStudentRepository,
    StudentReleaseStatus,
    approved_synthetic_policy,
    seed_synthetic_student_workflow,
)
from src.digital_twin.tutor_policy import build_initial_policy
from tests.fixtures.ingestion import write_synthetic_pdf


class SyntheticCourseOCR:
    implementation_id = "synthetic-course-ocr"
    version = "1.0.0"

    def recognize(
        self,
        page_image,
        *,
        page_number,
        image_width,
        image_height,
    ):
        assert page_image and page_number == 1
        assert image_width > 0 and image_height > 0
        return [
            OCRTextRegion(
                text="Scanned release evidence describes cache ownership.",
                bounding_box=(0.1, 0.1, 0.9, 0.3),
                confidence=0.99,
            )
        ]


def _headers(account_id: str) -> dict[str, str]:
    return {"X-Account-ID": account_id}


def _client(
    tmp_path: Path,
    *,
    approved: bool,
    source_ocr_provider=None,
) -> tuple[TestClient, SQLiteStudentRepository, InMemorySessionRepository, object]:
    student_repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(student_repository)
    sessions = InMemorySessionRepository()
    session = create_session("onboarding-release-synthetic")
    session.current_step = "professor_approval"
    session.policy = (
        approved_synthetic_policy() if approved else build_initial_policy()
    )
    sessions.save(session)
    app = create_app(
        repository=sessions,
        student_repository=student_repository,
        source_root=tmp_path / "course-sources",
        region_crop_root=tmp_path / "region-crops",
        source_ocr_provider=source_ocr_provider,
    )
    return TestClient(app), student_repository, sessions, fixture


def _create_draft(client: TestClient, repository, sessions, fixture, release_id):
    source_release = repository.get_release(fixture.release_a_id)
    session = sessions.get("onboarding-release-synthetic")
    response = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json={
            "session_id": session.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "release_id": release_id,
            "chunks": [chunk.model_dump(mode="json") for chunk in source_release.chunks],
        },
    )
    assert response.status_code == 201
    return response.json()


def _set_evaluation(client: TestClient, fixture, release_id: str, status: str = "passed"):
    return client.patch(
        f"/api/professor/releases/{release_id}/evaluation",
        headers=_headers(fixture.professor_id),
        json={"status": status},
    )


def test_publication_requires_evaluation_and_resolved_policy(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=False)
    draft = _create_draft(
        client, repository, sessions, fixture, "release-a-blocked-synthetic"
    )
    assert draft["status"] == "draft"
    assert draft["evaluation_status"] == "pending"

    missing_evaluation = client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    )
    assert missing_evaluation.status_code == 409
    assert missing_evaluation.json()["detail"]["code"] == "evaluation_required"

    assert _set_evaluation(client, fixture, draft["id"]).status_code == 200
    blocked = client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "release_blocked"
    assert repository.get_published_release(fixture.course_a_id).id == fixture.release_a_id


def test_publish_replaces_current_release_and_denies_stale_conversation(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    conversation = client.post(
        f"/api/student/courses/{fixture.course_a_id}/conversations",
        headers=_headers(fixture.student_a_id),
    )
    assert conversation.status_code == 201

    draft = _create_draft(
        client, repository, sessions, fixture, "release-a-v2-synthetic"
    )
    assert _set_evaluation(client, fixture, draft["id"]).status_code == 200
    published = client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert repository.get_release(fixture.release_a_id).status == StudentReleaseStatus.WITHDRAWN

    stale_turn = client.post(
        f"/api/student/conversations/{conversation.json()['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "stale-release"},
    )
    assert stale_turn.status_code == 409
    assert stale_turn.json()["detail"]["code"] == "release_unavailable"


def test_withdraw_and_rollback_restore_previous_release(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    assert _set_evaluation(client, fixture, fixture.release_a_id).status_code == 200
    draft = _create_draft(
        client, repository, sessions, fixture, "release-a-v2-rollback-synthetic"
    )
    assert _set_evaluation(client, fixture, draft["id"]).status_code == 200
    assert client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    ).status_code == 200

    withdrawn = client.post(
        f"/api/professor/releases/{draft['id']}/withdraw",
        headers=_headers(fixture.professor_id),
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    assert client.get(
        "/api/student/courses", headers=_headers(fixture.student_a_id)
    ).json() == []

    rollback = client.post(
        f"/api/professor/releases/{fixture.release_a_id}/rollback",
        headers=_headers(fixture.professor_id),
    )
    assert rollback.status_code == 200
    assert rollback.json()["id"] == fixture.release_a_id
    assert rollback.json()["status"] == "published"
    assert repository.get_published_release(fixture.course_a_id).id == fixture.release_a_id


def test_professor_ingests_scanned_pdf_into_release_ready_region_chunks(tmp_path):
    client, repository, sessions, fixture = _client(
        tmp_path,
        approved=True,
        source_ocr_provider=SyntheticCourseOCR(),
    )
    scan = tmp_path / "scan.pdf"
    write_synthetic_pdf(scan, with_text=False, with_figure=True)

    response = client.put(
        f"/api/professor/courses/{fixture.course_a_id}/sources/scan-notes",
        params={
            "title": "Scanned cache notes",
            "version": 1,
            "display_allowed": True,
        },
        headers={
            **_headers(fixture.professor_id),
            "Content-Type": "application/pdf",
        },
        content=scan.read_bytes(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["region_kind_counts"]["ocr"] == 1
    assert payload["region_count"] >= 2
    assert payload["chunk_count"] == len(payload["chunks"])
    assert any("Scanned release evidence" in chunk["text"] for chunk in payload["chunks"])
    assert all(
        chunk["metadata"]["course_id"] == fixture.course_a_id
        for chunk in payload["chunks"]
    )
    assert all(chunk["crop_ref"].startswith("region://") for chunk in payload["chunks"])
    assert list((tmp_path / "course-sources").glob("source-*.pdf"))
    assert list((tmp_path / "region-crops").glob("region-*.png"))

    session = sessions.get("onboarding-release-synthetic")
    draft = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json={
            "session_id": session.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "release_id": "release-scanned-synthetic",
            "chunks": payload["chunks"],
        },
    )
    assert draft.status_code == 201
    assert draft.json()["chunks"][0]["region_id"]

    denied = client.put(
        f"/api/professor/courses/{fixture.course_a_id}/sources/denied",
        params={"title": "Denied"},
        headers={
            **_headers(fixture.student_a_id),
            "Content-Type": "application/pdf",
        },
        content=scan.read_bytes(),
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "professor_role_required"
