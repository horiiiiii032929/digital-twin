import math
import re
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


class OutreachChannel(StrEnum):
    IN_APP = "in-app"
    DISCORD = "discord"


class ProactiveTriggerKind(StrEnum):
    SCHEDULED_RETRIEVAL_PRACTICE = "scheduled-retrieval-practice"
    STUDENT_FOLLOW_UP = "student-follow-up"
    MISCONCEPTION_FOLLOW_UP = "misconception-follow-up"
    EVIDENCE_RECOVERY = "evidence-recovery"


class EvidenceRecoveryMode(StrEnum):
    SHADOW = "shadow"
    ACTIVE = "active"


class ProactiveTriggerStatus(StrEnum):
    PENDING = "pending"
    MATERIALIZED = "materialized"
    SUPPRESSED = "suppressed"
    CANCELLED = "cancelled"


class ProactiveMessageStatus(StrEnum):
    QUEUED = "queued"
    DELIVERED = "delivered"
    READ = "read"
    DISMISSED = "dismissed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DeliveryAttemptStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutreachPreference(BaseModel):
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    channel: OutreachChannel
    enabled: bool = False
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    max_messages_per_7_days: int = Field(default=3, ge=1, le=14)
    snoozed_until: str | None = None
    destination_ref: str | None = Field(default=None, max_length=128)
    private_destination: bool = False
    updated_at: str = Field(default_factory=timestamp_now)

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error
        return value

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def quiet_hour_must_be_hhmm(cls, value: str) -> str:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("quiet hours must use HH:MM in 24-hour time")
        return value

    @field_validator("destination_ref")
    @classmethod
    def destination_ref_must_be_opaque(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if (
            not normalized
            or "://" in normalized
            or not re.fullmatch(r"[A-Za-z0-9._:-]+", normalized)
        ):
            raise ValueError("destination_ref must be an opaque identifier, not a URL")
        return normalized

    @model_validator(mode="after")
    def enabled_channel_must_have_safe_destination(self) -> "OutreachPreference":
        if self.channel == OutreachChannel.IN_APP and self.destination_ref is not None:
            raise ValueError("in-app outreach cannot use an external destination")
        if self.channel == OutreachChannel.DISCORD and self.enabled and (
            not self.destination_ref or not self.private_destination
        ):
            raise ValueError(
                "enabled Discord outreach requires a linked private destination"
            )
        return self


class ProactiveTrigger(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    professor_id: str = Field(min_length=1, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    channel: OutreachChannel
    kind: ProactiveTriggerKind
    scheduled_for: str
    expires_at: str
    topic: str = Field(min_length=1, max_length=240)
    prompt: str = Field(min_length=1, max_length=2_000)
    source_chunk_id: str = Field(min_length=1, max_length=256)
    status: ProactiveTriggerStatus = ProactiveTriggerStatus.PENDING
    suppression_reason: str | None = Field(default=None, max_length=128)
    created_at: str = Field(default_factory=timestamp_now)
    updated_at: str = Field(default_factory=timestamp_now)


class ProactiveMessage(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    trigger_id: str = Field(min_length=1, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    channel: OutreachChannel
    content: str = Field(min_length=1, max_length=8_000)
    status: ProactiveMessageStatus
    created_at: str = Field(default_factory=timestamp_now)
    read_at: str | None = None
    dismissed_at: str | None = None


class ProactiveMessageView(BaseModel):
    message: ProactiveMessage
    citations: list[Citation] = Field(default_factory=list)


class DeliveryOutboxItem(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    message_id: str = Field(min_length=1, max_length=128)
    channel: OutreachChannel
    destination_ref: str = Field(min_length=1, max_length=128)
    status: DeliveryAttemptStatus = DeliveryAttemptStatus.PENDING
    attempts: int = Field(default=0, ge=0, le=3)
    last_error: str | None = Field(default=None, max_length=500)
    available_at: str = Field(default_factory=timestamp_now)
    created_at: str = Field(default_factory=timestamp_now)
    updated_at: str = Field(default_factory=timestamp_now)


class ProactiveProcessResult(BaseModel):
    outcome: Literal[
        "not-due",
        "deferred-quiet-hours",
        "suppressed",
        "delivered",
        "queued",
        "duplicate",
    ]
    trigger: ProactiveTrigger
    message: ProactiveMessageView | None = None


class NoEvidenceTurn(BaseModel):
    student_message_id: str = Field(min_length=1, max_length=128)
    tutor_message_id: str = Field(min_length=1, max_length=128)
    conversation_id: str = Field(min_length=1, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=100_000)
    created_at: str = Field(min_length=1)


class EvidenceRecoveryDecision(BaseModel):
    student_message_id: str = Field(min_length=1, max_length=128)
    tutor_message_id: str = Field(min_length=1, max_length=128)
    student_id: str = Field(min_length=1, max_length=128)
    course_id: str = Field(min_length=1, max_length=128)
    previous_release_id: str = Field(min_length=1, max_length=128)
    current_release_id: str = Field(min_length=1, max_length=128)
    action: Literal["propose", "no-action", "duplicate"]
    reason: str = Field(min_length=1, max_length=128)
    evidence_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    source_chunk_id: str | None = Field(default=None, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=128)
    trigger_id: str | None = Field(default=None, max_length=128)


class EvidenceRecoveryScanResult(BaseModel):
    mode: EvidenceRecoveryMode
    course_id: str = Field(min_length=1, max_length=128)
    release_id: str = Field(min_length=1, max_length=128)
    decisions: list[EvidenceRecoveryDecision] = Field(default_factory=list)
    proposed_count: int = Field(ge=0)
    no_action_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    trigger_count: int = Field(ge=0)
    provider_calls: int = Field(default=0, ge=0, le=0)

    @model_validator(mode="after")
    def counts_must_match_decisions(self) -> "EvidenceRecoveryScanResult":
        expected = {
            "propose": self.proposed_count,
            "no-action": self.no_action_count,
            "duplicate": self.duplicate_count,
        }
        actual = {
            action: sum(decision.action == action for decision in self.decisions)
            for action in expected
        }
        if expected != actual or self.trigger_count > self.proposed_count:
            raise ValueError("evidence-recovery counts do not match decisions")
        return self
