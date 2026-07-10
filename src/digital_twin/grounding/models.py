from pydantic import BaseModel, Field, field_validator

from src.digital_twin.tutor_policy import SourceLabel


class CourseDocument(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_label: SourceLabel
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    metadata: dict[str, str] = Field(default_factory=dict)


class RetrievalHit(BaseModel):
    chunk: DocumentChunk
    relevance_score: float = Field(ge=0, le=1)


class SourceCitation(BaseModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class TutorAnswer(BaseModel):
    content: str = Field(min_length=1)
    citations: list[SourceCitation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

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
