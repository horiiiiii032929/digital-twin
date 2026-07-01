from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FieldStatus(StrEnum):
    RESOLVED = "resolved"
    NEEDS_REVIEW = "needs_review"
    BLOCKS_RELEASE = "blocks_release"


class ReleaseStatus(StrEnum):
    DRAFT = "draft"
    BLOCKED = "blocked"
    APPROVED = "approved"


class SourcePermissionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EXCLUDED = "excluded"


class SourceLabel(StrEnum):
    COURSE_APPROVED = "course-approved"
    PROFESSOR_APPROVED_EXTERNAL = "professor-approved-external"
    SYSTEM_SUGGESTED_TRUSTED = "system-suggested-trusted"
    UNAPPROVED_EXTERNAL = "unapproved-external"


MessageRole = Literal["assistant", "instructor", "system"]
PromptTag = Literal[
    "source_grounding",
    "academic_integrity",
    "misconception",
    "teaching_behavior",
    "tone",
    "other",
]
PreviewDecisionValue = Literal["pending", "accepted", "rejected"]


def timestamp_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def infer_sensitive_source_name(name: str) -> bool:
    normalized = name.lower()
    sensitive_markers = (
        "student",
        "transcript",
        "consent",
        "private",
        "forum",
        "record",
        "grade",
        "grades",
    )
    return any(marker in normalized for marker in sensitive_markers)


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class SourceInventoryItem(BaseModel):
    id: str
    name: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    permission_status: SourcePermissionStatus = SourcePermissionStatus.PENDING
    source_label: SourceLabel = SourceLabel.COURSE_APPROVED
    excluded: bool = False
    sensitive: bool | None = None
    notes: str = ""

    @model_validator(mode="after")
    def apply_metadata_defaults(self) -> "SourceInventoryItem":
        if self.sensitive is None:
            self.sensitive = infer_sensitive_source_name(self.name)

        if self.permission_status == SourcePermissionStatus.EXCLUDED:
            self.excluded = True

        if self.excluded:
            self.permission_status = SourcePermissionStatus.EXCLUDED

        if (
            self.sensitive
            and self.permission_status == SourcePermissionStatus.PENDING
        ):
            self.excluded = True
            self.permission_status = SourcePermissionStatus.EXCLUDED

        return self


class TrustedSourceAllowlist(BaseModel):
    professor_defined: list[str] = Field(default_factory=list)
    derived_from_course_materials: list[str] = Field(default_factory=list)


class KnowledgeSourcePolicy(BaseModel):
    source_strictness: str = "unresolved"
    recommended_value: str = "any_source_with_labels"
    allowed_values: list[str] = Field(
        default_factory=lambda: [
            "course_only",
            "trusted_only",
            "any_source_with_labels",
        ]
    )
    preview_source_mode: str = "any_source_with_labels"
    source_labels: list[SourceLabel] = Field(
        default_factory=lambda: [
            SourceLabel.COURSE_APPROVED,
            SourceLabel.PROFESSOR_APPROVED_EXTERNAL,
            SourceLabel.SYSTEM_SUGGESTED_TRUSTED,
            SourceLabel.UNAPPROVED_EXTERNAL,
        ]
    )
    trusted_source_allowlist: TrustedSourceAllowlist = Field(
        default_factory=TrustedSourceAllowlist
    )
    system_trusted_source_categories: list[str] = Field(
        default_factory=lambda: [
            "official_documentation",
            "standards_or_security_bodies",
            "university_pages",
        ]
    )
    external_sources_require_visible_labels: bool = True
    confirmed: bool = False
    policy_level: str = "course"


class PolicyField(BaseModel):
    id: str
    label: str
    status: FieldStatus
    value: str | list[str] | dict
    safe_default: str | None = None
    warning: str | None = None

    @property
    def blocks_release(self) -> bool:
        return self.status == FieldStatus.BLOCKS_RELEASE


class PreviewCase(BaseModel):
    id: str
    tag: PromptTag
    prompt: str
    generic_response: str
    configured_response: str
    policy_signals: list[str] = Field(default_factory=list)
    source_audit: list["PreviewAuditEntry"] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    decision: PreviewDecisionValue = "pending"
    decision_reason: str | None = None
    policy_version: int = 1
    generated_at: str | None = None


class PreviewAuditEntry(BaseModel):
    source_title: str
    url: str
    source_type: str
    source_label: SourceLabel
    supports: str
    conflict_status: str = "not_checked"
    selection_reason: str


class PreviewDecisionRecord(BaseModel):
    preview_case_id: str
    decision: PreviewDecisionValue = "pending"
    reason: str | None = None
    policy_version: int = 1
    timestamp: str = Field(default_factory=timestamp_now)
    revision_resolved: bool = False


class EvidenceSnapshot(BaseModel):
    id: str
    preview_case_id: str
    prompt: str
    configured_response: str
    source_audit: list[PreviewAuditEntry] = Field(default_factory=list)
    source_labels: list[SourceLabel] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    decision: PreviewDecisionValue = "pending"
    policy_version: int = 1
    timestamp: str = Field(default_factory=timestamp_now)


class RevisionProposal(BaseModel):
    id: str
    preview_case_id: str | None = None
    feedback: str
    affected_policy_fields: list[str]
    proposed_value: str
    rationale: str
    status: Literal["pending", "confirmed", "discarded"] = "pending"
    created_at: str = Field(default_factory=timestamp_now)


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
                value=KnowledgeSourcePolicy().model_dump(mode="json"),
                safe_default="Preview may use labeled examples; release requires explicit source strictness.",
            ),
            PolicyField(
                id="disallowed_private_sources",
                label="Disallowed private sources",
                status=FieldStatus.BLOCKS_RELEASE,
                value=[
                    "private student data",
                    "consent records",
                    "raw transcripts",
                    "private forum exports",
                    "unapproved instructor material",
                ],
                safe_default="Exclude private student data, consent records, raw transcripts, private forum exports, and unapproved instructor material.",
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
            PolicyField(
                id="feedback_policy",
                label="Feedback policy",
                status=FieldStatus.NEEDS_REVIEW,
                value="process feedback with concise task-level correction",
            ),
            PolicyField(
                id="proactive_support",
                label="Proactive support",
                status=FieldStatus.NEEDS_REVIEW,
                value="short checks when useful; no unsolicited practice plan",
            ),
            PolicyField(
                id="course_scope_boundary",
                label="Course scope boundary",
                status=FieldStatus.NEEDS_REVIEW,
                value="stay within approved course topics and visibly label external grounding",
            ),
            PolicyField(
                id="preferred_examples",
                label="Preferred examples",
                status=FieldStatus.NEEDS_REVIEW,
                value=["course-provided examples", "small analogous examples"],
            ),
            PolicyField(
                id="rejection_criteria",
                label="Rejection criteria",
                status=FieldStatus.NEEDS_REVIEW,
                value=[
                    "solves graded work directly",
                    "uses unapproved sources",
                    "mentions private or sensitive data",
                ],
            ),
            PolicyField(
                id="tone_guidance",
                label="Tone guidance",
                status=FieldStatus.NEEDS_REVIEW,
                value="clear, concise, and professor-reviewable",
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
