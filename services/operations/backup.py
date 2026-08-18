"""Verified runtime backup and clean-environment restore."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, Field

from src.digital_twin.student.migrations import current_schema_version


class BackupFile(BaseModel):
    path: str = Field(min_length=1)
    checksum: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)


class BackupManifest(BaseModel):
    format_version: int = 1
    created_at: str
    schema_version: int = Field(ge=0)
    database: BackupFile
    data_files: list[BackupFile] = Field(default_factory=list)


def create_runtime_backup(
    database_path: Path,
    data_root: Path,
    output_path: Path,
) -> BackupManifest:
    database_path = database_path.resolve()
    data_root = data_root.resolve()
    output_path = output_path.resolve()
    if not database_path.is_file():
        raise FileNotFoundError("runtime database does not exist")
    if output_path == database_path or output_path.is_relative_to(data_root):
        raise ValueError("backup output must be outside the runtime data root")
    _require_no_running_jobs(database_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="digital-twin-backup-") as temporary:
        temporary_root = Path(temporary)
        database_snapshot = temporary_root / "database.sqlite3"
        source = sqlite3.connect(database_path)
        target = sqlite3.connect(database_snapshot)
        try:
            source.backup(target)
            schema_version = current_schema_version(target)
        finally:
            target.close()
            source.close()

        database_entry = _file_record(database_snapshot, "database.sqlite3")
        data_entries: list[BackupFile] = []
        if data_root.is_dir():
            for path in sorted(data_root.rglob("*")):
                if not path.is_file() or _is_database_sidecar(path, database_path):
                    continue
                if path.resolve() == database_path:
                    continue
                relative = path.relative_to(data_root).as_posix()
                data_entries.append(_file_record(path, f"data/{relative}"))
        manifest = BackupManifest(
            created_at=datetime.now(UTC).isoformat(),
            schema_version=schema_version,
            database=database_entry,
            data_files=data_entries,
        )

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f"{output_path.name}-",
            suffix=".pending",
            dir=output_path.parent,
        )
        os.close(descriptor)
        temporary_archive = Path(temporary_name)
        try:
            with zipfile.ZipFile(
                temporary_archive, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.write(database_snapshot, database_entry.path)
                for entry in data_entries:
                    archive.write(data_root / entry.path.removeprefix("data/"), entry.path)
                archive.writestr(
                    "manifest.json",
                    manifest.model_dump_json(indent=2),
                )
            verify_runtime_backup(temporary_archive)
            os.chmod(temporary_archive, 0o600)
            temporary_archive.replace(output_path)
        except Exception:
            temporary_archive.unlink(missing_ok=True)
            raise
    return manifest


def verify_runtime_backup(archive_path: Path) -> BackupManifest:
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        if "manifest.json" not in names:
            raise ValueError("backup manifest is missing")
        manifest = BackupManifest.model_validate_json(archive.read("manifest.json"))
        expected = [manifest.database, *manifest.data_files]
        if names != {"manifest.json", *(entry.path for entry in expected)}:
            raise ValueError("backup contains unexpected or missing files")
        for entry in expected:
            _validate_archive_path(entry.path)
            content = archive.read(entry.path)
            if len(content) != entry.size_bytes:
                raise ValueError(f"backup size mismatch for {entry.path}")
            if hashlib.sha256(content).hexdigest() != entry.checksum:
                raise ValueError(f"backup checksum mismatch for {entry.path}")
    return manifest


def restore_runtime_backup(
    archive_path: Path,
    database_path: Path,
    data_root: Path,
) -> BackupManifest:
    manifest = verify_runtime_backup(archive_path)
    database_path = database_path.resolve()
    data_root = data_root.resolve()
    if database_path.exists():
        raise FileExistsError("restore requires a clean database target")
    if data_root.exists() and any(data_root.iterdir()):
        raise FileExistsError("restore requires an empty runtime data root")

    with tempfile.TemporaryDirectory(prefix="digital-twin-restore-") as temporary:
        temporary_root = Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            for entry in [manifest.database, *manifest.data_files]:
                destination = temporary_root / entry.path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(entry.path))
        restored_database = temporary_root / manifest.database.path
        connection = sqlite3.connect(restored_database)
        try:
            if current_schema_version(connection) != manifest.schema_version:
                raise ValueError("restored database schema version mismatch")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("restored database integrity check failed")
        finally:
            connection.close()

        database_path.parent.mkdir(parents=True, exist_ok=True)
        data_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(restored_database, database_path)
        for entry in manifest.data_files:
            relative = entry.path.removeprefix("data/")
            destination = data_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(temporary_root / entry.path, destination)
    return manifest


def _require_no_running_jobs(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ingestion_jobs'"
        ).fetchone()
        if table and connection.execute(
            "SELECT 1 FROM ingestion_jobs WHERE status = 'running' LIMIT 1"
        ).fetchone():
            raise RuntimeError("stop or drain ingestion workers before backup")
    finally:
        connection.close()


def _file_record(path: Path, archive_path: str) -> BackupFile:
    return BackupFile(
        path=archive_path,
        checksum=_checksum(path),
        size_bytes=path.stat().st_size,
    )


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_archive_path(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("backup contains an unsafe path")


def _is_database_sidecar(path: Path, database_path: Path) -> bool:
    return path in {
        database_path.with_name(f"{database_path.name}-wal"),
        database_path.with_name(f"{database_path.name}-shm"),
    }
