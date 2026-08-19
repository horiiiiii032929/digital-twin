"""Run the network-free staging-foundation acceptance and capacity journey."""

from __future__ import annotations

import argparse
import json
import platform
import resource
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import pymupdf
from fastapi.testclient import TestClient

from services.api.app.config import AppSettings, RuntimeMode
from services.api.app.factory import create_app
from services.operations import create_runtime_backup, restore_runtime_backup
from src.digital_twin.student import (
    AccountRole,
    SQLiteStudentRepository,
    seed_synthetic_student_workflow,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "deployable-product-foundation-v1-development-001"
ORIGIN = "https://staging.example.test"
ADMIN_PASSWORD = "Admin-synthetic-password-42"
PROFESSOR_PASSWORD = "Professor-synthetic-password-42"
STUDENT_PASSWORD = "Student-synthetic-password-42"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(ROOT / "reports/generated" / RUN_ID / "result.json"),
    )
    args = parser.parse_args()
    result = run_acceptance()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        f"{result['decision'].upper()}: {result['passed_checks']}/"
        f"{result['total_checks']} gates passed; result written to {args.output}"
    )
    if result["decision"] == "refine":
        raise SystemExit(1)


def run_acceptance() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    metrics: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="digital-twin-foundation-") as temporary:
        root = Path(temporary)
        runtime_root = root / "primary-runtime"
        settings = _settings(runtime_root)
        app = create_app(settings=settings)
        client = TestClient(app, base_url="https://testserver")
        try:
            accounts = _provision_and_login(client, app, checks)
            workflow = _professor_workflow(client, app, root, accounts, checks, metrics)
            _student_workflow(client, accounts, workflow, checks)
            metrics.update(_capacity(client, checks))
            _record(
                checks,
                "provider-cost-control",
                app.state.provider_budget is None,
                "Deterministic staging run made zero external calls and cost USD 0.",
            )
        except Exception as error:
            failures.append({"class": "acceptance", "error_type": type(error).__name__})
        finally:
            client.close()
            _close_app(app)

        if not failures:
            try:
                _restart_verification(settings, accounts, workflow, checks)
                backup_metrics = _backup_restore_verification(
                    root, settings, accounts, workflow, checks
                )
                metrics.update(backup_metrics)
                _demo_rollback_verification(root, checks)
            except Exception as error:
                failures.append(
                    {"class": "recovery", "error_type": type(error).__name__}
                )

        metrics["database_bytes"] = (
            settings.database_path.stat().st_size
            if settings.database_path.exists()
            else 0
        )
        metrics["runtime_data_bytes"] = _tree_bytes(settings.data_root)
        metrics["peak_rss_bytes"] = _peak_rss_bytes()
        metrics["peak_rss_gate_bytes"] = 4 * 1024**3
        _record(
            checks,
            "memory-envelope",
            metrics["peak_rss_bytes"] < metrics["peak_rss_gate_bytes"],
            f"Peak RSS {metrics['peak_rss_bytes']} bytes.",
        )

    failed_checks = [check for check in checks if not check["passed"]]
    local_pass = not failures and not failed_checks
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "candidate_id": "A1-single-node-staging",
        "baseline_id": "A0-local-demo",
        "dataset": "synthetic-deployable-foundation-v1",
        "split": "development",
        "network_calls": 0,
        "private_data_used": False,
        "code_revision": _git_value("rev-parse", "HEAD"),
        "working_tree_dirty": bool(_git_value("status", "--porcelain")),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "checks": checks,
        "total_checks": len(checks),
        "passed_checks": sum(check["passed"] for check in checks),
        "failures": [*failures, *failed_checks],
        "metrics": metrics,
        "external_https_rehearsal": "pending-host-and-domain",
        "decision": "go-deeper" if local_pass else "refine",
        "decision_reason": (
            "All local hard gates passed; public DNS/certificate issuance remains."
            if local_pass
            else "One or more frozen local gates failed."
        ),
    }


