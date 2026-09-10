"""Exercise real staging API seeding and retry behavior without network/provider calls."""
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from scripts import seed_aws_pilot as seed
from services.api.app.config import AppSettings, RuntimeMode
from services.api.app.factory import create_app
from src.digital_twin.grounding import AnyHitEvidenceGate
from src.digital_twin.identity import IdentityService, SQLiteIdentityRepository
from src.digital_twin.student import AccountRole, SQLiteStudentRepository


def test_seed_staging_workflow_and_repeat_preserve_credentials(tmp_path, monkeypatch):
    url = "https://seed.example.test"
    settings = AppSettings(mode=RuntimeMode.STAGING, database_path=tmp_path / "state.sqlite3",
        data_root=tmp_path / "data", allowed_origins=(url,), secure_cookies=True,
        login_attempts_per_minute=1000, authenticated_requests_per_minute=10000)
    students = SQLiteStudentRepository(settings.database_path)
    identities = SQLiteIdentityRepository(settings.database_path)
    identity = IdentityService(identities, students)
    identity.provision_account(account_id="admin-original", email="admin@example.test",
        display_name="Admin", role=AccountRole.ADMIN, password="Original-admin-password-123")
    original_admin = identities.get_credential_by_email("admin@example.test").password_hash
    app = create_app(settings=settings, student_repository=students, identity_repository=identities,
        student_profile_path=seed.ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json",
        student_evidence_gate=AnyHitEvidenceGate(), source_root=tmp_path / "sources", region_crop_root=tmp_path / "crops")
    monkeypatch.setattr(seed, "subprocess", SimpleNamespace(run=lambda *a, **k: SimpleNamespace(stdout=json.dumps({
        "SecretString": json.dumps({"ADMIN_EMAIL": "admin@example.test", "BOOTSTRAP_ADMIN_PASSWORD": "Original-admin-password-123"})}))))
    def client(run):
        value = TestClient(app, base_url=url, headers={"Origin": url})
        original_request = value.request
        def request(method, path, **kwargs):
            if method == "GET" and "/ingestion-jobs/" in path:
                app.state.ingestion_job_service.process_one("seed-test-worker")
            return original_request(method, path, **kwargs)
        value.request = request
        run.clients.append(value)
        return value
    monkeypatch.setattr(seed.SeedRun, "client", client)
    path = tmp_path / "private/state.json"
    outputs = {"AppUrlOutput": url, "RuntimeSecretArnOutput": "test-secret"}
    for approved in [False, True, True]:
        run = seed.SeedRun(path, outputs)
        try:
            run.run(approved)
        finally:
            run.close()
        if approved:
            hashes = {item["email"]: identities.get_credential_by_email(item["email"]).password_hash
                      for item in run.state["accounts"].values()}
            if "previous_hashes" in locals():
                assert hashes == previous_hashes
            previous_hashes = hashes
    state = json.loads(path.read_text())
    assert len(state["accounts"]) == 8
    assert len(state["courses"]) == 3
    assert sum(c.get("status") == "published" for c in state["courses"].values()) == 2
    assert identities.get_credential_by_email("admin@example.test").password_hash == original_admin
    assert path.stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(settings.database_path) as con:
        for table, expected in [("accounts", 9), ("identity_credentials", 9), ("courses", 3), ("releases", 2), ("course_domain_models", 2)]:
            assert con.execute("SELECT count(*) FROM " + table).fetchone()[0] == expected
    from scripts.seed_pilot_personas import PersonaSeed
    persona_hashes = None
    for _ in range(2):
        api = seed.SeedRun(path, outputs)
        persona = PersonaSeed(api, tmp_path / "private/personas.json")
        admin = api.client()
        api.login(admin, "admin@example.test", "Original-admin-password-123")
        try:
            persona.apply(admin)
            persona.credential_sheet()
        finally:
            api.close()
        observed = {p["email"]: identities.get_credential_by_email(p["email"]).password_hash
                    for p in persona.state["personas"].values()}
        if persona_hashes is not None:
            assert observed == persona_hashes
        persona_hashes = observed
    with sqlite3.connect(settings.database_path) as con:
        for table, expected in [("accounts", 16), ("identity_credentials", 16), ("courses", 3),
                                ("releases", 2), ("conversations", 7), ("messages", 14)]:
            assert con.execute("SELECT count(*) FROM " + table).fetchone()[0] == expected
    assert persona.state["cross_persona_privacy"] == "passed"
    assert identities.get_credential_by_email("admin@example.test").password_hash == original_admin
    students.close()
    identities.close()


def test_changed_seed_manifest_is_rejected_before_remote_access(tmp_path):
    import pytest
    state = tmp_path / "state.json"
    seed.private_json(state, {"manifest_sha256": "changed", "url": "https://seed.example.test"})
    with pytest.raises(ValueError, match="changed"):
        seed.SeedRun(state, {"AppUrlOutput": "https://seed.example.test"})


def test_generated_demo_password_satisfies_policy_for_single_class_random_output(monkeypatch):
    from src.digital_twin.identity.service import _validate_password
    for random_output in ['a' * 27, 'A' * 27, '0' * 27, '_' * 27]:
        calls = []
        def token_urlsafe(n):
            calls.append(n)
            return random_output
        monkeypatch.setattr(seed.secrets, 'token_urlsafe', token_urlsafe)
        password = seed.generate_demo_password()
        _validate_password(password)
        assert password.endswith(random_output)
        assert calls == [20]
