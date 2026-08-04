from pathlib import Path

from fastapi.testclient import TestClient

from services.api.app.factory import create_app
from src.digital_twin.grounding.models import (
    GenerationTrace,
    GenerationUsage,
    SourceCitation,
    TutorAnswer,
)
from src.digital_twin.student import (
    SQLiteStudentRepository,
    StudentReleaseStatus,
    seed_synthetic_student_workflow,
)


class KeywordEmbedder:
    def embed_documents(self, texts):
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        return self._vector(text)

    @staticmethod
    def _vector(text):
        lowered = text.lower()
        return [
            float("cache" in lowered),
            float("memory" in lowered),
            float("policy" in lowered),
            0.1,
        ]


class QueryFailingEmbedder(KeywordEmbedder):
    def embed_query(self, text):
        del text
        raise RuntimeError("synthetic provider outage")


class InvalidCitationGenerator:
    implementation_id = "invalid-citation-generator"

    async def generate(self, question, hits, policy):
        del question, hits, policy
        return TutorAnswer(
            content="Synthetic unsupported response.",
            citations=[
                SourceCitation(
                    source_id="unknown-document",
                    title="Unknown source",
                    locator="unknown locator",
                )
            ],
            trace=GenerationTrace(
                generator_id=self.implementation_id,
                provider_model="synthetic/invalid",
                prompt_version="synthetic-v1",
                policy_action="answer",
                latency_ms=0,
                usage=GenerationUsage(),
            ),
        )


def _headers(account_id: str) -> dict[str, str]:
    return {"X-Account-ID": account_id}


def _client(
    tmp_path: Path,
    *,
    embedder=None,
    generator=None,
) -> tuple[TestClient, SQLiteStudentRepository, object]:
    repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    app = create_app(
        student_repository=repository,
        student_embedder=embedder,
        student_generator=generator,
    )
    return TestClient(app), repository, fixture


def _create_conversation(client: TestClient, fixture) -> dict:
    response = client.post(
        f"/api/student/courses/{fixture.course_a_id}/conversations",
        headers=_headers(fixture.student_a_id),
    )
    assert response.status_code == 201
    return response.json()


def test_authorized_student_journey_uses_m2_and_exposes_persisted_citation(tmp_path):
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())

    courses = client.get(
        "/api/student/courses", headers=_headers(fixture.student_a_id)
    )
    assert courses.status_code == 200
    assert [course["course_id"] for course in courses.json()] == [fixture.course_a_id]

    conversation = _create_conversation(client, fixture)
    turn = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "What does cache coherence do?", "request_id": "turn-1"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["duplicate"] is False
    assert payload["tutor_message"]["action"] == "answer"
    assert payload["citations"][0]["locator"] == "page 2"

    reloaded = client.get(
        f"/api/student/conversations/{conversation['id']}",
        headers=_headers(fixture.student_a_id),
    )
    assert reloaded.status_code == 200
    assert [message["role"] for message in reloaded.json()["messages"]] == [
        "student",
        "tutor",
    ]

    tutor_message_id = payload["tutor_message"]["id"]
    citations = client.get(
        f"/api/student/messages/{tutor_message_id}/citations",
        headers=_headers(fixture.student_a_id),
    )
    assert citations.status_code == 200
    assert citations.json() == payload["citations"]

    retrieval = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "retrieval-completed"
    )
    assert retrieval.details == {
        "hit_count": 2,
        "implementation": "qwen3-hybrid-v1",
        "primary_available": True,
    }


