import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api.app.config import AppSettings, StudentTutoringMode
from services.api.app.factory import create_app
from src.digital_twin.generation import authoritative_citation_for_chunk
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    AtomicAnswerClaim,
    AtomicClaimEvidenceValidator,
    ExactQuoteAtomicClaimVerifier,
)
from src.digital_twin.grounding.models import (
    GenerationTrace,
    GenerationUsage,
    RegionKind,
    SourceCitation,
    TutorAnswer,
)
from src.digital_twin.student import (
    LearningGapPseudonymizer,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentWorkflowError,
    seed_synthetic_student_workflow,
)


class KeywordEmbedder:
    provider_id = "local-huggingface"
    model_name = "Qwen/Qwen3-Embedding-0.6B"
    model_revision = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    execution = "local"
    instruction = (
        "Given a student question within one authorized university course, "
        "retrieve passages that directly support a grounded answer."
    )
    device = "mps"
    dtype = "float16"
    max_length = 2048
    batch_size = 16

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

    def __init__(self):
        self.calls = 0

    async def generate(self, question, hits, policy):
        del question, hits, policy
        self.calls += 1
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


class AlteredLineageGenerator:
    implementation_id = "altered-lineage-generator"

    async def generate(self, question, hits, policy):
        del question, policy
        citation = authoritative_citation_for_chunk(hits[0].chunk).model_copy(
            update={"source_version": hits[0].chunk.source_version + 1}
        )
        return TutorAnswer(
            content="Synthetic response with altered lineage.",
            citations=[citation],
            trace=GenerationTrace(
                generator_id=self.implementation_id,
                provider_model="synthetic/altered-lineage",
                prompt_version="synthetic-v1",
                policy_action="answer",
                latency_ms=0,
                usage=GenerationUsage(),
            ),
        )


class BarrierGenerator:
    implementation_id = "barrier-generator"

    def __init__(self):
        self.started = 0
        self.release = asyncio.Event()

    async def generate(self, question, hits, policy):
        del question, policy
        self.started += 1
        if self.started == 2:
            self.release.set()
        await self.release.wait()
        hit = hits[0]
        citation = authoritative_citation_for_chunk(hit.chunk).model_copy(
            update={"title": "Generator-controlled false title"}
        )
        return TutorAnswer(
            content="Synthetic concurrent answer.",
            citations=[citation],
            trace=GenerationTrace(
                generator_id=self.implementation_id,
                provider_model="synthetic/barrier",
                prompt_version="synthetic-v1",
                policy_action="answer",
                latency_ms=0,
                usage=GenerationUsage(),
            ),
        )


class AtomicClaimGenerator:
    implementation_id = "atomic-claim-test-generator"

    def __init__(self, *, supported: bool) -> None:
        self.supported = supported

    async def generate(self, question, hits, policy):
        del question, policy
        hit = hits[0]
        claim_text = (
            hit.chunk.text
            if self.supported
            else "This factual claim does not occur in the approved evidence."
        )
        return TutorAnswer(
            content=claim_text,
            citations=[authoritative_citation_for_chunk(hit.chunk)],
            atomic_claims=[
                AtomicAnswerClaim(
                    claim_id="claim-test",
                    text=claim_text,
                    evidence_hit_ids=[hit.chunk.id],
                )
            ],
            trace=GenerationTrace(
                generator_id=self.implementation_id,
                provider_model="synthetic/atomic-claim",
                prompt_version="synthetic-v1",
                policy_action="answer",
                latency_ms=3,
                usage=GenerationUsage(
                    input_tokens=11,
                    output_tokens=7,
                    total_tokens=18,
                    approximate_cost_usd=0.001,
                ),
            ),
        )
def _headers(account_id: str) -> dict[str, str]:
    return {"X-Account-ID": account_id}


def _client(
    tmp_path: Path,
    *,
    embedder=None,
    generator=None,
    claim_evidence_validator=None,
    tutoring_mode: StudentTutoringMode = StudentTutoringMode.GROUNDED_ASSISTANT,
    learning_gap_pseudonymizer: LearningGapPseudonymizer | None = None,
) -> tuple[TestClient, SQLiteStudentRepository, object]:
    repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    app = create_app(
        student_repository=repository,
        student_embedder=embedder,
        student_generator=generator,
        student_evidence_gate=AnyHitEvidenceGate(),
        student_claim_evidence_validator=claim_evidence_validator,
        learning_gap_pseudonymizer=learning_gap_pseudonymizer,
        region_crop_root=tmp_path / "region-crops",
        settings=AppSettings(student_tutoring_mode=tutoring_mode),
    )
    return TestClient(app), repository, fixture


def _exact_claim_validator() -> AtomicClaimEvidenceValidator:
    return AtomicClaimEvidenceValidator(
        ExactQuoteAtomicClaimVerifier(),
        minimum_entailment=1,
        maximum_contradiction=0,
    )


