from pathlib import Path

import httpx
import pytest

from scripts.verify_https_staging import (
    _login,
    _passwords_from_env,
    _validate_https_url,
    _wait_for_readiness,
    _write_synthetic_pdf,
    verify_tutoring_mode,
)


def test_live_verifier_defaults_target_the_qualified_local_profile() -> None:
    source = (Path(__file__).parents[1] / "scripts/verify_https_staging.py").read_text()

    assert 'default="student-tutor-r1-local-candidate"' in source
    assert 'default="v1"' in source
    assert 'default="bounded-tutoring-graph"' in source
    assert "if args.output is not None:" in source


def test_live_verifier_requires_every_readiness_subsystem() -> None:
    source = (Path(__file__).parents[1] / "scripts/verify_https_staging.py").read_text()

    assert 'all(readiness["checks"].values())' in source
    assert "time.sleep(1.0)" in source
    assert "release-bound-course-domain-model-approved" in source


def test_live_verifier_waits_through_bounded_restart_startup() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(502)
        return httpx.Response(
            200,
            json={"status": "ready", "checks": {"database": True}},
        )

    with httpx.Client(
        base_url="https://localhost:8443",
        transport=httpx.MockTransport(handler),
    ) as client:
        readiness = _wait_for_readiness(client, timeout_seconds=1.0)

    assert attempts == 2
    assert readiness["status"] == "ready"


def test_live_verifier_requires_an_https_origin() -> None:
    assert _validate_https_url("https://twin.example.edu/") == (
        "https://twin.example.edu",
        "https://twin.example.edu",
    )

    with pytest.raises(SystemExit, match="HTTPS origin"):
        _validate_https_url("http://twin.example.edu")
    with pytest.raises(SystemExit, match="without a path"):
        _validate_https_url("https://twin.example.edu/path")


def test_live_login_sends_the_same_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["origin"] = request.headers["origin"]
        return httpx.Response(200, json={"role": "student"})

    with httpx.Client(
        base_url="https://twin.example.edu",
        transport=httpx.MockTransport(handler),
    ) as client:
        response = _login(client, "student@example.edu", "synthetic-password")

    assert response.status_code == 200
    assert seen == {"origin": "https://twin.example.edu"}


def test_live_verifier_reads_passwords_only_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STAGING_ADMIN_PASSWORD", "admin-password-123")
    monkeypatch.setenv("STAGING_PROFESSOR_PASSWORD", "professor-password-123")
    monkeypatch.setenv("STAGING_STUDENT_PASSWORD", "student-password-123")

    assert _passwords_from_env() == {
        "admin": "admin-password-123",
        "professor": "professor-password-123",
        "student": "student-password-123",
    }


def test_live_verifier_emits_a_real_synthetic_pdf(tmp_path: Path) -> None:
    path = tmp_path / "source.pdf"

    _write_synthetic_pdf(path)

    assert path.read_bytes().startswith(b"%PDF")


def test_mode_check_requires_the_selected_runtime_mode(tmp_path: Path) -> None:
    result = tmp_path / "result.json"
    result.write_text(
        '{"run_id":"run-1","accounts":{"student_email":"student@example.edu"},'
        '"workflow":{"course_id":"course-1"}}'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/health/ready":
            return httpx.Response(
                200,
                json={"status": "ready", "checks": {"database": True}},
            )
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"role": "student"})
        if request.url.path.endswith("/conversations"):
            return httpx.Response(201, json={"id": "conversation-1"})
        return httpx.Response(
            200,
            json={
                "tutoring_mode": "bounded-tutoring-graph",
                "learner_state_revision": 1,
                "tutor_message": {"action": "answer"},
                "citations": [{"id": "citation-1"}],
            },
        )

    with httpx.Client(
        base_url="https://localhost:8443",
        transport=httpx.MockTransport(handler),
    ) as client:
        checked = verify_tutoring_mode(
            client,
            result,
            "student-password-123",
            expected_tutoring_mode="bounded-tutoring-graph",
            origin="https://localhost:8443",
        )

    assert checked["passed_checks"] == 3


def test_mode_check_accepts_governed_v2_as_a_stateful_runtime(tmp_path: Path) -> None:
    result = tmp_path / "result.json"
    result.write_text(
        '{"run_id":"run-1","accounts":{"student_email":"student@example.edu"},'
        '"workflow":{"course_id":"course-1"}}'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/health/ready":
            return httpx.Response(
                200,
                json={"status": "ready", "checks": {"database": True}},
            )
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"role": "student"})
        if request.url.path.endswith("/conversations"):
            return httpx.Response(201, json={"id": "conversation-1"})
        return httpx.Response(
            200,
            json={
                "tutoring_mode": "governed-autonomous-tutoring-graph-v2.1",
                "learner_state_revision": 1,
                "tutor_message": {"action": "answer"},
                "citations": [{"id": "citation-1"}],
            },
        )

    with httpx.Client(
        base_url="https://localhost:8443",
        transport=httpx.MockTransport(handler),
    ) as client:
        checked = verify_tutoring_mode(
            client,
            result,
            "student-password-123",
            expected_tutoring_mode="governed-autonomous-tutoring-graph-v2.1",
            origin="https://localhost:8443",
        )

    assert checked["passed_checks"] == 3
