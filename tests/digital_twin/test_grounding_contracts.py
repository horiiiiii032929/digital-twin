import pytest
from pydantic import ValidationError

from src.digital_twin.grounding import (
    CourseDocument,
    DocumentChunk,
    DocumentChunker,
    RetrievalHit,
    Retriever,
    SourceCitation,
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

    chunk = SyntheticDocumentChunker(words_per_chunk=4).chunk(
        synthetic_document()
    )[0]
    with pytest.raises(ValidationError):
        RetrievalHit(chunk=chunk, relevance_score=1.1)


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
    chunks = SyntheticDocumentChunker(words_per_chunk=6).chunk(
        synthetic_document()
    )
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
