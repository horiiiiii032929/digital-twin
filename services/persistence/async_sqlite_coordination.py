"""Coordinate short SQLite operations without locking async model generation.

The registry does not keep loops or idle locks alive. This is local contention
control, not a replacement for SQLite transactions or cross-process locking.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from weakref import WeakKeyDictionary, WeakValueDictionary

import aiosqlite

_registry: WeakKeyDictionary[
    asyncio.AbstractEventLoop, WeakValueDictionary[str, asyncio.Lock]
] = WeakKeyDictionary()
_registry_lock = Lock()


def database_operation_lock(database: str | Path) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    path = str(Path(database).resolve())
    with _registry_lock:
        locks = _registry.get(loop)
        if locks is None:
            locks = WeakValueDictionary()
            _registry[loop] = locks
        lock = locks.get(path)
        if lock is None:
            lock = asyncio.Lock()
            locks[path] = lock
        return lock


@asynccontextmanager
async def coordinated_connection(
    database: str | Path,
) -> AsyncIterator[aiosqlite.Connection]:
    # Close (and roll back uncommitted work) before releasing the mutex, also
    # when a waiting caller is cancelled. Explicit commits remain caller-owned.
    async with database_operation_lock(database):
        async with aiosqlite.connect(database) as connection:
            yield connection
