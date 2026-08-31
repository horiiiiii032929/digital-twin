"""Deterministic plan/observe retrieval without hidden-gold access.

The planner decomposes only the public question.  Each bounded subquery is run
through the same approved course retriever and the observed rankings are fused.
No model, source label, expected answer, or required evidence is consulted.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.retrieval import (
    EmptyQueryError,
    InvalidRetrievalLimitError,
)


_CONNECTOR = re.compile(
    r"\b(?:and|versus|vs\.?|compared with|compared to|together with)\b",
    flags=re.IGNORECASE,
)
_CONNECT_FORM = re.compile(
    r"\bconnect\s+(.{2,120}?)\s+with\s+(.{2,120}?)(?:\?|$)",
    flags=re.IGNORECASE,
)
_WHICH_TWO_PREFIX = re.compile(
    r"^\s*which\s+two\s+(?:statements|facts|ideas|details)\s+(?:in\s+.+?\s+)?",
    flags=re.IGNORECASE,
)


def decompose_evidence_queries(question: str, *, maximum: int = 3) -> tuple[str, ...]:
    """Return stable public-question subqueries, including the original query."""

    normalized = " ".join(question.split()).strip()
    if not normalized:
        raise EmptyQueryError("question must not be blank")
    if isinstance(maximum, bool) or maximum < 1 or maximum > 4:
        raise ValueError("maximum subqueries must be between one and four")

    candidates = [normalized]
    connect_match = _CONNECT_FORM.search(normalized)
    if connect_match is not None:
        candidates.extend(part.strip(" ?.,") for part in connect_match.groups())
    else:
        remainder = _WHICH_TWO_PREFIX.sub("", normalized).strip(" ?.,")
        parts = [part.strip(" ?.,") for part in _CONNECTOR.split(remainder)]
        if len(parts) > 1:
            candidates.extend(part for part in parts if len(part.split()) >= 2)

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.casefold()
        if candidate and key not in seen:
            seen.add(key)
            unique.append(candidate)
        if len(unique) == maximum:
            break
    return tuple(unique)


@dataclass(frozen=True)
class PlanObserveRetrievalTraceV1:
    queries: tuple[str, ...]
    observed_hit_count: int
    selected_hit_ids: tuple[str, ...]
    reciprocal_rank_constant: int


class PlanObserveRetrieverV1:
    """Fuse observations from a finite deterministic evidence-query plan."""

    implementation_id = "deterministic-plan-observe-retriever-v1"
    version = "v1"

    def __init__(
        self,
        base: Retriever,
        *,
        maximum_subqueries: int = 3,
        observation_limit: int = 30,
        reciprocal_rank_constant: int = 60,
    ) -> None:
        if maximum_subqueries < 1 or maximum_subqueries > 4:
            raise ValueError("maximum_subqueries must be between one and four")
        if observation_limit < 5:
            raise ValueError("observation_limit must be at least five")
        if reciprocal_rank_constant < 1:
            raise ValueError("reciprocal_rank_constant must be positive")
        self.base = base
        self.maximum_subqueries = maximum_subqueries
        self.observation_limit = observation_limit
        self.reciprocal_rank_constant = reciprocal_rank_constant
        self.last_trace: PlanObserveRetrievalTraceV1 | None = None

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise InvalidRetrievalLimitError("retrieval limit must be at least one")
        queries = decompose_evidence_queries(query, maximum=self.maximum_subqueries)
        scores: dict[str, float] = {}
        hits_by_id: dict[str, RetrievalHit] = {}
        observations = 0
        for planned_query in queries:
            hits = self.base.retrieve(planned_query, limit=self.observation_limit)
            observations += len(hits)
            for rank, hit in enumerate(hits, start=1):
                identifier = hit.chunk.id
                hits_by_id[identifier] = hit
                scores[identifier] = scores.get(identifier, 0.0) + 1 / (
                    self.reciprocal_rank_constant + rank
                )
        ordered = sorted(
            hits_by_id,
            key=lambda identifier: (
                -scores[identifier],
                -hits_by_id[identifier].relevance_score,
                hits_by_id[identifier].chunk.ordinal,
                identifier,
            ),
        )
        selected = ordered[:limit]
        maximum_score = max((scores[row] for row in selected), default=1.0)
        result = [
            RetrievalHit(
                chunk=hits_by_id[identifier].chunk,
                relevance_score=scores[identifier] / maximum_score,
                raw_score=scores[identifier],
            )
            for identifier in selected
        ]
        self.last_trace = PlanObserveRetrievalTraceV1(
            queries=queries,
            observed_hit_count=observations,
            selected_hit_ids=tuple(selected),
            reciprocal_rank_constant=self.reciprocal_rank_constant,
        )
        return result
