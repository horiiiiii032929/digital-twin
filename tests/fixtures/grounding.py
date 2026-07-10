import re

from src.digital_twin.grounding import (
    CourseDocument,
    DocumentChunk,
    RetrievalHit,
    SourceCitation,
    TutorAnswer,
)
from src.digital_twin.tutor_policy import TutorPolicy


class SyntheticDocumentChunker:
    def __init__(self, words_per_chunk: int = 12) -> None:
        if words_per_chunk < 1:
            raise ValueError("words_per_chunk must be positive")
        self.words_per_chunk = words_per_chunk

    def chunk(self, document: CourseDocument) -> list[DocumentChunk]:
        words = document.text.split()
        chunks: list[DocumentChunk] = []
        for ordinal, start in enumerate(range(0, len(words), self.words_per_chunk)):
            chunks.append(
                DocumentChunk(
                    id=f"{document.id}-chunk-{ordinal}",
                    document_id=document.id,
                    text=" ".join(words[start : start + self.words_per_chunk]),
                    ordinal=ordinal,
                    metadata={
                        **document.metadata,
                        "title": document.title,
                        "source_label": document.source_label.value,
                        "locator": f"chunk {ordinal + 1}",
                    },
                )
            )
        return chunks


class SyntheticRetriever:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = list(chunks)

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if limit < 1:
            return []

        query_terms = _terms(query)
        if not query_terms:
            return []

        hits = []
        for chunk in self.chunks:
            overlap = query_terms & _terms(chunk.text)
            if overlap:
                hits.append(
                    RetrievalHit(
                        chunk=chunk,
                        relevance_score=len(overlap) / len(query_terms),
                    )
                )

        return sorted(
            hits,
            key=lambda hit: (
                -hit.relevance_score,
                hit.chunk.document_id,
                hit.chunk.ordinal,
            ),
        )[:limit]


class SyntheticTutorGenerator:
    async def generate(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
    ) -> TutorAnswer:
        del question, policy
        if not hits:
            return TutorAnswer(
                content="I do not have approved course evidence for that question.",
                warnings=["No approved source evidence was retrieved."],
            )

        citations = [
            SourceCitation(
                source_id=hit.chunk.document_id,
                title=hit.chunk.metadata.get("title", hit.chunk.document_id),
                locator=hit.chunk.metadata.get(
                    "locator",
                    f"chunk {hit.chunk.ordinal + 1}",
                ),
            )
            for hit in hits
        ]
        return TutorAnswer(
            content=f"Synthetic grounded answer: {hits[0].chunk.text}",
            citations=citations,
        )


def _terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))
