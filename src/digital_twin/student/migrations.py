"""Ordered, checksum-verified SQLite schema migrations."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Iterable


MigrationOperation = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True, slots=True)
class SQLiteMigration:
    version: int
    name: str
    definition: str
    operation: MigrationOperation

    @property
    def checksum(self) -> str:
        value = f"{self.version}\x1f{self.name}\x1f{self.definition}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


def apply_migrations(
    connection: sqlite3.Connection,
    migrations: Iterable[SQLiteMigration] | None = None,
) -> int:
    selected = tuple(DEFAULT_MIGRATIONS if migrations is None else migrations)
    versions = [migration.version for migration in selected]
    if (
        any(version < 1 for version in versions)
        or versions != sorted(versions)
        or len(versions) != len(set(versions))
    ):
        raise ValueError("migration versions must be positive, unique, and ordered")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
               version INTEGER PRIMARY KEY,
               name TEXT NOT NULL,
               checksum TEXT NOT NULL,
               applied_at TEXT NOT NULL
           )"""
    )
    connection.commit()
    applied = {
        int(row[0]): (str(row[1]), str(row[2]))
        for row in connection.execute(
            "SELECT version, name, checksum FROM schema_migrations"
        ).fetchall()
    }
    unknown_versions = sorted(set(applied) - set(versions))
    if unknown_versions:
        formatted = ", ".join(str(version) for version in unknown_versions)
        raise RuntimeError(
            "database contains migrations unknown to this runtime: " + formatted
        )
    for migration in selected:
        recorded = applied.get(migration.version)
        if recorded is not None:
            if recorded != (migration.name, migration.checksum):
                raise RuntimeError(
                    f"migration {migration.version} checksum or name changed"
                )
            continue
        connection.execute("BEGIN IMMEDIATE")
        try:
            migration.operation(connection)
            connection.execute(
                """INSERT INTO schema_migrations
                   (version, name, checksum, applied_at) VALUES (?, ?, ?, ?)""",
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    datetime.now(UTC).isoformat(),
                ),
            )
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
    return max(versions, default=0)


def current_schema_version(connection: sqlite3.Connection) -> int:
    exists = connection.execute(
        """SELECT 1 FROM sqlite_master
           WHERE type = 'table' AND name = 'schema_migrations'"""
    ).fetchone()
    if exists is None:
        return 0
    row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return int(row[0] or 0)


def _execute_statements(connection: sqlite3.Connection, statements: tuple[str, ...]) -> None:
    for statement in statements:
        connection.execute(statement)


def _upgrade_release_and_citation_lineage(connection: sqlite3.Connection) -> None:
    release_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(releases)")
    }
    if "evaluation_status" not in release_columns:
        connection.execute(
            """ALTER TABLE releases ADD COLUMN evaluation_status TEXT
               NOT NULL DEFAULT 'passed'"""
        )
    citation_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(citations)")
    }
    for column, column_type in (
        ("source_checksum", "TEXT"),
        ("page", "INTEGER"),
        ("region_id", "TEXT"),
        ("region_kind", "TEXT"),
        ("bounding_box_json", "TEXT"),
        ("crop_ref", "TEXT"),
    ):
        if column not in citation_columns:
            connection.execute(
                f"ALTER TABLE citations ADD COLUMN {column} {column_type}"
            )


def _add_onboarding_session_revision(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(onboarding_sessions)")
    }
    if "revision" not in columns:
        connection.execute(
            """ALTER TABLE onboarding_sessions ADD COLUMN revision INTEGER
               NOT NULL DEFAULT 1"""
        )


