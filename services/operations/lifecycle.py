"""Explicit retention, privacy export, and deletion operations for staging."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from services.storage import FileSystemObjectStore


class RetentionResult(BaseModel):
    expired_sessions_deleted: int = Field(ge=0)
    terminal_jobs_deleted: int = Field(ge=0)
    audit_events_deleted: int = Field(ge=0)
    unreferenced_objects_deleted: int = Field(ge=0)


class DeletionResult(BaseModel):
    target_type: str
    target_id: str
    database_rows_deleted: int = Field(ge=0)
    objects_deleted: int = Field(default=0, ge=0)


def export_account_data(
    database_path: Path,
    account_id: str,
    output_path: Path,
) -> dict[str, Any]:
    """Write a redacted account export without password hashes or session tokens."""
    database_path = database_path.resolve()
    output_path = output_path.resolve()
    if output_path == database_path:
        raise ValueError("export output cannot overwrite the runtime database")
    connection = _connect(database_path)
    try:
        identity = _one_dict(
            connection,
            """SELECT a.id AS account_id, a.role, a.status, c.email, c.display_name,
                      c.created_at, c.updated_at
               FROM accounts a LEFT JOIN identity_credentials c ON c.account_id = a.id
               WHERE a.id = ?""",
            (account_id,),
        )
        if identity is None:
            raise KeyError("account_not_found")
        memberships = _rows(
            connection,
            "SELECT course_id, role, active FROM memberships WHERE account_id = ?",
            (account_id,),
        )
        owned_courses = _rows(
            connection,
            "SELECT id, title FROM courses WHERE owner_professor_id = ?",
            (account_id,),
        )
        onboarding = _rows(
            connection,
            """SELECT session_id, session_json, updated_at FROM onboarding_sessions
               WHERE owner_account_id = ?""",
            (account_id,),
        )
        conversation_ids = [
            row["id"]
            for row in _rows(
                connection,
                "SELECT id FROM conversations WHERE student_id = ?",
                (account_id,),
            )
        ]
        conversations = _by_ids(connection, "conversations", conversation_ids)
        message_ids = [
            row["id"]
            for row in _rows_for_foreign_ids(
                connection, "messages", "conversation_id", conversation_ids
            )
        ]
        messages = _by_ids(connection, "messages", message_ids)
        citations = _rows_for_foreign_ids(
            connection, "citations", "message_id", message_ids
        )
        audit_events = _rows(
            connection,
            """SELECT event_type, course_id, release_id, conversation_id,
                      details_json, created_at FROM audit_events WHERE account_id = ?""",
            (account_id,),
        )
        payload: dict[str, Any] = {
            "format_version": 1,
            "exported_at": datetime.now(UTC).isoformat(),
            "account": identity,
            "memberships": memberships,
            "owned_courses": owned_courses,
            "onboarding_sessions": onboarding,
            "conversations": conversations,
            "messages": messages,
            "citations": citations,
            "audit_events": audit_events,
            "excluded": [
                "password hashes",
                "session tokens and digests",
                "other users' conversations",
                "raw source file contents",
            ],
        }
    finally:
        connection.close()
    _atomic_json(output_path, payload)
    return payload


def prune_runtime_data(
    database_path: Path,
    object_store: FileSystemObjectStore,
    *,
    terminal_job_days: int = 30,
    audit_days: int = 365,
    now: datetime | None = None,
) -> RetentionResult:
    if terminal_job_days <= 0 or audit_days <= 0:
        raise ValueError("retention periods must be positive")
    current = now or datetime.now(UTC)
    job_cutoff = (current - timedelta(days=terminal_job_days)).isoformat()
    audit_cutoff = (current - timedelta(days=audit_days)).isoformat()
    connection = _connect(database_path.resolve())
    orphan_candidates: set[str] = set()
    try:
        connection.execute("BEGIN IMMEDIATE")
        sessions = connection.execute(
            "DELETE FROM identity_sessions WHERE expires_at <= ?",
            (current.isoformat(),),
        ).rowcount
        orphan_candidates = {
            str(row[0])
            for row in connection.execute(
                """SELECT source_object_key FROM ingestion_jobs
                   WHERE status IN ('failed', 'cancelled')
                     AND updated_at < ?""",
                (job_cutoff,),
            ).fetchall()
        }
        jobs = connection.execute(
            """DELETE FROM ingestion_jobs
               WHERE status IN ('failed', 'cancelled')
                 AND updated_at < ?""",
            (job_cutoff,),
        ).rowcount
        audits = connection.execute(
            "DELETE FROM audit_events WHERE created_at < ?", (audit_cutoff,)
        ).rowcount
        still_referenced = {
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT source_object_key FROM ingestion_jobs"
            ).fetchall()
        }
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    deleted_objects = sum(
        object_store.delete(key)
        for key in sorted(orphan_candidates - still_referenced)
    )
    return RetentionResult(
        expired_sessions_deleted=sessions,
        terminal_jobs_deleted=jobs,
        audit_events_deleted=audits,
        unreferenced_objects_deleted=deleted_objects,
    )


def delete_account_data(database_path: Path, account_id: str) -> DeletionResult:
    """Delete one non-admin account after owned courses are removed explicitly."""
    connection = _connect(database_path.resolve())
    deleted = 0
    try:
        connection.execute("BEGIN IMMEDIATE")
        account = connection.execute(
            "SELECT role FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if account is None:
            raise KeyError("account_not_found")
        if account["role"] == "admin":
            raise ValueError("administrator accounts must be revoked, not deleted")
        if connection.execute(
            "SELECT 1 FROM courses WHERE owner_professor_id = ? LIMIT 1", (account_id,)
        ).fetchone():
            raise ValueError("delete owned courses before deleting a professor account")
        conversation_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT id FROM conversations WHERE student_id = ?", (account_id,)
            ).fetchall()
        ]
        deleted += _delete_children(connection, conversation_ids)
        for sql in (
            "DELETE FROM memberships WHERE account_id = ?",
            "DELETE FROM onboarding_sessions WHERE owner_account_id = ?",
            "DELETE FROM identity_sessions WHERE account_id = ?",
            "DELETE FROM identity_credentials WHERE account_id = ?",
            "DELETE FROM audit_events WHERE account_id = ?",
            "DELETE FROM accounts WHERE id = ?",
        ):
            deleted += connection.execute(sql, (account_id,)).rowcount
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return DeletionResult(
        target_type="account",
        target_id=account_id,
        database_rows_deleted=deleted,
    )


def delete_course_data(
    database_path: Path,
    object_store: FileSystemObjectStore,
    course_id: str,
    *,
    source_root: Path | None = None,
    region_crop_root: Path | None = None,
) -> DeletionResult:
    """Delete a course graph and its now-unreferenced raw source objects."""
    connection = _connect(database_path.resolve())
    deleted = 0
    candidate_keys: set[str] = set()
    derived_refs: set[str] = set()
    try:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM courses WHERE id = ?", (course_id,)
        ).fetchone() is None:
            raise KeyError("course_not_found")
        if connection.execute(
            """SELECT 1 FROM ingestion_jobs
               WHERE course_id = ? AND status = 'running' LIMIT 1""",
            (course_id,),
        ).fetchone():
            raise RuntimeError("stop or drain running course ingestion before deletion")
        candidate_keys = {
            str(row[0])
            for row in connection.execute(
                "SELECT source_object_key FROM ingestion_jobs WHERE course_id = ?",
                (course_id,),
            ).fetchall()
        }
        for row in connection.execute(
            "SELECT result_json FROM ingestion_jobs WHERE course_id = ?",
            (course_id,),
        ).fetchall():
            if row[0]:
                payload = json.loads(str(row[0]))
                derived_refs.update(payload.get("derived_storage_refs", []))
        conversation_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT id FROM conversations WHERE course_id = ?", (course_id,)
            ).fetchall()
        ]
        deleted += _delete_children(connection, conversation_ids)
        release_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT id FROM releases WHERE course_id = ?", (course_id,)
            ).fetchall()
        ]
        deleted += _delete_for_ids(connection, "release_chunks", "release_id", release_ids)
        for sql in (
            "DELETE FROM citations WHERE course_id = ?",
            "DELETE FROM ingestion_jobs WHERE course_id = ?",
            "DELETE FROM releases WHERE course_id = ?",
            "DELETE FROM memberships WHERE course_id = ?",
            "DELETE FROM audit_events WHERE course_id = ?",
            "DELETE FROM courses WHERE id = ?",
        ):
            deleted += connection.execute(sql, (course_id,)).rowcount
        remaining = {
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT source_object_key FROM ingestion_jobs"
            ).fetchall()
        }
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    objects_deleted = sum(
        object_store.delete(key) for key in sorted(candidate_keys - remaining)
    )
    derived_deleted = _delete_derived_refs(
        derived_refs,
        source_root=source_root,
        region_crop_root=region_crop_root,
    )
    return DeletionResult(
        target_type="course",
        target_id=course_id,
        database_rows_deleted=deleted,
        objects_deleted=objects_deleted + derived_deleted,
    )


def _connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError("runtime database does not exist")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _delete_children(connection: sqlite3.Connection, conversation_ids: list[str]) -> int:
    message_ids = [
        str(row[0])
        for row in _select_for_ids(connection, "messages", "conversation_id", conversation_ids)
    ]
    deleted = _delete_for_ids(connection, "citations", "message_id", message_ids)
    deleted += _delete_for_ids(connection, "messages", "conversation_id", conversation_ids)
    deleted += _delete_for_ids(connection, "conversations", "id", conversation_ids)
    return deleted


def _select_for_ids(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    values: list[str],
) -> list[sqlite3.Row]:
    if not values:
        return []
    placeholders = ",".join("?" for _ in values)
    return connection.execute(
        f"SELECT id FROM {table} WHERE {column} IN ({placeholders})", values
    ).fetchall()


def _delete_for_ids(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    values: list[str],
) -> int:
    if not values:
        return 0
    placeholders = ",".join("?" for _ in values)
    return connection.execute(
        f"DELETE FROM {table} WHERE {column} IN ({placeholders})", values
    ).rowcount


def _one_dict(
    connection: sqlite3.Connection, sql: str, parameters: tuple[object, ...]
) -> dict[str, Any] | None:
    row = connection.execute(sql, parameters).fetchone()
    return dict(row) if row else None


def _rows(
    connection: sqlite3.Connection, sql: str, parameters: tuple[object, ...]
) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(sql, parameters).fetchall()]


def _by_ids(
    connection: sqlite3.Connection, table: str, values: list[str]
) -> list[dict[str, Any]]:
    return _rows_for_foreign_ids(connection, table, "id", values)


def _rows_for_foreign_ids(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    values: list[str],
) -> list[dict[str, Any]]:
    if not values:
        return []
    placeholders = ",".join("?" for _ in values)
    return _rows(
        connection,
        f"SELECT * FROM {table} WHERE {column} IN ({placeholders})",
        tuple(values),
    )


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{path.name}-", suffix=".pending", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _delete_derived_refs(
    refs: set[str],
    *,
    source_root: Path | None,
    region_crop_root: Path | None,
) -> int:
    deleted = 0
    roots = {
        "source": source_root.resolve() if source_root else None,
        "region": region_crop_root.resolve() if region_crop_root else None,
        "figure": (
            (region_crop_root / "figures").resolve() if region_crop_root else None
        ),
    }
    for ref in sorted(refs):
        scheme, separator, name = ref.partition("://")
        root = roots.get(scheme)
        if not separator or root is None or not name or "/" in name or "\\" in name:
            continue
        candidate = (root / name).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            candidate.unlink()
            deleted += 1
    return deleted
