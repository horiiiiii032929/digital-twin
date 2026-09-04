from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.grounding.evidence_sufficiency import (
    EvidenceSufficiencyDecision,
)
from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.student import (
    ClarificationRequestV1,
    ClarificationStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    build_clarification_request,
    resolve_clarification_option,
    seed_synthetic_student_workflow,
)


PROFILE = Path("research/05_evaluation/profiles/student-tutor-v1.json")


class FixedReleaseRetriever:
    implementation_id = "fixed-clarification-retriever"

    def __init__(self, chunks):
        self.chunks = list(chunks)

    def retrieve(self, query: str, limit: int = 5) -> list[RetrievalHit]:
        del query
        return [
            RetrievalHit(chunk=chunk, relevance_score=1 - index * 0.1)
            for index, chunk in enumerate(self.chunks[:limit])
        ]


class CompetingClaimsGate:
    implementation_id = "synthetic-competing-claims-gate"

    def assess(self, query: str, hits) -> EvidenceSufficiencyDecision:
        del query
        return EvidenceSufficiencyDecision(
            sufficient=False,
            score=0,
            reason="two source interpretations remain tied",
            clarification_candidate_hit_ids=[hit.chunk.id for hit in hits[:2]],
            recommended_action="clarify",
        )


def _service(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    clock = VirtualUtcClock(datetime(2026, 9, 5, tzinfo=UTC))
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=CompetingClaimsGate(),
        retriever_factory=lambda chunks, versions: FixedReleaseRetriever(chunks),
        clock=clock,
    )
    conversation = service.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )
    return repository, fixture, service, conversation, clock


@pytest.mark.asyncio
async def test_clarification_survives_restart_and_resolves_to_selected_source(
    tmp_path,
):
    repository, fixture, service, conversation, clock = _service(tmp_path)

    first = await service.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="What does this mechanism do?",
        client_request_id="ambiguous-1",
    )

    assert first.tutor_message.action == "clarify-request"
    assert first.pending_clarification is not None
    assert len(first.pending_clarification.options) == 2
    assert "Which one do you mean?" in first.tutor_message.content
    assert repository.get_pending_clarification(conversation.id) is not None

    restarted = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=CompetingClaimsGate(),
        retriever_factory=lambda chunks, versions: FixedReleaseRetriever(chunks),
        clock=clock,
    )
    restored = restarted.get_conversation(fixture.student_a_id, conversation.id)
    assert restored.pending_clarification is not None

    second = await restarted.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="2",
        client_request_id="clarification-selection-1",
    )

    assert second.tutor_message.action == "answer"
    assert second.pending_clarification is None
    assert len(second.citations) == 1
    assert second.citations[0].source_artifact_id == "source-memory-synthetic"
    assert repository.get_pending_clarification(conversation.id) is None
    event_types = [event.event_type for event in repository.list_audit_events()]
    assert "clarification-option-selected" in event_types

    duplicate = await restarted.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="2",
        client_request_id="clarification-selection-1",
    )
    assert duplicate.duplicate is True
    assert duplicate.pending_clarification is None


@pytest.mark.asyncio
async def test_unresolved_reply_keeps_exact_pending_request(tmp_path):
    repository, fixture, service, conversation, _ = _service(tmp_path)
    first = await service.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="What does this mechanism do?",
        client_request_id="ambiguous-2",
    )
    request = first.pending_clarification
    assert request is not None

    retry = await service.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="I am not sure",
        client_request_id="ambiguous-reply",
    )

    assert retry.tutor_message.action == "clarify-request"
    assert retry.pending_clarification == request
    assert repository.get_pending_clarification(conversation.id) == request


@pytest.mark.asyncio
async def test_release_withdrawal_cancels_pending_clarification(tmp_path):
    repository, fixture, service, conversation, _ = _service(tmp_path)
    first = await service.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="What does this mechanism do?",
        client_request_id="ambiguous-before-withdrawal",
    )
    assert first.pending_clarification is not None

    repository.set_release_status(
        fixture.release_a_id,
        StudentReleaseStatus.WITHDRAWN,
    )

    assert repository.get_pending_clarification(conversation.id) is None


def test_clarification_contract_rejects_inconsistent_resolution(tmp_path):
    repository, fixture, _, conversation, _ = _service(tmp_path)
    release = repository.get_release(fixture.release_a_id)
    assert release is not None
    request = build_clarification_request(
        conversation_id=conversation.id,
        student_id=fixture.student_a_id,
        course_id=fixture.course_a_id,
        release_id=fixture.release_a_id,
        original_student_message_id="message-not-yet-saved",
        original_question="What does this mechanism do?",
        chunks=release.chunks,
        created_at="2026-09-05T00:00:00+00:00",
        ttl=timedelta(hours=1),
    )

    assert resolve_clarification_option(request, "option 1") == request.options[0]
    assert (
        resolve_clarification_option(request, request.options[1].label)
        == request.options[1]
    )
    assert resolve_clarification_option(request, "both") is None
    with pytest.raises(ValidationError, match="complete lineage"):
        ClarificationRequestV1.model_validate(
            {
                **request.model_dump(mode="python"),
                "status": ClarificationStatus.RESOLVED,
            }
        )