def _provision_and_login(client, app, checks):
    identities = app.state.identity_service
    admin = identities.provision_account(
        account_id="admin-foundation",
        email="admin@foundation.example",
        display_name="Foundation Admin",
        role=AccountRole.ADMIN,
        password=ADMIN_PASSWORD,
    )
    response = _login(client, admin.email, ADMIN_PASSWORD)
    _expect(response, 200, "admin-credential-login", checks)
    professor = _expect_json(
        client.post(
            "/api/admin/accounts",
            headers={"Origin": ORIGIN},
            json={
                "email": "professor@foundation.example",
                "display_name": "Foundation Professor",
                "role": "professor",
                "temporary_password": PROFESSOR_PASSWORD,
            },
        ),
        201,
        "admin-invites-professor",
        checks,
    )
    student = _expect_json(
        client.post(
            "/api/admin/accounts",
            headers={"Origin": ORIGIN},
            json={
                "email": "student@foundation.example",
                "display_name": "Foundation Student",
                "role": "student",
                "temporary_password": STUDENT_PASSWORD,
            },
        ),
        201,
        "admin-invites-student",
        checks,
    )
    _expect(
        client.post("/api/auth/logout", headers={"Origin": ORIGIN}),
        204,
        "admin-session-revoked",
        checks,
    )
    _expect(
        _login(client, professor["email"], PROFESSOR_PASSWORD),
        200,
        "professor-credential-login",
        checks,
    )
    rejected = client.get(
        "/api/student/courses", headers={"X-Account-ID": student["account_id"]}
    )
    _record(
        checks,
        "synthetic-header-rejected",
        rejected.status_code == 401
        and rejected.json()["detail"]["code"] == "synthetic_identity_disabled",
    )
    return {"admin": admin.model_dump(), "professor": professor, "student": student}


def _professor_workflow(client, app, root, accounts, checks, metrics):
    course = _expect_json(
        client.post(
            "/api/professor/courses",
            headers={"Origin": ORIGIN},
            json={
                "title": "Synthetic Network Security",
                "course_id": "course-foundation",
            },
        ),
        201,
        "professor-creates-course",
        checks,
    )
    _expect(
        client.post(
            f"/api/professor/courses/{course['id']}/students",
            headers={"Origin": ORIGIN},
            json={"student_account_id": accounts["student"]["account_id"]},
        ),
        201,
        "professor-assigns-student",
        checks,
    )
    session = _expect_json(
        client.post(
            "/api/onboarding/sessions/supervisor-demo",
            headers={"Origin": ORIGIN},
        ),
        201,
        "professor-onboarding-persists",
        checks,
    )
    session = _approve_session(client, session)
    _record(
        checks,
        "professor-policy-approved",
        session["policy"]["release_status"] == "approved",
    )

    pdf_path = root / "synthetic-lecture.pdf"
    _write_synthetic_pdf(pdf_path)
    started = time.perf_counter()
    queued = _expect_json(
        client.put(
            f"/api/professor/courses/{course['id']}/sources/lecture-01",
            params={"title": "Synthetic Lecture 01", "display_allowed": True},
            headers={
                "Origin": ORIGIN,
                "Content-Type": "application/pdf",
                "Idempotency-Key": "foundation-upload-1",
            },
            content=pdf_path.read_bytes(),
        ),
        202,
        "source-upload-queued",
        checks,
    )
    duplicate = client.put(
        f"/api/professor/courses/{course['id']}/sources/lecture-01",
        params={"title": "Synthetic Lecture 01", "display_allowed": True},
        headers={
            "Origin": ORIGIN,
            "Content-Type": "application/pdf",
            "Idempotency-Key": "foundation-upload-1",
        },
        content=pdf_path.read_bytes(),
    )
    _record(
        checks,
        "source-upload-idempotent",
        duplicate.status_code == 202 and duplicate.json()["id"] == queued["id"],
    )
    completed = app.state.ingestion_job_service.process_one("foundation-worker")
    ingestion_ms = (time.perf_counter() - started) * 1000
    if completed is None:
        raise RuntimeError("worker did not claim the queued source")
    job = _expect_json(
        client.get(f"/api/professor/ingestion-jobs/{queued['id']}"),
        200,
        "worker-completes-ingestion",
        checks,
    )
    _record(checks, "source-lineage-preserved", bool(job["result"]["chunks"]))
    metrics["ingestion_queue_to_complete_ms"] = round(ingestion_ms, 3)
    metrics["ingestion_gate_ms"] = 10_000
    _record(checks, "ingestion-latency", ingestion_ms <= 10_000)

    release = _expect_json(
        client.post(
            f"/api/professor/courses/{course['id']}/releases",
            headers={"Origin": ORIGIN},
            json={
                "session_id": session["session_id"],
                "profile_id": "student-tutor",
                "profile_version": "v1",
                "release_id": "release-foundation-v1",
                "chunks": job["result"]["chunks"],
            },
        ),
        201,
        "release-draft-created",
        checks,
    )
    preflight = _expect_json(
        client.post(
            f"/api/professor/releases/{release['id']}/preflight",
            headers={"Origin": ORIGIN},
        ),
        200,
        "release-preflight-runs",
        checks,
    )
    _record(
        checks,
        "release-preflight-passes",
        preflight["passed"] and all(item["passed"] for item in preflight["checks"]),
    )
    published = _expect_json(
        client.post(
            f"/api/professor/releases/{release['id']}/publish",
            headers={"Origin": ORIGIN},
        ),
        200,
        "evaluated-release-published",
        checks,
    )
    _record(checks, "release-is-published", published["status"] == "published")
    _expect(
        client.post("/api/auth/logout", headers={"Origin": ORIGIN}),
        204,
        "professor-session-revoked",
        checks,
    )
    return {
        "course_id": course["id"],
        "session_id": session["session_id"],
        "job_id": queued["id"],
        "release_id": release["id"],
    }


