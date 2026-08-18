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

    with pytest.raises(ValueError, match="unexpected|size|checksum"):
        verify_runtime_backup(archive)
