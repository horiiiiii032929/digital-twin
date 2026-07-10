from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.app.store import store


client = TestClient(app)


def setup_function() -> None:
    store.clear()


def test_create_session_returns_first_prompt():
    response = client.post("/api/onboarding/sessions")

    assert response.status_code == 201
    payload = response.json()
    assert payload["current_step"] == "source_permissions"
    assert payload["messages"][-1]["role"] == "assistant"


def test_submit_message_advances_session():
    created = client.post("/api/onboarding/sessions").json()

    response = client.post(
        f"/api/onboarding/sessions/{created['session_id']}/messages",
        json={"content": "Use syllabus and slides only."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_step"] == "teaching_approach"


def test_unknown_session_returns_404():
    response = client.get("/api/onboarding/sessions/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "session_not_found"


def test_cors_allows_vite_fallback_localhost_port():
    response = client.options(
        "/api/onboarding/sessions",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5174"
    )


def test_source_inventory_routes_create_and_update_metadata_only_items():
    created = _completed_session()

    create_response = client.post(
        f"/api/onboarding/sessions/{created['session_id']}/source-inventory",
        json={
            "name": "week-01-slides.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 4096,
            "notes": "Synthetic filename for manual review.",
        },
    )

    assert create_response.status_code == 200
    created_payload = create_response.json()
    source = created_payload["source_inventory"][0]
    assert source["name"] == "week-01-slides.pdf"
    assert source["permission_status"] == "pending"

    update_response = client.patch(
        f"/api/onboarding/sessions/{created['session_id']}/source-inventory/{source['id']}",
        json={
            "permission_status": "approved",
            "source_label": "course-approved",
            "excluded": False,
            "notes": "Approved for Sprint 1 preview.",
        },
    )

    assert update_response.status_code == 200
    updated_source = update_response.json()["source_inventory"][0]
    assert updated_source["permission_status"] == "approved"
    assert updated_source["notes"] == "Approved for Sprint 1 preview."


def test_preview_decision_custom_prompt_revision_and_approval_routes():
    created = _completed_session()
    session_id = created["session_id"]

    decision_response = client.patch(
        f"/api/onboarding/sessions/{session_id}/preview-cases/academic-integrity/decision",
        json={
            "decision": "rejected",
            "reason": "Too much homework structure.",
        },
    )

    assert decision_response.status_code == 200
    assert decision_response.json()["preview_decisions"]["academic-integrity"][
        "decision"
    ] == "rejected"

    custom_response = client.post(
        f"/api/onboarding/sessions/{session_id}/preview-cases",
        json={
            "prompt": "Give one hint for a CSRF assignment question.",
            "tag": "teaching_behavior",
        },
    )

    assert custom_response.status_code == 200
    custom_payload = custom_response.json()
    assert custom_payload["preview_cases"][-1]["id"].startswith("custom-")
    assert custom_payload["preview_cases"][-1]["tag"] == "teaching_behavior"

    chat_response = client.post(
        f"/api/onboarding/sessions/{session_id}/messages",
        json={
            "content": (
                "This gives away too much homework help; require one guiding "
                "question before hints."
            )
        },
    )
    assert chat_response.status_code == 200
    assert chat_response.json()["revision_proposal"]["preview_case_id"] == (
        "academic-integrity"
    )

    confirm_response = client.post(
        f"/api/onboarding/sessions/{session_id}/revision-proposal/confirm"
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["policy_version"] == 2
    assert confirm_response.json()["revision_proposal"] is None

    approval_response = client.patch(
        f"/api/onboarding/sessions/{session_id}/approval-checklist/integrity",
        json={"checked": True},
    )
    assert approval_response.status_code == 200
    integrity_item = next(
        item
        for item in approval_response.json()["approval_checklist"]
        if item["id"] == "integrity"
    )
    assert integrity_item["checked"] is True


def _completed_session():
    created = client.post("/api/onboarding/sessions").json()
    session_id = created["session_id"]
    answers = [
        "Use syllabus, slides, assignments, and rubrics only.",
        "Balance concise explanations with guiding questions.",
        "Ask what the student tried first, then give hints.",
        "Correct directly, then show a contrastive example.",
        "Reject answers that complete graded work or cite unapproved sources.",
    ]

    session = created
    for answer in answers:
        response = client.post(
            f"/api/onboarding/sessions/{session_id}/messages",
            json={"content": answer},
        )
        assert response.status_code == 200
        session = response.json()

    return session
