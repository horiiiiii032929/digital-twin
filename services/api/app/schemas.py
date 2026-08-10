from pydantic import BaseModel, Field

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.student.models import ReleaseEvaluationStatus
from src.digital_twin.tutor_policy import (
    FieldStatus,
    PreviewDecisionValue,
    PromptTag,
    SourceLabel,
    SourcePermissionStatus,
)


class MessageRequest(BaseModel):
    content: str


class PolicyFieldUpdateRequest(BaseModel):
    value: str | list[str] | dict
    status: FieldStatus = FieldStatus.RESOLVED


class SourceInventoryCreateRequest(BaseModel):
    name: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    permission_status: SourcePermissionStatus = SourcePermissionStatus.PENDING
    source_label: SourceLabel = SourceLabel.COURSE_APPROVED
    excluded: bool = False
    sensitive: bool | None = None
    notes: str = ""


class SourceInventoryUpdateRequest(BaseModel):
    name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    permission_status: SourcePermissionStatus | None = None
    source_label: SourceLabel | None = None
    excluded: bool | None = None
    sensitive: bool | None = None
    notes: str | None = None


class ApprovalChecklistUpdateRequest(BaseModel):
    checked: bool


class PreviewDecisionRequest(BaseModel):
    decision: PreviewDecisionValue
    reason: str | None = None


class CustomPreviewRequest(BaseModel):
    prompt: str
    tag: PromptTag


class StudentMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    request_id: str = Field(min_length=1, max_length=128)


class ReleaseCreateRequest(BaseModel):
    session_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    release_id: str | None = Field(default=None, min_length=1)


class ReleaseEvaluationRequest(BaseModel):
    status: ReleaseEvaluationStatus
