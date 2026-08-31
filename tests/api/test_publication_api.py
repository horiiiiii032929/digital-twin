from pathlib import Path

from fastapi.testclient import TestClient

from services.api.app.factory import create_app
from src.digital_twin.grounding import AnyHitEvidenceGate, OCRTextRegion
from src.digital_twin.onboarding import InMemorySessionRepository, create_session
from src.digital_twin.student import (
    Conversation,
    Message,
    OutreachChannel,
    ReleaseEvaluationStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    approved_synthetic_policy,
    seed_synthetic_student_workflow,
)
from src.digital_twin.tutor_policy import SourceLabel, build_initial_policy
from tests.fixtures.ingestion import write_synthetic_pdf


class SyntheticCourseOCR:
    implementation_id = "synthetic-course-ocr"
    version = "1.0.0"

    def recognize(
        self,
        page_image,
        *,
        page_number,
        image_width,
        image_height,
    ):
        assert page_image and page_number == 1
        assert image_width > 0 and image_height > 0
        return [
            OCRTextRegion(
                text="Scanned release evidence describes cache ownership.",
                bounding_box=(0.1, 0.1, 0.9, 0.3),
                confidence=0.99,
            )
        ]


def _headers(account_id: str) -> dict[str, str]:
    return {"X-Account-ID": account_id}


def _client(
    tmp_path: Path,
    *,
    approved: bool,
    source_ocr_provider=None,
) -> tuple[TestClient, SQLiteStudentRepository, InMemorySessionRepository, object]:
    student_repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(student_repository)
    sessions = InMemorySessionRepository()
    session = create_session("onboarding-release-synthetic")
    session.course_id = fixture.course_a_id
    session.current_step = "professor_approval"
    session.policy = approved_synthetic_policy() if approved else build_initial_policy()
    sessions.save(session)
    app = create_app(
        repository=sessions,
        student_repository=student_repository,
        source_root=tmp_path / "course-sources",
        region_crop_root=tmp_path / "region-crops",
        source_ocr_provider=source_ocr_provider,
        student_evidence_gate=AnyHitEvidenceGate(),
    )
    return TestClient(app), student_repository, sessions, fixture


def _create_draft(client: TestClient, repository, sessions, fixture, release_id):
    source_release = repository.get_release(fixture.release_a_id)
    session = sessions.get("onboarding-release-synthetic")
    response = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json={
            "session_id": session.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "release_id": release_id,
            "chunks": [
                chunk.model_dump(mode="json") for chunk in source_release.chunks
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def _set_evaluation(
    client: TestClient, fixture, release_id: str, status: str = "passed"
):
    return client.patch(
        f"/api/professor/releases/{release_id}/evaluation",
        headers=_headers(fixture.professor_id),
        json={"status": status},
    )


def _teaching_profile_payload() -> dict:
    return {
        "tone": "Encouraging, precise, and concise",
        "depth": "balanced",
        "explanation_structure": ["Concept", "Example", "Check understanding"],
        "example_preferences": ["Use small Python examples"],
        "misconception_handling": "Name the misconception, then contrast it with evidence.",
        "integrity_limits": "Use hints for assessed work and never provide a submission.",
        "help_ladder": ["Focused hint", "Worked analogous example", "Full explanation"],
        "outreach_policy": "Send only professor-scheduled review prompts to opted-in students.",
    }


def test_approved_teaching_profile_is_hash_bound_to_release(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    created = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/teaching-profiles",
        headers=_headers(fixture.professor_id),
        json=_teaching_profile_payload(),
    )
    assert created.status_code == 201
    profile = created.json()

    rejected = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json={
            "session_id": "onboarding-release-synthetic",
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "teaching_profile_id": profile["profile_id"],
            "release_id": "release-with-draft-teaching-profile",
            "chunks": [
                chunk.model_dump(mode="json")
                for chunk in repository.get_release(fixture.release_a_id).chunks
            ],
        },
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "teaching_profile_not_approved"

    preview = client.get(
        f"/api/professor/courses/{fixture.course_a_id}/teaching-profiles/"
        f"{profile['profile_id']}/preview",
        headers=_headers(fixture.professor_id),
    )
    assert preview.status_code == 200
    approved = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/teaching-profiles/"
        f"{profile['profile_id']}/approve",
        headers=_headers(fixture.professor_id),
        json={"preview_sha256": preview.json()["preview_sha256"]},
    )
    assert approved.status_code == 200

    draft = _create_draft(
        client,
        repository,
        sessions,
        fixture,
        "release-with-approved-teaching-profile",
    )
    request = {
        "session_id": "onboarding-release-synthetic",
        "profile_id": "student-tutor",
        "profile_version": "v1",
        "teaching_profile_id": profile["profile_id"],
        "release_id": "release-with-approved-teaching-profile-bound",
        "chunks": [
            chunk.model_dump(mode="json")
            for chunk in repository.get_release(fixture.release_a_id).chunks
        ],
    }
    response = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json=request,
    )
    assert draft["teaching_profile_id"] is None
    assert response.status_code == 201
    bound = response.json()
    assert bound["teaching_profile_id"] == profile["profile_id"]
    assert bound["teaching_profile_sha256"] == approved.json()["content_sha256"]


