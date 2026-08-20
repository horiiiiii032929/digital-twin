import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol

from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.student.migrations import apply_migrations


class SessionRepository(Protocol):
    def healthcheck(self) -> bool: ...

    def get(self, session_id: str) -> OnboardingSession | None: ...

    def save(self, session: OnboardingSession) -> OnboardingSession: ...

    def clear(self) -> None: ...


class SessionWriteConflictError(RuntimeError):
    """The caller attempted to save a stale or replaced session snapshot."""


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, OnboardingSession] = {}
        self._lock = RLock()

    def get(self, session_id: str) -> OnboardingSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
        return session.model_copy(deep=True) if session is not None else None

    def healthcheck(self) -> bool:
        return True

    def save(self, session: OnboardingSession) -> OnboardingSession:
        stored = session.model_copy(deep=True)
        with self._lock:
            existing = self._sessions.get(stored.session_id)
            if existing is None:
                if stored.revision != 0:
                    raise SessionWriteConflictError("onboarding session no longer exists")
                stored.revision = 1
            else:
                if existing.owner_account_id != stored.owner_account_id:
                    raise PermissionError("onboarding session owner mismatch")
                if existing.revision != stored.revision:
                    raise SessionWriteConflictError("onboarding session was updated")
                stored.revision += 1
            self._sessions[stored.session_id] = stored
        return stored.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


class SQLiteSessionRepository:
    """Restart-surviving onboarding sessions stored as versioned JSON."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.execute("PRAGMA journal_mode = WAL")
        apply_migrations(self._connection)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def healthcheck(self) -> bool:
        with self._lock:
            return self._connection.execute("SELECT 1").fetchone()[0] == 1

    def get(self, session_id: str) -> OnboardingSession | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT session_json, revision FROM onboarding_sessions
                   WHERE session_id = ?""",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        session = OnboardingSession.model_validate_json(row["session_json"])
        session.revision = int(row["revision"])
        return session

    def save(self, session: OnboardingSession) -> OnboardingSession:
        stored = session.model_copy(deep=True)
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._connection.execute(
                    """SELECT owner_account_id, revision FROM onboarding_sessions
                       WHERE session_id = ?""",
                    (stored.session_id,),
                ).fetchone()
                if row is None:
                    if stored.revision != 0:
                        raise SessionWriteConflictError(
                            "onboarding session no longer exists"
                        )
                    stored.revision = 1
                    self._connection.execute(
                        """INSERT INTO onboarding_sessions
                           (session_id, owner_account_id, session_json, revision, updated_at)
                           VALUES (?, ?, ?, ?, datetime('now'))""",
                        (
                            stored.session_id,
                            stored.owner_account_id,
                            stored.model_dump_json(),
                            stored.revision,
                        ),
                    )
                else:
                    if row["owner_account_id"] != stored.owner_account_id:
                        raise PermissionError("onboarding session owner mismatch")
                    if int(row["revision"]) != stored.revision:
                        raise SessionWriteConflictError(
                            "onboarding session was updated"
                        )
                    stored.revision += 1
                    cursor = self._connection.execute(
                        """UPDATE onboarding_sessions
                           SET session_json = ?, revision = ?, updated_at = datetime('now')
                           WHERE session_id = ? AND revision = ?""",
                        (
                            stored.model_dump_json(),
                            stored.revision,
                            stored.session_id,
                            stored.revision - 1,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise SessionWriteConflictError(
                            "onboarding session was updated"
                        )
            except Exception:
                self._connection.rollback()
                raise
            else:
                self._connection.commit()
        return stored.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM onboarding_sessions")


class ScopedSessionRepository:
    """Bind onboarding reads and writes to one authenticated professor."""

    def __init__(self, repository: SessionRepository, owner_account_id: str) -> None:
        self.repository = repository
        self.owner_account_id = owner_account_id

    def get(self, session_id: str) -> OnboardingSession | None:
        session = self.repository.get(session_id)
        if session is None or session.owner_account_id != self.owner_account_id:
            return None
        return session

    def healthcheck(self) -> bool:
        return self.repository.healthcheck()

    def save(self, session: OnboardingSession) -> OnboardingSession:
        if session.owner_account_id not in {None, self.owner_account_id}:
            raise PermissionError("onboarding session owner mismatch")
        return self.repository.save(
            session.model_copy(update={"owner_account_id": self.owner_account_id})
        )

    def clear(self) -> None:
        raise PermissionError("scoped repositories cannot clear all sessions")
