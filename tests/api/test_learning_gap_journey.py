"""Real student turns must populate the professor's privacy-safe cohort view.

Uses the existing deterministic test retriever; no provider calls or direct
insertion of learning-gap signals. This is integration coverage, not a model
quality or final-profile qualification.
"""

from src.digital_twin.student.models import Account, AccountRole, CourseMembership, MembershipRole
from src.digital_twin.student import LearningGapPseudonymizer
from services.api.app.config import StudentTutoringMode
from tests.api.test_student_api import KeywordEmbedder, _client, _headers


def test_student_turns_populate_private_professor_cohort_insights(tmp_path, monkeypatch):
    client, repository, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(
            b"synthetic-cohort-integration-secret-32-bytes"
        ),
    )
    endpoint = f"/api/professor/courses/{fixture.course_a_id}/learning-gaps"
    query = {"release_id": fixture.release_a_id}

    for number in range(5):
        student_id = f"synthetic-cohort-student-{number}"
        repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
        repository.save_membership(CourseMembership(
            account_id=student_id, course_id=fixture.course_a_id,
            role=MembershipRole.STUDENT,
        ))
        conversation = client.post(
            f"/api/student/courses/{fixture.course_a_id}/conversations",
            headers=_headers(student_id),
        )
        assert conversation.status_code == 201
        messages = f"/api/student/conversations/{conversation.json()['id']}/messages"
        for index, content in enumerate((
            "What does cache coherence do?",
            "I am confused why cache coherence matters.",
        )):
            response = client.post(messages, headers=_headers(student_id), json={
                "content": content, "request_id": f"cohort-{number}-{index}",
            })
            assert response.status_code == 200, response.text
        # Retrying the same committed turn must not inflate the cohort signal.
        duplicate = client.post(messages, headers=_headers(student_id), json={
            "content": "I am confused why cache coherence matters.",
            "request_id": f"cohort-{number}-1",
        })
        assert duplicate.status_code == 200
        assert duplicate.json()["duplicate"] is True
        overview = client.get(endpoint, params=query, headers=_headers(fixture.professor_id))
        assert overview.status_code == 200, overview.text
        aggregation = overview.json()["aggregation"]
        if number < 4:
            assert aggregation["visible_aggregates"] == []
            assert overview.json()["proposals"] == []
            assert "source_title" not in overview.text
            assert aggregation["active_learner_count"] is None

    gaps = aggregation["visible_aggregates"]
    assert aggregation["active_learner_count"] == 5
    assert aggregation["reporting_window_start"]
    assert len(gaps) == 1
    assert gaps[0]["signal_kind"] == "confusion"
    assert gaps[0]["distinct_learners"] == gaps[0]["signal_count"] == 5
    # Current real-service granularity is a source, unlike concept-key fixtures.
    assert gaps[0]["topic_key"].startswith("source-")
    release = repository.get_release(fixture.release_a_id)
    assert gaps[0]["source_title"] == release.chunks[0].metadata["title"]
    assert len(overview.json()["proposals"]) == 1
    assert "synthetic-cohort-student" not in overview.text
    assert "I am confused" not in overview.text
    proposal = overview.json()["proposals"][0]
    review = client.post(
        endpoint + "/review",
        headers=_headers(fixture.professor_id),
        json={
            "release_id": fixture.release_a_id,
            "proposal_id": proposal["proposal_id"],
            "decision": "consider-for-next-release",
            "rationale": "Review the approved source explanation.",
        },
    )
    assert review.status_code == 200, review.text
    repeated_review = client.post(endpoint + "/review", headers=_headers(fixture.professor_id),
        json={"release_id": fixture.release_a_id, "proposal_id": proposal["proposal_id"],
            "decision": "consider-for-next-release", "rationale": "Retry after uncertain response."})
    assert repeated_review.status_code == 200, repeated_review.text
    refreshed = client.get(endpoint, params=query, headers=_headers(fixture.professor_id)).json()
    assert refreshed["proposals"][0]["review_decision"] == "consider-for-next-release"
    assert refreshed["proposals"][0]["reviewed_at"]
    # A learner without a gap signal still belongs in the active denominator.
    quiet_student = "synthetic-without-gap"
    repository.save_account(Account(id=quiet_student, role=AccountRole.STUDENT))
    repository.save_membership(CourseMembership(account_id=quiet_student,
        course_id=fixture.course_a_id, role=MembershipRole.STUDENT))
    conversation = client.post(f"/api/student/courses/{fixture.course_a_id}/conversations",
        headers=_headers(quiet_student)).json()
    assert client.post(f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(quiet_student), json={"content": "What does cache coherence do?", "request_id": "no-gap"}).status_code == 200
    refreshed = client.get(endpoint, params=query, headers=_headers(fixture.professor_id)).json()
    assert refreshed["aggregation"]["active_learner_count"] == 6
    assert refreshed["aggregation"]["visible_aggregates"][0]["distinct_learners"] == 5


    repository.save_account(Account(id="unrelated-professor", role=AccountRole.PROFESSOR))
    denied = client.get(endpoint, params=query, headers=_headers("unrelated-professor"))
    assert denied.status_code == 403
    denied_student = client.get(endpoint, params=query, headers=_headers(fixture.student_a_id))
    assert denied_student.status_code == 403
    wrong_release = client.get(
        endpoint, params={"release_id": fixture.release_b_id},
        headers=_headers(fixture.professor_id),
    )
    assert wrong_release.status_code == 422
    assert "source_title" not in wrong_release.text

    # The denominator and numerator use the same exact release reporting window.
    from datetime import datetime, timedelta
    from services.api.app.routers import publication
    later = (datetime.fromisoformat(refreshed["aggregation"]["computed_at"]) + timedelta(days=31)).isoformat()
    monkeypatch.setattr(publication, "_now", lambda: later)
    old_window = client.get(endpoint, params=query, headers=_headers(fixture.professor_id)).json()
    assert old_window["aggregation"]["visible_aggregates"] == []
    assert old_window["aggregation"]["active_learner_count"] is None
    assert old_window["proposals"] == []
