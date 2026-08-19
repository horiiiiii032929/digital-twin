"""Repository contracts and SQLite adapter for credentials and sessions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol

from src.digital_twin.identity.models import CredentialRecord, SessionRecord


class IdentityRepository(Protocol):
    def save_credential(self, credential: CredentialRecord) -> CredentialRecord: ...

    def get_credential_by_email(self, normalized_email: str) -> CredentialRecord | None: ...

    def get_credential(self, account_id: str) -> CredentialRecord | None: ...

    def save_session(self, session: SessionRecord) -> SessionRecord: ...

    def get_session(self, token_digest: str) -> SessionRecord | None: ...

    def touch_session(self, token_digest: str, last_seen_at: str) -> None: ...

    def revoke_session(self, token_digest: str, revoked_at: str) -> None: ...

    def revoke_account_sessions(self, account_id: str, revoked_at: str) -> None: ...

    def delete_expired_sessions(self, before: str) -> int: ...


class SQLiteIdentityRepository:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        if self.path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS identity_credentials (
                    account_id TEXT PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
                    email TEXT NOT NULL,
                    normalized_email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS identity_sessions (
                    token_digest TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    revoked_at TEXT
                );
                CREATE INDEX IF NOT EXISTS identity_sessions_account_idx
                    ON identity_sessions(account_id);
                CREATE INDEX IF NOT EXISTS identity_sessions_expiry_idx
                    ON identity_sessions(expires_at);
                """
            )

    def save_credential(self, credential: CredentialRecord) -> CredentialRecord:
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO identity_credentials
                   (account_id, email, normalized_email, display_name, password_hash,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(account_id) DO UPDATE SET
                     email = excluded.email,
                     normalized_email = excluded.normalized_email,
                     display_name = excluded.display_name,
                     password_hash = excluded.password_hash,
                     updated_at = excluded.updated_at""",
                (
                    credential.account_id,
                    credential.email,
                    credential.normalized_email,
                    credential.display_name,
                    credential.password_hash,
                    credential.created_at,
                    credential.updated_at,
                ),
            )
        return credential.model_copy(deep=True)

    def get_credential_by_email(
        self, normalized_email: str
    ) -> CredentialRecord | None:
        return self._credential(
            "SELECT * FROM identity_credentials WHERE normalized_email = ?",
            (normalized_email,),
        )

    def get_credential(self, account_id: str) -> CredentialRecord | None:
        return self._credential(
            "SELECT * FROM identity_credentials WHERE account_id = ?", (account_id,)
        )

    def save_session(self, session: SessionRecord) -> SessionRecord:
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO identity_sessions
                   (token_digest, account_id, created_at, expires_at, last_seen_at,
                    revoked_at) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session.token_digest,
                    session.account_id,
                    session.created_at,
                    session.expires_at,
                    session.last_seen_at,
                    session.revoked_at,
                ),
            )
        return session.model_copy(deep=True)

    def get_session(self, token_digest: str) -> SessionRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM identity_sessions WHERE token_digest = ?",
                (token_digest,),
            ).fetchone()
        return SessionRecord.model_validate(dict(row)) if row else None

    def touch_session(self, token_digest: str, last_seen_at: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE identity_sessions SET last_seen_at = ? WHERE token_digest = ?",
                (last_seen_at, token_digest),
            )

    def revoke_session(self, token_digest: str, revoked_at: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE identity_sessions SET revoked_at = ?
                   WHERE token_digest = ? AND revoked_at IS NULL""",
                (revoked_at, token_digest),
            )

    def revoke_account_sessions(self, account_id: str, revoked_at: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE identity_sessions SET revoked_at = ?
                   WHERE account_id = ? AND revoked_at IS NULL""",
                (revoked_at, account_id),
            )

    def delete_expired_sessions(self, before: str) -> int:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM identity_sessions WHERE expires_at <= ?", (before,)
            )
            return cursor.rowcount

    def _credential(
        self, sql: str, parameters: tuple[object, ...]
    ) -> CredentialRecord | None:
        with self._lock:
            row = self._connection.execute(sql, parameters).fetchone()
        return CredentialRecord.model_validate(dict(row)) if row else None
