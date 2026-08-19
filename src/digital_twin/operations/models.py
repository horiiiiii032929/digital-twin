"""Operational models for durable source ingestion."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

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
