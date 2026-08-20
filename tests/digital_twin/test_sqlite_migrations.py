import sqlite3

import pytest

from src.digital_twin.student import SQLiteStudentRepository
from src.digital_twin.student.migrations import (
    DEFAULT_MIGRATIONS,
    SQLiteMigration,
    apply_migrations,
    current_schema_version,
)


def test_clean_database_applies_all_ordered_migrations(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "clean.sqlite3")

    assert current_schema_version(repository._connection) == len(DEFAULT_MIGRATIONS)
    assert {
        row[0]
        for row in repository._connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    } >= {
        "accounts",
        "releases",
        "citations",
        "identity_credentials",
        "identity_sessions",
        "schema_migrations",
    }
    repository.close()


def test_legacy_schema_is_upgraded_without_losing_rows(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE accounts (id TEXT PRIMARY KEY, role TEXT, status TEXT);
        CREATE TABLE releases (
          id TEXT PRIMARY KEY, course_id TEXT, profile_id TEXT,
          profile_version TEXT, policy_version INTEGER, policy_json TEXT,
          status TEXT, created_at TEXT
        );
        CREATE TABLE citations (
          id TEXT PRIMARY KEY, message_id TEXT, course_id TEXT, release_id TEXT,
          source_artifact_id TEXT, source_document_id TEXT, source_version INTEGER,
          title TEXT, locator TEXT
        );
        INSERT INTO accounts VALUES ('legacy-professor', 'professor', 'active');
        """
    )
    connection.close()

    repository = SQLiteStudentRepository(path)

    assert repository.get_account("legacy-professor").role.value == "professor"
    assert "evaluation_status" in {
        row[1] for row in repository._connection.execute("PRAGMA table_info(releases)")
    }
    assert "crop_ref" in {
        row[1] for row in repository._connection.execute("PRAGMA table_info(citations)")
    }
    repository.close()


def test_failed_migration_rolls_back_and_is_not_recorded():
    connection = sqlite3.connect(":memory:")

    def fail_after_write(database: sqlite3.Connection) -> None:
        database.execute("CREATE TABLE should_rollback (id TEXT)")
        raise RuntimeError("synthetic migration failure")

    failing = SQLiteMigration(
        version=1,
        name="failure",
        definition="synthetic failure",
        operation=fail_after_write,
    )

    with pytest.raises(RuntimeError, match="synthetic migration failure"):
        apply_migrations(connection, (failing,))

    assert current_schema_version(connection) == 0
    assert connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'should_rollback'"
    ).fetchone() is None


def test_applied_migration_checksum_change_fails_closed():
    connection = sqlite3.connect(":memory:")
    apply_migrations(connection, (DEFAULT_MIGRATIONS[0],))
    changed = SQLiteMigration(
        version=1,
        name=DEFAULT_MIGRATIONS[0].name,
        definition="changed after application",
        operation=lambda database: None,
    )

    with pytest.raises(RuntimeError, match="checksum"):
        apply_migrations(connection, (changed,))


def test_explicit_empty_migration_set_does_not_apply_defaults():
    connection = sqlite3.connect(":memory:")

    assert apply_migrations(connection, ()) == 0
    assert current_schema_version(connection) == 0
    assert connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'accounts'"
    ).fetchone() is None


def test_database_with_newer_unknown_migration_fails_closed():
    connection = sqlite3.connect(":memory:")
    apply_migrations(connection, (DEFAULT_MIGRATIONS[0],))
    connection.execute(
        """INSERT INTO schema_migrations(version, name, checksum, applied_at)
           VALUES (999, 'future', 'future-checksum', '2026-08-19T00:00:00+00:00')"""
    )
    connection.commit()

    with pytest.raises(RuntimeError, match="unknown to this runtime: 999"):
        apply_migrations(connection, DEFAULT_MIGRATIONS)
