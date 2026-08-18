from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api.app.config import AppSettings, RuntimeMode
from services.api.app.factory import create_app
from src.digital_twin.identity import IdentityService, SQLiteIdentityRepository
from src.digital_twin.student import (
    AccountRole,
    SQLiteStudentRepository,
    seed_synthetic_student_workflow,
)
from tests.fixtures.ingestion import write_synthetic_pdf


ORIGIN = "https://staging.example.test"
ADMIN_ID = "admin-synthetic"
ADMIN_PASSWORD = "Admin-password-42"
PROFESSOR_PASSWORD = "Professor-pass-42"
PROFESSOR_NEW_PASSWORD = "Professor-new-pass-43"


def _settings(
    tmp_path: Path,
    *,
    login_limit: int = 10,
    max_upload_bytes: int = 50 * 1024 * 1024,
) -> AppSettings:
    return AppSettings(
        mode=RuntimeMode.STAGING,
        database_path=tmp_path / "runtime.sqlite3",
        data_root=tmp_path / "runtime",
        allowed_origins=(ORIGIN,),
        secure_cookies=True,
        session_ttl_seconds=3600,
        login_attempts_per_minute=login_limit,
        max_upload_bytes=max_upload_bytes,
    )


def _client(
    tmp_path: Path,
    *,
    login_limit: int = 10,
    max_upload_bytes: int = 50 * 1024 * 1024,
):
    settings = _settings(
        tmp_path,
        login_limit=login_limit,
        max_upload_bytes=max_upload_bytes,
    )
    students = SQLiteStudentRepository(settings.database_path)
    fixture = seed_synthetic_student_workflow(students)
    identities = SQLiteIdentityRepository(settings.database_path)
    service = IdentityService(identities, students, session_ttl_seconds=3600)
    service.provision_account(
        account_id=ADMIN_ID,
        email="admin@example.test",
        display_name="Pilot Admin",
        role=AccountRole.ADMIN,
        password=ADMIN_PASSWORD,
    )
    service.provision_account(
        account_id=fixture.professor_id,
        email="professor@example.test",
        display_name="Pilot Professor",
        role=AccountRole.PROFESSOR,
        password=PROFESSOR_PASSWORD,
    )
    app = create_app(
        student_repository=students,
        identity_repository=identities,
        settings=settings,
        source_root=tmp_path / "sources",
        region_crop_root=tmp_path / "crops",
    )
    return (
        TestClient(app, base_url="https://testserver"),
        students,
        identities,
        service,
        fixture,
        settings,
    )


def _login(client: TestClient, email: str, password: str):
    return client.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )


def test_staging_rejects_synthetic_header_and_uses_secure_cookie_session(tmp_path):
    client, *_ = _client(tmp_path)

    denied = client.get(
        "/api/student/courses", headers={"X-Account-ID": "student-a-synthetic"}
    )
    assert denied.status_code == 401
    assert denied.json()["detail"]["code"] == "synthetic_identity_disabled"

    logged_in = _login(client, "PROFESSOR@example.test", PROFESSOR_PASSWORD)
    assert logged_in.status_code == 200
    assert logged_in.json()["role"] == "professor"
    cookie = logged_in.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["email"] == "professor@example.test"
    assert session.headers["cache-control"] == "no-store"


def test_logout_revokes_session_and_requires_allowed_origin(tmp_path):
    client, *_ = _client(tmp_path)
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 200
    )

    blocked = client.post("/api/auth/logout", headers={"Origin": "https://evil.test"})
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "origin_not_allowed"

    logged_out = client.post("/api/auth/logout", headers={"Origin": ORIGIN})
    assert logged_out.status_code == 204
    assert client.get("/api/auth/session").status_code == 401


def test_cross_origin_login_is_rejected_before_cookie_issue(tmp_path):
    client, *_ = _client(tmp_path)

    blocked = client.post(
        "/api/auth/login",
        headers={"Origin": "https://evil.test"},
        json={
            "email": "professor@example.test",
            "password": PROFESSOR_PASSWORD,
        },
    )

    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "origin_not_allowed"


def test_only_admin_can_invite_and_revoked_account_session_fails(tmp_path):
    client, students, _, identity, fixture, _ = _client(tmp_path)
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 200
    )

    professor_denied = client.post(
        "/api/admin/accounts",
        headers={"Origin": ORIGIN},
        json={
            "email": "student@example.test",
            "display_name": "Pilot Student",
            "role": "student",
            "temporary_password": "Student-password-42",
        },
    )
    assert professor_denied.status_code == 403
    assert professor_denied.json()["detail"]["code"] == "admin_required"

    client.cookies.clear()
    assert _login(client, "admin@example.test", ADMIN_PASSWORD).status_code == 200
    invited = client.post(
        "/api/admin/accounts",
        headers={"Origin": ORIGIN},
        json={
            "email": "student@example.test",
            "display_name": "Pilot Student",
            "role": "student",
            "temporary_password": "Student-password-42",
        },
    )
    assert invited.status_code == 201
    assert invited.json()["role"] == "student"

    client.cookies.clear()
    assert (
        _login(client, "student@example.test", "Student-password-42").status_code == 200
    )
    student_id = invited.json()["account_id"]
    identity.revoke_account(ADMIN_ID, student_id)
    assert client.get("/api/auth/session").status_code == 401
    assert students.get_account(student_id).status.value == "revoked"


