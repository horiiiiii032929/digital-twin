"""Runtime boundaries for selected retrieval providers and explicit fallbacks."""

from __future__ import annotations

from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.retrieval import (
    EmptyQueryError,
    InvalidRetrievalLimitError,
    lexical_tokens,
)


class FallbackRetriever:
    """Use a selected retriever while retaining an inspectable control fallback.

    Provider failures are deliberately visible through sanitized counters and
    failure types. Query text and provider exception messages are never stored.
    """

    implementation_id = "retriever-with-control-fallback"
    version = "v1"

    def __init__(
        self,
        primary: Retriever | None,
        fallback: Retriever,
        *,
        primary_implementation_id: str,
        fallback_implementation_id: str,
        initialization_failure_type: str | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_implementation_id = primary_implementation_id
        self.fallback_implementation_id = fallback_implementation_id
        self.fallback_count = 0
        self.last_failure_type = initialization_failure_type

    @property
    def primary_available(self) -> bool:
        return self.primary is not None

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if limit < 1:
            raise InvalidRetrievalLimitError("retrieval limit must be at least 1")
        if not lexical_tokens(query):
            raise EmptyQueryError("query must contain at least one lexical token")

        if self.primary is None:
            self.fallback_count += 1
            return self.fallback.retrieve(query, limit=limit)

        try:
            return self.primary.retrieve(query, limit=limit)
        except (RuntimeError, ValueError) as error:
            self.fallback_count += 1
            self.last_failure_type = type(error).__name__
            return self.fallback.retrieve(query, limit=limit)


__all__ = ["FallbackRetriever"]
