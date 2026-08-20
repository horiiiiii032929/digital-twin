"""Operational models for durable source ingestion."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.tutor_policy import SourceLabel


class IngestionJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StoredObject(BaseModel):
    key: str = Field(min_length=1)
    checksum: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    mime_type: str = Field(min_length=1)

    @field_validator("checksum")
    @classmethod
    def checksum_must_be_sha256(cls, value: str) -> str:
        return _sha256(value)


class IngestionJobResult(BaseModel):
    source_artifact_id: str
    source_version: int = Field(ge=1)
    source_checksum: str
    document_id: str
    chunk_count: int = Field(ge=0)
    region_count: int = Field(ge=0)
    region_kind_counts: dict[str, int] = Field(default_factory=dict)
    processing_warnings: list[str] = Field(default_factory=list)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    derived_storage_refs: list[str] = Field(default_factory=list)

    @field_validator("source_checksum")
    @classmethod
    def source_checksum_must_be_sha256(cls, value: str) -> str:
        return _sha256(value)

    @model_validator(mode="after")
    def result_counts_and_lineage_must_match(self) -> "IngestionJobResult":
        if any(
            not kind.strip()
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for kind, count in self.region_kind_counts.items()
        ):
            raise ValueError(
                "region kind names must be nonblank and counts non-negative integers"
            )
        if self.chunk_count != len(self.chunks):
            raise ValueError("chunk_count must match the returned chunks")
        if sum(self.region_kind_counts.values()) != self.region_count:
            raise ValueError("region kind counts must match region_count")
        identifiers = [chunk.id for chunk in self.chunks]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("ingestion result chunk IDs must be unique")
        if any(
            chunk.source_artifact_id != self.source_artifact_id
            or chunk.source_version != self.source_version
            or chunk.source_checksum != self.source_checksum
            for chunk in self.chunks
        ):
            raise ValueError("ingestion result chunk lineage is inconsistent")
        if len(self.derived_storage_refs) != len(set(self.derived_storage_refs)):
            raise ValueError("derived storage references must be unique")
        return self


class IngestionJob(BaseModel):
    id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    version: int = Field(ge=1)
    professor_id: str = Field(min_length=1)
    display_allowed: bool = False
    source_label: SourceLabel = SourceLabel.COURSE_APPROVED
    source_object_key: str = Field(min_length=1)
    source_checksum: str = Field(min_length=64, max_length=64)
    status: IngestionJobStatus = IngestionJobStatus.PENDING
    attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    lease_owner: str | None = None
    lease_expires_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    result: IngestionJobResult | None = None
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)

    @field_validator("source_checksum")
    @classmethod
    def source_checksum_must_be_sha256(cls, value: str) -> str:
        return _sha256(value)

    @model_validator(mode="after")
    def state_must_be_internally_consistent(self) -> "IngestionJob":
        if self.attempts > self.max_attempts:
            raise ValueError("ingestion attempts cannot exceed max_attempts")
        has_owner = self.lease_owner is not None
        has_expiry = self.lease_expires_at is not None
        if has_owner != has_expiry:
            raise ValueError("ingestion lease owner and expiry must be set together")
        if self.status == IngestionJobStatus.RUNNING and not has_owner:
            raise ValueError("running ingestion jobs require a lease")
        if self.status != IngestionJobStatus.RUNNING and has_owner:
            raise ValueError("only running ingestion jobs may hold a lease")
        if self.status == IngestionJobStatus.SUCCEEDED:
            if self.result is None or self.error_code or self.error_message:
                raise ValueError("succeeded ingestion jobs require only a result")
        elif self.result is not None:
            raise ValueError("only succeeded ingestion jobs may contain a result")
        if self.status == IngestionJobStatus.FAILED and (
            not self.error_code or not self.error_message
        ):
            raise ValueError("failed ingestion jobs require a sanitized error")
        return self


def _sha256(value: str) -> str:
    normalized = value.casefold()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("checksum must be a SHA-256 digest")
    return normalized
