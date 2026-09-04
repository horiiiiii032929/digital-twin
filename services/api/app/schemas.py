import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.student.models import (
    AccountRole,
    OutreachChannel,
    ProactiveTriggerKind,
    ReleaseEvaluationStatus,
)
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
    CourseConceptV1,
    CourseMisconceptionV1,
    CourseObjectiveV1,
)
from src.digital_twin.student.teaching_profile import TeachingProfileDepth
from src.digital_twin.tutor_policy import (
    FieldStatus,
    PreviewDecisionValue,
    PromptTag,
    SourceLabel,
    SourcePermissionStatus,
)


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8_000)

    @field_validator("content")
    @classmethod
    def content_must_be_nonblank(cls, value: str) -> str:
        return _nonblank(value, "message")


class PolicyFieldUpdateRequest(BaseModel):
    value: str | list[str] | dict
    status: FieldStatus = FieldStatus.RESOLVED

    @field_validator("value")
    @classmethod
    def value_must_be_bounded_json(
        cls, value: str | list[str] | dict
    ) -> str | list[str] | dict:
        try:
            encoded = json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise ValueError("policy field value must be finite JSON") from error
        if len(encoded) > 65_536:
            raise ValueError("policy field value exceeds 65536 bytes")
        return value


class SourceInventoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(
        default="application/octet-stream", min_length=1, max_length=255
    )
    size_bytes: int = Field(default=0, ge=0, le=1_099_511_627_776)
    permission_status: SourcePermissionStatus = SourcePermissionStatus.PENDING
    source_label: SourceLabel = SourceLabel.COURSE_APPROVED
    excluded: bool = False
    sensitive: bool | None = None
    notes: str = Field(default="", max_length=4_000)

    @field_validator("name", "mime_type")
    @classmethod
    def required_text_must_be_nonblank(cls, value: str) -> str:
        return _nonblank(value, "source metadata")


class SourceInventoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    mime_type: str | None = Field(default=None, min_length=1, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0, le=1_099_511_627_776)
    permission_status: SourcePermissionStatus | None = None
    source_label: SourceLabel | None = None
    excluded: bool | None = None
    sensitive: bool | None = None
    notes: str | None = Field(default=None, max_length=4_000)

    @field_validator("name", "mime_type")
    @classmethod
    def required_text_must_be_nonblank(cls, value: str | None) -> str | None:
        return None if value is None else _nonblank(value, "source metadata")


class ApprovalChecklistUpdateRequest(BaseModel):
    checked: bool


class PreviewDecisionRequest(BaseModel):
    decision: PreviewDecisionValue
    reason: str | None = Field(default=None, max_length=2_000)


class CustomPreviewRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8_000)
    tag: PromptTag


class RevisionAlternativeSelectionRequest(BaseModel):
    alternative_id: str = Field(min_length=1, max_length=128)


class StudentMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8_000)
    request_id: str = Field(min_length=1, max_length=128)
    responding_to_outreach_message_id: str | None = Field(
        default=None, min_length=1, max_length=128
    )

    @field_validator("request_id", "responding_to_outreach_message_id")
    @classmethod
    def required_text_must_be_nonblank(cls, value: str | None) -> str | None:
        return None if value is None else _nonblank(value, "student request identifier")


class OutreachPreferenceRequest(BaseModel):
    enabled: bool
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    max_messages_per_7_days: int = Field(default=3, ge=1, le=14)
    snoozed_until: str | None = Field(default=None, max_length=64)
    destination_ref: str | None = Field(default=None, max_length=128)
    private_destination: bool = False


class ProactiveTriggerRequest(BaseModel):
    student_account_id: str = Field(min_length=1, max_length=128)
    channel: OutreachChannel = OutreachChannel.IN_APP
    kind: ProactiveTriggerKind
    scheduled_for: str = Field(min_length=1, max_length=64)
    expires_at: str = Field(min_length=1, max_length=64)
    topic: str = Field(min_length=1, max_length=240)
    prompt: str = Field(min_length=1, max_length=2_000)
    source_chunk_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=128)

    @field_validator(
        "student_account_id",
        "scheduled_for",
        "expires_at",
        "topic",
        "prompt",
        "source_chunk_id",
        "idempotency_key",
    )
    @classmethod
    def proactive_text_must_be_nonblank(cls, value: str) -> str:
        return _nonblank(value, "proactive trigger field")


class TeachingProfileDraftRequest(BaseModel):
    tone: str = Field(min_length=1, max_length=240)
    depth: TeachingProfileDepth
    explanation_structure: list[str] = Field(min_length=1, max_length=6)
    example_preferences: list[str] = Field(default_factory=list, max_length=8)
    misconception_handling: str = Field(min_length=1, max_length=1_000)
    integrity_limits: str = Field(min_length=1, max_length=1_000)
    help_ladder: list[str] = Field(min_length=2, max_length=6)
    outreach_policy: str = Field(min_length=1, max_length=1_000)


