from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from services.api.app.config import AppSettings
from services.api.app.factory import create_app
from src.digital_twin.student import (
    SQLiteStudentRepository,
    seed_synthetic_student_workflow,
)


def _headers(account_id: str) -> dict[str, str]:
    return {"X-Account-ID": account_id}


def test_professor_can_schedule_and_student_controls_private_in_app_outreach(
    tmp_path,
):
    repository = SQLiteStudentRepository(tmp_path / "proactive-api.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    app = create_app(student_repository=repository, settings=AppSettings())
    client = TestClient(app)
    now = datetime.now(UTC)
    quiet_hours_start = (now + timedelta(hours=1)).strftime("%H:%M")
    quiet_hours_end = (now + timedelta(hours=2)).strftime("%H:%M")

    preference = client.put(
        f"/api/student/courses/{fixture.course_a_id}/outreach-preferences/in-app",
        headers=_headers(fixture.student_a_id),
        json={
            "enabled": True,
            "timezone": "UTC",
            "quiet_hours_start": quiet_hours_start,
            "quiet_hours_end": quiet_hours_end,
            "max_messages_per_7_days": 3,
        },
    )
    scheduled = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/proactive-triggers",
        headers=_headers(fixture.professor_id),
        json={
            "student_account_id": fixture.student_a_id,
            "channel": "in-app",
            "kind": "scheduled-retrieval-practice",
            "scheduled_for": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "topic": "Cache coherence check",
            "prompt": "Why is cache coherence required?",
            "source_chunk_id": "chunk-cache-synthetic",
            "idempotency_key": "api-proactive-1",
        },
    )

    assert preference.status_code == 200
    assert preference.json()["enabled"] is True
    assert scheduled.status_code == 201
    trigger_id = scheduled.json()["id"]

    processed = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/proactive-triggers/{trigger_id}/process",
        headers=_headers(fixture.professor_id),
    )
    assert processed.status_code == 200
    assert processed.json()["outcome"] == "delivered"

    inbox = client.get(
        f"/api/student/outreach?course_id={fixture.course_a_id}",
        headers=_headers(fixture.student_a_id),
    )
    assert inbox.status_code == 200
    assert len(inbox.json()) == 1
    message_id = inbox.json()[0]["message"]["id"]
    assert inbox.json()[0]["citations"][0]["source_document_id"] == "document-cache"

    forbidden = client.post(
        f"/api/student/outreach/{message_id}/read",
        headers=_headers(fixture.student_b_id),
    )
    marked_read = client.post(
        f"/api/student/outreach/{message_id}/read",
        headers=_headers(fixture.student_a_id),
    )

    assert forbidden.status_code == 403
    assert marked_read.status_code == 200
    assert marked_read.json()["message"]["status"] == "read"


def test_outreach_is_opt_in_and_cross_course_scheduling_is_forbidden(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "proactive-api.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    client = TestClient(
        create_app(student_repository=repository, settings=AppSettings())
    )
    now = datetime.now(UTC)

    response = client.post(
        f"/api/professor/courses/{fixture.course_b_id}/proactive-triggers",
        headers=_headers(fixture.professor_id),
        json={
            "student_account_id": fixture.student_a_id,
            "channel": "in-app",
            "kind": "scheduled-retrieval-practice",
            "scheduled_for": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "topic": "Policy check",
            "prompt": "What does a release policy define?",
            "source_chunk_id": "chunk-policy-synthetic",
            "idempotency_key": "api-cross-course",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "course_forbidden"


def test_student_can_snooze_and_resume_autonomous_check_ins(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "proactive-snooze-api.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    client = TestClient(
        create_app(student_repository=repository, settings=AppSettings())
    )
    snoozed_until = (datetime.now(UTC) + timedelta(days=7)).isoformat()

    snoozed = client.put(
        f"/api/student/courses/{fixture.course_a_id}/outreach-preferences/in-app",
        headers=_headers(fixture.student_a_id),
        json={
            "enabled": True,
            "timezone": "UTC",
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "max_messages_per_7_days": 3,
            "snoozed_until": snoozed_until,
        },
    )
    assert snoozed.status_code == 200
    assert snoozed.json()["snoozed_until"] == snoozed_until

    resumed = client.put(
        f"/api/student/courses/{fixture.course_a_id}/outreach-preferences/in-app",
        headers=_headers(fixture.student_a_id),
        json={
            "enabled": True,
            "timezone": "UTC",
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "max_messages_per_7_days": 3,
            "snoozed_until": None,
        },
    )
    assert resumed.status_code == 200
    assert resumed.json()["snoozed_until"] is None
