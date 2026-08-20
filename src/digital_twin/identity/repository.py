"""Repository contracts and SQLite adapter for credentials and sessions."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol

from src.digital_twin.identity.models import CredentialRecord, SessionRecord
from src.digital_twin.student.models import Account, AccountStatus, AuditEvent
from src.digital_twin.student.migrations import apply_migrations


class IdentityRepository(Protocol):
    def healthcheck(self) -> bool: ...

    def save_account_credential(
        self,
        account: Account,
        credential: CredentialRecord,
        audit_event: AuditEvent | None = None,
    ) -> CredentialRecord: ...

    def save_credential(self, credential: CredentialRecord) -> CredentialRecord: ...

    def get_credential_by_email(self, normalized_email: str) -> CredentialRecord | None: ...

    def get_credential(self, account_id: str) -> CredentialRecord | None: ...

    def save_session(
        self, session: SessionRecord, audit_event: AuditEvent | None = None
    ) -> SessionRecord: ...

    def get_session(self, token_digest: str) -> SessionRecord | None: ...

    def touch_session(self, token_digest: str, last_seen_at: str) -> None: ...

    def revoke_session(
        self,
        token_digest: str,
        revoked_at: str,
        audit_event: AuditEvent | None = None,
    ) -> None: ...

    def revoke_account_sessions(self, account_id: str, revoked_at: str) -> None: ...

    def replace_credential_and_revoke_sessions(
        self,
        credential: CredentialRecord,
        revoked_at: str,
        audit_event: AuditEvent | None = None,
    ) -> None: ...

    def revoke_account_and_sessions(
        self,
        account_id: str,
        revoked_at: str,
        audit_event: AuditEvent | None = None,
    ) -> bool: ...

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

    def healthcheck(self) -> bool:
        with self._lock:
            return self._connection.execute("SELECT 1").fetchone()[0] == 1

    def _initialize(self) -> None:
        with self._lock:
            apply_migrations(self._connection)

    def save_account_credential(
        self,
        account: Account,
        credential: CredentialRecord,
        audit_event: AuditEvent | None = None,
    ) -> CredentialRecord:
        account = Account.model_validate(account.model_dump(mode="python"))
        credential = CredentialRecord.model_validate(
            credential.model_dump(mode="python")
        )
        audit_event = _validated_audit_event(audit_event)
        if account.id != credential.account_id:
            raise ValueError("account and credential identities must match")
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT role FROM accounts WHERE id = ?", (account.id,)
            ).fetchone()
            if existing is not None and existing["role"] != account.role.value:
                raise ValueError("account role is immutable")
            self._connection.execute(
                """INSERT INTO accounts(id, role, status) VALUES (?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET status = excluded.status""",
                (account.id, account.role.value, account.status.value),
            )
            self._upsert_credential(credential)
            self._insert_audit_event(audit_event)
        return credential.model_copy(deep=True)

    def save_credential(self, credential: CredentialRecord) -> CredentialRecord:
        credential = CredentialRecord.model_validate(
            credential.model_dump(mode="python")
        )
        with self._lock, self._connection:
            self._upsert_credential(credential)
        return credential.model_copy(deep=True)

    def _upsert_credential(self, credential: CredentialRecord) -> None:
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

    def save_session(
        self, session: SessionRecord, audit_event: AuditEvent | None = None
    ) -> SessionRecord:
        session = SessionRecord.model_validate(session.model_dump(mode="python"))
        audit_event = _validated_audit_event(audit_event)
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
            self._insert_audit_event(audit_event)
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

    def revoke_session(
        self,
        token_digest: str,
        revoked_at: str,
        audit_event: AuditEvent | None = None,
    ) -> None:
        audit_event = _validated_audit_event(audit_event)
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE identity_sessions SET revoked_at = ?
                   WHERE token_digest = ? AND revoked_at IS NULL""",
                (revoked_at, token_digest),
            )
            self._insert_audit_event(audit_event)

    def revoke_account_sessions(self, account_id: str, revoked_at: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE identity_sessions SET revoked_at = ?
                   WHERE account_id = ? AND revoked_at IS NULL""",
                (revoked_at, account_id),
            )

    def replace_credential_and_revoke_sessions(
        self,
        credential: CredentialRecord,
        revoked_at: str,
        audit_event: AuditEvent | None = None,
    ) -> None:
        credential = CredentialRecord.model_validate(
            credential.model_dump(mode="python")
        )
        audit_event = _validated_audit_event(audit_event)
        with self._lock, self._connection:
            self._upsert_credential(credential)
            self._connection.execute(
                """UPDATE identity_sessions SET revoked_at = ?
                   WHERE account_id = ? AND revoked_at IS NULL""",
                (revoked_at, credential.account_id),
            )
            self._insert_audit_event(audit_event)

    def revoke_account_and_sessions(
        self,
        account_id: str,
        revoked_at: str,
        audit_event: AuditEvent | None = None,
    ) -> bool:
        audit_event = _validated_audit_event(audit_event)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE accounts SET status = ? WHERE id = ?",
                (AccountStatus.REVOKED.value, account_id),
            )
            if cursor.rowcount != 1:
                return False
            self._connection.execute(
                """UPDATE identity_sessions SET revoked_at = ?
                   WHERE account_id = ? AND revoked_at IS NULL""",
                (revoked_at, account_id),
            )
            self._insert_audit_event(audit_event)
        return True

    def _insert_audit_event(self, event: AuditEvent | None) -> None:
        if event is None:
            return
        self._connection.execute(
            """INSERT INTO audit_events
               (id, event_type, account_id, course_id, release_id,
                conversation_id, details_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.id,
                event.event_type,
                event.account_id,
                event.course_id,
                event.release_id,
                event.conversation_id,
                json.dumps(event.details, sort_keys=True),
                event.created_at,
            ),
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


def _validated_audit_event(event: AuditEvent | None) -> AuditEvent | None:
    if event is None:
        return None
    return AuditEvent.model_validate(event.model_dump(mode="python"))