def _student_workflow(client, accounts, workflow, checks):
    _expect(
        _login(client, accounts["student"]["email"], STUDENT_PASSWORD),
        200,
        "student-credential-login",
        checks,
    )
    courses = _expect_json(
        client.get("/api/student/courses"), 200, "student-sees-assigned-course", checks
    )
    _record(
        checks,
        "course-isolation",
        [course["course_id"] for course in courses] == [workflow["course_id"]],
    )
    conversation = _expect_json(
        client.post(
            f"/api/student/courses/{workflow['course_id']}/conversations",
            headers={"Origin": ORIGIN},
        ),
        201,
        "student-creates-conversation",
        checks,
    )
    turn = _expect_json(
        client.post(
            f"/api/student/conversations/{conversation['id']}/messages",
            headers={"Origin": ORIGIN},
            json={
                "content": "What does CSRF abuse?",
                "request_id": "foundation-turn-1",
            },
        ),
        200,
        "student-receives-grounded-answer",
        checks,
    )
    citations = turn["citations"]
    _record(checks, "answer-has-source-citation", len(citations) >= 1)
    citation = citations[0]
    _record(
        checks,
        "citation-has-original-region-lineage",
        bool(citation.get("source_checksum"))
        and citation.get("page") is not None
        and citation.get("bounding_box") is not None,
    )
    crop = client.get(
        f"/api/student/messages/{turn['tutor_message']['id']}/citations/"
        f"{citation['id']}/crop"
    )
    _record(
        checks,
        "authorized-citation-crop",
        crop.status_code == 200 and crop.headers["content-type"].startswith("image/"),
    )
    workflow["conversation_id"] = conversation["id"]
    workflow["tutor_message_id"] = turn["tutor_message"]["id"]
    workflow["citation_id"] = citation["id"]


