"""Verify the credentialed Course Digital Twin journey through live HTTPS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import ssl
import tempfile
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pymupdf


PASSWORD_ENV = {
    "admin": "STAGING_ADMIN_PASSWORD",
    "professor": "STAGING_PROFESSOR_PASSWORD",
    "student": "STAGING_STUDENT_PASSWORD",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--ca-file", type=Path)
    parser.add_argument("--admin-email", default="admin@foundation.local")
    parser.add_argument("--profile-id", default="student-tutor-r1-local-candidate")
    parser.add_argument("--profile-version", default="v1")
    parser.add_argument(
        "--expected-tutoring-mode",
        default="bounded-tutoring-graph",
        choices=("grounded-assistant", "bounded-tutoring-graph"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--resume",
        type=Path,
        help="Verify a previous workflow after restart or clean restore.",
    )
    parser.add_argument(
        "--mode-check",
        action="store_true",
        help="Create one new grounded turn and verify the selected tutoring mode.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    args = parser.parse_args()

    base_url, origin = _validate_https_url(args.base_url)
    passwords = _passwords_from_env()
    context = ssl.create_default_context(
        cafile=str(args.ca_file) if args.ca_file is not None else None
    )
    with httpx.Client(
        base_url=base_url,
        verify=context,
        timeout=30.0,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        if args.resume is not None:
            result = (
                verify_tutoring_mode(
                    client,
                    args.resume,
                    passwords["student"],
                    expected_tutoring_mode=args.expected_tutoring_mode,
                    origin=origin,
                )
                if args.mode_check
                else verify_resume(client, args.resume, passwords["student"])
            )
        else:
            if args.output is None:
                parser.error("--output is required for a new staging journey")
            result = run_journey(
                client,
                origin=origin,
                admin_email=args.admin_email,
                passwords=passwords,
                timeout_seconds=args.timeout_seconds,
                profile_id=args.profile_id,
                profile_version=args.profile_version,
                expected_tutoring_mode=args.expected_tutoring_mode,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    print(
        f"PASSED: {result['passed_checks']}/{result['total_checks']} live HTTPS "
        f"checks ({result['mode']})."
    )


def run_journey(
    client: httpx.Client,
    *,
    origin: str,
    admin_email: str,
    passwords: dict[str, str],
    timeout_seconds: float,
    profile_id: str,
    profile_version: str,
    expected_tutoring_mode: str,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    run_token = uuid4().hex[:10]
    started_at = time.time()

    readiness = _expect_json(client.get("/api/health/ready"), 200)
    _record(
        checks,
        "https-readiness",
        readiness.get("status") == "ready"
        and bool(readiness.get("checks"))
        and all(readiness["checks"].values()),
    )

    admin_response = _login(client, admin_email, passwords["admin"])
    _expect_status(admin_response, 200)
    _record(checks, "admin-credential-login", True)
    cookie = admin_response.headers.get("set-cookie", "").lower()
    _record(
        checks,
        "secure-session-cookie",
        all(flag in cookie for flag in ("secure", "httponly", "samesite=strict")),
    )
    professor_email = f"professor-{run_token}@foundation.local"
    student_email = f"student-{run_token}@foundation.local"
    professor = _expect_json(
        client.post(
            "/api/admin/accounts",
            headers={"Origin": origin},
            json={
                "email": professor_email,
                "display_name": "HTTPS Rehearsal Professor",
                "role": "professor",
                "temporary_password": passwords["professor"],
            },
        ),
        201,
    )
    student = _expect_json(
        client.post(
            "/api/admin/accounts",
            headers={"Origin": origin},
            json={
                "email": student_email,
                "display_name": "HTTPS Rehearsal Student",
                "role": "student",
                "temporary_password": passwords["student"],
            },
        ),
        201,
    )
    _record(checks, "invite-only-accounts", bool(professor and student))
    _expect_status(client.post("/api/auth/logout", headers={"Origin": origin}), 204)

    _expect_status(_login(client, professor_email, passwords["professor"]), 200)
    rejected_origin = client.post(
        "/api/professor/courses",
        headers={"Origin": "https://invalid-origin.example"},
        json={"title": "Rejected origin"},
    )
    _record(checks, "unsafe-origin-rejected", rejected_origin.status_code == 403)
    rejected_header = client.get(
        "/api/student/courses",
        headers={"X-Account-ID": student["account_id"]},
    )
    _record(
        checks,
        "synthetic-account-header-rejected",
        rejected_header.status_code == 401
        and rejected_header.json().get("detail", {}).get("code")
        == "synthetic_identity_disabled",
    )

    course_id = f"course-live-{run_token}"
    course = _expect_json(
        client.post(
            "/api/professor/courses",
            headers={"Origin": origin},
            json={"title": "Synthetic HTTPS Security", "course_id": course_id},
        ),
        201,
    )
    _expect_status(
        client.post(
            f"/api/professor/courses/{course['id']}/students",
            headers={"Origin": origin},
            json={"student_account_id": student["account_id"]},
        ),
        201,
    )
    _record(checks, "professor-course-and-membership", course["id"] == course_id)

    session = _expect_json(
        client.post(
            "/api/onboarding/sessions/supervisor-demo",
            headers={"Origin": origin},
        ),
        201,
    )
    session = _expect_json(
        client.post(
            f"/api/professor/courses/{course_id}/onboarding-sessions/"
            f"{session['session_id']}/bind",
            headers={"Origin": origin},
        ),
        200,
    )
    _record(
        checks,
        "professor-session-bound-to-course",
        session["course_id"] == course_id,
    )
    session = _approve_session(client, session, origin)
    _record(
        checks,
        "professor-policy-approved",
        session["policy"]["release_status"] == "approved",
    )
    teaching_profile = _expect_json(
        client.post(
            f"/api/professor/courses/{course_id}/teaching-profiles",
            headers={"Origin": origin},
            json={
                "tone": "Clear, encouraging, and concise",
                "depth": "balanced",
                "explanation_structure": [
                    "State the core concept",
                    "Connect it to approved evidence",
                    "Check the student's next step",
                ],
                "example_preferences": ["Use compact systems examples"],
                "misconception_handling": (
                    "Name the mismatch, point to evidence, and ask for a revision."
                ),
                "integrity_limits": (
                    "Do not complete graded work; request an attempt and give one hint."
                ),
                "help_ladder": [
                    "Ask what the student already understands",
                    "Give one evidence-linked hint",
                    "Explain the relevant source statement",
                ],
                "outreach_policy": (
                    "Only professor-scheduled, consented, private in-app messages."
                ),
            },
        ),
        201,
    )
    profile_preview = _expect_json(
        client.get(
            f"/api/professor/courses/{course_id}/teaching-profiles/"
            f"{teaching_profile['profile_id']}/preview"
        ),
        200,
    )
    teaching_profile = _expect_json(
        client.post(
            f"/api/professor/courses/{course_id}/teaching-profiles/"
            f"{teaching_profile['profile_id']}/approve",
            headers={"Origin": origin},
            json={"preview_sha256": profile_preview["preview_sha256"]},
        ),
        200,
    )
    _record(
        checks,
        "professor-teaching-profile-approved",
        teaching_profile["status"] == "approved"
        and len(profile_preview["cases"]) == 10,
    )

    with tempfile.TemporaryDirectory(prefix="digital-twin-https-") as temporary:
        pdf_path = Path(temporary) / "synthetic-lecture.pdf"
        _write_synthetic_pdf(pdf_path)
        queued_at = time.perf_counter()
        queued = _expect_json(
            client.put(
                f"/api/professor/courses/{course_id}/sources/lecture-01",
                params={"title": "Synthetic Lecture 01", "display_allowed": True},
                headers={
                    "Origin": origin,
                    "Content-Type": "application/pdf",
                    "Idempotency-Key": f"https-upload-{run_token}",
                },
                content=pdf_path.read_bytes(),
            ),
            202,
        )
        job = _wait_for_job(
            client,
            queued["id"],
            timeout_seconds=timeout_seconds,
        )
        ingestion_ms = (time.perf_counter() - queued_at) * 1000
    _record(
        checks,
        "asynchronous-ingestion-succeeded",
        job["status"] == "succeeded" and bool(job.get("result", {}).get("chunks")),
    )

    release_id = f"release-live-{run_token}"
    release = _expect_json(
        client.post(
            f"/api/professor/courses/{course_id}/releases",
            headers={"Origin": origin},
            json={
                "session_id": session["session_id"],
                "profile_id": profile_id,
                "profile_version": profile_version,
                "teaching_profile_id": teaching_profile["profile_id"],
                "release_id": release_id,
                "ingestion_job_ids": [queued["id"]],
            },
        ),
        201,
    )
    preflight = _expect_json(
        client.post(
            f"/api/professor/releases/{release['id']}/preflight",
            headers={"Origin": origin},
        ),
        200,
    )
    _record(
        checks,
        "deterministic-release-preflight",
        preflight["passed"] and all(item["passed"] for item in preflight["checks"]),
    )
    published = _expect_json(
        client.post(
            f"/api/professor/releases/{release['id']}/publish",
            headers={"Origin": origin},
        ),
        200,
    )
    _record(checks, "evaluated-release-published", published["status"] == "published")
    _expect_status(client.post("/api/auth/logout", headers={"Origin": origin}), 204)

    _expect_status(_login(client, student_email, passwords["student"]), 200)
    now = datetime.now(UTC)
    preference = _expect_json(
        client.put(
            f"/api/student/courses/{course_id}/outreach-preferences/in-app",
            headers={"Origin": origin},
            json={
                "enabled": True,
                "timezone": "UTC",
                "quiet_hours_start": (now + timedelta(hours=1)).strftime("%H:%M"),
                "quiet_hours_end": (now + timedelta(hours=2)).strftime("%H:%M"),
                "max_messages_per_7_days": 3,
            },
        ),
        200,
    )
    _record(checks, "student-consented-in-app-outreach", preference["enabled"] is True)
    _expect_status(client.post("/api/auth/logout", headers={"Origin": origin}), 204)
    _expect_status(_login(client, professor_email, passwords["professor"]), 200)
    source_chunk_id = release["chunks"][0]["id"]
    trigger = _expect_json(
        client.post(
            f"/api/professor/courses/{course_id}/proactive-triggers",
            headers={"Origin": origin},
            json={
                "student_account_id": student["account_id"],
                "channel": "in-app",
                "kind": "scheduled-retrieval-practice",
                "scheduled_for": (now - timedelta(minutes=1)).isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat(),
                "topic": "Synthetic security retrieval check",
                "prompt": "What does the approved source say about CSRF?",
                "source_chunk_id": source_chunk_id,
                "idempotency_key": f"https-outreach-{run_token}",
            },
        ),
        201,
    )
    trigger_list = _expect_json(
        client.get(f"/api/professor/courses/{course_id}/proactive-triggers"),
        200,
    )
    _record(
        checks,
        "professor-scheduled-private-outreach",
        any(row["id"] == trigger["id"] for row in trigger_list),
    )
    _expect_status(client.post("/api/auth/logout", headers={"Origin": origin}), 204)
    _expect_status(_login(client, student_email, passwords["student"]), 200)
    inbox = _wait_for_outreach(
        client,
        course_id=course_id,
        timeout_seconds=timeout_seconds,
    )
    _record(
        checks,
        "scheduled-outreach-worker-delivered",
        len(inbox) == 1 and bool(inbox[0]["citations"]),
    )
    courses = _expect_json(client.get("/api/student/courses"), 200)
    _record(
        checks,
        "student-course-isolation",
        [item["course_id"] for item in courses] == [course_id],
    )
    conversation = _expect_json(
        client.post(
            f"/api/student/courses/{course_id}/conversations",
            headers={"Origin": origin},
        ),
        201,
    )
    turn = _expect_json(
        client.post(
            f"/api/student/conversations/{conversation['id']}/messages",
            headers={"Origin": origin},
            json={
                "content": "How does CSRF abuse an authenticated browser session?",
                "request_id": f"https-turn-{run_token}",
            },
        ),
        200,
    )
    _record(
        checks,
        "grounded-answer-released",
        turn["tutor_message"]["action"] == "answer" and bool(turn["citations"]),
    )
    _assert_all_passed(checks)
    citation = turn["citations"][0]
    _record(
        checks,
        "grounded-answer-with-lineage",
        bool(turn["citations"])
        and bool(citation.get("source_checksum"))
        and citation.get("page") is not None
        and citation.get("bounding_box") is not None,
    )
    adaptive_turn = _expect_json(
        client.post(
            f"/api/student/conversations/{conversation['id']}/messages",
            headers={"Origin": origin},
            json={
                "content": "I am confused why this matters.",
                "request_id": f"https-turn-confused-{run_token}",
            },
        ),
        200,
    )
    _record(
        checks,
        "selected-tutoring-mode-active",
        turn["tutoring_mode"] == expected_tutoring_mode
        and adaptive_turn["tutoring_mode"] == expected_tutoring_mode,
    )
    _record(
        checks,
        "bounded-tutoring-state-visible",
        expected_tutoring_mode != "bounded-tutoring-graph"
        or adaptive_turn["learner_state_revision"] == 2,
    )
    crop = client.get(
        f"/api/student/messages/{turn['tutor_message']['id']}/citations/"
        f"{citation['id']}/crop"
    )
    _expect_status(crop, 200)
    crop_sha256 = hashlib.sha256(crop.content).hexdigest()
    _record(
        checks,
        "authorized-original-citation-region",
        crop.headers.get("content-type", "").startswith("image/")
        and len(crop.content) > 0,
    )

    durations: list[float] = []
    for _ in range(25):
        request_started = time.perf_counter()
        _expect_status(client.get("/api/student/courses"), 200)
        durations.append((time.perf_counter() - request_started) * 1000)
    durations.sort()
    p95 = durations[max(0, int(len(durations) * 0.95) - 1)]
    _record(checks, "live-api-p95", p95 <= 750.0)
    _expect_status(client.post("/api/auth/logout", headers={"Origin": origin}), 204)
    _expect_status(_login(client, professor_email, passwords["professor"]), 200)
    learning_gaps = _expect_json(
        client.get(
            f"/api/professor/courses/{course_id}/learning-gaps",
            params={"release_id": release_id},
        ),
        200,
    )
    aggregation = learning_gaps["aggregation"]
    _record(
        checks,
        "privacy-preserving-learning-gap-view",
        aggregation["minimum_distinct_learners"] == 5
        and aggregation["visible_aggregates"] == []
        and learning_gaps["proposals"] == [],
    )
    _assert_all_passed(checks)

    return {
        "schema_version": 1,
        "run_id": f"deployable-product-foundation-live-{run_token}",
        "mode": "new-live-https-journey",
        "base_url": str(client.base_url).rstrip("/"),
        "synthetic_data_only": True,
        "external_model_calls": "recorded-by-runtime-provider-budget",
        "started_at_epoch": started_at,
        "duration_ms": round((time.time() - started_at) * 1000, 3),
        "checks": checks,
        "passed_checks": len(checks),
        "total_checks": len(checks),
        "metrics": {
            "ingestion_queue_to_complete_ms": round(ingestion_ms, 3),
            "live_api_p95_ms": round(p95, 3),
            "live_api_requests": len(durations),
            "tutoring_mode": adaptive_turn["tutoring_mode"],
        },
        "accounts": {
            "professor_email": professor_email,
            "student_email": student_email,
        },
        "workflow": {
            "course_id": course_id,
            "session_id": session["session_id"],
            "job_id": job["id"],
            "release_id": release_id,
            "teaching_profile_id": teaching_profile["profile_id"],
            "proactive_trigger_id": trigger["id"],
            "conversation_id": conversation["id"],
            "conversation_message_count": 4,
            "tutor_message_id": turn["tutor_message"]["id"],
            "citation_id": citation["id"],
            "citation_crop_sha256": crop_sha256,
        },
    }


def verify_resume(
    client: httpx.Client,
    result_path: Path,
    student_password: str,
) -> dict[str, Any]:
    recorded = json.loads(result_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    readiness = _expect_json(client.get("/api/health/ready"), 200)
    _record(checks, "restored-readiness", readiness["status"] == "ready")
    _expect_status(
        _login(client, recorded["accounts"]["student_email"], student_password),
        200,
    )
    courses = _expect_json(client.get("/api/student/courses"), 200)
    _record(
        checks,
        "restored-course",
        [course["course_id"] for course in courses]
        == [recorded["workflow"]["course_id"]],
    )
    conversation = _expect_json(
        client.get(
            f"/api/student/conversations/{recorded['workflow']['conversation_id']}"
        ),
        200,
    )
    expected_message_count = recorded["workflow"].get("conversation_message_count", 4)
    _record(
        checks,
        "restored-conversation",
        len(conversation["messages"]) == expected_message_count,
    )
    tutor_messages = [
        message for message in conversation["messages"] if message["role"] == "tutor"
    ]
    expected_mode = recorded.get("metrics", {}).get("tutoring_mode")
    _record(
        checks,
        "restored-tutoring-state",
        bool(tutor_messages)
        and all(message["tutoring_mode"] == expected_mode for message in tutor_messages)
        and (
            expected_mode != "bounded-tutoring-graph"
            or tutor_messages[-1]["learner_state_revision"] == 2
        ),
    )
    citations = _expect_json(
        client.get(
            f"/api/student/messages/{recorded['workflow']['tutor_message_id']}/citations"
        ),
        200,
    )
    _record(
        checks,
        "restored-citation",
        len(citations) == 1
        and citations[0]["id"] == recorded["workflow"]["citation_id"],
    )
    crop = client.get(
        f"/api/student/messages/{recorded['workflow']['tutor_message_id']}/citations/"
        f"{recorded['workflow']['citation_id']}/crop"
    )
    _record(
        checks,
        "restored-citation-region",
        crop.status_code == 200
        and hashlib.sha256(crop.content).hexdigest()
        == recorded["workflow"]["citation_crop_sha256"],
    )
    _assert_all_passed(checks)
    return {
        "schema_version": 1,
        "run_id": recorded["run_id"],
        "mode": "resume-live-https-journey",
        "checks": checks,
        "passed_checks": len(checks),
        "total_checks": len(checks),
    }


def verify_tutoring_mode(
    client: httpx.Client,
    result_path: Path,
    student_password: str,
    *,
    expected_tutoring_mode: str,
    origin: str,
) -> dict[str, Any]:
    recorded = json.loads(result_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    _expect_status(
        _login(client, recorded["accounts"]["student_email"], student_password),
        200,
    )
    conversation = _expect_json(
        client.post(
            f"/api/student/courses/{recorded['workflow']['course_id']}/conversations",
            headers={"Origin": origin},
        ),
        201,
    )
    turn = _expect_json(
        client.post(
            f"/api/student/conversations/{conversation['id']}/messages",
            headers={"Origin": origin},
            json={
                "content": "How does CSRF abuse an authenticated browser session?",
                "request_id": f"mode-check-{uuid4().hex}",
            },
        ),
        200,
    )
    _record(
        checks,
        "selected-tutoring-mode",
        turn["tutoring_mode"] == expected_tutoring_mode,
    )
    _record(
        checks,
        "mode-check-grounded-answer",
        turn["tutor_message"]["action"] == "answer" and bool(turn["citations"]),
    )
    _record(
        checks,
        "mode-check-state-boundary",
        (
            expected_tutoring_mode == "grounded-assistant"
            and turn["learner_state_revision"] is None
        )
        or (
            expected_tutoring_mode == "bounded-tutoring-graph"
            and turn["learner_state_revision"] == 1
        ),
    )
    _assert_all_passed(checks)
    return {
        "schema_version": 1,
        "run_id": recorded["run_id"],
        "mode": "live-tutoring-mode-check",
        "expected_tutoring_mode": expected_tutoring_mode,
        "checks": checks,
        "passed_checks": len(checks),
        "total_checks": len(checks),
    }


def _passwords_from_env() -> dict[str, str]:
    passwords = {name: os.getenv(variable, "") for name, variable in PASSWORD_ENV.items()}
    missing = [PASSWORD_ENV[name] for name, value in passwords.items() if len(value) < 12]
    if missing:
        raise SystemExit(
            "Required password environment variables must contain at least 12 characters: "
            + ", ".join(missing)
        )
    return passwords


def _validate_https_url(value: str) -> tuple[str, str]:
    parsed = urlsplit(value.rstrip("/"))
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
        raise SystemExit("--base-url must be an HTTPS origin without a path")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return origin, origin


def _login(client: httpx.Client, email: str, password: str) -> httpx.Response:
    origin = str(client.base_url).rstrip("/")
    return client.post(
        "/api/auth/login",
        headers={"Origin": origin},
        json={"email": email, "password": password},
    )


def _wait_for_job(
    client: httpx.Client,
    job_id: str,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job = _expect_json(client.get(f"/api/professor/ingestion-jobs/{job_id}"), 200)
        if job["status"] == "succeeded":
            return job
        if job["status"] in {"failed", "cancelled"}:
            raise RuntimeError(f"ingestion job ended as {job['status']}")
        time.sleep(0.25)
    raise TimeoutError("ingestion job did not finish before the live HTTPS deadline")


def _wait_for_outreach(
    client: httpx.Client,
    *,
    course_id: str,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        inbox = _expect_json(
            client.get(f"/api/student/outreach?course_id={course_id}"),
            200,
        )
        if inbox:
            return inbox
        time.sleep(1.0)
    raise TimeoutError("scheduled outreach did not arrive before the HTTPS deadline")


def _approve_session(
    client: httpx.Client,
    session: dict[str, Any],
    origin: str,
) -> dict[str, Any]:
    session_id = session["session_id"]
    for item in list(session["approval_checklist"]):
        if item["id"].startswith("preview_") or item["id"] == (
            "professor_release_approval"
        ):
            continue
        session = _expect_json(
            client.patch(
                f"/api/onboarding/sessions/{session_id}/approval-checklist/"
                f"{item['id']}",
                headers={"Origin": origin},
                json={"checked": True},
            ),
            200,
        )
    for preview in list(session["preview_cases"]):
        session = _expect_json(
            client.patch(
                f"/api/onboarding/sessions/{session_id}/preview-cases/{preview['id']}/decision",
                headers={"Origin": origin},
                json={"decision": "accepted", "reason": "Synthetic HTTPS rehearsal."},
            ),
            200,
        )
    session = _expect_json(
        client.post(
            f"/api/onboarding/sessions/{session_id}/preview-cases",
            headers={"Origin": origin},
            json={
                "prompt": "Explain the approved CSRF concept in one sentence.",
                "tag": "teaching_behavior",
            },
        ),
        200,
    )
    custom = session["preview_cases"][-1]
    session = _expect_json(
        client.patch(
            f"/api/onboarding/sessions/{session_id}/preview-cases/{custom['id']}/decision",
            headers={"Origin": origin},
            json={"decision": "accepted", "reason": "Synthetic HTTPS rehearsal."},
        ),
        200,
    )
    session = _expect_json(
        client.patch(
            f"/api/onboarding/sessions/{session_id}/approval-checklist/"
            "professor_release_approval",
            headers={"Origin": origin},
            json={"checked": True},
        ),
        200,
    )
    return session


def _write_synthetic_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "Synthetic network security course notes")
    page.insert_text((72, 110), "CSRF abuses an authenticated browser session.")
    page.draw_rect(pymupdf.Rect(72, 150, 216, 246), color=(0.2, 0.2, 0.2))
    page.insert_text((72, 270), "Figure 1: Synthetic authenticated request flow")
    document.save(path, no_new_id=True)
    document.close()


def _expect_json(response: httpx.Response, expected: int) -> Any:
    _expect_status(response, expected)
    return response.json()


def _expect_status(response: httpx.Response, expected: int) -> None:
    if response.status_code != expected:
        raise RuntimeError(
            f"{response.request.method} {response.request.url.path} returned "
            f"{response.status_code}, expected {expected}: {response.text[:300]}"
        )


def _record(checks: list[dict[str, Any]], name: str, passed: bool) -> None:
    checks.append({"name": name, "passed": bool(passed)})


def _assert_all_passed(checks: list[dict[str, Any]]) -> None:
    failed = [check["name"] for check in checks if not check["passed"]]
    if failed:
        raise RuntimeError("live HTTPS checks failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