def _add_bounded_tutoring_state(connection: sqlite3.Connection) -> None:
    message_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(messages)")
    }
    additions = (
        ("tutoring_mode", "TEXT NOT NULL DEFAULT 'grounded-assistant'"),
        ("tutoring_intent", "TEXT"),
        ("learner_state_revision", "INTEGER"),
    )
    for name, definition in additions:
        if name not in message_columns:
            connection.execute(f"ALTER TABLE messages ADD COLUMN {name} {definition}")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS conversation_learner_states (
               conversation_id TEXT PRIMARY KEY
                   REFERENCES conversations(id) ON DELETE CASCADE,
               course_id TEXT NOT NULL REFERENCES courses(id),
               release_id TEXT NOT NULL REFERENCES releases(id),
               revision INTEGER NOT NULL CHECK(revision >= 1),
               state_json TEXT NOT NULL,
               updated_at TEXT NOT NULL
           )"""
    )


LEARNING_GAP_SIGNAL_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS learning_gap_signals (
           signal_id TEXT PRIMARY KEY,
           source_turn_key TEXT NOT NULL,
           learner_key TEXT NOT NULL,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           release_id TEXT NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
           topic_key TEXT NOT NULL,
           signal_kind TEXT NOT NULL,
           observed_at TEXT NOT NULL,
           expires_at TEXT NOT NULL,
           signal_json TEXT NOT NULL,
           UNIQUE(source_turn_key, topic_key, signal_kind)
       )""",
    """CREATE INDEX IF NOT EXISTS learning_gap_signals_scope_idx
       ON learning_gap_signals(course_id, release_id, expires_at, topic_key,
                               signal_kind)""",
)


