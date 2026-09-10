"""Initial cloud administrator creation must never reset an existing account."""
import json
from types import SimpleNamespace

import pytest

from infra.cdk.runtime import bootstrap_admin


def configure_secret(tmp_path, monkeypatch):
    secret = tmp_path / "synthetic-secret.json"
    secret.write_text(json.dumps({
        "ADMIN_EMAIL": "admin@example.test",
        "BOOTSTRAP_ADMIN_PASSWORD": "Synthetic-Only-Password-123",
    }))
    monkeypatch.setenv("SECRET_FILE", str(secret))


def test_existing_administrator_is_never_reset(tmp_path, monkeypatch):
    configure_secret(tmp_path, monkeypatch)
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(bootstrap_admin.subprocess, "run", run)
    bootstrap_admin.main()
    assert len(calls) == 1
    assert "scripts.bootstrap_admin" not in calls[0]


def test_first_password_is_passed_by_environment_not_command_arguments(tmp_path, monkeypatch):
    configure_secret(tmp_path, monkeypatch)
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=42 if len(calls) == 1 else 0)

    monkeypatch.setattr(bootstrap_admin.subprocess, "run", run)
    bootstrap_admin.main()
    args, kwargs = calls[1]
    assert "scripts.bootstrap_admin" in args
    assert "Synthetic-Only-Password-123" not in " ".join(args)
    assert kwargs["env"]["BOOTSTRAP_ADMIN_PASSWORD"] == "Synthetic-Only-Password-123"


def test_database_probe_error_prevents_provisioning(tmp_path, monkeypatch):
    configure_secret(tmp_path, monkeypatch)
    monkeypatch.setattr(bootstrap_admin.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    with pytest.raises(SystemExit, match="refusing to provision"):
        bootstrap_admin.main()
