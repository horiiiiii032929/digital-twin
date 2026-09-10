import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from scripts.recording_app import make_recording_app
from services.api.app.runtime_identity import runtime_identity, worker_status, write_worker_heartbeat


def test_runtime_identity_records_actual_database_and_excludes_secrets(tmp_path):
    first = make_recording_app(tmp_path / "first")
    second = make_recording_app(tmp_path / "second")
    a, b = runtime_identity(first), runtime_identity(second)
    assert a["composition_sha256"] != b["composition_sha256"]
    assert a["database_binding_comparable"]
    encoded = json.dumps(a)
    assert str(tmp_path) not in encoded
    assert "synthetic-recording-only-not-a-private-key" not in encoded
    first.state.experimental_tutoring_configuration = {"version": "test", "secret": "must-not-expose"}
    assert "must-not-expose" not in json.dumps(runtime_identity(first))


def test_worker_heartbeat_distinguishes_match_mismatch_stale_and_invalid(tmp_path):
    app = make_recording_app(tmp_path)
    identity = runtime_identity(app)
    assert worker_status(app, identity) == []
    write_worker_heartbeat(app, worker_id="synthetic", status="waiting", poll_seconds=30)
    row = worker_status(app, identity)[0]
    assert row["composition_matches_api"] and not row["stale"]
    file = next((tmp_path / "worker-status").glob("*.json"))
    data = json.loads(file.read_text())
    data["composition_sha256"] = "different"
    data["updated_at"] = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    file.write_text(json.dumps(data))
    row = worker_status(app, identity)[0]
    assert not row["composition_matches_api"] and row["stale"]
    file.write_text("invalid")
    assert worker_status(app, identity)[0]["status"] == "unreadable"


def test_runtime_endpoint_requires_course_owner(tmp_path):
    with TestClient(make_recording_app(tmp_path)) as client:
        headers = {"X-Account-ID": "professor-synthetic"}
        created = client.post("/api/professor/courses", headers=headers,
            json={"title": "Synthetic", "course_id": "identity-course"})
        assert created.status_code == 201
        endpoint = "/api/professor/courses/identity-course/runtime-status"
        assert client.get(endpoint).status_code == 401
        assert client.get(endpoint, headers={"X-Account-ID": "student-a-synthetic"}).status_code == 403
        assert client.get(endpoint, headers={"X-Account-ID": "professor-b-recording"}).status_code == 403
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 200
        assert response.json()["workers"] == []
        assert response.json()["api"]["generator_implementation"]
