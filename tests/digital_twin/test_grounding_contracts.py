import pytest
from pydantic import ValidationError

from src.digital_twin.grounding import (
    CourseDocument,
    DocumentChunk,
    DocumentChunker,
    DocumentRegion,
    ParsedDocumentBundle,
    RegionKind,
    RetrievalHit,
    Retriever,
    SourceCitation,
    SourcePermissions,
    TutorAnswer,
    TutorGenerator,
)
from src.digital_twin.tutor_policy import SourceLabel, build_initial_policy
from tests.fixtures.grounding import (
    SyntheticDocumentChunker,
    SyntheticRetriever,
    SyntheticTutorGenerator,
)


def synthetic_document() -> CourseDocument:
    return CourseDocument(
        id="document-1",
        title="Synthetic course syllabus",
        text=(
            "Office hours are Tuesday afternoon. "
            "The final project requires a short reflection and demonstration."
        ),
        source_label=SourceLabel.COURSE_APPROVED,
        metadata={"fixture": "true"},
    )


def test_contract_models_validate_labels_scores_and_ordinals():
    with pytest.raises(ValidationError):
        CourseDocument(
            id="document-1",
            title="Synthetic source",
            text="Safe synthetic text.",
            source_label="unknown-source",
        )

    with pytest.raises(ValidationError):
        DocumentChunk(
            id="chunk-1",
            document_id="document-1",
            text="Synthetic chunk.",
            ordinal=-1,
        )

    chunk = SyntheticDocumentChunker(words_per_chunk=4).chunk(synthetic_document())[0]
    with pytest.raises(ValidationError):
        RetrievalHit(chunk=chunk, relevance_score=1.1)
    with pytest.raises(ValidationError):
        RetrievalHit(chunk=chunk, relevance_score=float("nan"))
    with pytest.raises(ValidationError):
        RetrievalHit(chunk=chunk, relevance_score=1, raw_score=float("inf"))


def test_source_citation_validates_checksum_and_normalized_bounding_box():
    with pytest.raises(ValidationError, match="SHA-256"):
        SourceCitation(
            source_id="document-1",
            title="Synthetic source",
            locator="page 1",
            source_checksum="not-a-checksum",
        )
    with pytest.raises(ValidationError, match="normalized"):
        SourceCitation(
            source_id="document-1",
            title="Synthetic source",
            locator="page 1",
            bounding_box=(0, 0, 2, 1),
        )


def test_grounding_text_models_reject_whitespace_only_content():
    with pytest.raises(ValidationError, match="must not be blank"):
        DocumentChunk(
            id="chunk-blank",
            document_id="document-blank",
            text="   ",
            ordinal=0,
        )


def test_parsed_bundle_rejects_cross_document_or_permission_escalation():
    permissions = SourcePermissions(
        processing_allowed=True,
        tutoring_allowed=False,
        display_allowed=False,
    )
    document = CourseDocument(
        id="document-1",
        title="Synthetic source",
        text="Synthetic source text.",
        source_label="course-approved",
        permissions=permissions,
    )
    region = DocumentRegion(
        id="region-1",
        document_id=document.id,
        source_artifact_id=document.source_artifact_id,
        source_version=document.source_version,
        source_checksum="a" * 64,
        page=1,
        kind=RegionKind.TEXT,
        bounding_box=(0.1, 0.1, 0.9, 0.2),
        reading_order=0,
        locator="page 1",
        text="Synthetic region text.",
        extraction_method="synthetic",
        checksum="b" * 64,
        crop_ref="region://region-1.png",
        permissions=permissions,
    )

    with pytest.raises(ValidationError, match="lineage does not match"):
        ParsedDocumentBundle(
            document=document,
            regions=[region.model_copy(update={"document_id": "other-document"})],
        )
    elevated = region.model_copy(
        update={
            "permissions": SourcePermissions(
                processing_allowed=True,
                tutoring_allowed=True,
                display_allowed=False,
            )
        }
    )
    with pytest.raises(ValidationError, match="permissions exceed"):
        ParsedDocumentBundle(document=document, regions=[elevated])


def test_tutor_answer_rejects_duplicate_citation_relationships():
    citation = SourceCitation(
        source_id="document-1",
        title="Synthetic course syllabus",
        locator="chunk 1",
    )

    with pytest.raises(ValidationError, match="duplicate source citation"):
        TutorAnswer(
            content="Synthetic answer.",
            citations=[citation, citation],
        )


def test_synthetic_fixtures_implement_provider_neutral_contracts():
    chunker: DocumentChunker = SyntheticDocumentChunker(words_per_chunk=6)
    chunks = chunker.chunk(synthetic_document())
    retriever: Retriever = SyntheticRetriever(chunks)
    generator: TutorGenerator = SyntheticTutorGenerator()

    assert len(chunks) == 3
    assert chunks[0].document_id == "document-1"
    assert chunks[0].metadata["source_label"] == "course-approved"
    assert retriever.retrieve("final project reflection", limit=1)[0].chunk == chunks[1]
    assert generator is not None


@pytest.mark.asyncio
async def test_synthetic_grounding_path_has_citation_relationships_and_no_network():
    chunks = SyntheticDocumentChunker(words_per_chunk=6).chunk(synthetic_document())
    hits = SyntheticRetriever(chunks).retrieve("final project reflection")

    answer = await SyntheticTutorGenerator().generate(
        "What does the final project require?",
        hits,
        build_initial_policy(),
    )

    assert answer.content.startswith("Synthetic grounded answer:")
    assert answer.warnings == []
    assert {citation.source_id for citation in answer.citations} == {
        hit.chunk.document_id for hit in hits
    }
    assert answer.citations[0].title == "Synthetic course syllabus"


@pytest.mark.asyncio
async def test_synthetic_generator_warns_when_retrieval_has_no_evidence():
    answer = await SyntheticTutorGenerator().generate(
        "Question outside the fixture.",
        [],
        build_initial_policy(),
    )

    assert answer.citations == []
    assert answer.warnings == ["No approved source evidence was retrieved."]
