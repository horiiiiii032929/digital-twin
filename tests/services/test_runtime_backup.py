import hashlib
import json
import sqlite3
import zipfile

import pytest

from services.operations import (
    create_runtime_backup,
    restore_runtime_backup,
    verify_runtime_backup,
)
from services.storage import FileSystemObjectStore
from src.digital_twin.student import SQLiteStudentRepository, seed_synthetic_student_workflow


def test_backup_and_clean_restore_preserve_database_and_object_checksums(tmp_path):
    source_root = tmp_path / "source-runtime"
    database = source_root / "digital-twin.sqlite3"
    repository = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(repository)
    store = FileSystemObjectStore(source_root / "objects")
    stored = store.put(
        b"%PDF-synthetic-course-source",
        namespace="course-sources",
        suffix=".pdf",
        mime_type="application/pdf",
    )
    archive = tmp_path / "backup.zip"

    manifest = create_runtime_backup(database, source_root, archive)
    verified = verify_runtime_backup(archive)

    assert verified == manifest
    assert archive.stat().st_mode & 0o077 == 0
    restored_root = tmp_path / "restored-runtime"
    restored_database = restored_root / "digital-twin.sqlite3"
    restore_runtime_backup(archive, restored_database, restored_root)
    restored_repository = SQLiteStudentRepository(restored_database)
    restored_store = FileSystemObjectStore(restored_root / "objects")
    assert restored_repository.get_account(fixture.student_a_id) is not None
    assert restored_store.checksum(stored.key) == stored.checksum


def test_restore_refuses_nonempty_target(tmp_path):
    source_root = tmp_path / "source-runtime"
    database = source_root / "digital-twin.sqlite3"
    repository = SQLiteStudentRepository(database)
    seed_synthetic_student_workflow(repository)
    archive = tmp_path / "backup.zip"
    create_runtime_backup(database, source_root, archive)
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_text("do not overwrite")

    with pytest.raises(FileExistsError, match="clean|empty"):
        restore_runtime_backup(archive, target / "db.sqlite3", target)


def test_tampered_backup_fails_verification(tmp_path):
    source_root = tmp_path / "source-runtime"
    database = source_root / "digital-twin.sqlite3"
    repository = SQLiteStudentRepository(database)
    seed_synthetic_student_workflow(repository)
    archive = tmp_path / "backup.zip"
    create_runtime_backup(database, source_root, archive)

    with zipfile.ZipFile(archive, "a") as backup:
        backup.writestr("database.sqlite3", b"tampered")

    with pytest.raises(ValueError, match="duplicate|unexpected|size|checksum"):
        verify_runtime_backup(archive)


def test_backup_rejects_symbolic_links_in_runtime_data(tmp_path):
    source_root = tmp_path / "source-runtime"
    database = source_root / "digital-twin.sqlite3"
    repository = SQLiteStudentRepository(database)
    seed_synthetic_student_workflow(repository)
    external = tmp_path / "outside-secret.txt"
    external.write_text("must not be archived")
    (source_root / "linked-secret.txt").symlink_to(external)

    with pytest.raises(ValueError, match="symbolic link"):
        create_runtime_backup(database, source_root, tmp_path / "backup.zip")


def test_backup_verification_enforces_uncompressed_size_limit(tmp_path):
    source_root = tmp_path / "source-runtime"
    database = source_root / "digital-twin.sqlite3"
    repository = SQLiteStudentRepository(database)
    seed_synthetic_student_workflow(repository)
    archive = tmp_path / "backup.zip"
    create_runtime_backup(database, source_root, archive)

    with pytest.raises(ValueError, match="size limit"):
        verify_runtime_backup(archive, max_total_bytes=1)


def test_invalid_database_restore_leaves_clean_target_untouched(tmp_path):
    database_content = b"not-a-sqlite-database"
    manifest = {
        "format_version": 1,
        "created_at": "2026-08-19T00:00:00+00:00",
        "schema_version": 6,
        "database": {
            "path": "database.sqlite3",
            "checksum": hashlib.sha256(database_content).hexdigest(),
            "size_bytes": len(database_content),
        },
        "data_files": [],
    }
    archive = tmp_path / "invalid-database.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as backup:
        backup.writestr("database.sqlite3", database_content)
        backup.writestr("manifest.json", json.dumps(manifest))
    target = tmp_path / "restored-runtime"
    target.mkdir()

    with pytest.raises(sqlite3.DatabaseError):
        restore_runtime_backup(archive, target / "digital-twin.sqlite3", target)

    assert list(target.iterdir()) == []