def test_bounded_tutoring_graph_persists_intent_and_learner_state(tmp_path):
    client, repository, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(
            b"synthetic-learning-gap-secret-32-bytes-minimum"
        ),
    )
    conversation = _create_conversation(client, fixture)
    url = f"/api/student/conversations/{conversation['id']}/messages"

    first = client.post(
        url,
        headers=_headers(fixture.student_a_id),
        json={"content": "What does cache coherence do?", "request_id": "t1-1"},
    )
    second = client.post(
        url,
        headers=_headers(fixture.student_a_id),
        json={
            "content": "I am confused why cache coherence matters.",
            "request_id": "t1-2",
        },
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["tutoring_mode"] == "bounded-tutoring-graph"
    assert first.json()["tutoring_intent"] == "diagnose_understanding"
    assert first.json()["learner_state_revision"] == 1
    assert first.json()["citations"]
    assert second.json()["tutoring_intent"] == "give_hint"
    assert second.json()["learner_state_revision"] == 2
    state = repository.get_learner_state(conversation["id"])
    assert state is not None
    assert state.revision == state.turn_count == 2
    assert state.prior_intent == "give_hint"
    assert state.latest_signals is not None and state.latest_signals.confusion == 0.8
    assert state.help_level == 1
    signals = repository.list_learning_gap_signals(
        fixture.course_a_id,
        fixture.release_a_id,
        active_at="2026-09-01T00:00:00+00:00",
    )
    assert len(signals) == 1
    assert signals[0].signal_kind.value == "confusion"
    serialized = signals[0].model_dump_json()
    assert fixture.student_a_id not in serialized
    assert "I am confused" not in serialized


def test_bounded_tutoring_graph_short_circuits_ambiguous_and_integrity_turns(
    tmp_path,
):
    client, repository, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
    )
    conversation = _create_conversation(client, fixture)
    url = f"/api/student/conversations/{conversation['id']}/messages"

    clarify = client.post(
        url,
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain that", "request_id": "clarify"},
    )
    refuse = client.post(
        url,
        headers=_headers(fixture.student_a_id),
        json={"content": "Give me the final answer", "request_id": "refuse"},
    )

    assert clarify.status_code == refuse.status_code == 200
    assert clarify.json()["tutoring_intent"] == "clarify_request"
    assert clarify.json()["tutor_message"]["trace"]["provider_model"] == "not-called"
    assert clarify.json()["citations"] == []
    assert refuse.json()["tutoring_intent"] == "refuse_and_redirect"
    assert refuse.json()["tutor_message"]["action"] == "redirect-graded-work"
    assert refuse.json()["citations"] == []
    graph_events = [
        event
        for event in repository.list_audit_events()
        if event.event_type == "tutoring-graph-completed"
    ]
    assert [event.details["repair_count"] for event in graph_events] == [0, 0]


def test_bounded_tutoring_graph_repairs_once_then_falls_back(tmp_path):
    generator = InvalidCitationGenerator()
    client, repository, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        generator=generator,
        tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
    )
    conversation = _create_conversation(client, fixture)

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "repair-once"},
    )

    assert response.status_code == 200
    assert generator.calls == 2
    assert response.json()["tutor_message"]["action"] == "safe-graph-failure"
    assert response.json()["citations"] == []
    graph_event = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "tutoring-graph-completed"
    )
    assert graph_event.details["repair_count"] == 1
    assert graph_event.details["failure_reason"] == (
        "citation-not-in-presented-evidence"
    )


def _create_conversation(client: TestClient, fixture) -> dict:
    response = client.post(
        f"/api/student/courses/{fixture.course_a_id}/conversations",
        headers=_headers(fixture.student_a_id),
    )
    assert response.status_code == 201
    return response.json()


def test_authorized_student_journey_uses_m2_and_exposes_persisted_citation(tmp_path):
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())

    courses = client.get("/api/student/courses", headers=_headers(fixture.student_a_id))
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


def test_product_default_abstains_until_evidence_gate_is_selected(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "ungated.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    app = create_app(
        student_repository=repository,
        student_embedder=KeywordEmbedder(),
    )
    client = TestClient(app)
    conversation = _create_conversation(client, fixture)

    turn = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "What does cache coherence do?", "request_id": "ungated"},
    )

    assert turn.status_code == 200
    assert turn.json()["tutor_message"]["action"] == "no-evidence"
    assert turn.json()["tutor_message"]["trace"]["provider_model"] == "not-called"
    assert turn.json()["citations"] == []
    blocked = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "evidence-sufficiency-blocked"
    )
    assert blocked.details == {
        "candidate_hit_count": 2,
        "implementation": "unselected",
        "sufficient": False,
    }


