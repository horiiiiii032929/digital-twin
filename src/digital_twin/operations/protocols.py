from __future__ import annotations

from typing import Protocol

from src.digital_twin.operations.models import IngestionJob, StoredObject


class ObjectStore(Protocol):
    def put(
        self,
        content: bytes,
        *,
        namespace: str,
        suffix: str,
        mime_type: str,
    ) -> StoredObject: ...

    def read(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def checksum(self, key: str) -> str: ...

    def delete(self, key: str) -> bool: ...


class IngestionJobRepository(Protocol):
    def healthcheck(self) -> bool: ...

    def get_by_idempotency_key(
        self, professor_id: str, course_id: str, idempotency_key: str
    ) -> IngestionJob | None: ...

    def enqueue(self, job: IngestionJob) -> tuple[IngestionJob, bool]: ...

    def get(self, job_id: str) -> IngestionJob | None: ...

    def list_for_course(
        self, professor_id: str, course_id: str
    ) -> list[IngestionJob]: ...

    def claim(self, worker_id: str, *, lease_seconds: int) -> IngestionJob | None: ...

    def renew_lease(
        self, job_id: str, worker_id: str, *, lease_seconds: int
    ) -> bool: ...

    def complete(self, job_id: str, worker_id: str, result_json: str) -> bool: ...

    def fail(
        self, job_id: str, worker_id: str, *, error_code: str, error_message: str
    ) -> bool: ...

    def cancel(self, job_id: str) -> IngestionJob | None: ...

    def retry(self, job_id: str) -> IngestionJob | None: ...

    def recover_expired(self, now: str) -> int: ...
