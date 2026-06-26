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