def _capacity(client, checks):
    durations = []
    errors = 0
    started = time.perf_counter()
    for _ in range(100):
        request_started = time.perf_counter()
        response = client.get("/api/student/courses")
        durations.append((time.perf_counter() - request_started) * 1000)
        errors += int(response.status_code != 200)
    elapsed = time.perf_counter() - started
    p50 = _percentile(durations, 0.50)
    p95 = _percentile(durations, 0.95)
    _record(checks, "capacity-error-rate", errors == 0)
    _record(checks, "capacity-api-p95", p95 <= 750)
    return {
        "capacity_requests": 100,
        "capacity_errors": errors,
        "capacity_error_rate": errors / 100,
        "api_latency_p50_ms": round(p50, 3),
        "api_latency_p95_ms": round(p95, 3),
        "api_latency_gate_ms": 750,
        "throughput_requests_per_second": round(100 / elapsed, 3),
        "external_generation_included": False,
        "external_provider_cost_usd": 0.0,
    }


def _restart_verification(settings, accounts, workflow, checks):
    app = create_app(settings=settings)
    client = TestClient(app, base_url="https://testserver")
    try:
        _expect(
            _login(client, accounts["student"]["email"], STUDENT_PASSWORD),
            200,
            "restart-student-login",
            checks,
        )
        restored = client.get(
            f"/api/student/conversations/{workflow['conversation_id']}"
        )
        _record(
            checks,
            "restart-state-durability",
            restored.status_code == 200 and len(restored.json()["messages"]) == 2,
        )
        citations = client.get(
            f"/api/student/messages/{workflow['tutor_message_id']}/citations"
        )
        _record(
            checks,
            "restart-citation-durability",
            citations.status_code == 200
            and citations.json()[0]["id"] == workflow["citation_id"],
        )
        _record(
            checks,
            "restart-object-durability",
            bool(app.state.object_store.iter_keys()),
        )
    finally:
        client.close()
        _close_app(app)


def _backup_restore_verification(root, settings, accounts, workflow, checks):
    archive = root / "off-host" / "runtime-backup.zip"
    started = time.perf_counter()
    manifest = create_runtime_backup(
        settings.database_path, settings.data_root, archive
    )
    backup_ms = (time.perf_counter() - started) * 1000
    restored_root = root / "restored-runtime"
    restored_database = restored_root / "digital-twin.sqlite3"
    started = time.perf_counter()
    restored = restore_runtime_backup(archive, restored_database, restored_root)
    restore_ms = (time.perf_counter() - started) * 1000
    _record(
        checks,
        "backup-restore-checksums",
        manifest.model_dump() == restored.model_dump(),
    )
    restored_settings = _settings(restored_root)
    app = create_app(settings=restored_settings)
    client = TestClient(app, base_url="https://testserver")
    try:
        _expect(
            _login(client, accounts["student"]["email"], STUDENT_PASSWORD),
            200,
            "restored-credential-login",
            checks,
        )
        response = client.get(
            f"/api/student/conversations/{workflow['conversation_id']}"
        )
        _record(
            checks,
            "clean-restore-workflow-state",
            response.status_code == 200 and len(response.json()["messages"]) == 2,
        )
    finally:
        client.close()
        _close_app(app)
    return {
        "backup_duration_ms": round(backup_ms, 3),
        "restore_duration_ms": round(restore_ms, 3),
        "backup_bytes": archive.stat().st_size,
        "backup_schema_version": manifest.schema_version,
        "backup_data_files": len(manifest.data_files),
    }


def _demo_rollback_verification(root, checks):
    database = root / "demo" / "demo.sqlite3"
    students = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(students)
    settings = AppSettings(
        mode=RuntimeMode.DEMO,
        database_path=database,
        data_root=root / "demo-data",
        allowed_origins=("http://localhost:5173",),
        secure_cookies=False,
    )
    app = create_app(student_repository=students, settings=settings)
    client = TestClient(app)
    try:
        response = client.get(
            "/api/student/courses",
            headers={"X-Account-ID": fixture.student_a_id},
        )
        _record(
            checks,
            "a0-demo-rollback",
            response.status_code == 200 and len(response.json()) == 1,
        )
    finally:
        client.close()
        _close_app(app)


