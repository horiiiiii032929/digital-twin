from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from src.digital_twin.grounding.models import DocumentChunk, GenerationTrace
from src.digital_twin.tutor_policy import TutorPolicy, timestamp_now


class AccountRole(StrEnum):
    ADMIN = "admin"
    PROFESSOR = "professor"
    STUDENT = "student"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class MembershipRole(StrEnum):
    PROFESSOR = "professor"
    STUDENT = "student"


class StudentReleaseStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class ReleaseEvaluationStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class Account(BaseModel):
    id: str = Field(min_length=1)
    role: AccountRole
    status: AccountStatus = AccountStatus.ACTIVE


class Course(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    owner_professor_id: str = Field(min_length=1)


class CourseMembership(BaseModel):
    account_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    role: MembershipRole
    active: bool = True


class DigitalTwinRelease(BaseModel):
    id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    policy_version: int = Field(ge=1)
    policy: TutorPolicy
    chunks: list[DocumentChunk]
    status: StudentReleaseStatus = StudentReleaseStatus.PUBLISHED
    evaluation_status: ReleaseEvaluationStatus = ReleaseEvaluationStatus.PENDING
    created_at: str = Field(default_factory=timestamp_now)


class Conversation(BaseModel):
    id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    created_at: str = Field(default_factory=timestamp_now)
    updated_at: str = Field(default_factory=timestamp_now)


MessageRole = Literal["student", "tutor"]


class Message(BaseModel):
    id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    role: MessageRole
    content: str = Field(min_length=1)
    action: str = Field(min_length=1)
    trace: GenerationTrace | None = None
    client_request_id: str | None = None
    response_to_message_id: str | None = None
    created_at: str = Field(default_factory=timestamp_now)


class Citation(BaseModel):
    id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    source_version: int = Field(ge=1)
    title: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class AuditEvent(BaseModel):
    id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    account_id: str | None = None
    course_id: str | None = None
    release_id: str | None = None
    conversation_id: str | None = None
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: str = Field(default_factory=timestamp_now)


class StudentCourse(BaseModel):
    course_id: str
    title: str
    release_id: str
    profile_id: str
    profile_version: str


class ConversationView(BaseModel):
    conversation: Conversation
    messages: list[Message]


class TutorTurn(BaseModel):
    student_message: Message
    tutor_message: Message
    citations: list[Citation]
    duplicate: bool = False
