"""Atomic content-addressed storage for a persistent single-host volume."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from threading import RLock

from src.digital_twin.operations.models import StoredObject


_SAFE_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SAFE_SUFFIX = re.compile(r"^\.[a-z0-9]{1,10}$")


class FileSystemObjectStore:
    implementation_id = "content-addressed-filesystem-object-store"
    version = "v1"

    def __init__(self, root: Path, *, max_bytes: int | None = None) -> None:
        if max_bytes is not None and max_bytes <= 0:
            raise ValueError("object storage quota must be positive")
        self.root = root.resolve()
        self.max_bytes = max_bytes
        self._lock = RLock()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(
        self,
        content: bytes,
        *,
        namespace: str,
        suffix: str,
        mime_type: str,
    ) -> StoredObject:
        if not content:
            raise ValueError("object content is empty")
        if not _SAFE_SEGMENT.fullmatch(namespace):
            raise ValueError("object namespace must use lowercase kebab-case")
        if not _SAFE_SUFFIX.fullmatch(suffix):
            raise ValueError("object suffix is invalid")
        digest = hashlib.sha256(content).hexdigest()
        key = f"{namespace}/{digest[:2]}/{digest}{suffix}"
        destination = self._resolve(key)
        with self._lock:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if self.checksum(key) != digest:
                    raise RuntimeError("content-addressed object checksum mismatch")
            else:
                if (
                    self.max_bytes is not None
                    and self.used_bytes() + len(content) > self.max_bytes
                ):
                    raise ValueError("object storage quota exceeded")
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix="object-",
                    suffix=".pending",
                    dir=destination.parent,
                )
                temporary_path = Path(temporary_name)
                try:
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.chmod(temporary_path, 0o600)
                    temporary_path.replace(destination)
                except Exception:
                    temporary_path.unlink(missing_ok=True)
                    raise
        return StoredObject(
            key=key,
            checksum=digest,
            size_bytes=len(content),
            mime_type=mime_type,
        )

    def read(self, key: str) -> bytes:
        with self._lock:
            return self._resolve(key).read_bytes()

    def exists(self, key: str) -> bool:
        with self._lock:
            return self._resolve(key).is_file()

    def checksum(self, key: str) -> str:
        with self._lock:
            digest = hashlib.sha256()
            with self._resolve(key).open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            return digest.hexdigest()

    def delete(self, key: str) -> bool:
        with self._lock:
            path = self._resolve(key)
            if not path.exists():
                return False
            path.unlink()
            parent = path.parent
            while parent != self.root:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
            return True

    def iter_keys(self) -> list[str]:
        with self._lock:
            return sorted(
                path.relative_to(self.root).as_posix()
                for path in self._storage_files()
                if not path.name.endswith(".pending")
            )

    def used_bytes(self) -> int:
        with self._lock:
            return sum(
                path.stat().st_size
                for path in self._storage_files()
                if not path.name.endswith(".pending")
            )

    def _resolve(self, key: str) -> Path:
        if not key or key.startswith("/") or "\\" in key:
            raise ValueError("object key is invalid")
        parts = Path(key).parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("object key is invalid")
        candidate = self.root.joinpath(*parts)
        current = self.root
        for part in parts:
            current = current / part
            if current.is_symlink():
                raise RuntimeError("object storage contains a symbolic link")
        return candidate

    def _storage_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.root.rglob("*"):
            if path.is_symlink():
                raise RuntimeError("object storage contains a symbolic link")
            if path.is_file():
                files.append(path)
        return files
