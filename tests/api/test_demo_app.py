from fastapi.testclient import TestClient

from services.api.app.main import app


def test_default_demo_app_boots_with_valid_professor_and_student_fixtures() -> None:
    client = TestClient(app)

    professor_response = client.get(
        "/api/professor/courses",
        headers={"X-Account-ID": "professor-synthetic"},
    )
    student_response = client.get(
        "/api/student/courses",
        headers={"X-Account-ID": "student-a-synthetic"},
    )

    assert professor_response.status_code == 200
    assert student_response.status_code == 200
    assert any(
        release["status"] == "published"
        and release["evaluation_status"] == "passed"
        for course in professor_response.json()
        for release in course["releases"]
    )
    assert student_response.json()
