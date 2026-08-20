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
    storage_deletions_pending: int = Field(default=0, ge=0)


class DeletionResult(BaseModel):
    target_type: str
    target_id: str
    database_rows_deleted: int = Field(ge=0)
    objects_deleted: int = Field(default=0, ge=0)
    storage_deletions_pending: int = Field(default=0, ge=0)


class StorageDeletionResult(BaseModel):
    records_completed: int = Field(default=0, ge=0)
    objects_deleted: int = Field(default=0, ge=0)
    referenced_records_released: int = Field(default=0, ge=0)
    deletions_pending: int = Field(default=0, ge=0)


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
    orphan_grace_minutes: int = 60,
    source_root: Path | None = None,
    region_crop_root: Path | None = None,
    now: datetime | None = None,
) -> RetentionResult:
    if terminal_job_days <= 0 or audit_days <= 0 or orphan_grace_minutes <= 0:
        raise ValueError("retention periods must be positive")
    current = now or datetime.now(UTC)
    job_cutoff = (current - timedelta(days=terminal_job_days)).isoformat()
    audit_cutoff = (current - timedelta(days=audit_days)).isoformat()
    orphan_cutoff = current - timedelta(minutes=orphan_grace_minutes)
    connection = _connect(database_path.resolve())
    orphan_candidates: set[str] = set()
    queue_ids: set[int] = set()
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
        orphan_candidates.update(
            key
            for key in object_store.iter_keys()
            if key not in still_referenced
            and datetime.fromtimestamp(
                (object_store.root / key).stat().st_mtime, UTC
            )
            < orphan_cutoff
        )
        queue_ids = _enqueue_storage_deletions(
            connection,
            storage_kind="object",
            refs=orphan_candidates - still_referenced,
            target_type="retention",
            target_id=job_cutoff,
        )
        referenced_derived = _all_derived_refs(connection)
        queue_ids |= _enqueue_storage_deletions(
            connection,
            storage_kind="derived",
            refs=(
                _derived_refs_on_disk(
                    source_root=source_root,
                    region_crop_root=region_crop_root,
                    older_than=orphan_cutoff,
                )
                - referenced_derived
            ),
            target_type="retention",
            target_id=job_cutoff,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    storage = drain_storage_deletions(
        database_path,
        object_store,
        source_root=source_root,
        region_crop_root=region_crop_root,
        queue_ids=queue_ids,
    )
    return RetentionResult(
        expired_sessions_deleted=sessions,
        terminal_jobs_deleted=jobs,
        audit_events_deleted=audits,
        unreferenced_objects_deleted=storage.objects_deleted,
        storage_deletions_pending=storage.deletions_pending,
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
    queue_ids: set[int] = set()
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
        remaining_derived_refs = _all_derived_refs(connection)
        queue_ids |= _enqueue_storage_deletions(
            connection,
            storage_kind="object",
            refs=candidate_keys - remaining,
            target_type="course",
            target_id=course_id,
        )
        queue_ids |= _enqueue_storage_deletions(
            connection,
            storage_kind="derived",
            refs=derived_refs - remaining_derived_refs,
            target_type="course",
            target_id=course_id,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    storage = drain_storage_deletions(
        database_path,
        object_store,
        source_root=source_root,
        region_crop_root=region_crop_root,
        queue_ids=queue_ids,
    )
    return DeletionResult(
        target_type="course",
        target_id=course_id,
        database_rows_deleted=deleted,
        objects_deleted=storage.objects_deleted,
        storage_deletions_pending=storage.deletions_pending,
    )


def drain_storage_deletions(
    database_path: Path,
    object_store: FileSystemObjectStore,
    *,
    source_root: Path | None = None,
    region_crop_root: Path | None = None,
    queue_ids: set[int] | None = None,
) -> StorageDeletionResult:
    """Retry durable object/derived-file cleanup without losing failed work."""
    connection = _connect(database_path.resolve())
    completed = 0
    objects_deleted = 0
    referenced_released = 0
    try:
        if queue_ids is not None and not queue_ids:
            return StorageDeletionResult()
        sql = "SELECT * FROM storage_deletion_queue"
        parameters: tuple[object, ...] = ()
        if queue_ids is not None:
            placeholders = ",".join("?" for _ in queue_ids)
            sql += f" WHERE id IN ({placeholders})"
            parameters = tuple(sorted(queue_ids))
        sql += " ORDER BY created_at, id"
        rows = connection.execute(sql, parameters).fetchall()
        for row in rows:
            connection.execute("BEGIN IMMEDIATE")
            try:
                current = connection.execute(
                    "SELECT * FROM storage_deletion_queue WHERE id = ?", (row["id"],)
                ).fetchone()
                if current is None:
                    connection.commit()
                    continue
                if _storage_ref_is_referenced(
                    connection, current["storage_kind"], current["storage_ref"]
                ):
                    connection.execute(
                        "DELETE FROM storage_deletion_queue WHERE id = ?", (current["id"],)
                    )
                    referenced_released += 1
                else:
                    deleted = _delete_storage_ref(
                        object_store,
                        current["storage_kind"],
                        current["storage_ref"],
                        source_root=source_root,
                        region_crop_root=region_crop_root,
                    )
                    connection.execute(
                        "DELETE FROM storage_deletion_queue WHERE id = ?", (current["id"],)
                    )
                    completed += 1
                    objects_deleted += int(deleted)
                connection.commit()
            except Exception as error:
                connection.rollback()
                connection.execute(
                    """UPDATE storage_deletion_queue SET
                         attempts = attempts + 1, last_error = ?, updated_at = ?
                       WHERE id = ?""",
                    (str(error)[:500], datetime.now(UTC).isoformat(), row["id"]),
                )
                connection.commit()
        pending_sql = "SELECT COUNT(*) FROM storage_deletion_queue"
        pending_parameters: tuple[object, ...] = ()
        if queue_ids is not None:
            placeholders = ",".join("?" for _ in queue_ids)
            pending_sql += f" WHERE id IN ({placeholders})"
            pending_parameters = tuple(sorted(queue_ids))
        pending = int(connection.execute(pending_sql, pending_parameters).fetchone()[0])
    finally:
        connection.close()
    return StorageDeletionResult(
        records_completed=completed,
        objects_deleted=objects_deleted,
        referenced_records_released=referenced_released,
        deletions_pending=pending,
    )


def _connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError("runtime database does not exist")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _enqueue_storage_deletions(
    connection: sqlite3.Connection,
    *,
    storage_kind: str,
    refs: set[str],
    target_type: str,
    target_id: str,
) -> set[int]:
    if storage_kind not in {"object", "derived"}:
        raise ValueError("unsupported storage deletion kind")
    now = datetime.now(UTC).isoformat()
    queue_ids: set[int] = set()
    for ref in sorted(refs):
        connection.execute(
            """INSERT INTO storage_deletion_queue
               (storage_kind, storage_ref, target_type, target_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(storage_kind, storage_ref) DO UPDATE SET
                 target_type = excluded.target_type,
                 target_id = excluded.target_id,
                 updated_at = excluded.updated_at""",
            (storage_kind, ref, target_type, target_id, now, now),
        )
        row = connection.execute(
            """SELECT id FROM storage_deletion_queue
               WHERE storage_kind = ? AND storage_ref = ?""",
            (storage_kind, ref),
        ).fetchone()
        if row is None:
            raise RuntimeError("storage deletion was not durably queued")
        queue_ids.add(int(row[0]))
    return queue_ids


def _all_derived_refs(connection: sqlite3.Connection) -> set[str]:
    refs: set[str] = set()
    for row in connection.execute(
        "SELECT result_json FROM ingestion_jobs WHERE result_json IS NOT NULL"
    ).fetchall():
        try:
            payload = json.loads(str(row[0]))
        except (TypeError, json.JSONDecodeError):
            continue
        values = payload.get("derived_storage_refs", [])
        if isinstance(values, list):
            refs.update(value for value in values if isinstance(value, str))
    return refs


def _derived_refs_on_disk(
    *,
    source_root: Path | None,
    region_crop_root: Path | None,
    older_than: datetime,
) -> set[str]:
    locations = (
        ("source", source_root),
        ("region", region_crop_root),
        ("figure", region_crop_root / "figures" if region_crop_root else None),
    )
    refs: set[str] = set()
    for scheme, configured_root in locations:
        if configured_root is None:
            continue
        root = configured_root.resolve()
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_dir() and not path.is_symlink():
                continue
            if not (path.is_file() or path.is_symlink()):
                continue
            modified = datetime.fromtimestamp(path.lstat().st_mtime, UTC)
            if modified < older_than:
                refs.add(f"{scheme}://{path.name}")
    return refs


def _storage_ref_is_referenced(
    connection: sqlite3.Connection, storage_kind: str, storage_ref: str
) -> bool:
    if storage_kind == "object":
        return connection.execute(
            "SELECT 1 FROM ingestion_jobs WHERE source_object_key = ? LIMIT 1",
            (storage_ref,),
        ).fetchone() is not None
    if storage_kind == "derived":
        return storage_ref in _all_derived_refs(connection)
    raise ValueError("unsupported storage deletion kind")


def _delete_storage_ref(
    object_store: FileSystemObjectStore,
    storage_kind: str,
    storage_ref: str,
    *,
    source_root: Path | None,
    region_crop_root: Path | None,
) -> bool:
    if storage_kind == "object":
        return object_store.delete(storage_ref)
    if storage_kind == "derived":
        return bool(
            _delete_derived_refs(
                {storage_ref},
                source_root=source_root,
                region_crop_root=region_crop_root,
            )
        )
    raise ValueError("unsupported storage deletion kind")


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
        lexical_candidate = root / name
        if lexical_candidate.is_symlink():
            lexical_candidate.unlink()
            deleted += 1
        elif candidate.is_relative_to(root) and candidate.is_file():
            candidate.unlink()
            deleted += 1
    return deleted
