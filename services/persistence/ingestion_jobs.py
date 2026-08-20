"""SQLite-backed leased ingestion queue."""

from __future__ import annotations

import sqlite3
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock

from src.digital_twin.operations import (
    IngestionJob,
    IngestionJobResult,
    IngestionJobStatus,
)
from src.digital_twin.student.migrations import apply_migrations


class SQLiteIngestionJobRepository:
    def __init__(self, path: str | Path) -> None:
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
        apply_migrations(self._connection)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def healthcheck(self) -> bool:
        with self._lock:
            return self._connection.execute("SELECT 1").fetchone()[0] == 1

    def enqueue(self, job: IngestionJob) -> tuple[IngestionJob, bool]:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """INSERT OR IGNORE INTO ingestion_jobs
                   (id, idempotency_key, course_id, artifact_id, title, version,
                    professor_id, display_allowed, source_label, source_object_key,
                    source_checksum, status, attempts, max_attempts, lease_owner,
                    lease_expires_at, error_code, error_message, result_json,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                _job_values(job),
            )
            created = cursor.rowcount == 1
            row = self._connection.execute(
                """SELECT * FROM ingestion_jobs
                   WHERE professor_id = ? AND course_id = ? AND idempotency_key = ?""",
                (job.professor_id, job.course_id, job.idempotency_key),
            ).fetchone()
        if row is None:
            raise RuntimeError("ingestion job enqueue did not return a row")
        return _job(row), created

    def get(self, job_id: str) -> IngestionJob | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM ingestion_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return _job(row) if row else None

    def list_for_course(self, professor_id: str, course_id: str) -> list[IngestionJob]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM ingestion_jobs
                   WHERE professor_id = ? AND course_id = ?
                   ORDER BY created_at DESC, id DESC""",
                (professor_id, course_id),
            ).fetchall()
        return [_job(row) for row in rows]

    def get_by_idempotency_key(
        self, professor_id: str, course_id: str, idempotency_key: str
    ) -> IngestionJob | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT * FROM ingestion_jobs
                   WHERE professor_id = ? AND course_id = ? AND idempotency_key = ?""",
                (professor_id, course_id, idempotency_key),
            ).fetchone()
        return _job(row) if row else None

    def claim(self, worker_id: str, *, lease_seconds: int) -> IngestionJob | None:
        if (
            not worker_id.strip()
            or isinstance(lease_seconds, bool)
            or not isinstance(lease_seconds, (int, float))
            or not math.isfinite(lease_seconds)
            or lease_seconds <= 0
        ):
            raise ValueError("worker_id and a positive lease are required")
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=lease_seconds)
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._recover_expired(now.isoformat())
                row = self._connection.execute(
                    """SELECT id FROM ingestion_jobs
                       WHERE status = ? AND attempts < max_attempts
                       ORDER BY created_at, id LIMIT 1""",
                    (IngestionJobStatus.PENDING.value,),
                ).fetchone()
                if row is None:
                    self._connection.commit()
                    return None
                updated = self._connection.execute(
                    """UPDATE ingestion_jobs SET
                         status = ?, attempts = attempts + 1, lease_owner = ?,
                         lease_expires_at = ?, updated_at = ?
                       WHERE id = ? AND status = ?""",
                    (
                        IngestionJobStatus.RUNNING.value,
                        worker_id,
                        expires.isoformat(),
                        now.isoformat(),
                        row["id"],
                        IngestionJobStatus.PENDING.value,
                    ),
                )
                if updated.rowcount != 1:
                    self._connection.rollback()
                    return None
                claimed = self._connection.execute(
                    "SELECT * FROM ingestion_jobs WHERE id = ?", (row["id"],)
                ).fetchone()
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise
        return _job(claimed)

    def complete(self, job_id: str, worker_id: str, result_json: str) -> bool:
        now = _timestamp()
        result = IngestionJobResult.model_validate_json(result_json)
        with self._lock, self._connection:
            job = self._connection.execute(
                """SELECT course_id, artifact_id, version, source_checksum
                   FROM ingestion_jobs WHERE id = ?""",
                (job_id,),
            ).fetchone()
            if job is None:
                return False
            if (
                result.source_artifact_id
                != f"{job['course_id']}:{job['artifact_id']}"
                or result.source_version != job["version"]
                or result.source_checksum != job["source_checksum"]
            ):
                raise ValueError("ingestion result does not match the claimed source")
            cursor = self._connection.execute(
                """UPDATE ingestion_jobs SET
                     status = ?, result_json = ?, error_code = NULL,
                     error_message = NULL, lease_owner = NULL,
                     lease_expires_at = NULL, updated_at = ?
                   WHERE id = ? AND status = ? AND lease_owner = ?
                     AND lease_expires_at > ?""",
                (
                    IngestionJobStatus.SUCCEEDED.value,
                    result_json,
                    now,
                    job_id,
                    IngestionJobStatus.RUNNING.value,
                    worker_id,
                    now,
                ),
            )
        return cursor.rowcount == 1

    def renew_lease(
        self, job_id: str, worker_id: str, *, lease_seconds: int
    ) -> bool:
        if (
            isinstance(lease_seconds, bool)
            or not isinstance(lease_seconds, (int, float))
            or not math.isfinite(lease_seconds)
            or lease_seconds <= 0
        ):
            raise ValueError("lease_seconds must be positive")
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=lease_seconds)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """UPDATE ingestion_jobs SET lease_expires_at = ?, updated_at = ?
                   WHERE id = ? AND status = ? AND lease_owner = ?
                     AND lease_expires_at > ?""",
                (
                    expires.isoformat(),
                    now.isoformat(),
                    job_id,
                    IngestionJobStatus.RUNNING.value,
                    worker_id,
                    now.isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def fail(
        self,
        job_id: str,
        worker_id: str,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        if not error_code.strip() or not error_message.strip():
            raise ValueError("failed jobs require a sanitized error")
        now = _timestamp()
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """UPDATE ingestion_jobs SET
                     status = ?, error_code = ?, error_message = ?,
                     lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                   WHERE id = ? AND status = ? AND lease_owner = ?
                     AND lease_expires_at > ?""",
                (
                    IngestionJobStatus.FAILED.value,
                    error_code[:80],
                    error_message[:500],
                    now,
                    job_id,
                    IngestionJobStatus.RUNNING.value,
                    worker_id,
                    now,
                ),
            )
        return cursor.rowcount == 1

    def cancel(self, job_id: str) -> IngestionJob | None:
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE ingestion_jobs SET
                     status = ?, lease_owner = NULL, lease_expires_at = NULL,
                     updated_at = ?
                   WHERE id = ? AND status IN (?, ?)""",
                (
                    IngestionJobStatus.CANCELLED.value,
                    _timestamp(),
                    job_id,
                    IngestionJobStatus.PENDING.value,
                    IngestionJobStatus.FAILED.value,
                ),
            )
        return self.get(job_id)

    def retry(self, job_id: str) -> IngestionJob | None:
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE ingestion_jobs SET
                     status = ?, error_code = NULL, error_message = NULL,
                     updated_at = ?
                   WHERE id = ? AND status = ? AND attempts < max_attempts""",
                (
                    IngestionJobStatus.PENDING.value,
                    _timestamp(),
                    job_id,
                    IngestionJobStatus.FAILED.value,
                ),
            )
        return self.get(job_id)

    def recover_expired(self, now: str) -> int:
        normalized_now = _normalized_timestamp(now)
        with self._lock, self._connection:
            return self._recover_expired(normalized_now)

    def _recover_expired(self, now: str) -> int:
        retryable = self._connection.execute(
            """UPDATE ingestion_jobs SET
                 status = ?, lease_owner = NULL, lease_expires_at = NULL,
                 error_code = 'lease-expired',
                 error_message = 'The previous worker lease expired; the job was recovered.',
                 updated_at = ?
               WHERE status = ? AND lease_expires_at <= ? AND attempts < max_attempts""",
            (
                IngestionJobStatus.PENDING.value,
                now,
                IngestionJobStatus.RUNNING.value,
                now,
            ),
        ).rowcount
        exhausted = self._connection.execute(
            """UPDATE ingestion_jobs SET
                 status = ?, lease_owner = NULL, lease_expires_at = NULL,
                 error_code = 'lease-exhausted',
                 error_message = 'Worker leases expired until the retry budget was exhausted.',
                 updated_at = ?
               WHERE status = ? AND lease_expires_at <= ? AND attempts >= max_attempts""",
            (
                IngestionJobStatus.FAILED.value,
                now,
                IngestionJobStatus.RUNNING.value,
                now,
            ),
        ).rowcount
        return retryable + exhausted


def _job_values(job: IngestionJob) -> tuple[object, ...]:
    return (
        job.id,
        job.idempotency_key,
        job.course_id,
        job.artifact_id,
        job.title,
        job.version,
        job.professor_id,
        int(job.display_allowed),
        job.source_label.value,
        job.source_object_key,
        job.source_checksum,
        job.status.value,
        job.attempts,
        job.max_attempts,
        job.lease_owner,
        job.lease_expires_at,
        job.error_code,
        job.error_message,
        job.result.model_dump_json() if job.result else None,
        job.created_at,
        job.updated_at,
    )


def _job(row: sqlite3.Row) -> IngestionJob:
    values = dict(row)
    values["display_allowed"] = bool(values["display_allowed"])
    result_json = values.pop("result_json")
    values["result"] = (
        IngestionJobResult.model_validate_json(result_json) if result_json else None
    )
    return IngestionJob.model_validate(values)


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _normalized_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError("lease recovery time must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("lease recovery time must include a timezone")
    return parsed.astimezone(UTC).isoformat()
