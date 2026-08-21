import math
import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.digital_twin.generation.policy import policy_is_approved_for_generation
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
    status: StudentReleaseStatus = StudentReleaseStatus.DRAFT
    evaluation_status: ReleaseEvaluationStatus = ReleaseEvaluationStatus.PENDING
    created_at: str = Field(default_factory=timestamp_now)

    @model_validator(mode="after")
    def published_release_must_be_approved_and_evaluated(self) -> "DigitalTwinRelease":
        identifiers = [chunk.id for chunk in self.chunks]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("release chunk IDs must be unique")
        if self.status == StudentReleaseStatus.PUBLISHED and (
            self.evaluation_status != ReleaseEvaluationStatus.PASSED
            or not self.chunks
            or not policy_is_approved_for_generation(self.policy)
        ):
            raise ValueError(
                "published releases require passed evaluation, evidence, and policy"
            )
        return self


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
    content: str = Field(min_length=1, max_length=100_000)
    action: str = Field(min_length=1)
    trace: GenerationTrace | None = None
    client_request_id: str | None = None
    response_to_message_id: str | None = None
    tutoring_mode: str = "grounded-assistant"
    tutoring_intent: str | None = None
    learner_state_revision: int | None = Field(default=None, ge=0)
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
    source_checksum: str | None = None
    page: int | None = Field(default=None, ge=1)
    region_id: str | None = None
    region_kind: str | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    crop_ref: str | None = None

    @field_validator("source_checksum")
    @classmethod
    def source_checksum_must_be_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.casefold()
        if not re.fullmatch(r"[0-9a-f]{64}", normalized):
            raise ValueError("citation source checksum must be a SHA-256 digest")
        return normalized

    @field_validator("bounding_box")
    @classmethod
    def bounding_box_must_be_normalized(
        cls, value: tuple[float, float, float, float] | None
    ) -> tuple[float, float, float, float] | None:
        if value is None:
            return None
        x0, y0, x1, y1 = value
        if any(not math.isfinite(coordinate) for coordinate in value) or not (
            0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
        ):
            raise ValueError("citation bounding_box must be normalized")
        return value


class AuditEvent(BaseModel):
    id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    account_id: str | None = None
    course_id: str | None = None
    release_id: str | None = None
    conversation_id: str | None = None
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: str = Field(default_factory=timestamp_now)

    @field_validator("details")
    @classmethod
    def detail_numbers_must_be_finite(
        cls, value: dict[str, str | int | float | bool | None]
    ) -> dict[str, str | int | float | bool | None]:
        if any(
            isinstance(item, float) and not math.isfinite(item)
            for item in value.values()
        ):
            raise ValueError("audit detail numbers must be finite")
        return value


class StudentCourse(BaseModel):
    course_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)


class ProfessorReleaseSummary(BaseModel):
    id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    status: StudentReleaseStatus
    evaluation_status: ReleaseEvaluationStatus
    policy_version: int = Field(ge=1)
    chunk_count: int = Field(ge=0)
    created_at: str = Field(min_length=1)


class ProfessorCourseView(BaseModel):
    course_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    student_account_ids: list[str] = Field(default_factory=list)
    releases: list[ProfessorReleaseSummary] = Field(default_factory=list)


class ReleasePreflightCheck(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    passed: bool
    detail: str = Field(min_length=1)


class ReleasePreflightResult(BaseModel):
    release_id: str = Field(min_length=1)
    passed: bool
    checks: list[ReleasePreflightCheck]
    evaluated_at: str = Field(default_factory=timestamp_now)


class ConversationView(BaseModel):
    conversation: Conversation
    messages: list[Message]


class TutorTurn(BaseModel):
    student_message: Message
    tutor_message: Message
    citations: list[Citation]
    duplicate: bool = False
    tutoring_mode: str = "grounded-assistant"
    tutoring_intent: str | None = None
    learner_state_revision: int | None = Field(default=None, ge=0)
