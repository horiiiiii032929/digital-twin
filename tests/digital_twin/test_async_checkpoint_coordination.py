"""Shared checkpoints coordinate writes while independent tutoring calls overlap."""
import asyncio
import gc
import weakref

import aiosqlite
import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from services.persistence.async_sqlite_coordination import (
    coordinated_connection,
    database_operation_lock,
)


@pytest.mark.asyncio
async def test_path_aliases_and_saver_instances_share_ledger_writer_lock(tmp_path):
    database = tmp_path / 'checkpoint.sqlite3'
    alias = tmp_path / 'alias.sqlite3'
    database.touch()
    alias.symlink_to(database)
    lock = database_operation_lock(database)
    assert database_operation_lock(alias) is lock
    assert database_operation_lock(tmp_path / 'other.sqlite3') is not lock
    async with aiosqlite.connect(database) as first, aiosqlite.connect(alias) as second:
        savers = [AsyncSqliteSaver(first), AsyncSqliteSaver(second)]
        for saver in savers:
            saver.lock = database_operation_lock(database)
            await saver.setup()
        async with coordinated_connection(alias) as writer:
            await writer.execute('CREATE TABLE IF NOT EXISTS ledger (value INTEGER)')
            await writer.commit()
            await writer.execute('INSERT INTO ledger VALUES (1)')
            config = {'configurable': {'thread_id': 'synthetic', 'checkpoint_ns': '', 'checkpoint_id': 'checkpoint'}}
            pending = asyncio.create_task(savers[1].aput_writes(config, [('answer', 'synthetic')], 'task'))
            await asyncio.sleep(0)
            assert not pending.done()
            await writer.commit()
        await asyncio.wait_for(pending, 2)
        async with second.execute('SELECT COUNT(*) FROM writes') as cursor:
            assert (await cursor.fetchone())[0] == 1


@pytest.mark.asyncio
async def test_cancelled_ledger_transaction_rolls_back_before_next_writer(tmp_path):
    database = tmp_path / 'cancel.sqlite3'
    async with coordinated_connection(database) as connection:
        await connection.execute('CREATE TABLE ledger (value INTEGER)')
        await connection.commit()
    entered = asyncio.Event()

    async def interrupted():
        async with coordinated_connection(database) as connection:
            await connection.execute('INSERT INTO ledger VALUES (1)')
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(interrupted())
    await asyncio.wait_for(entered.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with coordinated_connection(database) as connection:
        async with connection.execute('SELECT COUNT(*) FROM ledger') as cursor:
            assert (await cursor.fetchone())[0] == 0
        await connection.execute('INSERT INTO ledger VALUES (2)')
        await connection.commit()


def test_registry_does_not_reuse_loop_bound_locks_or_keep_idle_locks_alive(tmp_path):
    locks = []

    async def contend():
        lock = database_operation_lock(tmp_path / 'same.sqlite3')
        async with lock:
            pending = asyncio.create_task(lock.acquire())
            await asyncio.sleep(0)
        await pending
        lock.release()
        locks.append(lock)

    asyncio.run(contend())
    asyncio.run(contend())
    assert locks[0] is not locks[1]
    references = [weakref.ref(lock) for lock in locks]
    locks.clear()
    gc.collect()
    assert all(ref() is None for ref in references)


@pytest.mark.asyncio
async def test_graph_savers_share_lock_without_serializing_provider_calls(tmp_path, monkeypatch):
    from scripts import run_asgi_tutoring_concurrency_development as runner
    from src.digital_twin.grounding.models import GenerationUsage
    from src.digital_twin.llm import LlmResponse
    from src.digital_twin.student import tutoring_graph

    class BarrierClient:
        def __init__(self):
            self.arrived = 0
            self.active = 0
            self.peak = 0
            self.both = asyncio.Event()

        async def chat(self, messages, task):
            self.arrived += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
            if self.arrived == 2:
                self.both.set()
            try:
                # This deadline catches a lock incorrectly held across model work;
                # it is not a throughput/performance threshold.
                await asyncio.wait_for(self.both.wait(), 5)
                return LlmResponse(content='{}', provider_model=runner.MODEL,
                    provider_revision='synthetic-barrier', usage=GenerationUsage(
                        input_tokens=10, output_tokens=5, total_tokens=15,
                        approximate_cost_usd=0.001))
            finally:
                self.active -= 1

    savers = []
    original = tutoring_graph.AsyncSqliteSaver

    def record_saver(*args, **kwargs):
        saver = original(*args, **kwargs)
        savers.append(saver)
        return saver

    monkeypatch.setattr(tutoring_graph, 'AsyncSqliteSaver', record_saver)
    provider = BarrierClient()
    result = await runner.run(tmp_path / 'run', contract=True, students=2, turns=1,
        injected_client=provider, provider_max_concurrency=5)
    assert result.get('error') is None
    assert result['probe']['failure_count'] == 0
    assert result['persistence_counts_pass']
    assert result['provider_attempts'] == provider.arrived == 2
    assert provider.peak == 2
    assert len(savers) == 2 and savers[0].lock is savers[1].lock
