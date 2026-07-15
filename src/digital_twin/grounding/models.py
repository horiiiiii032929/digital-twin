import hashlib
import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from src.digital_twin.tutor_policy import SourceLabel


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SourceSensitivity(StrEnum):
    STANDARD = "standard"
    SENSITIVE = "sensitive"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class SourcePermissions(BaseModel):
    processing_allowed: bool = False
    tutoring_allowed: bool = False
    display_allowed: bool = False


class SourceArtifact(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    checksum: str
    version: int = Field(ge=1)
    source_label: SourceLabel
    storage_ref: str = Field(min_length=1)
    provider_role: str = Field(min_length=1)
    sensitivity: SourceSensitivity = SourceSensitivity.STANDARD
    excluded: bool = False

    @field_validator("checksum")
    @classmethod
    def checksum_must_be_sha256(cls, checksum: str) -> str:
        normalized = checksum.lower()
        if not _SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("checksum must be a lowercase SHA-256 digest")
        return normalized


class ApprovalRecord(BaseModel):
    id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_version: int = Field(ge=1)
    decision: ApprovalDecision
    permissions: SourcePermissions = Field(default_factory=SourcePermissions)
    reviewer_id: str = Field(min_length=1)
    reviewer_role: str = Field(min_length=1)
    reviewed_at: datetime
    restrictions: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("reviewed_at")
    @classmethod
    def reviewed_at_must_include_timezone(cls, reviewed_at: datetime) -> datetime:
        if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must include a timezone")
        return reviewed_at

    @model_validator(mode="after")
    def approval_requires_a_professor_reviewer(self) -> "ApprovalRecord":
        if self.decision == ApprovalDecision.APPROVED and self.reviewer_role != "professor":
            raise ValueError("only a professor can approve a source")
        return self


class DocumentSegment(BaseModel):
    text: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    heading_path: list[str] = Field(default_factory=list)
    page: int | None = Field(default=None, ge=1)
    bounding_box: tuple[float, float, float, float] | None = None

    @field_validator("bounding_box")
    @classmethod
    def bounding_box_must_be_normalized(
        cls,
        bounding_box: tuple[float, float, float, float] | None,
    ) -> tuple[float, float, float, float] | None:
        if bounding_box is None:
            return None
        x0, y0, x1, y1 = bounding_box
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError("bounding_box must contain normalized x0, y0, x1, y1")
        return bounding_box


class CourseDocument(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_label: SourceLabel
    source_artifact_id: str | None = None
    source_version: int = Field(default=1, ge=1)
    content_hash: str | None = None
    locator: str = "document"
    permissions: SourcePermissions = Field(default_factory=SourcePermissions)
    approval_record_id: str | None = None
    segments: list[DocumentSegment] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fill_stable_provenance_defaults(self) -> "CourseDocument":
        if self.source_artifact_id is None:
            self.source_artifact_id = self.id
        if self.content_hash is None:
            self.content_hash = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        elif not _SHA256_PATTERN.fullmatch(self.content_hash):
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        return self


class DocumentChunk(BaseModel):
    id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    source_artifact_id: str | None = None
    source_version: int = Field(default=1, ge=1)
    source_label: SourceLabel | None = None
    content_hash: str | None = None
    locator: str | None = None
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    retrieval_allowed: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fill_chunk_defaults(self) -> "DocumentChunk":
        if self.source_artifact_id is None:
            self.source_artifact_id = self.document_id
        if self.content_hash is None:
            self.content_hash = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        elif not _SHA256_PATTERN.fullmatch(self.content_hash):
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        if self.locator is None:
            self.locator = self.metadata.get("locator", f"chunk {self.ordinal + 1}")
        if self.page_start and self.page_end and self.page_end < self.page_start:
            raise ValueError("page_end must not be before page_start")
        return self


class FigureAsset(BaseModel):
    id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_version: int = Field(ge=1)
    page: int = Field(ge=1)
    bounding_box: tuple[float, float, float, float]
    caption: str = ""
    surrounding_text: str = ""
    extraction_method: str = Field(min_length=1)
    checksum: str
    image_ref: str = Field(min_length=1)
    permissions: SourcePermissions

    @field_validator("bounding_box")
    @classmethod
    def figure_bounding_box_must_be_normalized(
        cls,
        bounding_box: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float]:
        validated = DocumentSegment.bounding_box_must_be_normalized(bounding_box)
        if validated is None:
            raise ValueError("figure bounding_box is required")
        return validated

    @field_validator("checksum")
    @classmethod
    def figure_checksum_must_be_sha256(cls, checksum: str) -> str:
        normalized = checksum.lower()
        if not _SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("checksum must be a lowercase SHA-256 digest")
        return normalized


class FigureDescription(BaseModel):
    figure_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    method: str = Field(min_length=1)
    model_version: str | None = None
    prompt_version: str | None = None
    review_status: str = Field(min_length=1)


class ParsedDocumentBundle(BaseModel):
    document: CourseDocument
    figures: list[FigureAsset] = Field(default_factory=list)


class RetrievalHit(BaseModel):
    chunk: DocumentChunk
    relevance_score: float = Field(ge=0, le=1)


class SourceCitation(BaseModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class GenerationUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    approximate_cost_usd: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )


class GenerationTrace(BaseModel):
    generator_id: str = Field(min_length=1)
    provider_model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    policy_action: str = Field(min_length=1)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    usage: GenerationUsage = Field(default_factory=GenerationUsage)


class TutorAnswer(BaseModel):
    content: str = Field(min_length=1)
    citations: list[SourceCitation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: GenerationTrace | None = None

    @field_validator("citations")
    @classmethod
    def citations_must_be_unique(
        cls,
        citations: list[SourceCitation],
    ) -> list[SourceCitation]:
        relationships = [
            (citation.source_id, citation.locator) for citation in citations
        ]
        if len(relationships) != len(set(relationships)):
            raise ValueError("duplicate source citation")
        return citations