def _approve_session(client, session):
    session_id = session["session_id"]
    policy_fields = [
        field
        for group in ("safety_compliance", "pedagogy", "professor_review")
        for field in session["policy"][group]
    ]
    by_id = {field["id"]: field for field in policy_fields}
    for field_id in list(session["release_blockers"]["policy_fields"]):
        field = by_id[field_id]
        value = field["value"]
        if field_id == "professor_release_approval":
            value = "Approved for the synthetic foundation verification."
        response = client.patch(
            f"/api/onboarding/sessions/{session_id}/policy-fields/{field_id}",
            headers={"Origin": ORIGIN},
            json={"value": value, "status": "resolved"},
        )
        if response.status_code != 200:
            raise RuntimeError("could not resolve synthetic policy field")
        session = response.json()
    for preview in list(session["preview_cases"]):
        response = client.patch(
            f"/api/onboarding/sessions/{session_id}/preview-cases/{preview['id']}/decision",
            headers={"Origin": ORIGIN},
            json={"decision": "accepted", "reason": "Synthetic verification."},
        )
        if response.status_code != 200:
            raise RuntimeError("could not accept synthetic preview")
        session = response.json()
    response = client.post(
        f"/api/onboarding/sessions/{session_id}/preview-cases",
        headers={"Origin": ORIGIN},
        json={
            "prompt": "Explain the approved CSRF course concept in one sentence.",
            "tag": "teaching_behavior",
        },
    )
    if response.status_code != 200:
        raise RuntimeError("could not add synthetic custom preview")
    session = response.json()
    custom = session["preview_cases"][-1]
    response = client.patch(
        f"/api/onboarding/sessions/{session_id}/preview-cases/{custom['id']}/decision",
        headers={"Origin": ORIGIN},
        json={"decision": "accepted", "reason": "Synthetic verification."},
    )
    if response.status_code != 200:
        raise RuntimeError("could not accept synthetic custom preview")
    session = response.json()
    for item in list(session["approval_checklist"]):
        response = client.patch(
            f"/api/onboarding/sessions/{session_id}/approval-checklist/{item['id']}",
            headers={"Origin": ORIGIN},
            json={"checked": True},
        )
        if response.status_code != 200:
            raise RuntimeError("could not complete synthetic approval checklist")
        session = response.json()
    return session


def _write_synthetic_pdf(path):
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "Synthetic network security course notes")
    page.insert_text((72, 110), "CSRF abuses an authenticated browser session.")
    page.draw_rect(pymupdf.Rect(72, 150, 216, 246), color=(0.2, 0.2, 0.2))
    page.insert_text((72, 270), "Figure 1: Synthetic authenticated request flow")
    document.save(path, no_new_id=True)
    document.close()


def _settings(data_root):
    return AppSettings(
        mode=RuntimeMode.STAGING,
        database_path=data_root / "digital-twin.sqlite3",
        data_root=data_root,
        allowed_origins=(ORIGIN,),
        secure_cookies=True,
        session_ttl_seconds=3_600,
        login_attempts_per_minute=100,
        authenticated_requests_per_minute=1_000,
    )


def _login(client, email, password):
    return client.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )


def _expect(response, status_code, name, checks):
    passed = response.status_code == status_code
    _record(
        checks, name, passed, f"HTTP {response.status_code}; expected {status_code}."
    )
    if not passed:
        raise RuntimeError(f"{name} failed with HTTP {response.status_code}")
    return response


def _expect_json(response, status_code, name, checks):
    return _expect(response, status_code, name, checks).json()


def _record(checks, name, passed, detail=""):
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def _percentile(values, quantile):
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def _tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _peak_rss_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if platform.system() == "Darwin" else value * 1024)


def _close_app(app):
    closed: set[int] = set()
    for name in (
        "ingestion_job_repository",
        "identity_repository",
        "student_repository",
        "session_repository",
    ):
        repository = getattr(app.state, name, None)
        close = getattr(repository, "close", None)
        if close is not None and id(repository) not in closed:
            close()
            closed.add(id(repository))


def _git_value(*arguments):
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":
    main()