class TeachingProfileApprovalRequest(BaseModel):
    preview_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LearningGapReviewRequest(BaseModel):
    release_id: str = Field(min_length=1, max_length=128)
    proposal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: str = Field(pattern=r"^(consider-for-next-release|dismissed)$")
    rationale: str = Field(default="", max_length=1_000)


class AutonomyPolicyRequest(BaseModel):
    approved_course_objectives: list[str] = Field(min_length=1, max_length=32)
    allowed_actions: list[AutonomousActionKind] = Field(max_length=9)
    autonomy_enabled: bool
    paused: bool = False
    kill_switch: bool = False


class CourseDomainModelCreateRequest(BaseModel):
    release_id: str = Field(min_length=1, max_length=128)
    version: int = Field(ge=1)
    objectives: list[CourseObjectiveV1] = Field(min_length=1, max_length=64)
    concepts: list[CourseConceptV1] = Field(min_length=1, max_length=256)
    misconceptions: list[CourseMisconceptionV1] = Field(
        default_factory=list,
        max_length=256,
    )


class CourseTutoringRuntimeProfileRequest(BaseModel):
    mode: Literal[
        "grounded-assistant",
        "bounded-tutoring-graph",
        "governed-autonomous-tutoring-graph-v2.1",
    ]
    reason: str = Field(min_length=1, max_length=500)


class AutonomousGoalCreateRequest(BaseModel):
    student_account_id: str = Field(min_length=1, max_length=128)
    approved_course_objective: str = Field(min_length=1, max_length=500)
    learner_subgoal: str = Field(min_length=1, max_length=500)
    success_condition: str = Field(min_length=1, max_length=500)
    expires_at: str = Field(min_length=1, max_length=64)
    priority: int = Field(default=1, ge=1, le=5)
    attempt_limit: int = Field(default=3, ge=1, le=10)


class AutonomousOpportunityCreateRequest(BaseModel):
    student_account_id: str = Field(min_length=1, max_length=128)
    event_kind: AutonomousEventKind
    earliest_action_at: str = Field(min_length=1, max_length=64)
    latest_action_at: str = Field(min_length=1, max_length=64)
    goal_id: str | None = Field(default=None, max_length=128)
    concept_id: str | None = Field(default=None, max_length=128)
    source_chunk_id: str | None = Field(default=None, max_length=256)
    source_chunk_ids: list[str] = Field(default_factory=list, max_length=5)
    supporting_observation_ids: list[str] = Field(default_factory=list, max_length=16)
    idempotency_key: str | None = Field(default=None, max_length=128)


class ReleaseCreateRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    profile_id: str = Field(min_length=1, max_length=128)
    profile_version: str = Field(min_length=1, max_length=128)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    ingestion_job_ids: list[str] = Field(default_factory=list, max_length=100)
    teaching_profile_id: str | None = Field(default=None, min_length=1, max_length=128)
    release_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator(
        "session_id",
        "profile_id",
        "profile_version",
        "teaching_profile_id",
        "release_id",
    )
    @classmethod
    def identifiers_must_be_nonblank(cls, value: str | None) -> str | None:
        return None if value is None else _nonblank(value, "release identifier")

    @field_validator("ingestion_job_ids")
    @classmethod
    def job_ids_must_be_unique_and_nonblank(cls, value: list[str]) -> list[str]:
        normalized = [_nonblank(item, "ingestion job identifier") for item in value]
        if len(normalized) != len(set(normalized)):
            raise ValueError("ingestion job identifiers must be unique")
        return normalized

    @model_validator(mode="after")
    def release_sources_must_not_be_ambiguous(self) -> "ReleaseCreateRequest":
        if self.chunks and self.ingestion_job_ids:
            raise ValueError("provide chunks or ingestion jobs, not both")
        return self


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

    @field_validator("email")
    @classmethod
    def email_must_be_nonblank(cls, value: str) -> str:
        return _nonblank(value, "email")


class AccountInviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=160)
    role: AccountRole
    temporary_password: str = Field(min_length=12, max_length=1024)

    @field_validator("email", "display_name")
    @classmethod
    def identity_text_must_be_nonblank(cls, value: str) -> str:
        return _nonblank(value, "account field")


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=1024)


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    course_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("title", "course_id")
    @classmethod
    def course_text_must_be_nonblank(cls, value: str | None) -> str | None:
        return None if value is None else _nonblank(value, "course field")


class StudentAssignmentRequest(BaseModel):
    student_account_id: str = Field(min_length=1, max_length=128)

    @field_validator("student_account_id")
    @classmethod
    def student_id_must_be_nonblank(cls, value: str) -> str:
        return _nonblank(value, "student account identifier")


def _nonblank(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} cannot be blank")
    return normalized
