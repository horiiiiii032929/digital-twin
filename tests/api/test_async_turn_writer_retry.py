"""A real async checkpoint writer must be able to commit while a turn retries."""
import asyncio

import aiosqlite
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import pytest

from services.api.app.routers.student import _http_error
from src.digital_twin.student.models import Message
from src.digital_twin.student.repository import TurnAuthorityChangedError
from src.digital_twin.student import StudentWorkflowError
from tests.api.test_student_api import _client, KeywordEmbedder


@pytest.mark.asyncio
@pytest.mark.parametrize("interleaving", ["commit", "revoke", "deadline"])
async def test_checkpoint_writer_can_finish_without_losing_turn_invariants(tmp_path, interleaving):
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder())
    service = client.app.state.student_service
    conversation = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
    student = Message(id="retry-student", conversation_id=conversation.id, role="student",
        content="Synthetic question", action="ask", client_request_id="writer-retry")
    tutor = Message(id="retry-tutor", conversation_id=conversation.id, role="tutor",
        content="Synthetic answer", action="answer", response_to_message_id=student.id)
    args = (conversation, student, tutor, [], [])
    ready, release = asyncio.Event(), asyncio.Event()
    async with aiosqlite.connect(repository.path) as connection:
        saver = AsyncSqliteSaver(connection)
        await saver.setup()
        actual_commit = connection.commit
        async def delayed_commit():
            ready.set()
            await release.wait()
            await actual_commit()
        connection.commit = delayed_commit
        checkpoint_task = asyncio.create_task(saver.aput(
            {"configurable": {"thread_id": "real-writer", "checkpoint_ns": ""}},
            empty_checkpoint(), {"source": "input", "step": 0, "parents": {}}, {}))
        await asyncio.wait_for(ready.wait(), 1)
        retry_task = asyncio.create_task(service._save_turn_with_retry(*args,
            timeout_seconds=0.04 if interleaving == "deadline" else 1))
        # This must run promptly; the old synchronous 5s SQLite busy wait could
        # prevent both this coroutine and the checkpoint commit from advancing.
        await asyncio.sleep(0.02)
        assert repository._connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert repository._connection.in_transaction is False
        if interleaving == "revoke":
            await connection.execute("UPDATE accounts SET status='revoked' WHERE id=?", (fixture.student_a_id,))
        if interleaving == "deadline":
            with pytest.raises(StudentWorkflowError) as caught:
                await retry_task
            assert caught.value.code == "turn_storage_busy"
            assert _http_error(caught.value).status_code == 503
            assert repository.list_messages(conversation.id) == []
        release.set()
        await checkpoint_task
        if interleaving == "revoke":
            with pytest.raises(TurnAuthorityChangedError):
                await retry_task
            assert repository.list_messages(conversation.id) == []
        elif interleaving == "commit":
            await retry_task
            assert len(repository.list_messages(conversation.id)) == 2
        assert repository._connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    client.close()
    repository.close()


@pytest.mark.asyncio
async def test_duplicate_requests_wait_for_checkpoint_then_converge_without_regeneration(tmp_path):
    from tests.api.test_student_api import BarrierGenerator
    generator = BarrierGenerator()
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder(), generator=generator)
    service = client.app.state.student_service
    conversation = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
    ready, release = asyncio.Event(), asyncio.Event()
    async with aiosqlite.connect(repository.path) as connection:
        saver = AsyncSqliteSaver(connection)
        await saver.setup()
        actual_commit = connection.commit
        async def delayed_commit():
            ready.set()
            await release.wait()
            await actual_commit()
        connection.commit = delayed_commit
        checkpoint = asyncio.create_task(saver.aput(
            {"configurable": {"thread_id": "duplicate-writer", "checkpoint_ns": ""}},
            empty_checkpoint(), {"source": "input", "step": 0, "parents": {}}, {}))
        await ready.wait()
        tasks = [asyncio.create_task(service.submit_message(fixture.student_a_id, conversation.id,
            content="Explain cache coherence.", client_request_id="same-request")) for _ in range(2)]
        await generator.release.wait()
        await asyncio.sleep(0.02)
        assert not any(task.done() for task in tasks)
        release.set()
        await checkpoint
        first, second = await asyncio.gather(*tasks)
        assert sorted([first.duplicate, second.duplicate]) == [False, True]
        assert first.tutor_message.id == second.tutor_message.id
        assert len(repository.list_messages(conversation.id)) == 2
        assert generator.started == 2  # One per submitted request, none on writer retry.
    client.close()
    repository.close()