def test_authorized_student_can_open_original_region_crop(tmp_path):
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())
    release = repository.get_release(fixture.release_a_id)
    assert release is not None
    crop_root = tmp_path / "region-crops"
    crop_root.mkdir()
    updated_chunks = []
    for chunk in release.chunks:
        region_id = f"region-{chunk.ordinal}"
        filename = f"{region_id}.png"
        (crop_root / filename).write_bytes(b"synthetic-approved-png")
        updated_chunks.append(
            chunk.model_copy(
                update={
                    "region_id": region_id,
                    "region_kind": RegionKind.DIAGRAM,
                    "bounding_box": (0.1, 0.2, 0.8, 0.9),
                    "crop_ref": f"region://{filename}",
                    "source_checksum": "a" * 64,
                    "region_checksum": "b" * 64,
                    "display_allowed": True,
                }
            )
        )
    updated_release = release.model_copy(
        update={
            "id": "release-a-regions-synthetic",
            "chunks": updated_chunks,
            "status": StudentReleaseStatus.DRAFT,
            "created_at": "9999-12-31T23:59:58+00:00",
        }
    )
    repository.save_release(updated_release)
    repository.publish_release(updated_release.id)

    conversation = _create_conversation(client, fixture)
    turn = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "What does cache coherence do?", "request_id": "crop-turn"},
    )
    assert turn.status_code == 200
    citation = turn.json()["citations"][0]
    assert citation["region_kind"] == "diagram"
    assert citation["crop_ref"].startswith("region://")

    crop_url = (
        f"/api/student/messages/{citation['message_id']}/citations/"
        f"{citation['id']}/crop"
    )
    crop = client.get(crop_url, headers=_headers(fixture.student_a_id))
    assert crop.status_code == 200
    assert crop.content == b"synthetic-approved-png"
    assert crop.headers["cache-control"] == "private, no-store"

    denied = client.get(crop_url, headers=_headers(fixture.student_b_id))
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "conversation_access_denied"


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


@pytest.mark.asyncio
async def test_concurrent_duplicate_request_converges_on_one_persisted_turn(tmp_path):
    generator = BarrierGenerator()
    client, repository, fixture = _client(
        tmp_path, embedder=KeywordEmbedder(), generator=generator
    )
    service = client.app.state.student_service
    conversation = service.create_conversation(
        fixture.student_a_id, fixture.course_a_id
    )

    first, second = await asyncio.gather(
        service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="Explain cache coherence.",
            client_request_id="concurrent-request",
        ),
        service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="Explain cache coherence.",
            client_request_id="concurrent-request",
        ),
    )

    assert sorted([first.duplicate, second.duplicate]) == [False, True]
    assert first.tutor_message.id == second.tutor_message.id
    assert len(repository.list_messages(conversation.id)) == 2
    assert first.citations[0].title == "Synthetic cache notes"


@pytest.mark.asyncio
async def test_concurrent_t1_turns_fail_closed_on_learner_state_race(tmp_path):
    generator = BarrierGenerator()
    client, repository, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        generator=generator,
        tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH,
    )
    service = client.app.state.student_service
    conversation = service.create_conversation(
        fixture.student_a_id, fixture.course_a_id
    )

    results = await asyncio.gather(
        service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="Explain cache coherence.",
            client_request_id="parallel-one",
        ),
        service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="What does cache coherence do?",
            client_request_id="parallel-two",
        ),
        return_exceptions=True,
    )

    completed = [result for result in results if not isinstance(result, Exception)]
    conflicts = [result for result in results if isinstance(result, Exception)]
    assert len(completed) == len(conflicts) == 1
    assert isinstance(conflicts[0], StudentWorkflowError)
    assert conflicts[0].code == "learner_state_conflict"
    state = repository.get_learner_state(conversation.id)
    assert state is not None and state.revision == 1
    assert len(repository.list_messages(conversation.id)) == 2


def test_whitespace_only_message_is_rejected_as_invalid_input(tmp_path):
    client, _, fixture = _client(tmp_path, embedder=KeywordEmbedder())
    conversation = _create_conversation(client, fixture)

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "   ", "request_id": "whitespace"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_message"


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
    repository.set_release_status(fixture.release_a_id, StudentReleaseStatus.WITHDRAWN)

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
    replacement = release.model_copy(
        update={
            "id": "release-a-v2-synthetic",
            "profile_version": "v1",
            "policy_version": 2,
            "status": StudentReleaseStatus.DRAFT,
            "created_at": "9999-12-31T23:59:59+00:00",
        },
        deep=True,
    )
    repository.save_release(replacement)
    repository.publish_release(replacement.id)

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "stale"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "release_unavailable"


