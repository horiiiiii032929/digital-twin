"""Run the network-free synthetic acceptance journey for the student slice."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from src.digital_twin.student import (
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    StudentWorkflowError,
    seed_synthetic_student_workflow,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"


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


class RaisingGenerator:
    implementation_id = "synthetic-raising-generator"

    async def generate(self, question, hits, policy):
        del question, hits, policy
        raise RuntimeError("synthetic malformed provider output")


async def verify_student_workflow_slice() -> dict:
    checks: list[dict[str, str | bool]] = []
    with tempfile.TemporaryDirectory(prefix="digital-twin-student-") as directory:
        root = Path(directory)
        database = root / "primary.sqlite3"
        repository = SQLiteStudentRepository(database)
        fixture = seed_synthetic_student_workflow(repository)
        service = StudentTutoringService(
            repository,
            profile_path=PROFILE,
            embedder=KeywordEmbedder(),
        )

        courses = service.list_courses(fixture.student_a_id)
        _record(checks, "assigned-published-course", len(courses) == 1)
        conversation = service.create_conversation(
            fixture.student_a_id, fixture.course_a_id
        )
        _record(checks, "conversation-created", bool(conversation.id))
        turn = await service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="What does cache coherence do?",
            client_request_id="primary-turn",
        )
        _record(checks, "selected-m2-turn", turn.tutor_message.action == "answer")
        _record(checks, "citation-persisted", len(turn.citations) == 1)
        citation_rows = service.list_citations(
            fixture.student_a_id, turn.tutor_message.id
        )
        _record(checks, "citation-lookup", citation_rows == turn.citations)
        duplicate = await service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="What does cache coherence do?",
            client_request_id="primary-turn",
        )
        _record(
            checks,
            "duplicate-request-idempotent",
            duplicate.duplicate and duplicate.tutor_message.id == turn.tutor_message.id,
        )
        _expect_error(
            checks,
            "cross-course-denied",
            "course_access_denied",
            lambda: service.create_conversation(
                fixture.student_a_id, fixture.course_b_id
            ),
        )
        _expect_error(
            checks,
            "cross-student-conversation-denied",
            "conversation_access_denied",
            lambda: service.get_conversation(fixture.student_b_id, conversation.id),
        )
        _expect_error(
            checks,
            "revoked-account-denied",
            "account_inactive",
            lambda: service.list_courses(fixture.revoked_student_id),
        )
        repository.close()

        restarted = SQLiteStudentRepository(database)
        restarted_service = StudentTutoringService(
            restarted,
            profile_path=PROFILE,
            embedder=KeywordEmbedder(),
        )
        restored = restarted_service.get_conversation(
            fixture.student_a_id, conversation.id
        )
        _record(checks, "restart-persistence", len(restored.messages) == 2)
        restarted.set_release_status(
            fixture.release_a_id, StudentReleaseStatus.WITHDRAWN
        )
        await _expect_async_error(
            checks,
            "withdrawn-release-denied",
            "release_unavailable",
            restarted_service.submit_message(
                fixture.student_a_id,
                conversation.id,
                content="Can I ask another question?",
                client_request_id="withdrawn-turn",
            ),
        )
        restarted.close()

        fallback_repository = SQLiteStudentRepository(root / "fallback.sqlite3")
        fallback_fixture = seed_synthetic_student_workflow(fallback_repository)
        fallback_service = StudentTutoringService(
            fallback_repository,
            profile_path=PROFILE,
            embedder=QueryFailingEmbedder(),
        )
        fallback_conversation = fallback_service.create_conversation(
            fallback_fixture.student_a_id, fallback_fixture.course_a_id
        )
        fallback_turn = await fallback_service.submit_message(
            fallback_fixture.student_a_id,
            fallback_conversation.id,
            content="Explain cache coherence.",
            client_request_id="fallback-turn",
        )
        fallback_events = fallback_repository.list_audit_events()
        _record(
            checks,
            "bm25-provider-fallback",
            bool(fallback_turn.citations)
            and any(event.event_type == "retrieval-fallback" for event in fallback_events),
        )
        serialized_audit = " ".join(
            event.model_dump_json() for event in fallback_events
        )
        _record(
            checks,
            "redacted-audit",
            "Explain cache coherence" not in serialized_audit
            and "synthetic provider outage" not in serialized_audit,
        )
        fallback_repository.close()

        malformed_repository = SQLiteStudentRepository(root / "malformed.sqlite3")
        malformed_fixture = seed_synthetic_student_workflow(malformed_repository)
        malformed_service = StudentTutoringService(
            malformed_repository,
            profile_path=PROFILE,
            embedder=KeywordEmbedder(),
            generator=RaisingGenerator(),
        )
        malformed_conversation = malformed_service.create_conversation(
            malformed_fixture.student_a_id, malformed_fixture.course_a_id
        )
        malformed_turn = await malformed_service.submit_message(
            malformed_fixture.student_a_id,
            malformed_conversation.id,
            content="Explain cache coherence.",
            client_request_id="malformed-turn",
        )
        _record(
            checks,
            "malformed-generation-safe-failure",
            malformed_turn.tutor_message.action == "safe-provider-failure"
            and not malformed_turn.citations,
        )
        malformed_repository.close()

    passed = sum(bool(check["passed"]) for check in checks)
    result = {
        "verification_id": "student-workflow-slice-v1-synthetic",
        "status": "passed" if passed == len(checks) else "failed",
        "case_count": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
        "network_called": False,
        "private_data_used": False,
        "checks": checks,
    }
    if result["status"] != "passed":
        raise AssertionError(json.dumps(result, indent=2))
    return result


def _record(checks: list[dict[str, str | bool]], name: str, passed: bool) -> None:
    checks.append({"name": name, "passed": bool(passed)})


def _expect_error(checks, name, code, operation) -> None:
    try:
        operation()
    except StudentWorkflowError as error:
        _record(checks, name, error.code == code)
        return
    _record(checks, name, False)


async def _expect_async_error(checks, name, code, operation) -> None:
    try:
        await operation
    except StudentWorkflowError as error:
        _record(checks, name, error.code == code)
        return
    _record(checks, name, False)


def main() -> None:
    print(json.dumps(asyncio.run(verify_student_workflow_slice()), indent=2))


if __name__ == "__main__":
    main()