def test_professor_can_list_and_cancel_pending_scheduled_outreach(tmp_path):
    client, repository, _, fixture = _client(tmp_path, approved=True)
    release = repository.get_release(fixture.release_a_id)
    assert release is not None
    source_chunk = next(chunk for chunk in release.chunks if chunk.retrieval_allowed)
    scheduled = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/proactive-triggers",
        headers=_headers(fixture.professor_id),
        json={
            "student_account_id": fixture.student_a_id,
            "channel": "in-app",
            "kind": "scheduled-retrieval-practice",
            "scheduled_for": "2026-09-01T09:00:00+00:00",
            "expires_at": "2026-09-08T09:00:00+00:00",
            "topic": "Review cache coherence",
            "prompt": "Revisit the evidence and explain the invariant in your own words.",
            "source_chunk_id": source_chunk.id,
            "idempotency_key": "scheduled-outreach-list-cancel-test",
        },
    )
    assert scheduled.status_code == 201

    listed = client.get(
        f"/api/professor/courses/{fixture.course_a_id}/proactive-triggers",
        headers=_headers(fixture.professor_id),
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [scheduled.json()["id"]]

    cancelled = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/proactive-triggers/"
        f"{scheduled.json()['id']}/cancel",
        headers=_headers(fixture.professor_id),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["suppression_reason"] == "professor-cancelled"
    repeated = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/proactive-triggers/"
        f"{scheduled.json()['id']}/cancel",
        headers=_headers(fixture.professor_id),
    )
    assert repeated.status_code == 200


def test_autonomy_recipient_index_explains_ineligible_students(tmp_path):
    client, _, _, fixture = _client(tmp_path, approved=True)

    response = client.get(
        f"/api/professor/courses/{fixture.course_a_id}/autonomy-recipients",
        headers=_headers(fixture.professor_id),
    )

    assert response.status_code == 200
    recipients = {
        item["student_account_id"]: item for item in response.json()
    }
    active = recipients[fixture.student_a_id]
    assert active["account_active"] is True
    assert active["membership_active"] is True
    assert active["goal_eligible"] is False
    assert "Autonomy policy is not active" in active["ineligibility_reasons"]

    revoked = recipients[fixture.revoked_student_id]
    assert revoked["account_active"] is False
    assert revoked["goal_eligible"] is False
    assert revoked["outreach_eligible"] is False
    assert "Student account is inactive" in revoked["ineligibility_reasons"]


def _record_prior_no_evidence_turn(repository, fixture) -> None:
    current = repository.get_release(fixture.release_a_id)
    assert current is not None
    previous = current.model_copy(
        update={
            "id": "release-a-prior-without-cache",
            "status": StudentReleaseStatus.WITHDRAWN,
            "chunks": [current.chunks[1]],
            "created_at": "2026-08-01T00:00:00+00:00",
        },
        deep=True,
    )
    repository.save_release(previous)
    conversation = repository.save_conversation(
        Conversation(
            id="conversation-publication-recovery",
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            release_id=previous.id,
            created_at="2026-08-10T00:00:00+00:00",
            updated_at="2026-08-10T00:00:01+00:00",
        )
    )
    student_message = Message(
        id="message-publication-recovery-question",
        conversation_id=conversation.id,
        role="student",
        content="Why is cache coherence needed for replicated processor data?",
        action="question",
        client_request_id="publication-recovery-request",
        created_at="2026-08-10T00:00:00+00:00",
    )
    tutor_message = Message(
        id="message-publication-recovery-no-evidence",
        conversation_id=conversation.id,
        role="tutor",
        content="I do not have enough approved course evidence.",
        action="no-evidence",
        response_to_message_id=student_message.id,
        created_at="2026-08-10T00:00:01+00:00",
    )
    repository.save_turn(conversation, student_message, tutor_message, [], [])


