"""Verified runtime backup and clean-environment restore."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, Field

from src.digital_twin.student.migrations import current_schema_version


MAX_BACKUP_FILES = 100_000
MAX_BACKUP_TOTAL_BYTES = 6 * 1024 * 1024 * 1024
MAX_BACKUP_MANIFEST_BYTES = 1024 * 1024
_COPY_BLOCK_BYTES = 1024 * 1024


class BackupFile(BaseModel):
    path: str = Field(min_length=1)
    checksum: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)


class BackupManifest(BaseModel):
    format_version: Literal[1] = 1
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
                if path.is_symlink():
                    raise ValueError(
                        f"runtime data contains a symbolic link: {path.relative_to(data_root)}"
                    )
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


def verify_runtime_backup(
    archive_path: Path,
    *,
    max_files: int = MAX_BACKUP_FILES,
    max_total_bytes: int = MAX_BACKUP_TOTAL_BYTES,
    max_manifest_bytes: int = MAX_BACKUP_MANIFEST_BYTES,
) -> BackupManifest:
    if max_files <= 0 or max_total_bytes <= 0 or max_manifest_bytes <= 0:
        raise ValueError("backup verification limits must be positive")
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names_list = [info.filename for info in infos]
        names = set(names_list)
        if len(names_list) != len(names):
            raise ValueError("backup contains duplicate file names")
        if len(infos) > max_files + 1:
            raise ValueError("backup contains too many files")
        if "manifest.json" not in names:
            raise ValueError("backup manifest is missing")
        by_name = {info.filename: info for info in infos}
        manifest_info = by_name["manifest.json"]
        _validate_archive_member(manifest_info)
        if manifest_info.file_size > max_manifest_bytes:
            raise ValueError("backup manifest exceeds the verification limit")
        manifest = BackupManifest.model_validate_json(archive.read(manifest_info))
        expected = [manifest.database, *manifest.data_files]
        if manifest.database.path != "database.sqlite3":
            raise ValueError("backup database path is invalid")
        if any(
            not entry.path.startswith("data/") or entry.path == "data/"
            for entry in manifest.data_files
        ):
            raise ValueError("backup data path is invalid")
        if names != {"manifest.json", *(entry.path for entry in expected)}:
            raise ValueError("backup contains unexpected or missing files")
        if len(expected) > max_files:
            raise ValueError("backup contains too many files")
        total_bytes = sum(entry.size_bytes for entry in expected)
        if total_bytes > max_total_bytes:
            raise ValueError("backup exceeds the uncompressed size limit")
        for entry in expected:
            _validate_archive_path(entry.path)
            info = by_name[entry.path]
            _validate_archive_member(info)
            if info.file_size != entry.size_bytes:
                raise ValueError(f"backup size mismatch for {entry.path}")
            size, checksum = _archive_member_checksum(archive, info)
            if size != entry.size_bytes:
                raise ValueError(f"backup size mismatch for {entry.path}")
            if checksum != entry.checksum:
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
    if not database_path.is_relative_to(data_root):
        raise ValueError("restore database target must be inside the runtime data root")
    if database_path.exists():
        raise FileExistsError("restore requires a clean database target")
    if data_root.exists() and any(data_root.iterdir()):
        raise FileExistsError("restore requires an empty runtime data root")

    data_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="digital-twin-restore-", dir=data_root.parent
    ) as temporary:
        temporary_root = Path(temporary)
        staged_root = temporary_root / "runtime"
        staged_root.mkdir()
        database_relative = database_path.relative_to(data_root)
        with zipfile.ZipFile(archive_path) as archive:
            database_destination = staged_root / database_relative
            database_destination.parent.mkdir(parents=True, exist_ok=True)
            _copy_archive_member(archive, manifest.database.path, database_destination)
            for entry in manifest.data_files:
                relative = entry.path.removeprefix("data/")
                destination = staged_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                _copy_archive_member(archive, entry.path, destination)
        connection = sqlite3.connect(database_destination)
        try:
            if current_schema_version(connection) != manifest.schema_version:
                raise ValueError("restored database schema version mismatch")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("restored database integrity check failed")
        finally:
            connection.close()
        for path in staged_root.rglob("*"):
            if path.is_file():
                os.chmod(path, 0o600)
        if data_root.exists():
            data_root.rmdir()
        staged_root.replace(data_root)
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
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or "\\" in value
    ):
        raise ValueError("backup contains an unsafe path")


def _validate_archive_member(info: zipfile.ZipInfo) -> None:
    mode = (info.external_attr >> 16) & 0o170000
    if info.is_dir() or mode == 0o120000:
        raise ValueError("backup contains a directory or symbolic-link member")
    if info.flag_bits & 0x1:
        raise ValueError("encrypted backup members are not supported")
    if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
        raise ValueError("backup uses an unsupported compression method")


def _archive_member_checksum(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with archive.open(info, "r") as source:
        for block in iter(lambda: source.read(_COPY_BLOCK_BYTES), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def _copy_archive_member(
    archive: zipfile.ZipFile, archive_path: str, destination: Path
) -> None:
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with archive.open(archive_path, "r") as source, os.fdopen(
            descriptor, "wb"
        ) as target:
            descriptor = -1
            for block in iter(lambda: source.read(_COPY_BLOCK_BYTES), b""):
                target.write(block)
            target.flush()
            os.fsync(target.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _is_database_sidecar(path: Path, database_path: Path) -> bool:
    return path in {
        database_path.with_name(f"{database_path.name}-wal"),
        database_path.with_name(f"{database_path.name}-shm"),
    }
