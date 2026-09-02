from pathlib import Path
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from services.api.app.config import (
    AppSettings,
    AutonomyPlannerMode,
    EvidenceGateMode,
    GeneratorMode,
    RuntimeMode,
    StudentTutoringMode,
)
from services.api.app.factory import (
    _configured_evidence_gate,
    _configured_generator,
    create_app,
)
from src.digital_twin.evaluation import (
    ComponentKind,
    SystemReleaseProfile,
    load_release_profile,
)
from src.digital_twin.identity import IdentityService, SQLiteIdentityRepository
from src.digital_twin.grounding import (
    AmbiguitySafeEvidenceGateV1,
    ContiguousQuoteAtomicClaimVerifier,
    QuestionTargetedAtomicEvidenceGate,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.onboarding import create_session
from src.digital_twin.student import (
    AccountRole,
    SQLiteStudentRepository,
    approved_synthetic_policy,
    seed_synthetic_student_workflow,
)
from tests.fixtures.ingestion import write_synthetic_pdf


ORIGIN = "https://staging.example.test"
ADMIN_ID = "admin-synthetic"
ADMIN_PASSWORD = "Admin-password-42"
PROFESSOR_PASSWORD = "Professor-pass-42"
PROFESSOR_NEW_PASSWORD = "Professor-new-pass-43"
CANDIDATE_PROFILE = (
    Path(__file__).resolve().parents[2]
    / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)
LOCAL_R1_PROFILE = (
    Path(__file__).resolve().parents[2]
    / "research/05_evaluation/profiles/student-tutor-r1-local-candidate-v1.json"
)
LOCAL_R1_V2_PROFILE = (
    Path(__file__).resolve().parents[2]
    / "research/05_evaluation/profiles/student-tutor-r1-local-candidate-v2.json"
)
LOCAL_R1_RESULT = (
    Path(__file__).resolve().parents[2]
    / "research/05_evaluation/records/autonomous-tutoring-r1-confirmation-002.json"
)


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


def test_staging_configuration_cannot_exceed_proxy_upload_cap(tmp_path):
    with pytest.raises(ValueError, match="proxy 64 MiB cap"):
        AppSettings(
            mode=RuntimeMode.STAGING,
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=(ORIGIN,),
            secure_cookies=True,
            max_upload_bytes=65 * 1024 * 1024,
        ).validate()


def test_conservative_local_release_gate_is_explicit_and_deterministic() -> None:
    settings = AppSettings(
        evidence_gate_mode=EvidenceGateMode.STRUCTURED_LEXICAL_V1,
    )

    gate = _configured_evidence_gate(settings)

    assert isinstance(gate, StructuredLexicalCoverageEvidenceGate)
    assert gate.minimum_content_matching_terms == 2
    assert gate.evidence_limit == 3


def test_unselected_evidence_gate_remains_fail_closed() -> None:
    assert _configured_evidence_gate(AppSettings()) is None


def test_ambiguity_safe_gate_is_available_without_selecting_it_by_default() -> None:
    settings = AppSettings(
        evidence_gate_mode=(
            EvidenceGateMode.AMBIGUITY_SAFE_STRUCTURED_LEXICAL_V1
        ),
    )

    gate = _configured_evidence_gate(settings)

    assert isinstance(gate, AmbiguitySafeEvidenceGateV1)
    assert isinstance(gate.base, StructuredLexicalCoverageEvidenceGate)


def test_question_targeted_ambiguity_safe_gate_is_explicit() -> None:
    gate = _configured_evidence_gate(
        AppSettings(
            evidence_gate_mode=EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2
        )
    )

    assert isinstance(gate, AmbiguitySafeEvidenceGateV1)
    assert isinstance(gate.base, QuestionTargetedAtomicEvidenceGate)
    assert isinstance(gate.base.base_gate, StructuredLexicalCoverageEvidenceGate)


def test_staging_configuration_rejects_unselected_t1_graph(tmp_path):
    with pytest.raises(ValueError, match="T1_QUALIFICATION_RESULT_PATH"):
        AppSettings(
            mode=RuntimeMode.STAGING,
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=(ORIGIN,),
            secure_cookies=True,
            student_tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
        ).validate()


def test_staging_configuration_accepts_hash_bound_t1_qualification(tmp_path):
    core = {
        "instrument_id": "autonomous-tutoring-r1-confirmation-001",
        "status": "completed-keep",
        "decision": "Keep",
        "hard_gates_passed": True,
        "t0_rollback_available": True,
        "selected_implementation_id": "deterministic-bounded-tutoring-graph-t1",
        "selected_model": "gpt-5.4-mini-2026-03-17",
        "profile_sha256": hashlib.sha256(CANDIDATE_PROFILE.read_bytes()).hexdigest(),
    }
    result = {
        **core,
        "content_sha256": hashlib.sha256(
            json.dumps(
                core,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest(),
    }
    result_path = tmp_path / "t1-result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")

    AppSettings(
        mode=RuntimeMode.STAGING,
        database_path=tmp_path / "db.sqlite3",
        data_root=tmp_path,
        allowed_origins=(ORIGIN,),
        secure_cookies=True,
        student_tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
        learning_gap_hmac_secret=b"x" * 32,
        student_profile_path=CANDIDATE_PROFILE,
        t1_qualification_result_path=result_path,
    ).validate()


def test_staging_configuration_accepts_immutable_local_t1_v1_qualification(tmp_path):
    result_path = tmp_path / "local-t1-result.json"
    result_path.write_bytes(LOCAL_R1_RESULT.read_bytes())

    AppSettings(
        mode=RuntimeMode.STAGING,
        database_path=tmp_path / "db.sqlite3",
        data_root=tmp_path,
        allowed_origins=(ORIGIN,),
        secure_cookies=True,
        student_tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
        learning_gap_hmac_secret=b"x" * 32,
        student_profile_path=LOCAL_R1_PROFILE,
        t1_qualification_result_path=result_path,
    ).validate()


def test_staging_configuration_rejects_v1_evidence_for_v2_profile(tmp_path):
    result_path = tmp_path / "local-t1-result.json"
    result_path.write_bytes(LOCAL_R1_RESULT.read_bytes())

    with pytest.raises(ValueError, match="does not bind this release"):
        AppSettings(
            mode=RuntimeMode.STAGING,
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=(ORIGIN,),
            secure_cookies=True,
            student_tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
            learning_gap_hmac_secret=b"x" * 32,
            student_profile_path=LOCAL_R1_V2_PROFILE,
            t1_qualification_result_path=result_path,
        ).validate()


def test_staging_configuration_rejects_t1_v1_evidence_for_governed_v2(tmp_path):
    result_path = tmp_path / "local-t1-result.json"
    result_path.write_bytes(LOCAL_R1_RESULT.read_bytes())

    with pytest.raises(ValueError, match="does not bind this release"):
        AppSettings(
            mode=RuntimeMode.STAGING,
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=(ORIGIN,),
            secure_cookies=True,
            student_tutoring_mode=(
                StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
            ),
            learning_gap_hmac_secret=b"x" * 32,
            student_profile_path=LOCAL_R1_PROFILE,
            t1_qualification_result_path=result_path,
        ).validate()


def test_governed_qualification_binds_planner_gate_and_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    source = (
        Path(__file__).resolve().parents[2]
        / "research/05_evaluation/records/governed-full-autonomy-v2-1-confirmation-001.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    selected = next(
        candidate
        for candidate in payload["candidates"]
        if candidate["role"] == "candidate"
    )
    selected["implementation"]["configuration"]["evidence_gate"] = (
        EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2.value
    )
    result_path = tmp_path / "governed-result.json"
    result_path.write_text(json.dumps(payload), encoding="utf-8")

    AppSettings(
        mode=RuntimeMode.STAGING,
        database_path=tmp_path / "db.sqlite3",
        data_root=tmp_path,
        allowed_origins=(ORIGIN,),
        secure_cookies=True,
        generator_mode=GeneratorMode.DETERMINISTIC,
        evidence_gate_mode=EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2,
        student_tutoring_mode=(
            StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
        ),
        autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_TERRA,
        learning_gap_hmac_secret=b"x" * 32,
        student_profile_path=LOCAL_R1_V2_PROFILE,
        t1_qualification_result_path=result_path,
    ).validate()

    selected["implementation"]["configuration"]["evidence_gate"] = (
        EvidenceGateMode.STRUCTURED_LEXICAL_V1.value
    )
    result_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind this release"):
        AppSettings(
            mode=RuntimeMode.STAGING,
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=(ORIGIN,),
            secure_cookies=True,
            generator_mode=GeneratorMode.DETERMINISTIC,
            evidence_gate_mode=(
                EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2
            ),
            student_tutoring_mode=(
                StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
            ),
            autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_TERRA,
            learning_gap_hmac_secret=b"x" * 32,
            student_profile_path=LOCAL_R1_V2_PROFILE,
            t1_qualification_result_path=result_path,
        ).validate()


def test_governed_deterministic_generator_requires_compatible_gate(tmp_path):
    with pytest.raises(ValueError, match="question-targeted-ambiguity-safe-v2"):
        AppSettings(
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            generator_mode=GeneratorMode.DETERMINISTIC,
            evidence_gate_mode=EvidenceGateMode.STRUCTURED_LEXICAL_V1,
            student_tutoring_mode=(
                StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
            ),
        ).validate()


@pytest.mark.parametrize(
    "origin",
    (
        "https://user:secret@example.test",
        "https://example.test/path",
        "https://example.test/",
        "https://example.test?query=1",
    ),
)
def test_configuration_rejects_non_origin_cors_values(tmp_path, origin):
    with pytest.raises(ValueError, match=r"plain HTTP\(S\) origins"):
        AppSettings(
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=(origin,),
        ).validate()


def test_configuration_rejects_nonfinite_or_boolean_direct_limits(tmp_path):
    with pytest.raises(ValueError, match="COST"):
        AppSettings(
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            provider_cost_cap_usd=float("nan"),
        ).validate()
    with pytest.raises(ValueError, match="integer limits"):
        AppSettings(
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            max_upload_bytes=True,
        ).validate()


def test_live_generator_configuration_requires_environment_credential(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        AppSettings(
            mode=RuntimeMode.STAGING,
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            allowed_origins=(ORIGIN,),
            secure_cookies=True,
            generator_mode="openai-gpt-5.4-mini",
            student_profile_path=CANDIDATE_PROFILE,
        ).validate()


def test_t0_rollback_ignores_inactive_openai_autonomy_planner(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    AppSettings(
        mode=RuntimeMode.STAGING,
        database_path=tmp_path / "db.sqlite3",
        data_root=tmp_path,
        allowed_origins=(ORIGIN,),
        secure_cookies=True,
        student_tutoring_mode=StudentTutoringMode.GROUNDED_ASSISTANT,
        autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_TERRA,
        student_profile_path=CANDIDATE_PROFILE,
    ).validate()


def test_historical_deepseek_runtime_mode_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="historical"):
        AppSettings(
            database_path=tmp_path / "db.sqlite3",
            data_root=tmp_path,
            generator_mode=GeneratorMode.DEEPSEEK_V4_FLASH,
        ).validate()


def test_live_generator_is_bound_to_openai_snapshot_and_responses_api():
    profile = load_release_profile(CANDIDATE_PROFILE)
    settings = AppSettings(
        generator_mode=GeneratorMode.OPENAI_GPT_5_4_MINI,
        student_profile_path=CANDIDATE_PROFILE,
    )

    generator, budget = _configured_generator(settings, profile)

    assert generator.client is budget
    assert budget.client.model == "gpt-5.4-mini-2026-03-17"
    assert budget.client.API_URL == "https://api.openai.com/v1/responses"

    payload = profile.model_dump(mode="json")
    component = next(
        entry
        for entry in payload["components"]
        if entry["component"] == ComponentKind.GENERATOR
    )
    component["implementation"]["configuration"]["reasoning_effort"] = "high"
    drifted = SystemReleaseProfile.model_validate(payload)

    with pytest.raises(ValueError, match="reasoning effort is unsupported"):
        _configured_generator(settings, drifted)


def test_governed_runtime_binds_planner_and_generator_identities(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    app = create_app(
        settings=AppSettings(
            generator_mode=GeneratorMode.OPENAI_GPT_5_4_MINI,
            evidence_gate_mode=EvidenceGateMode.STRUCTURED_LEXICAL_V1,
            learning_gap_hmac_secret=b"x" * 32,
            student_profile_path=CANDIDATE_PROFILE,
            student_tutoring_mode=(
                StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
            ),
            autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_TERRA,
        )
    )

    graph = app.state.governed_autonomy_service.graph
    tutoring = app.state.student_service
    assert graph.planner.model_id == "gpt-5.6-terra"
    assert graph.planner.client.client.model == "gpt-5.6-terra"
    assert graph.generator.model_id == "gpt-5.4-mini-2026-03-17"
    assert tutoring.autonomy_planner_model == graph.planner.model_id
    assert tutoring.autonomy_generator_model == graph.generator.model_id
    assert isinstance(graph.generator.claim_validator.verifier, ContiguousQuoteAtomicClaimVerifier)


def test_governed_runtime_decouples_live_planning_from_safe_generation(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    app = create_app(
        settings=AppSettings(
            generator_mode=GeneratorMode.DETERMINISTIC,
            evidence_gate_mode=EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2,
            learning_gap_hmac_secret=b"x" * 32,
            student_profile_path=LOCAL_R1_PROFILE,
            student_tutoring_mode=(
                StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
            ),
            autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_TERRA,
        )
    )

    graph = app.state.governed_autonomy_service.graph
    assert graph.planner.model_id == "gpt-5.6-terra"
    assert graph.generator.model_id == "deterministic/evidence-set-v2"
    assert graph.generator.generator.policy_enforcer.action_router.implementation_id == (
        "deterministic-tutor-action-router-v2"
    )
    assert app.state.provider_budget is None


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

    onboarding = create_session("staging-release-session")
    onboarding.owner_account_id = fixture.professor_id
    onboarding.course_id = fixture.course_a_id
    onboarding.current_step = "professor_approval"
    onboarding.policy = approved_synthetic_policy()
    client.app.state.session_repository.save(onboarding)
    release = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers={"Origin": ORIGIN},
        json={
            "session_id": onboarding.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "ingestion_job_ids": [completed.id],
            "chunks": [],
        },
    )
    assert release.status_code == 201
    assert release.json()["chunks"] == [
        chunk.model_dump(mode="json") for chunk in completed.result.chunks
    ]

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


def test_staging_streamed_upload_is_bounded_without_content_length(tmp_path):
    client, _, _, _, fixture, _ = _client(tmp_path, max_upload_bytes=8)
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 200
    )

    response = client.put(
        f"/api/professor/courses/{fixture.course_a_id}/sources/lecture-large",
        params={"title": "Large lecture"},
        headers={
            "Origin": ORIGIN,
            "Content-Type": "application/pdf",
            "Idempotency-Key": "streamed-large-upload",
            "Transfer-Encoding": "chunked",
        },
        content=(part for part in (b"%PDF-", b"too-large")),
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "source_too_large"
    assert client.app.state.ingestion_job_repository.list_for_course(
        fixture.professor_id, fixture.course_a_id
    ) == []


def test_staging_release_rejects_browser_supplied_chunks(tmp_path):
    client, students, _, _, fixture, _ = _client(tmp_path)
    assert (
        _login(client, "professor@example.test", PROFESSOR_PASSWORD).status_code == 200
    )
    onboarding = create_session("staging-untrusted-chunks")
    onboarding.owner_account_id = fixture.professor_id
    onboarding.course_id = fixture.course_a_id
    onboarding.current_step = "professor_approval"
    onboarding.policy = approved_synthetic_policy()
    client.app.state.session_repository.save(onboarding)
    existing = students.get_release(fixture.release_a_id)
    assert existing is not None

    response = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers={"Origin": ORIGIN},
        json={
            "session_id": onboarding.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "chunks": [chunk.model_dump(mode="json") for chunk in existing.chunks],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "server_bound_sources_required"


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
    client.app.state.autonomy_planner_budget = type(
        "PlannerBudget",
        (),
        {"snapshot": lambda self: {"calls": 2, "reported_cost_usd": 0.25}},
    )()
    assert _login(client, "admin@example.test", ADMIN_PASSWORD).status_code == 200
    metrics = client.get("/api/operations/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["request_count"] >= 4
    assert "latency_p95_ms" in metrics.json()
    assert metrics.json()["autonomy_planner_budget"] == {
        "calls": 2,
        "reported_cost_usd": 0.25,
    }


def test_readiness_reports_closed_durable_dependency_as_unavailable(tmp_path):
    client, _, identities, *_ = _client(tmp_path)
    identities.close()

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["checks"]["identity_database"] is False
