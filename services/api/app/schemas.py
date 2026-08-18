from pydantic import BaseModel, Field

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.student.models import AccountRole, ReleaseEvaluationStatus
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


class CourseSourceIngestionResponse(BaseModel):
    source_artifact_id: str
    source_version: int = Field(ge=1)
    source_checksum: str
    document_id: str
    chunk_count: int = Field(ge=0)
    region_count: int = Field(ge=0)
    region_kind_counts: dict[str, int] = Field(default_factory=dict)
    processing_warnings: list[str] = Field(default_factory=list)
    chunks: list[DocumentChunk] = Field(default_factory=list)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class AccountInviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=160)
    role: AccountRole
    temporary_password: str = Field(min_length=12, max_length=1024)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=1024)


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    course_id: str | None = Field(default=None, min_length=1, max_length=128)


class StudentAssignmentRequest(BaseModel):
    student_account_id: str = Field(min_length=1, max_length=128)