def test_publication_requires_evaluation_and_resolved_policy(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=False)
    draft = _create_draft(
        client, repository, sessions, fixture, "release-a-blocked-synthetic"
    )
    assert draft["status"] == "draft"
    assert draft["evaluation_status"] == "pending"

    missing_evaluation = client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    )
    assert missing_evaluation.status_code == 409
    assert missing_evaluation.json()["detail"]["code"] == "evaluation_required"

    assert _set_evaluation(client, fixture, draft["id"]).status_code == 200
    blocked = client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "release_blocked"
    assert (
        repository.get_published_release(fixture.course_a_id).id == fixture.release_a_id
    )


def test_product_preflight_blocks_without_selected_evidence_sufficiency(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "ungated-publication.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    client = TestClient(create_app(student_repository=repository))

    preflight = client.post(
        f"/api/professor/releases/{fixture.release_a_id}/preflight",
        headers=_headers(fixture.professor_id),
    )

    assert preflight.status_code == 200
    evidence = next(
        check
        for check in preflight.json()["checks"]
        if check["id"] == "evidence-sufficiency"
    )
    assert preflight.json()["passed"] is False
    assert evidence["passed"] is False
    assert (
        repository.get_release(fixture.release_a_id).evaluation_status
        == ReleaseEvaluationStatus.PASSED
    )


def test_onboarding_session_must_be_bound_once_to_release_course(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    unbound = create_session("unbound-course-session")
    unbound.current_step = "professor_approval"
    unbound.policy = approved_synthetic_policy()
    unbound = sessions.save(unbound)
    source_release = repository.get_release(fixture.release_a_id)
    assert source_release is not None
    payload = {
        "session_id": unbound.session_id,
        "profile_id": "student-tutor",
        "profile_version": "v1",
        "chunks": [chunk.model_dump(mode="json") for chunk in source_release.chunks],
    }

    rejected = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json=payload,
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "onboarding_course_required"

    bound = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/onboarding-sessions/{unbound.session_id}/bind",
        headers=_headers(fixture.professor_id),
    )
    assert bound.status_code == 200
    assert bound.json()["course_id"] == fixture.course_a_id

    rebound = client.post(
        f"/api/professor/courses/{fixture.course_b_id}/onboarding-sessions/{unbound.session_id}/bind",
        headers=_headers(fixture.professor_id),
    )
    assert rebound.status_code == 409
    assert rebound.json()["detail"]["code"] == "onboarding_course_scope_mismatch"


def test_release_draft_rejects_ambiguous_citation_locations(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    source_release = repository.get_release(fixture.release_a_id)
    session = sessions.get("onboarding-release-synthetic")
    chunks = [chunk.model_copy(deep=True) for chunk in source_release.chunks]
    chunks[1].document_id = chunks[0].document_id
    chunks[1].locator = chunks[0].locator

    response = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json={
            "session_id": session.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "release_id": "ambiguous-citation-release",
            "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "course_scope_violation"


def test_release_preflight_rejects_mixed_versions_of_one_source(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    source_release = repository.get_release(fixture.release_a_id)
    session = sessions.get("onboarding-release-synthetic")
    chunks = [chunk.model_copy(deep=True) for chunk in source_release.chunks]
    chunks[1].source_artifact_id = chunks[0].source_artifact_id
    chunks[1].source_version = chunks[0].source_version + 1

    draft = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json={
            "session_id": session.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "release_id": "mixed-source-version-release",
            "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        },
    )
    assert draft.status_code == 201

    preflight = client.post(
        f"/api/professor/releases/{draft.json()['id']}/preflight",
        headers=_headers(fixture.professor_id),
    )

    assert preflight.status_code == 200
    assert preflight.json()["passed"] is False
    source_check = next(
        check
        for check in preflight.json()["checks"]
        if check["id"] == "active-source-versions"
    )
    assert source_check["passed"] is False


def test_release_preflight_enforces_course_only_source_policy(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    source_release = repository.get_release(fixture.release_a_id)
    session = sessions.get("onboarding-release-synthetic")
    chunks = [chunk.model_copy(deep=True) for chunk in source_release.chunks]
    chunks[1].source_label = SourceLabel.PROFESSOR_APPROVED_EXTERNAL

    draft = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json={
            "session_id": session.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "release_id": "source-policy-mismatch-release",
            "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        },
    )
    assert draft.status_code == 201

    preflight = client.post(
        f"/api/professor/releases/{draft.json()['id']}/preflight",
        headers=_headers(fixture.professor_id),
    )

    source_check = next(
        check for check in preflight.json()["checks"] if check["id"] == "source-policy"
    )
    assert preflight.json()["passed"] is False
    assert source_check["passed"] is False


def test_professor_course_index_is_resumable_without_returning_release_payloads(
    tmp_path,
):
    client, _, _, fixture = _client(tmp_path, approved=True)

    response = client.get(
        "/api/professor/courses",
        headers=_headers(fixture.professor_id),
    )

    assert response.status_code == 200
    courses = response.json()
    assert [course["course_id"] for course in courses] == [
        fixture.course_b_id,
        fixture.course_a_id,
    ]
    course_a = next(
        course for course in courses if course["course_id"] == fixture.course_a_id
    )
    assert fixture.student_a_id in course_a["student_account_ids"]
    assert course_a["releases"][0]["chunk_count"] == 2
    assert "chunks" not in course_a["releases"][0]


def test_publish_replaces_current_release_and_denies_stale_conversation(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    conversation = client.post(
        f"/api/student/courses/{fixture.course_a_id}/conversations",
        headers=_headers(fixture.student_a_id),
    )
    assert conversation.status_code == 201

    draft = _create_draft(
        client, repository, sessions, fixture, "release-a-v2-synthetic"
    )
    assert _set_evaluation(client, fixture, draft["id"]).status_code == 200
    published = client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert (
        repository.get_release(fixture.release_a_id).status
        == StudentReleaseStatus.WITHDRAWN
    )

    stale_turn = client.post(
        f"/api/student/conversations/{conversation.json()['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "stale-release"},
    )
    assert stale_turn.status_code == 409
    assert stale_turn.json()["detail"]["code"] == "release_unavailable"


def test_publish_runs_evidence_recovery_in_shadow_without_creating_trigger(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    _record_prior_no_evidence_turn(repository, fixture)
    client.app.state.proactive_outreach_service.update_preference(
        fixture.student_a_id,
        fixture.course_a_id,
        channel=OutreachChannel.IN_APP,
        enabled=True,
        timezone="UTC",
        quiet_hours_start="23:00",
        quiet_hours_end="06:00",
        max_messages_per_7_days=3,
    )
    draft = _create_draft(
        client, repository, sessions, fixture, "release-a-v2-shadow-recovery"
    )
    assert _set_evaluation(client, fixture, draft["id"]).status_code == 200

    published = client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    )

    assert published.status_code == 200
    recovery_events = [
        event
        for event in repository.list_audit_events()
        if event.event_type == "evidence-recovery-scan-completed"
    ]
    assert len(recovery_events) == 1
    assert recovery_events[0].release_id == draft["id"]
    assert recovery_events[0].details == {
        "mode": "shadow",
        "opportunity_count": 1,
        "proposed_count": 1,
        "no_action_count": 0,
        "duplicate_count": 0,
        "trigger_count": 0,
        "provider_calls": 0,
    }
    assert repository.list_due_proactive_triggers("9999-12-31T00:00:00+00:00") == []


def test_publish_preserves_release_and_audits_shadow_hook_failure(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    draft = _create_draft(
        client, repository, sessions, fixture, "release-a-v2-hook-failure"
    )
    assert _set_evaluation(client, fixture, draft["id"]).status_code == 200

    def fail_after_publish(_professor_id: str, _course_id: str) -> None:
        raise RuntimeError("synthetic shadow failure with private-looking text")

    client.app.state.publication_service.post_publish_hook = fail_after_publish
    published = client.post(
        f"/api/professor/releases/{draft['id']}/publish",
        headers=_headers(fixture.professor_id),
    )

    assert published.status_code == 200
    assert repository.get_published_release(fixture.course_a_id).id == draft["id"]
    failure = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "release.post_publish_hook_failed"
    )
    assert failure.details == {
        "hook": "proactive-evidence-recovery-shadow",
        "error_type": "RuntimeError",
        "publication_preserved": True,
    }
    assert "private-looking" not in repr(failure)


def test_withdraw_and_rollback_restore_previous_release(tmp_path):
    client, repository, sessions, fixture = _client(tmp_path, approved=True)
    assert _set_evaluation(client, fixture, fixture.release_a_id).status_code == 200
    draft = _create_draft(
        client, repository, sessions, fixture, "release-a-v2-rollback-synthetic"
    )
    assert _set_evaluation(client, fixture, draft["id"]).status_code == 200
    assert (
        client.post(
            f"/api/professor/releases/{draft['id']}/publish",
            headers=_headers(fixture.professor_id),
        ).status_code
        == 200
    )

    withdrawn = client.post(
        f"/api/professor/releases/{draft['id']}/withdraw",
        headers=_headers(fixture.professor_id),
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    assert (
        client.get(
            "/api/student/courses", headers=_headers(fixture.student_a_id)
        ).json()
        == []
    )

    rollback = client.post(
        f"/api/professor/releases/{fixture.release_a_id}/rollback",
        headers=_headers(fixture.professor_id),
    )
    assert rollback.status_code == 200
    assert rollback.json()["id"] == fixture.release_a_id
    assert rollback.json()["status"] == "published"
    assert (
        repository.get_published_release(fixture.course_a_id).id == fixture.release_a_id
    )


def test_professor_ingests_scanned_pdf_into_release_ready_region_chunks(tmp_path):
    client, repository, sessions, fixture = _client(
        tmp_path,
        approved=True,
        source_ocr_provider=SyntheticCourseOCR(),
    )
    scan = tmp_path / "scan.pdf"
    write_synthetic_pdf(scan, with_text=False, with_figure=True)

    response = client.put(
        f"/api/professor/courses/{fixture.course_a_id}/sources/scan-notes",
        params={
            "title": "Scanned cache notes",
            "version": 1,
            "display_allowed": True,
        },
        headers={
            **_headers(fixture.professor_id),
            "Content-Type": "application/pdf",
        },
        content=scan.read_bytes(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["region_kind_counts"]["ocr"] == 1
    assert payload["region_count"] >= 2
    assert payload["chunk_count"] == len(payload["chunks"])
    assert any(
        "Scanned release evidence" in chunk["text"] for chunk in payload["chunks"]
    )
    assert all(
        chunk["metadata"]["course_id"] == fixture.course_a_id
        for chunk in payload["chunks"]
    )
    assert all(chunk["crop_ref"].startswith("region://") for chunk in payload["chunks"])
    assert list((tmp_path / "course-sources").glob("source-*.pdf"))
    assert list((tmp_path / "region-crops").glob("region-*.png"))

    session = sessions.get("onboarding-release-synthetic")
    draft = client.post(
        f"/api/professor/courses/{fixture.course_a_id}/releases",
        headers=_headers(fixture.professor_id),
        json={
            "session_id": session.session_id,
            "profile_id": "student-tutor",
            "profile_version": "v1",
            "release_id": "release-scanned-synthetic",
            "chunks": payload["chunks"],
        },
    )
    assert draft.status_code == 201
    assert draft.json()["chunks"][0]["region_id"]

    preflight = client.post(
        f"/api/professor/releases/{draft.json()['id']}/preflight",
        headers=_headers(fixture.professor_id),
    )
    assert preflight.status_code == 200
    assert preflight.json()["passed"] is True
    assert all(check["passed"] for check in preflight.json()["checks"])
    assert (
        repository.get_release(draft.json()["id"]).evaluation_status.value == "passed"
    )

    denied = client.put(
        f"/api/professor/courses/{fixture.course_a_id}/sources/denied",
        params={"title": "Denied"},
        headers={
            **_headers(fixture.student_a_id),
            "Content-Type": "application/pdf",
        },
        content=scan.read_bytes(),
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "professor_role_required"
