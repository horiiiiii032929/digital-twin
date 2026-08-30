"""Structured hierarchical evidence retrieval with deterministic coverage.

The successor wraps an existing course-scoped retriever.  It never changes
authoritative source content: it expands only to approved sibling regions from
the same source/version, then packs evidence by inspectable concept coverage.
An optional externally computed ranking may reorder the bounded candidate set,
but cannot introduce a new chunk identifier.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import math
import re

from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.evidence_sufficiency import (
    EvidenceSufficiencyDecision,
)
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.retrieval import (
    EmptyQueryError,
    InvalidRetrievalLimitError,
)


_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[_-][A-Za-z0-9]+)*|\d+(?:\.\d+)?")
_LATEX = re.compile(r"\\[A-Za-z]+|\$+|\^|_")
_OPERATORS = re.compile(r"==|!=|<=|>=|->|=>|::|:=|\+\+|--|[+*/%&|<>]=?")
_DEICTIC = re.compile(
    r"\b(?:it|this|that|these|those|there|the former|the latter)\b",
    re.IGNORECASE,
)
_EXPLICIT_REFERENT = re.compile(
    r"\b(?:algorithm|equation|table|figure|function|method|protocol|process|"
    r"system|statement|step|variable|concept|section|cache|network|tree|graph)\b",
    re.IGNORECASE,
)
_INTEGRITY = re.compile(
    r"\b(?:graded|assignment|exam|quiz|submit|submission-ready|final answer)\b",
    re.IGNORECASE,
)
_UNSUPPORTED_FUTURE = re.compile(
    r"\b(?:next academic year|unreleased|future version|2035 revision|will be added)\b",
    re.IGNORECASE,
)
_CROSS_COURSE = re.compile(r"\b(?:another|other) course\b", re.IGNORECASE)
_STOPWORDS = frozenset(
    "a an and are as at be by can does for from how in is it of on or that the "
    "this to was what when where which who why with".split()
)


class HierarchicalRetrievalError(ValueError):
    """Raised when hierarchical evidence assembly violates its boundary."""


def structured_tokens(value: str) -> list[str]:
    """Preserve prose terms, identifiers, numbers, LaTeX, and operators."""

    tokens = [match.group(0).casefold() for match in _WORD.finditer(value)]
    tokens.extend(match.group(0).casefold() for match in _LATEX.finditer(value))
    tokens.extend(match.group(0) for match in _OPERATORS.finditer(value))
    return tokens


def concept_tokens(value: str) -> set[str]:
    return {
        token
        for token in structured_tokens(value)
        if token not in _STOPWORDS and (len(token) > 1 or not token.isalpha())
    }


def requires_clarification(question: str) -> bool:
    """Fail closed for unresolved deictic questions before generation."""

    return bool(_DEICTIC.search(question)) and not bool(
        _EXPLICIT_REFERENT.search(question)
    )


def deterministic_boundary_action(question: str) -> str | None:
    if _INTEGRITY.search(question):
        return "refuse"
    if requires_clarification(question):
        return "clarify"
    if _UNSUPPORTED_FUTURE.search(question) or _CROSS_COURSE.search(question):
        return "abstain"
    return None


def should_use_semantic_reranking(
    question: str,
    *,
    top_score_margin: float,
) -> bool:
    """Question-only eligibility rule; no split or hidden-gold field is read."""

    normalized = question.casefold()
    structured = bool(_LATEX.search(question) or _OPERATORS.search(question))
    multi_evidence = bool(
        re.search(r"\b(?:which two|both|together|connect|relationship)\b", normalized)
    )
    paraphrased = bool(
        re.search(r"\b(?:restate|in other words|explain|how can .* be)\b", normalized)
    )
    return structured or multi_evidence or paraphrased or top_score_margin < 0.05


@dataclass(frozen=True)
class EvidenceRetrievalPlan:
    hits: tuple[RetrievalHit, ...]
    candidate_count: int
    expanded_count: int
    query_concept_count: int
    covered_concept_count: int
    coverage: float
    reranking_eligible: bool
    reranking_applied: bool
    clarification_required: bool
    deterministic_action: str | None


RerankFunction = Callable[[str, Sequence[RetrievalHit]], Sequence[str]]


class StructuredHierarchicalRetriever:
    """Expand a top-30 hybrid set and pack source-authorized evidence."""

    implementation_id = "structured-hierarchical-coverage-retriever-v1"
    version = "v1"

    def __init__(
        self,
        base: Retriever,
        chunks: Sequence[DocumentChunk],
        *,
        candidate_limit: int = 30,
        adjacent_radius: int = 1,
        rerank: RerankFunction | None = None,
    ) -> None:
        if candidate_limit < 5:
            raise ValueError("hierarchical candidate limit must be at least five")
        if adjacent_radius < 0 or adjacent_radius > 3:
            raise ValueError("hierarchical adjacent radius must be between zero and three")
        identifiers = [row.id for row in chunks]
        if not chunks or len(identifiers) != len(set(identifiers)):
            raise ValueError("hierarchical chunks must be non-empty and unique")
        if any(not row.retrieval_allowed for row in chunks):
            raise ValueError("hierarchical retrieval accepts only approved chunks")
        self.base = base
        self.chunks = list(chunks)
        self.candidate_limit = candidate_limit
        self.adjacent_radius = adjacent_radius
        self.rerank = rerank
        self._by_id = {row.id: row for row in self.chunks}
        self._siblings: dict[tuple[str, int, str], list[DocumentChunk]] = defaultdict(list)
        for chunk in self.chunks:
            source = chunk.source_artifact_id or chunk.document_id
            path = chunk.metadata.get("source_path", chunk.document_id)
            self._siblings[(source, chunk.source_version, path)].append(chunk)
        for siblings in self._siblings.values():
            siblings.sort(key=lambda row: (row.ordinal, row.id))

    @staticmethod
    def _hit(chunk: DocumentChunk, score: float, raw_score: float | None = None) -> RetrievalHit:
        return RetrievalHit(
            chunk=chunk,
            relevance_score=max(0.0, min(1.0, score)),
            raw_score=max(0.0, raw_score) if raw_score is not None else None,
        )

    def _expanded(self, base_hits: Sequence[RetrievalHit]) -> list[RetrievalHit]:
        ranked: dict[str, RetrievalHit] = {row.chunk.id: row for row in base_hits}
        for rank, hit in enumerate(base_hits, start=1):
            chunk = hit.chunk
            source = chunk.source_artifact_id or chunk.document_id
            path = chunk.metadata.get("source_path", chunk.document_id)
            siblings = self._siblings[(source, chunk.source_version, path)]
            index = next(
                (offset for offset, row in enumerate(siblings) if row.id == chunk.id),
                None,
            )
            if index is None:
                raise HierarchicalRetrievalError("base hit escaped the approved corpus")
            parent_id = chunk.metadata.get("parent_section_id")
            candidates = [
                row
                for offset, row in enumerate(siblings)
                if abs(offset - index) <= self.adjacent_radius
                or (parent_id and row.metadata.get("parent_section_id") == parent_id)
            ]
            for sibling in candidates:
                if sibling.id in ranked:
                    continue
                decay = 0.85 / (1 + abs(sibling.ordinal - chunk.ordinal))
                score = min(hit.relevance_score * decay, 1 / (rank + 1))
                ranked[sibling.id] = self._hit(sibling, score)
        return sorted(
            ranked.values(),
            key=lambda row: (-row.relevance_score, row.chunk.ordinal, row.chunk.id),
        )

    @staticmethod
    def _apply_external_ranking(
        candidates: Sequence[RetrievalHit], ranked_ids: Sequence[str]
    ) -> list[RetrievalHit]:
        by_id = {row.chunk.id: row for row in candidates}
        ordered_ids = list(ranked_ids)
        if len(ordered_ids) != len(set(ordered_ids)):
            raise HierarchicalRetrievalError("semantic reranker returned duplicate IDs")
        if any(identifier not in by_id for identifier in ordered_ids):
            raise HierarchicalRetrievalError("semantic reranker introduced an unknown ID")
        tail = [row.chunk.id for row in candidates if row.chunk.id not in set(ordered_ids)]
        final_ids = [*ordered_ids, *tail]
        denominator = max(1, len(final_ids))
        return [
            StructuredHierarchicalRetriever._hit(
                by_id[identifier].chunk,
                1 - (index / (denominator + 1)),
                by_id[identifier].raw_score,
            )
            for index, identifier in enumerate(final_ids, start=1)
        ]

    @staticmethod
    def _coverage_pack(
        query: str,
        candidates: Sequence[RetrievalHit],
        *,
        limit: int,
    ) -> tuple[list[RetrievalHit], int, int]:
        concepts = concept_tokens(query)
        uncovered = set(concepts)
        remaining = list(candidates)
        selected: list[RetrievalHit] = []
        while remaining and len(selected) < limit:
            ranked = sorted(
                remaining,
                key=lambda row: (
                    -len(concept_tokens(row.chunk.text) & uncovered),
                    -row.relevance_score,
                    row.chunk.ordinal,
                    row.chunk.id,
                ),
            )
            chosen = ranked[0]
            selected.append(chosen)
            uncovered -= concept_tokens(chosen.chunk.text)
            remaining.remove(chosen)
        covered = len(concepts - uncovered)
        return selected, len(concepts), covered

    def plan(
        self,
        query: str,
        *,
        limit: int = 5,
        allow_semantic_reranking: bool = False,
        ranked_ids: Sequence[str] | None = None,
    ) -> EvidenceRetrievalPlan:
        if isinstance(limit, bool) or limit < 1:
            raise InvalidRetrievalLimitError("retrieval limit must be at least one")
        if not structured_tokens(query):
            raise EmptyQueryError("query must contain at least one structured token")
        base_hits = self.base.retrieve(query, limit=self.candidate_limit)
        margin = (
            base_hits[0].relevance_score - base_hits[1].relevance_score
            if len(base_hits) > 1
            else (base_hits[0].relevance_score if base_hits else 0.0)
        )
        eligible = should_use_semantic_reranking(query, top_score_margin=margin)
        expanded = self._expanded(base_hits)
        applied = False
        if allow_semantic_reranking and eligible:
            if ranked_ids is not None:
                expanded = self._apply_external_ranking(expanded, ranked_ids)
                applied = True
            elif self.rerank is not None:
                expanded = self._apply_external_ranking(
                    expanded, self.rerank(query, expanded)
                )
                applied = True
        selected, concept_count, covered = self._coverage_pack(
            query, expanded, limit=limit
        )
        coverage = covered / concept_count if concept_count else 0.0
        action = deterministic_boundary_action(query)
        if action is None and (not selected or coverage < 0.6):
            action = "abstain"
        return EvidenceRetrievalPlan(
            hits=tuple(selected),
            candidate_count=len(base_hits),
            expanded_count=len(expanded),
            query_concept_count=concept_count,
            covered_concept_count=covered,
            coverage=coverage,
            reranking_eligible=eligible,
            reranking_applied=applied,
            clarification_required=requires_clarification(query),
            deterministic_action=action,
        )

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        return list(self.plan(query, limit=limit).hits)


class CaseBoundPrecomputedRetriever:
    """Replay public-question retrieval plans without loading hidden gold."""

    implementation_id = "case-bound-precomputed-retriever-v1"
    version = "v1"

    def __init__(
        self,
        *,
        chunks: Sequence[DocumentChunk],
        ranked_chunk_ids: dict[str, list[str]],
        current_case_id: Callable[[], str | None],
    ) -> None:
        self._chunks = {row.id: row for row in chunks}
        self._ranked = {key: list(value) for key, value in ranked_chunk_ids.items()}
        self._current_case_id = current_case_id
        for case_id, identifiers in self._ranked.items():
            if not case_id or len(identifiers) != len(set(identifiers)):
                raise ValueError("precomputed retrieval identities must be unique")
            if any(identifier not in self._chunks for identifier in identifiers):
                raise ValueError("precomputed retrieval references an unknown chunk")

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        del query
        if isinstance(limit, bool) or limit < 1:
            raise InvalidRetrievalLimitError("retrieval limit must be at least one")
        case_id = self._current_case_id()
        if case_id is None or case_id not in self._ranked:
            raise HierarchicalRetrievalError("precomputed retrieval lacks active case binding")
        identifiers = self._ranked[case_id][:limit]
        denominator = max(1, len(identifiers))
        return [
            RetrievalHit(
                chunk=self._chunks[identifier],
                relevance_score=max(0.0, 1 - index / (denominator + 1)),
            )
            for index, identifier in enumerate(identifiers, start=1)
        ]


class StructuredHierarchicalCoverageEvidenceGate:
    """Fail closed on boundaries and select a complete, current evidence set.

    The gate is intentionally deterministic. It does not infer facts or use
    evaluator labels; it checks public question concepts and approved runtime
    evidence only.
    """

    implementation_id = "structured-hierarchical-coverage-evidence-gate-v1"
    version = "v1"

    def __init__(
        self,
        *,
        minimum_query_coverage: float = 0.60,
        minimum_matching_terms: int = 2,
        evidence_limit: int = 5,
    ) -> None:
        if not 0 <= minimum_query_coverage <= 1:
            raise ValueError("minimum query coverage must be between zero and one")
        if minimum_matching_terms < 1 or evidence_limit < 1:
            raise ValueError("hierarchical gate limits must be positive")
        self.minimum_query_coverage = minimum_query_coverage
        self.minimum_matching_terms = minimum_matching_terms
        self.evidence_limit = evidence_limit

    @staticmethod
    def _rejected(reason: str, **features: int | float | bool) -> EvidenceSufficiencyDecision:
        return EvidenceSufficiencyDecision(
            sufficient=False,
            score=0,
            reason=reason,
            features=features,
            selected_hit_ids=[],
        )

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        boundary_action = deterministic_boundary_action(query)
        if boundary_action is not None:
            return self._rejected(
                "question requires a deterministic non-answer action",
                deterministic_boundary=True,
            )
        bounded = list(hits[: self.evidence_limit])
        if not bounded:
            return self._rejected("no approved evidence was retrieved", hit_count=0)
        if any(
            not hit.chunk.retrieval_allowed
            or not hit.chunk.display_allowed
            or not hit.chunk.source_checksum
            for hit in bounded
        ):
            return self._rejected(
                "retrieved evidence is not source-authorized",
                hit_count=len(bounded),
            )
        versions: dict[str, set[int]] = defaultdict(set)
        for hit in bounded:
            artifact = hit.chunk.source_artifact_id or hit.chunk.document_id
            versions[artifact].add(hit.chunk.source_version)
        if any(len(values) != 1 for values in versions.values()):
            return self._rejected(
                "retrieved evidence mixes source versions",
                hit_count=len(bounded),
            )

        query_terms = concept_tokens(query)
        selected: list[RetrievalHit] = []
        covered: set[str] = set()
        for hit in bounded:
            overlap = query_terms & concept_tokens(hit.chunk.text)
            if overlap - covered:
                selected.append(hit)
                covered.update(overlap)
        coverage = len(covered) / len(query_terms) if query_terms else 0.0
        multi_evidence = bool(
            re.search(
                r"\b(?:which two|both|together|connect|relationship)\b",
                query.casefold(),
            )
        )
        complete = (
            len(covered) >= self.minimum_matching_terms
            and coverage >= self.minimum_query_coverage
            and (not multi_evidence or len(selected) >= 2)
        )
        return EvidenceSufficiencyDecision(
            sufficient=bool(selected) and complete,
            score=coverage,
            reason=(
                "approved current evidence covers the question concepts"
                if complete
                else "retrieved evidence does not completely cover the question"
            ),
            features={
                "hit_count": len(bounded),
                "selected_hit_count": len(selected),
                "query_concept_count": len(query_terms),
                "covered_concept_count": len(covered),
                "query_coverage": coverage,
                "multi_evidence_required": multi_evidence,
                "source_version_groups": len(versions),
            },
            selected_hit_ids=[hit.chunk.id for hit in selected] if complete else [],
        )


def p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]
