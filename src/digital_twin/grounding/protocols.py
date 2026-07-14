from typing import Protocol

from src.digital_twin.grounding.models import (
    CourseDocument,
    DocumentChunk,
    RetrievalHit,
    TutorAnswer,
)
from src.digital_twin.tutor_policy import TutorPolicy


class DocumentChunker(Protocol):
    def chunk(self, document: CourseDocument) -> list[DocumentChunk]:
        """Split one approved document while preserving source identity."""


class FigureStore(Protocol):
    def store(self, figure_id: str, extension: str, content: bytes) -> str:
        """Persist extracted bytes outside domain models and return an opaque ref."""


class Retriever(Protocol):
    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        """Return ranked chunks for a question without choosing a provider."""


class TutorGenerator(Protocol):
    async def generate(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
    ) -> TutorAnswer:
        """Generate a policy-aware answer from already retrieved evidence."""