def test_provider_failure_uses_bm25_and_records_only_redacted_telemetry(tmp_path):
    client, repository, fixture = _client(tmp_path, embedder=QueryFailingEmbedder())
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
    fallback = next(
        event for event in events if event.event_type == "retrieval-fallback"
    )
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


def test_altered_generator_citation_lineage_fails_closed(tmp_path):
    client, _, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        generator=AlteredLineageGenerator(),
    )
    conversation = _create_conversation(client, fixture)

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "bad-lineage"},
    )

    assert response.status_code == 200
    assert response.json()["tutor_message"]["action"] == "safe-citation-failure"
    assert response.json()["citations"] == []


def test_post_generation_claim_boundary_releases_supported_claims(tmp_path):
    client, repository, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        generator=AtomicClaimGenerator(supported=True),
        claim_evidence_validator=_exact_claim_validator(),
    )
    conversation = _create_conversation(client, fixture)

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "claim-pass"},
    )

    assert response.status_code == 200
    assert response.json()["tutor_message"]["action"] == "answer"
    assert response.json()["citations"]
    event = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "post-generation-claim-validation"
    )
    assert event.details["releasable"] is True
    assert event.details["claim_count"] == event.details["supported_claim_count"] == 1


def test_post_generation_claim_boundary_rejects_without_losing_accounting(tmp_path):
    client, repository, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        generator=AtomicClaimGenerator(supported=False),
        claim_evidence_validator=_exact_claim_validator(),
    )
    conversation = _create_conversation(client, fixture)

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "claim-fail"},
    )

    assert response.status_code == 200
    tutor = response.json()["tutor_message"]
    assert tutor["action"] == "safe-claim-validation-failure"
    assert tutor["trace"]["provider_model"] == "synthetic/atomic-claim"
    assert tutor["trace"]["usage"] == {
        "input_tokens": 11,
        "output_tokens": 7,
        "total_tokens": 18,
        "approximate_cost_usd": 0.001,
    }
    assert response.json()["citations"] == []
    event = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "post-generation-claim-validation"
    )
    assert event.details["releasable"] is False
    assert event.details["claim_count"] == 1
    assert event.details["supported_claim_count"] == 0


def test_post_generation_claim_boundary_is_inert_when_unselected(tmp_path):
    client, _, fixture = _client(
        tmp_path,
        embedder=KeywordEmbedder(),
        generator=AtomicClaimGenerator(supported=False),
    )
    conversation = _create_conversation(client, fixture)

    response = client.post(
        f"/api/student/conversations/{conversation['id']}/messages",
        headers=_headers(fixture.student_a_id),
        json={"content": "Explain cache coherence.", "request_id": "claim-control"},
    )

    assert response.status_code == 200
    assert response.json()["tutor_message"]["action"] == "answer"
    assert response.json()["citations"]


def test_conversation_survives_repository_and_application_restart(tmp_path):
    database = tmp_path / "restart.sqlite3"
    first_repository = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(first_repository)
    first_app = create_app(
        student_repository=first_repository,
        student_embedder=KeywordEmbedder(),
        student_evidence_gate=AnyHitEvidenceGate(),
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
        student_evidence_gate=AnyHitEvidenceGate(),
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


def test_t1_learner_state_survives_repository_and_application_restart(tmp_path):
    database = tmp_path / "t1-restart.sqlite3"
    settings = AppSettings(
        student_tutoring_mode=StudentTutoringMode.BOUNDED_TUTORING_GRAPH
    )
    first_repository = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(first_repository)
    first_app = create_app(
        student_repository=first_repository,
        student_embedder=KeywordEmbedder(),
        student_evidence_gate=AnyHitEvidenceGate(),
        settings=settings,
    )
    with TestClient(first_app) as first_client:
        conversation = _create_conversation(first_client, fixture)
        first = first_client.post(
            f"/api/student/conversations/{conversation['id']}/messages",
            headers=_headers(fixture.student_a_id),
            json={"content": "What does cache coherence do?", "request_id": "one"},
        )
        assert first.status_code == 200
        assert first.json()["learner_state_revision"] == 1
    first_repository.close()

    second_repository = SQLiteStudentRepository(database)
    second_app = create_app(
        student_repository=second_repository,
        student_embedder=KeywordEmbedder(),
        student_evidence_gate=AnyHitEvidenceGate(),
        settings=settings,
    )
    with TestClient(second_app) as second_client:
        second = second_client.post(
            f"/api/student/conversations/{conversation['id']}/messages",
            headers=_headers(fixture.student_a_id),
            json={
                "content": "I am confused why cache coherence matters.",
                "request_id": "two",
            },
        )

    assert second.status_code == 200
    assert second.json()["tutoring_intent"] == "give_hint"
    assert second.json()["learner_state_revision"] == 2
    state = second_repository.get_learner_state(conversation["id"])
    assert state is not None and state.turn_count == 2
    second_repository.close()