def test_password_change_and_admin_reset_revoke_existing_sessions(tmp_path):
    client, students, _, _, fixture, _ = _client(tmp_path)
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 200
    )

    changed = client.post(
        "/api/auth/password",
        headers={"Origin": ORIGIN},
        json={
            "current_password": PROFESSOR_PASSWORD,
            "new_password": PROFESSOR_NEW_PASSWORD,
        },
    )
    assert changed.status_code == 204
    assert client.get("/api/auth/session").status_code == 401
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 401
    )
    assert (
        _login(client, "professor@example.test", PROFESSOR_NEW_PASSWORD).status_code
        == 200
    )

    client.cookies.clear()
    assert _login(client, "admin@example.test", ADMIN_PASSWORD).status_code == 200
    reset = client.post(
        f"/api/admin/accounts/{fixture.professor_id}/password",
        headers={"Origin": ORIGIN},
        json={"new_password": "Professor-reset-pass-44"},
    )
    assert reset.status_code == 204
    assert (
        _login(
            TestClient(client.app, base_url="https://testserver"),
            "professor@example.test",
            "Professor-reset-pass-44",
        ).status_code
        == 200
    )
    assert {event.event_type for event in students.list_audit_events()} >= {
        "identity.login",
        "identity.password_changed",
        "identity.password_reset",
    }


def test_staging_configuration_fails_closed_for_insecure_origin(tmp_path):
    with pytest.raises(ValueError, match="origins must use https"):
        AppSettings(
            mode=RuntimeMode.STAGING,
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=("http://example.test",),
            secure_cookies=True,
        ).validate()


def test_live_generator_configuration_requires_environment_credential(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        AppSettings(
            mode=RuntimeMode.STAGING,
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=(ORIGIN,),
            secure_cookies=True,
            generator_mode="deepseek-v4-flash",
        ).validate()


def test_staging_upload_is_idempotent_async_and_professor_scoped(tmp_path):
    client, _, _, identity, fixture, _ = _client(tmp_path)
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 200
    )
    pdf = tmp_path / "lecture.pdf"
    write_synthetic_pdf(pdf, with_text=True, with_figure=True)
    headers = {
        "Origin": ORIGIN,
        "Content-Type": "application/pdf",
        "Idempotency-Key": "lecture-upload-1",
    }

    queued = client.put(
        f"/api/professor/courses/{fixture.course_a_id}/sources/lecture-01",
        params={"title": "Lecture 01", "display_allowed": True},
        headers=headers,
        content=pdf.read_bytes(),
    )
    duplicate = client.put(
        f"/api/professor/courses/{fixture.course_a_id}/sources/lecture-01",
        params={"title": "Lecture 01", "display_allowed": True},
        headers=headers,
        content=pdf.read_bytes(),
    )

    assert queued.status_code == 202
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == queued.json()["id"]
    completed = client.app.state.ingestion_job_service.process_one("test-worker")
    assert completed.status.value == "succeeded"

    course_jobs = client.get(
        f"/api/professor/courses/{fixture.course_a_id}/ingestion-jobs"
    )
    assert course_jobs.status_code == 200
    assert [job["id"] for job in course_jobs.json()] == [queued.json()["id"]]
    fetched = client.get(
        f"/api/professor/ingestion-jobs/{completed.id}",
    )
    assert fetched.status_code == 200
    assert fetched.json()["result"]["chunks"]

    identity.provision_account(
        account_id="professor-other",
        email="other-professor@example.test",
        display_name="Other Professor",
        role=AccountRole.PROFESSOR,
        password="Other-professor-42",
    )
    client.cookies.clear()
    assert (
        _login(client, "other-professor@example.test", "Other-professor-42").status_code
        == 200
    )
    denied = client.get(f"/api/professor/ingestion-jobs/{completed.id}")
    assert denied.status_code == 404


def test_staging_does_not_accept_manual_release_pass(tmp_path):
    client, _, _, _, fixture, _ = _client(tmp_path)
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 200
    )

    response = client.patch(
        f"/api/professor/releases/{fixture.release_a_id}/evaluation",
        headers={"Origin": ORIGIN},
        json={"status": "passed"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "preflight_required"


def test_operations_health_metrics_rate_limit_and_log_redaction(tmp_path, caplog):
    client, *_ = _client(tmp_path, login_limit=2)

    live = client.get("/api/health/live")
    ready = client.get("/api/health/ready")
    assert live.json() == {"status": "ok"}
    assert ready.json()["status"] == "ready"
    assert live.headers["x-content-type-options"] == "nosniff"
    assert "max-age=31536000" in live.headers["strict-transport-security"]

    secret = "Never-log-this-password-42"
    with caplog.at_level("INFO", logger="digital_twin.api"):
        assert _login(client, "missing@example.test", secret).status_code == 401
    assert secret not in caplog.text

    second = _login(client, "missing@example.test", secret)
    limited = _login(client, "missing@example.test", secret)
    assert second.status_code == 401
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"


def test_metrics_require_administrator_and_upload_size_is_guarded(tmp_path):
    client, *_ = _client(tmp_path, max_upload_bytes=10)
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 200
    )
    assert client.get("/api/operations/metrics").status_code == 403

    oversized = client.put(
        "/api/professor/courses/course-a-synthetic/sources/too-large",
        params={"title": "Too large"},
        headers={
            "Origin": ORIGIN,
            "Content-Type": "application/pdf",
            "Idempotency-Key": "too-large",
        },
        content=b"%PDF-" + b"x" * 20,
    )
    assert oversized.status_code == 413
    assert oversized.json()["detail"]["code"] == "source_too_large"

    client.cookies.clear()
    assert _login(client, "admin@example.test", ADMIN_PASSWORD).status_code == 200
    metrics = client.get("/api/operations/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["request_count"] >= 4
    assert "latency_p95_ms" in metrics.json()