def test_duplicate_request_returns_the_original_persisted_turn(tmp_path):
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())
    conversation = _create_conversation(client, fixture)
    url = f"/api/student/conversations/{conversation['id']}/messages"
    body = {"content": "Explain cache coherence.", "request_id": "stable-request"}

    first = client.post(url, headers=_headers(fixture.student_a_id), json=body)
    second = client.post(url, headers=_headers(fixture.student_a_id), json=body)

    assert first.status_code == second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["tutor_message"]["id"] == first.json()["tutor_message"]["id"]
    assert len(repository.list_messages(conversation["id"])) == 2

    conflict = client.post(
        url,
        headers=_headers(fixture.student_a_id),
        json={"content": "A different question.", "request_id": "stable-request"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "request_id_conflict"


def test_student_access_is_fail_closed_for_header_role_course_and_revocation(tmp_path):
    client, repository, fixture = _client(tmp_path)

    assert client.get("/api/student/courses").status_code == 401
    professor = client.get(
        "/api/student/courses", headers=_headers(fixture.professor_id)
    )
    assert professor.status_code == 403
    assert professor.json()["detail"]["code"] == "student_role_required"

    cross_course = client.post(
        f"/api/student/courses/{fixture.course_b_id}/conversations",
        headers=_headers(fixture.student_a_id),
    )
    assert cross_course.status_code == 403
    assert cross_course.json()["detail"]["code"] == "course_access_denied"

    revoked = client.get(
        "/api/student/courses", headers=_headers(fixture.revoked_student_id)
    )
    assert revoked.status_code == 403
    assert revoked.json()["detail"]["code"] == "account_inactive"
    assert any(
        event.details.get("reason") == "course_access_denied"
        for event in repository.list_audit_events()
    )


def test_cross_student_conversation_and_citation_access_are_denied(tmp_path):
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())
    conversation = _create_conversation(client, fixture)
    turn = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "turn-1"},
    ).json()

    history = client.get(
        f"/api/student/conversations/{conversation['id']}",
        headers=_headers(fixture.student_b_id),
    )
    citations = client.get(
        f"/api/student/messages/{turn['tutor_message']['id']}/citations",
        headers=_headers(fixture.student_b_id),
    )

    assert history.status_code == citations.status_code == 403
    assert history.json()["detail"]["code"] == "conversation_access_denied"
    assert citations.json()["detail"]["code"] == "conversation_access_denied"


def test_withdrawal_immediately_blocks_new_turns(tmp_path):
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())
    conversation = _create_conversation(client, fixture)
    repository.set_release_status(
        fixture.release_a_id, StudentReleaseStatus.WITHDRAWN
    )

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "after-withdraw"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "release_unavailable"
    assert repository.list_messages(conversation["id"]) == []


def test_newer_published_release_blocks_a_stale_conversation(tmp_path):
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())
    conversation = _create_conversation(client, fixture)
    release = repository.get_release(fixture.release_a_id)
    repository.save_release(
        release.model_copy(
            update={
                "id": "release-a-v2-synthetic",
                "profile_version": "v1",
                "policy_version": 2,
                "created_at": "9999-12-31T23:59:59+00:00",
            },
            deep=True,
        )
    )

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "stale"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "release_unavailable"


def test_provider_failure_uses_bm25_and_records_only_redacted_telemetry(tmp_path):
    client, repository, fixture = _client(
        tmp_path, embedder=QueryFailingEmbedder()
    )
    conversation = _create_conversation(client, fixture)
    question = "Explain cache coherence without logging this question."

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": question, "request_id": "fallback-turn"},
    )

    assert response.status_code == 200
    assert response.json()["citations"]
    events = repository.list_audit_events()
    fallback = next(event for event in events if event.event_type == "retrieval-fallback")
    assert fallback.details == {
        "failure_type": "RuntimeError",
        "fallback": "bm25-v1",
        "primary": "qwen3-hybrid-v1",
    }
    assert question not in " ".join(event.model_dump_json() for event in events)


def test_invalid_generator_citation_becomes_a_persisted_safe_failure(tmp_path):
    client, repository, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        generator=InvalidCitationGenerator(),
    )
    conversation = _create_conversation(client, fixture)

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "bad-citation"},
    )

    assert response.status_code == 200
    assert response.json()["tutor_message"]["action"] == "safe-citation-failure"
    assert response.json()["citations"] == []
    assert any(
        event.event_type == "citation-validation-failure"
        for event in repository.list_audit_events()
    )


def test_conversation_survives_repository_and_application_restart(tmp_path):
    database = tmp_path / "restart.sqlite3"
    first_repository = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(first_repository)
    first_app = create_app(
        student_repository=first_repository,
        student_embedder=KeywordEmbedder(),
    )
    with TestClient(first_app) as first_client:
        conversation = _create_conversation(first_client, fixture)
        response = first_client.post(
            f"/api/student/conversations/{conversation['id']}/messages",
            headers=_headers(fixture.student_a_id),
            json={"content": "Explain cache coherence.", "request_id": "restart"},
        )
        assert response.status_code == 200
    first_repository.close()

    second_repository = SQLiteStudentRepository(database)
    second_app = create_app(
        student_repository=second_repository,
        student_embedder=KeywordEmbedder(),
    )
    with TestClient(second_app) as second_client:
        reloaded = second_client.get(
            f"/api/student/conversations/{conversation['id']}",
            headers=_headers(fixture.student_a_id),
        )

    assert reloaded.status_code == 200
    assert len(reloaded.json()["messages"]) == 2
    assert reloaded.json()["messages"][1]["action"] == "answer"
    second_repository.close()
