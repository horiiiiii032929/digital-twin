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


def _execute_statements(
    connection: sqlite3.Connection, statements: tuple[str, ...]
) -> None:
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


PROACTIVE_OUTREACH_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS outreach_preferences (
           student_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           channel TEXT NOT NULL CHECK(channel IN ('in-app', 'discord')),
           enabled INTEGER NOT NULL DEFAULT 0,
           timezone TEXT NOT NULL,
           quiet_hours_start TEXT NOT NULL,
           quiet_hours_end TEXT NOT NULL,
           max_messages_per_7_days INTEGER NOT NULL,
           snoozed_until TEXT,
           destination_ref TEXT,
           private_destination INTEGER NOT NULL DEFAULT 0,
           updated_at TEXT NOT NULL,
           PRIMARY KEY (student_id, course_id, channel)
       )""",
    """CREATE TABLE IF NOT EXISTS proactive_triggers (
           id TEXT PRIMARY KEY,
           idempotency_key TEXT NOT NULL UNIQUE,
           professor_id TEXT NOT NULL REFERENCES accounts(id),
           student_id TEXT NOT NULL REFERENCES accounts(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           channel TEXT NOT NULL CHECK(channel IN ('in-app', 'discord')),
           kind TEXT NOT NULL,
           scheduled_for TEXT NOT NULL,
           expires_at TEXT NOT NULL,
           topic TEXT NOT NULL,
           prompt TEXT NOT NULL,
           source_chunk_id TEXT NOT NULL,
           status TEXT NOT NULL,
           suppression_reason TEXT,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE INDEX IF NOT EXISTS proactive_triggers_due_idx
       ON proactive_triggers(status, scheduled_for, id)""",
    """CREATE INDEX IF NOT EXISTS proactive_triggers_student_idx
       ON proactive_triggers(student_id, course_id, created_at)""",
    """CREATE TABLE IF NOT EXISTS proactive_messages (
           id TEXT PRIMARY KEY,
           trigger_id TEXT NOT NULL UNIQUE
               REFERENCES proactive_triggers(id) ON DELETE CASCADE,
           student_id TEXT NOT NULL REFERENCES accounts(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           channel TEXT NOT NULL CHECK(channel IN ('in-app', 'discord')),
           content TEXT NOT NULL,
           status TEXT NOT NULL,
           created_at TEXT NOT NULL,
           read_at TEXT,
           dismissed_at TEXT
       )""",
    """CREATE INDEX IF NOT EXISTS proactive_messages_inbox_idx
       ON proactive_messages(student_id, course_id, created_at DESC)""",
    """CREATE TABLE IF NOT EXISTS proactive_citations (
           id TEXT PRIMARY KEY,
           message_id TEXT NOT NULL
               REFERENCES proactive_messages(id) ON DELETE CASCADE,
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
    """CREATE TABLE IF NOT EXISTS proactive_delivery_outbox (
           id TEXT PRIMARY KEY,
           message_id TEXT NOT NULL UNIQUE
               REFERENCES proactive_messages(id) ON DELETE CASCADE,
           channel TEXT NOT NULL CHECK(channel = 'discord'),
           destination_ref TEXT NOT NULL,
           status TEXT NOT NULL,
           attempts INTEGER NOT NULL DEFAULT 0,
           last_error TEXT,
           available_at TEXT NOT NULL,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE INDEX IF NOT EXISTS proactive_outbox_pending_idx
       ON proactive_delivery_outbox(status, available_at, id)""",
)


TEACHING_PROFILE_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS teaching_profiles (
           profile_id TEXT PRIMARY KEY,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           version INTEGER NOT NULL,
           status TEXT NOT NULL,
           content_sha256 TEXT NOT NULL,
           preview_sha256 TEXT,
           profile_json TEXT NOT NULL,
           created_at TEXT NOT NULL,
           approved_at TEXT,
           withdrawn_at TEXT,
           UNIQUE(course_id, version)
       )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS teaching_profiles_one_approved
       ON teaching_profiles(course_id) WHERE status = 'approved'""",
    """CREATE INDEX IF NOT EXISTS teaching_profiles_course_idx
       ON teaching_profiles(course_id, version DESC)""",
)


GOVERNED_AUTONOMY_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS autonomy_policies (
           course_id TEXT PRIMARY KEY REFERENCES courses(id) ON DELETE CASCADE,
           version INTEGER NOT NULL CHECK(version >= 1),
           policy_json TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS autonomous_goals (
           goal_id TEXT PRIMARY KEY,
           student_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           release_id TEXT NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
           policy_version INTEGER NOT NULL,
           profile_id TEXT NOT NULL,
           profile_sha256 TEXT NOT NULL,
           graph_version TEXT NOT NULL,
           planner_model TEXT NOT NULL,
           generator_model TEXT NOT NULL,
           status TEXT NOT NULL,
           priority INTEGER NOT NULL,
           expires_at TEXT NOT NULL,
           goal_json TEXT NOT NULL,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE INDEX IF NOT EXISTS autonomous_goals_active_idx
       ON autonomous_goals(student_id, course_id, release_id, status, priority,
                           expires_at)""",
    """CREATE TABLE IF NOT EXISTS autonomous_opportunities (
           opportunity_id TEXT PRIMARY KEY,
           idempotency_key TEXT NOT NULL UNIQUE,
           goal_id TEXT REFERENCES autonomous_goals(goal_id) ON DELETE CASCADE,
           student_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           release_id TEXT NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
           policy_version INTEGER NOT NULL,
           profile_id TEXT NOT NULL,
           profile_sha256 TEXT NOT NULL,
           graph_version TEXT NOT NULL,
           planner_model TEXT NOT NULL,
           generator_model TEXT NOT NULL,
           event_kind TEXT NOT NULL,
           status TEXT NOT NULL,
           earliest_action_at TEXT NOT NULL,
           latest_action_at TEXT NOT NULL,
           opportunity_json TEXT NOT NULL,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE INDEX IF NOT EXISTS autonomous_opportunities_due_idx
       ON autonomous_opportunities(status, earliest_action_at, latest_action_at,
                                   opportunity_id)""",
    """CREATE TABLE IF NOT EXISTS autonomous_plans (
           plan_id TEXT PRIMARY KEY,
           opportunity_id TEXT NOT NULL UNIQUE
               REFERENCES autonomous_opportunities(opportunity_id) ON DELETE CASCADE,
           goal_id TEXT REFERENCES autonomous_goals(goal_id) ON DELETE CASCADE,
           student_id TEXT NOT NULL REFERENCES accounts(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           policy_version INTEGER NOT NULL,
           profile_sha256 TEXT NOT NULL,
           graph_version TEXT NOT NULL,
           plan_json TEXT NOT NULL,
           created_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS autonomous_actions (
           action_id TEXT PRIMARY KEY,
           plan_id TEXT NOT NULL UNIQUE
               REFERENCES autonomous_plans(plan_id) ON DELETE CASCADE,
           opportunity_id TEXT NOT NULL UNIQUE
               REFERENCES autonomous_opportunities(opportunity_id) ON DELETE CASCADE,
           goal_id TEXT REFERENCES autonomous_goals(goal_id) ON DELETE CASCADE,
           student_id TEXT NOT NULL REFERENCES accounts(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           policy_version INTEGER NOT NULL,
           profile_sha256 TEXT NOT NULL,
           graph_version TEXT NOT NULL,
           proactive_trigger_id TEXT UNIQUE REFERENCES proactive_triggers(id),
           status TEXT NOT NULL,
           action_json TEXT NOT NULL,
           created_at TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE INDEX IF NOT EXISTS autonomous_actions_audit_idx
       ON autonomous_actions(course_id, student_id, created_at DESC)""",
    """CREATE TABLE IF NOT EXISTS autonomous_outcomes (
           outcome_id TEXT PRIMARY KEY,
           action_id TEXT NOT NULL UNIQUE
               REFERENCES autonomous_actions(action_id) ON DELETE CASCADE,
           goal_id TEXT REFERENCES autonomous_goals(goal_id) ON DELETE CASCADE,
           student_id TEXT NOT NULL REFERENCES accounts(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           policy_version INTEGER NOT NULL,
           profile_sha256 TEXT NOT NULL,
           graph_version TEXT NOT NULL,
           outcome_json TEXT NOT NULL,
           recorded_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS autonomous_graph_checkpoints (
           job_id TEXT PRIMARY KEY,
           opportunity_id TEXT NOT NULL UNIQUE
               REFERENCES autonomous_opportunities(opportunity_id) ON DELETE CASCADE,
           binding_sha256 TEXT NOT NULL,
           status TEXT NOT NULL,
           state_json TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS autonomous_wakeups (
           wake_up_id TEXT PRIMARY KEY,
           goal_id TEXT NOT NULL REFERENCES autonomous_goals(goal_id) ON DELETE CASCADE,
           student_id TEXT NOT NULL REFERENCES accounts(id),
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           due_at TEXT NOT NULL,
           event_kind TEXT NOT NULL,
           status TEXT NOT NULL,
           wake_up_json TEXT NOT NULL,
           created_at TEXT NOT NULL
       )""",
    """CREATE INDEX IF NOT EXISTS autonomous_wakeups_due_idx
       ON autonomous_wakeups(status, due_at, wake_up_id)""",
    """CREATE TABLE IF NOT EXISTS autonomous_response_links (
           proactive_message_id TEXT PRIMARY KEY
               REFERENCES proactive_messages(id) ON DELETE CASCADE,
           student_message_id TEXT NOT NULL UNIQUE
               REFERENCES messages(id) ON DELETE CASCADE,
           action_id TEXT REFERENCES autonomous_actions(action_id) ON DELETE SET NULL,
           goal_id TEXT REFERENCES autonomous_goals(goal_id) ON DELETE SET NULL,
           course_id TEXT NOT NULL REFERENCES courses(id),
           release_id TEXT NOT NULL REFERENCES releases(id),
           linked_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS autonomy_execution_leases (
           opportunity_id TEXT PRIMARY KEY
               REFERENCES autonomous_opportunities(opportunity_id) ON DELETE CASCADE,
           lease_owner TEXT NOT NULL,
           lease_expires_at TEXT NOT NULL,
           acquired_at TEXT NOT NULL
       )""",
)


GOVERNED_AUTONOMY_V2_RUNTIME_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS course_domain_models (
           domain_model_id TEXT PRIMARY KEY,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           release_id TEXT NOT NULL UNIQUE REFERENCES releases(id) ON DELETE CASCADE,
           release_sha256 TEXT NOT NULL,
           version INTEGER NOT NULL CHECK(version >= 1),
           model_json TEXT NOT NULL,
           approved_by TEXT NOT NULL REFERENCES accounts(id),
           approved_at TEXT NOT NULL,
           UNIQUE(course_id, version)
       )""",
    """CREATE INDEX IF NOT EXISTS course_domain_models_course_idx
       ON course_domain_models(course_id, version DESC)""",
    """CREATE TABLE IF NOT EXISTS learner_observations_v2 (
           observation_id TEXT PRIMARY KEY,
           conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
           learner_key TEXT NOT NULL,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           release_id TEXT NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
           source_turn_key TEXT UNIQUE,
           observation_json TEXT NOT NULL,
           observed_at TEXT NOT NULL
       )""",
    """CREATE INDEX IF NOT EXISTS learner_observations_v2_scope_idx
       ON learner_observations_v2(learner_key, course_id, release_id, observed_at)""",
    """CREATE TABLE IF NOT EXISTS learner_belief_states_v2 (
           conversation_id TEXT PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
           learner_key TEXT NOT NULL,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           release_id TEXT NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
           revision INTEGER NOT NULL CHECK(revision >= 1),
           state_json TEXT NOT NULL,
           updated_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS learner_concept_attributions_v2 (
           conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
           revision INTEGER NOT NULL CHECK(revision >= 1),
           concept_id TEXT NOT NULL,
           attribution_json TEXT NOT NULL,
           updated_at TEXT NOT NULL,
           PRIMARY KEY(conversation_id, revision, concept_id)
       )""",
    """CREATE TABLE IF NOT EXISTS learner_state_deltas_v2 (
           conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
           next_revision INTEGER NOT NULL CHECK(next_revision >= 1),
           observation_id TEXT NOT NULL UNIQUE
               REFERENCES learner_observations_v2(observation_id) ON DELETE CASCADE,
           delta_json TEXT NOT NULL,
           created_at TEXT NOT NULL,
           PRIMARY KEY(conversation_id, next_revision)
       )""",
    """CREATE TABLE IF NOT EXISTS reactive_pedagogical_plans_v2 (
           observation_id TEXT PRIMARY KEY
               REFERENCES learner_observations_v2(observation_id) ON DELETE CASCADE,
           conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
           plan_json TEXT NOT NULL,
           created_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS grounded_tutor_responses_v2 (
           observation_id TEXT PRIMARY KEY
               REFERENCES learner_observations_v2(observation_id) ON DELETE CASCADE,
           conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
           response_json TEXT NOT NULL,
           created_at TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS tutoring_agent_traces_v2 (
           trace_id TEXT PRIMARY KEY,
           event_id TEXT NOT NULL UNIQUE,
           conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
           learner_key TEXT NOT NULL,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           release_id TEXT NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
           graph_version TEXT NOT NULL,
           input_state_revision INTEGER NOT NULL,
           output_state_revision INTEGER NOT NULL,
           trace_json TEXT NOT NULL,
           created_at TEXT NOT NULL,
           completed_at TEXT
       )""",
    """CREATE INDEX IF NOT EXISTS tutoring_agent_traces_v2_scope_idx
       ON tutoring_agent_traces_v2(course_id, release_id, created_at DESC)""",
)


COURSE_TUTORING_RUNTIME_PROFILE_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS course_tutoring_runtime_profiles (
           course_id TEXT PRIMARY KEY REFERENCES courses(id) ON DELETE CASCADE,
           mode TEXT NOT NULL,
           version INTEGER NOT NULL CHECK(version >= 1),
           profile_json TEXT NOT NULL,
           changed_by TEXT NOT NULL REFERENCES accounts(id),
           updated_at TEXT NOT NULL
       )""",
)


V2_MODEL_CALL_LEDGER_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS tutoring_model_calls_v2 (
           event_id TEXT NOT NULL,
           stage TEXT NOT NULL,
           conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
           request_sha256 TEXT NOT NULL,
           status TEXT NOT NULL CHECK(status IN ('started', 'completed', 'failed')),
           output_json TEXT,
           audit_events_json TEXT,
           failure_code TEXT,
           started_at TEXT NOT NULL,
           completed_at TEXT,
           PRIMARY KEY(event_id, stage)
       )""",
    """CREATE INDEX IF NOT EXISTS tutoring_model_calls_v2_conversation_idx
       ON tutoring_model_calls_v2(conversation_id, started_at)""",
    """CREATE TABLE IF NOT EXISTS autonomous_model_calls_v2 (
           opportunity_id TEXT NOT NULL
               REFERENCES autonomous_opportunities(opportunity_id) ON DELETE CASCADE,
           stage TEXT NOT NULL,
           request_sha256 TEXT NOT NULL,
           status TEXT NOT NULL CHECK(status IN ('started', 'completed', 'failed')),
           output_json TEXT,
           failure_code TEXT,
           started_at TEXT NOT NULL,
           completed_at TEXT,
           PRIMARY KEY(opportunity_id, stage)
       )""",
)


STATEFUL_CLARIFICATION_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS clarification_requests (
           request_id TEXT PRIMARY KEY,
           conversation_id TEXT NOT NULL
               REFERENCES conversations(id) ON DELETE CASCADE,
           student_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
           course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
           release_id TEXT NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
           original_student_message_id TEXT NOT NULL UNIQUE
               REFERENCES messages(id) ON DELETE CASCADE,
           status TEXT NOT NULL CHECK(status IN
               ('pending', 'resolved', 'expired', 'cancelled')),
           selected_option_id TEXT,
           resolved_by_message_id TEXT REFERENCES messages(id),
           request_json TEXT NOT NULL,
           created_at TEXT NOT NULL,
           expires_at TEXT NOT NULL,
           resolved_at TEXT
       )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS clarification_one_pending_per_conversation
       ON clarification_requests(conversation_id) WHERE status = 'pending'""",
    """CREATE INDEX IF NOT EXISTS clarification_scope_idx
       ON clarification_requests(course_id, release_id, status, expires_at)""",
)


def _add_teaching_profiles(connection: sqlite3.Connection) -> None:
    _execute_statements(connection, TEACHING_PROFILE_SCHEMA_STATEMENTS)
    columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(releases)")}
    if "teaching_profile_id" not in columns:
        connection.execute("ALTER TABLE releases ADD COLUMN teaching_profile_id TEXT")
    if "teaching_profile_sha256" not in columns:
        connection.execute(
            "ALTER TABLE releases ADD COLUMN teaching_profile_sha256 TEXT"
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
        definition=("add message tutoring metadata and conversation_learner_states"),
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
    SQLiteMigration(
        version=11,
        name="opt-in-proactive-outreach",
        definition="\n".join(PROACTIVE_OUTREACH_SCHEMA_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, PROACTIVE_OUTREACH_SCHEMA_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=12,
        name="explicit-professor-teaching-profiles",
        definition=(
            "create versioned teaching profiles and bind approved profile hashes to releases"
        ),
        operation=_add_teaching_profiles,
    ),
    SQLiteMigration(
        version=13,
        name="governed-autonomous-tutoring-v2-1",
        definition="\n".join(GOVERNED_AUTONOMY_SCHEMA_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, GOVERNED_AUTONOMY_SCHEMA_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=14,
        name="governed-autonomous-tutoring-v2-1-runtime-state",
        definition="\n".join(GOVERNED_AUTONOMY_V2_RUNTIME_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, GOVERNED_AUTONOMY_V2_RUNTIME_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=15,
        name="course-tutoring-runtime-profile",
        definition="\n".join(COURSE_TUTORING_RUNTIME_PROFILE_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, COURSE_TUTORING_RUNTIME_PROFILE_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=16,
        name="governed-tutoring-v2-model-call-ledger",
        definition="\n".join(V2_MODEL_CALL_LEDGER_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, V2_MODEL_CALL_LEDGER_STATEMENTS
        ),
    ),
    SQLiteMigration(
        version=17,
        name="bounded-stateful-evidence-clarification",
        definition="\n".join(STATEFUL_CLARIFICATION_SCHEMA_STATEMENTS),
        operation=lambda connection: _execute_statements(
            connection, STATEFUL_CLARIFICATION_SCHEMA_STATEMENTS
        ),
    ),
)
