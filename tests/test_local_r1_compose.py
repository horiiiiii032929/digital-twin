from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _compose() -> dict:
    return yaml.safe_load((ROOT / "compose.local-r1.yml").read_text(encoding="utf-8"))


def test_local_r1_uses_the_qualified_offline_t1_profile() -> None:
    compose = _compose()
    runtime = compose["x-runtime-environment"]

    assert runtime["APP_MODE"] == "staging"
    assert runtime["APP_GENERATOR_MODE"] == "deterministic"
    assert runtime["APP_EVIDENCE_GATE_MODE"] == "structured-lexical-v1"
    assert runtime["APP_STUDENT_TUTORING_MODE"] == (
        "${APP_STUDENT_TUTORING_MODE:-bounded-tutoring-graph}"
    )
    assert runtime["APP_PROACTIVE_OUTREACH_WORKER_ENABLED"] == "true"
    assert runtime["APP_STUDENT_PROFILE_PATH"].endswith(
        "student-tutor-r1-local-candidate-v1.json"
    )
    assert runtime["APP_T1_QUALIFICATION_RESULT_PATH"].endswith(
        "autonomous-tutoring-r1-confirmation-002.json"
    )
    assert "OPENAI_API_KEY" not in runtime


def test_local_r1_exposes_only_the_https_web_origin() -> None:
    compose = _compose()
    services = compose["services"]

    assert set(services) == {"api", "ingestion-worker", "outreach-worker", "web"}
    assert "ports" not in services["api"]
    assert "ports" not in services["ingestion-worker"]
    assert "ports" not in services["outreach-worker"]
    assert services["web"]["ports"] == [
        "127.0.0.1:${LOCAL_R1_HTTPS_PORT:-8443}:443"
    ]
    assert compose["x-runtime-environment"]["APP_ALLOWED_ORIGINS"] == (
        "https://localhost:${LOCAL_R1_HTTPS_PORT:-8443}"
    )


def test_local_r1_services_are_restart_safe_and_least_privileged() -> None:
    services = _compose()["services"]

    for service in services.values():
        assert service["read_only"] is True
        assert service["init"] is True
        assert service["restart"] == "unless-stopped"
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["cap_drop"] == ["ALL"]
        assert service["tmpfs"] == ["/tmp:size=64m,mode=1777"]

    assert services["web"]["cap_add"] == ["NET_BIND_SERVICE"]
    assert services["api"]["volumes"] == [
        "runtime-data:/var/lib/digital-twin-parent"
    ]
    assert services["ingestion-worker"]["volumes"] == [
        "runtime-data:/var/lib/digital-twin-parent"
    ]
    assert services["outreach-worker"]["volumes"] == [
        "runtime-data:/var/lib/digital-twin-parent"
    ]
    assert services["outreach-worker"]["command"][-2:] == [
        "--poll-seconds",
        "2",
    ]
    runtime = _compose()["x-runtime-environment"]
    assert runtime["APP_DATA_ROOT"] == "/var/lib/digital-twin-parent/runtime"
    assert runtime["APP_DATABASE_PATH"].startswith(runtime["APP_DATA_ROOT"])


def test_local_caddy_uses_internal_https_and_release_headers() -> None:
    caddyfile = (ROOT / "deploy/Caddyfile.local").read_text(encoding="utf-8")

    assert "localhost {" in caddyfile
    assert "tls internal" in caddyfile
    assert 'Strict-Transport-Security "max-age=31536000"' in caddyfile
    assert "script-src 'self'" in caddyfile
    assert "reverse_proxy api:8000" in caddyfile


def test_local_runbook_writes_backup_to_durable_host_mount() -> None:
    runbook = (ROOT / "docs/local-r1-runbook.md").read_text(encoding="utf-8")

    assert '"$(pwd)/reports/generated:/host-output"' in runbook
    assert "--output /host-output/local-r1-runtime-backup.zip" in runbook
    assert "cp api:/tmp/local-r1-runtime.zip" not in runbook
