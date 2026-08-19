from pathlib import Path

import httpx
import pytest

from scripts.verify_https_staging import (
    _login,
    _passwords_from_env,
    _validate_https_url,
    _write_synthetic_pdf,
)


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