CORE_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS accounts (
           id TEXT PRIMARY KEY,
           role TEXT NOT NULL,
           status TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS courses (
           id TEXT PRIMARY KEY,
           title TEXT NOT NULL,
           owner_professor_id TEXT NOT NULL REFERENCES accounts(id)
       )""",
    """CREATE TABLE IF NOT EXISTS memberships (
           account_id TEXT NOT NULL REFERENCES accounts(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           role TEXT NOT NULL,
           active INTEGER NOT NULL,
           PRIMARY KEY (account_id, course_id)
       )""",
    """CREATE TABLE IF NOT EXISTS releases (
           id TEXT PRIMARY KEY,
           course_id TEXT NOT NULL REFERENCES courses(id),
           profile_id TEXT NOT NULL,
           profile_version TEXT NOT NULL,
           policy_version INTEGER NOT NULL,
           policy_json TEXT NOT NULL,
           status TEXT NOT NULL,
           evaluation_status TEXT NOT NULL DEFAULT 'pending',
           created_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS release_chunks (
           release_id TEXT NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
           chunk_id TEXT NOT NULL,
           chunk_json TEXT NOT NULL,
           PRIMARY KEY (release_id, chunk_id)
       )""",
    """CREATE TABLE IF NOT EXISTS conversations (
           id TEXT PRIMARY KEY,
           student_id TEXT NOT NULL REFERENCES accounts(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS messages (
           id TEXT PRIMARY KEY,
           conversation_id TEXT NOT NULL REFERENCES conversations(id),
           role TEXT NOT NULL,
           content TEXT NOT NULL,
           action TEXT NOT NULL,
           trace_json TEXT,
           client_request_id TEXT,
           response_to_message_id TEXT REFERENCES messages(id),
           created_at TEXT NOT NULL
       )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS messages_request_unique
       ON messages(conversation_id, client_request_id)
       WHERE client_request_id IS NOT NULL""",
    """CREATE TABLE IF NOT EXISTS citations (
           id TEXT PRIMARY KEY,
           message_id TEXT NOT NULL REFERENCES messages(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           source_artifact_id TEXT NOT NULL,
           source_document_id TEXT NOT NULL,
           source_version INTEGER NOT NULL,
           title TEXT NOT NULL,
           locator TEXT NOT NULL,
           source_checksum TEXT,
           page INTEGER,
           region_id TEXT,
           region_kind TEXT,
           bounding_box_json TEXT,
           crop_ref TEXT
       )""",
    """CREATE TABLE IF NOT EXISTS audit_events (
           id TEXT PRIMARY KEY,
           event_type TEXT NOT NULL,
           account_id TEXT,
           course_id TEXT,
           release_id TEXT,
           conversation_id TEXT,
           details_json TEXT NOT NULL,
           created_at TEXT NOT NULL
       )""",
)


IDENTITY_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS identity_credentials (
           account_id TEXT PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
           email TEXT NOT NULL,
           normalized_email TEXT NOT NULL UNIQUE,
           display_name TEXT NOT NULL,
           password_hash TEXT NOT NULL,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS identity_sessions (
           token_digest TEXT PRIMARY KEY,
           account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
           created_at TEXT NOT NULL,
           expires_at TEXT NOT NULL,
           last_seen_at TEXT NOT NULL,
           revoked_at TEXT
       )""",
    """CREATE INDEX IF NOT EXISTS identity_sessions_account_idx
       ON identity_sessions(account_id)""",
    """CREATE INDEX IF NOT EXISTS identity_sessions_expiry_idx
       ON identity_sessions(expires_at)""",
)


ONBOARDING_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS onboarding_sessions (
           session_id TEXT PRIMARY KEY,
           owner_account_id TEXT REFERENCES accounts(id) ON DELETE CASCADE,
           session_json TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE INDEX IF NOT EXISTS onboarding_sessions_owner_idx
       ON onboarding_sessions(owner_account_id)""",
)


INGESTION_JOB_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS ingestion_jobs (
           id TEXT PRIMARY KEY,
           idempotency_key TEXT NOT NULL,
           course_id TEXT NOT NULL REFERENCES courses(id),
           artifact_id TEXT NOT NULL,
           title TEXT NOT NULL,
           version INTEGER NOT NULL,
           professor_id TEXT NOT NULL REFERENCES accounts(id),
           display_allowed INTEGER NOT NULL,
           source_label TEXT NOT NULL,
           source_object_key TEXT NOT NULL,
           source_checksum TEXT NOT NULL,
           status TEXT NOT NULL,
           attempts INTEGER NOT NULL,
           max_attempts INTEGER NOT NULL,
           lease_owner TEXT,
           lease_expires_at TEXT,
           error_code TEXT,
           error_message TEXT,
           result_json TEXT,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL,
           UNIQUE(professor_id, course_id, idempotency_key)
       )""",
    """CREATE INDEX IF NOT EXISTS ingestion_jobs_claim_idx
       ON ingestion_jobs(status, created_at)""",
    """CREATE INDEX IF NOT EXISTS ingestion_jobs_course_idx
       ON ingestion_jobs(professor_id, course_id, created_at)""",
)


STORAGE_DELETION_QUEUE_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS storage_deletion_queue (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           storage_kind TEXT NOT NULL CHECK(storage_kind IN ('object', 'derived')),
           storage_ref TEXT NOT NULL,
           target_type TEXT NOT NULL,
           target_id TEXT NOT NULL,
           attempts INTEGER NOT NULL DEFAULT 0,
           last_error TEXT,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL,
           UNIQUE(storage_kind, storage_ref)
       )""",
    """CREATE INDEX IF NOT EXISTS storage_deletion_queue_created_idx
       ON storage_deletion_queue(created_at, id)""",
)


RELEASE_INVARIANT_STATEMENTS = (
    """CREATE UNIQUE INDEX IF NOT EXISTS releases_one_published_per_course
       ON releases(course_id) WHERE status = 'published'""",
)


DEFAULT_MIGRATIONS = (
    SQLiteMigration(
        version=1,
        name="core-student-publication-schema",
        definition="\n".join(CORE_SCHEMA_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, CORE_SCHEMA_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=2,
        name="release-evaluation-and-citation-lineage",
        definition=(
            "add releases.evaluation_status and citation source/page/region/crop fields"
        ),
        operation=_upgrade_release_and_citation_lineage,
    ),
    SQLiteMigration(
        version=3,
        name="invite-credentials-and-sessions",
        definition="\n".join(IDENTITY_SCHEMA_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, IDENTITY_SCHEMA_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=4,
        name="durable-owned-onboarding-sessions",
        definition="\n".join(ONBOARDING_SCHEMA_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, ONBOARDING_SCHEMA_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=5,
        name="leased-ingestion-jobs",
        definition="\n".join(INGESTION_JOB_SCHEMA_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, INGESTION_JOB_SCHEMA_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=6,
        name="durable-storage-deletion-queue",
        definition="\n".join(STORAGE_DELETION_QUEUE_SCHEMA_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, STORAGE_DELETION_QUEUE_SCHEMA_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=7,
        name="optimistic-onboarding-session-revisions",
        definition="add onboarding_sessions.revision for ownership-safe compare-and-swap writes",
        operation=_add_onboarding_session_revision,
    ),
    SQLiteMigration(
        version=8,
        name="one-published-release-per-course",
        definition="\n".join(RELEASE_INVARIANT_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, RELEASE_INVARIANT_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=9,
        name="bounded-tutoring-learner-state",
        definition=(
            "add message tutoring metadata and conversation_learner_states"
        ),
        operation=_add_bounded_tutoring_state,
    ),
    SQLiteMigration(
        version=10,
        name="privacy-preserving-learning-gap-signals",
        definition="\n".join(LEARNING_GAP_SIGNAL_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, LEARNING_GAP_SIGNAL_STATEMENTS
        ),
    ),
)
