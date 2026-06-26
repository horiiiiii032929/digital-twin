from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class FieldStatus(StrEnum):
    RESOLVED = "resolved"
    NEEDS_REVIEW = "needs_review"
    BLOCKS_RELEASE = "blocks_release"


class ReleaseStatus(StrEnum):
    DRAFT = "draft"
    BLOCKED = "blocked"
    APPROVED = "approved"


MessageRole = Literal["assistant", "instructor", "system"]


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class PolicyField(BaseModel):
    id: str
    label: str
    status: FieldStatus
    value: str | list[str]
    safe_default: str | None = None
    warning: str | None = None

    @property
    def blocks_release(self) -> bool:
        return self.status == FieldStatus.BLOCKS_RELEASE


class PreviewCase(BaseModel):
    id: str
    prompt: str
    generic_response: str
    configured_response: str
    policy_signals: list[str] = Field(default_factory=list)


class ApprovalItem(BaseModel):
    id: str
    label: str
    blocks_release: bool
    checked: bool = False

    @property
    def is_blocking_incomplete(self) -> bool:
        return self.blocks_release and not self.checked


class WorkflowTraceItem(BaseModel):
    id: str
    title: str
    detail: str
    status: Literal["complete", "warning", "blocked"]


class TutorPolicy(BaseModel):
    status: ReleaseStatus = ReleaseStatus.DRAFT
    release_status: ReleaseStatus = ReleaseStatus.BLOCKED
    safety_compliance: list[PolicyField]
    pedagogy: list[PolicyField]
    professor_review: list[PolicyField]

    @property
    def all_fields(self) -> list[PolicyField]:
        return self.safety_compliance + self.pedagogy + self.professor_review

    @property
    def blocker_ids(self) -> list[str]:
        return [field.id for field in self.all_fields if field.blocks_release]


def build_initial_policy() -> TutorPolicy:
    return TutorPolicy(
        safety_compliance=[
            PolicyField(
                id="approved_source_permissions",
                label="Approved source permissions",
                status=FieldStatus.BLOCKS_RELEASE,
                value="unresolved",
                safe_default="No private or course-owned material may be used until approved.",
            ),
            PolicyField(
                id="knowledge_source_policy",
                label="Knowledge source policy",
                status=FieldStatus.BLOCKS_RELEASE,
                value="unresolved",
                safe_default="Preview may use labeled examples; release requires explicit source strictness.",
            ),
            PolicyField(
                id="academic_integrity_policy",
                label="Academic integrity policy",
                status=FieldStatus.NEEDS_REVIEW,
                value="strict no full graded-work answers",
                warning="Professor has not confirmed graded-work help rules.",
            ),
            PolicyField(
                id="sensitive_data_handling",
                label="Sensitive data handling",
                status=FieldStatus.BLOCKS_RELEASE,
                value="unresolved",
                safe_default="Do not ingest student data, consent records, or private transcripts.",
            ),
        ],
        pedagogy=[
            PolicyField(
                id="teaching_approach",
                label="Teaching approach",
                status=FieldStatus.NEEDS_REVIEW,
                value="balanced",
            ),
            PolicyField(
                id="tutoring_moves",
                label="Tutoring moves",
                status=FieldStatus.NEEDS_REVIEW,
                value=["hints", "prompts", "misconception_correction"],
            ),
            PolicyField(
                id="misconception_handling",
                label="Misconception handling",
                status=FieldStatus.NEEDS_REVIEW,
                value="correct and redirect with a contrastive example",
            ),
        ],
        professor_review=[
            PolicyField(
                id="professor_release_approval",
                label="Professor release approval",
                status=FieldStatus.BLOCKS_RELEASE,
                value="pending",
                safe_default="Tutor remains draft-only until explicitly approved.",
            )
        ],
    )
