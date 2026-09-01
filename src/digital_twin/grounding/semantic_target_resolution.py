"""Semantic target resolution over public questions and approved source ranges.

The resolver is deliberately narrower than a general answer model.  It may
rank immutable candidate identifiers, but it cannot author actions, claims,
citations, source versions, or learner state.  All selected evidence remains
subject to the deterministic source and claim validators.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
import math

from src.digital_twin.grounding.evidence_sufficiency import EvidenceSufficiencyDecision
from src.digital_twin.grounding.hierarchical_retrieval import concept_tokens
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.retrieval import EmptyQueryError, InvalidRetrievalLimitError
from src.digital_twin.grounding.source_range_evidence import (
    PublicSourceRangePlanV2,
    plan_public_source_ranges,
)


_QUESTION_WRAPPER_TERMS = frozenset(
    {
        "about",
        "according",
        "concerns",
        "connect",
        "detail",
        "does",
        "entry",
        "equation",
        "explain",
        "fact",
        "point",
        "restate",
        "restated",
        "source",
        "state",
        "statement",
        "statements",
        "table",
        "two",
    }
)


@dataclass(frozen=True)
class SemanticTargetCandidateV3:
    hit: RetrievalHit
    score: float
    target_coverage: float
    question_coverage: float
    context_match: bool


@dataclass(frozen=True)
class SemanticTargetResolutionV3:
    plan: PublicSourceRangePlanV2
    action: str
    selected_hit_ids: tuple[str, ...]
    candidate_count: int
    minimum_selected_score: float
    minimum_margin: float | None
    reason: str


@dataclass(frozen=True)
class SemanticTargetResolutionTraceV3:
    resolution: SemanticTargetResolutionV3
    retrieved_hit_ids: tuple[str, ...]
    context_expanded_hit_count: int


def _metadata(chunk: DocumentChunk, key: str) -> str:
    return str(chunk.metadata.get(key, "")).strip()


def _cluster_id(chunk: DocumentChunk) -> str:
    return _metadata(chunk, "parent_cluster_id") or (
        chunk.source_artifact_id or chunk.document_id
    )


def _authorized(chunk: DocumentChunk) -> bool:
    return bool(
        chunk.retrieval_allowed
        and chunk.display_allowed
        and chunk.source_checksum
        and chunk.source_version >= 1
    )


def _candidate_terms(chunk: DocumentChunk) -> set[str]:
    return concept_tokens(
        " ".join(
            (
                chunk.text,
                _metadata(chunk, "title"),
                _metadata(chunk, "search_description"),
            )
        )
    )


def _idf(hits: Sequence[RetrievalHit]) -> dict[str, float]:
    frequencies: Counter[str] = Counter()
    for hit in hits:
        frequencies.update(_candidate_terms(hit.chunk))
    count = max(1, len(hits))
    return {
        token: math.log((count + 1) / (frequency + 1)) + 1
        for token, frequency in frequencies.items()
    }


def _weighted_coverage(
    required: set[str],
    observed: set[str],
    weights: dict[str, float],
) -> float:
    if not required:
        return 0.0
    denominator = sum(weights.get(token, 1.0) for token in required)
    numerator = sum(weights.get(token, 1.0) for token in required & observed)
    return numerator / denominator if denominator else 0.0


def _scope(
    plan: PublicSourceRangePlanV2,
    hits: Sequence[RetrievalHit],
) -> tuple[list[RetrievalHit], bool]:
    scoped = list(hits)
    if plan.cluster_anchor:
        matching = [
            hit
            for hit in scoped
            if _metadata(hit.chunk, "parent_cluster_id") == plan.cluster_anchor
        ]
        if matching:
            scoped = matching
    context_match = False
    context = plan.evidence.context
    if context and not plan.cluster_anchor:
        matching = [
            hit
            for hit in scoped
            if _metadata(hit.chunk, "title").casefold() == context.casefold()
        ]
        if matching:
            scoped = matching
            context_match = True
    modality = plan.evidence.modality
    if modality:
        matching = [
            hit
            for hit in scoped
            if _metadata(hit.chunk, "modality") == modality
        ]
        if matching:
            scoped = matching
    return scoped, context_match


def _ranking_terms(
    *,
    question: str,
    target: str,
    context: str | None,
) -> tuple[set[str], set[str]]:
    target_terms = concept_tokens(target)
    question_terms = concept_tokens(question) - _QUESTION_WRAPPER_TERMS
    context_terms = concept_tokens(context or "")
    if len(target_terms) <= 1:
        target_terms = (question_terms - context_terms) or target_terms
    return target_terms, question_terms


def _rank(
    *,
    question: str,
    target: str,
    context: str | None,
    hits: Sequence[RetrievalHit],
    context_scoped: bool,
) -> list[SemanticTargetCandidateV3]:
    weights = _idf(hits)
    target_terms, question_terms = _ranking_terms(
        question=question,
        target=target,
        context=context,
    )
    rows: list[SemanticTargetCandidateV3] = []
    target_phrase = " ".join(target.casefold().split())
    for rank, hit in enumerate(hits):
        chunk_terms = _candidate_terms(hit.chunk)
        target_coverage = _weighted_coverage(target_terms, chunk_terms, weights)
        question_coverage = _weighted_coverage(question_terms, chunk_terms, weights)
        exact_phrase = bool(
            target_phrase
            and len(target_phrase) > 2
            and target_phrase in hit.chunk.text.casefold()
        )
        context_match = bool(
            context
            and _metadata(hit.chunk, "title").casefold() == context.casefold()
        )
        score = (
            0.52 * target_coverage
            + 0.23 * question_coverage
            + (0.15 if context_match else 0.0)
            + (0.07 if exact_phrase else 0.0)
            + 0.03 / (rank + 1)
        )
        if context_scoped:
            score += 0.05
        rows.append(
            SemanticTargetCandidateV3(
                hit=hit,
                score=score,
                target_coverage=target_coverage,
                question_coverage=question_coverage,
                context_match=context_match,
            )
        )
    return sorted(
        rows,
        key=lambda row: (
            -row.score,
            -row.target_coverage,
            -row.question_coverage,
            row.hit.chunk.ordinal,
            row.hit.chunk.id,
        ),
    )


def resolve_semantic_targets(
    question: str,
    hits: Sequence[RetrievalHit],
    *,
    minimum_score: float = 0.42,
    ambiguity_margin: float = 0.06,
) -> SemanticTargetResolutionV3:
    """Resolve public semantic targets to unique approved candidate ranges."""

    if not question.strip():
        raise EmptyQueryError("question must not be empty")
    if not 0 < minimum_score <= 1:
        raise ValueError("minimum semantic target score must be in (0, 1]")
    if not 0 <= ambiguity_margin < 1:
        raise ValueError("semantic ambiguity margin must be in [0, 1)")
    plan = plan_public_source_ranges(question)
    bounded = list(hits[:30])
    if not bounded:
        return SemanticTargetResolutionV3(
            plan=plan,
            action="abstain",
            selected_hit_ids=(),
            candidate_count=0,
            minimum_selected_score=0.0,
            minimum_margin=None,
            reason="no approved source-range candidates were retrieved",
        )
    if any(not _authorized(hit.chunk) for hit in bounded):
        return SemanticTargetResolutionV3(
            plan=plan,
            action="abstain",
            selected_hit_ids=(),
            candidate_count=len(bounded),
            minimum_selected_score=0.0,
            minimum_margin=None,
            reason="one or more source-range candidates are not authorized",
        )
    scoped, context_scoped = _scope(plan, bounded)
    if not scoped:
        return SemanticTargetResolutionV3(
            plan=plan,
            action="abstain",
            selected_hit_ids=(),
            candidate_count=len(bounded),
            minimum_selected_score=0.0,
            minimum_margin=None,
            reason="no candidate remains inside the public source scope",
        )

    selected: list[SemanticTargetCandidateV3] = []
    used: set[str] = set()
    margins: list[float] = []
    for target in plan.evidence.targets:
        ranked = [
            row
            for row in _rank(
                question=question,
                target=target,
                context=plan.evidence.context,
                hits=scoped,
                context_scoped=context_scoped,
            )
            if row.hit.chunk.id not in used
        ]
        if not ranked or ranked[0].score < minimum_score:
            return SemanticTargetResolutionV3(
                plan=plan,
                action="abstain",
                selected_hit_ids=(),
                candidate_count=len(scoped),
                minimum_selected_score=ranked[0].score if ranked else 0.0,
                minimum_margin=None,
                reason="semantic target support is incomplete",
            )
        top = ranked[0]
        margin = top.score - ranked[1].score if len(ranked) > 1 else top.score
        if (
            len(ranked) > 1
            and not context_scoped
            and _cluster_id(top.hit.chunk) != _cluster_id(ranked[1].hit.chunk)
            and margin < ambiguity_margin
        ):
            return SemanticTargetResolutionV3(
                plan=plan,
                action="clarify",
                selected_hit_ids=(),
                candidate_count=len(scoped),
                minimum_selected_score=top.score,
                minimum_margin=margin,
                reason="semantic target is not unique across source ranges",
            )
        selected.append(top)
        used.add(top.hit.chunk.id)
        margins.append(margin)

    if len(selected) != plan.evidence.requested_cardinality:
        return SemanticTargetResolutionV3(
            plan=plan,
            action="abstain",
            selected_hit_ids=(),
            candidate_count=len(scoped),
            minimum_selected_score=min((row.score for row in selected), default=0.0),
            minimum_margin=min(margins, default=None),
            reason="semantic target cardinality is incomplete",
        )
    return SemanticTargetResolutionV3(
        plan=plan,
        action="answer",
        selected_hit_ids=tuple(row.hit.chunk.id for row in selected),
        candidate_count=len(scoped),
        minimum_selected_score=min(row.score for row in selected),
        minimum_margin=min(margins, default=None),
        reason="every public semantic target resolves to a unique approved source range",
    )


class SemanticTargetEvidenceRetrieverV3:
    """Retrieve and place resolved source ranges before diagnostic candidates."""

    implementation_id = "semantic-target-evidence-retriever-v3"
    version = "v3"

    def __init__(
        self,
        base: Retriever,
        chunks: Sequence[DocumentChunk],
        *,
        candidate_limit: int = 30,
    ) -> None:
        if candidate_limit < 5:
            raise ValueError("semantic target candidate limit must be at least five")
        identifiers = [row.id for row in chunks]
        if not chunks or len(identifiers) != len(set(identifiers)):
            raise ValueError("semantic target chunks must be non-empty and unique")
        if any(not _authorized(row) for row in chunks):
            raise ValueError("semantic target retrieval accepts only approved chunks")
        self.base = base
        self.chunks = tuple(chunks)
        self.candidate_limit = candidate_limit
        self.last_trace: SemanticTargetResolutionTraceV3 | None = None

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise InvalidRetrievalLimitError("retrieval limit must be at least one")
        retrieved = list(self.base.retrieve(query, limit=self.candidate_limit))
        plan = plan_public_source_ranges(query)
        known = {row.chunk.id for row in retrieved}
        expanded = 0
        context = plan.evidence.context
        if context:
            for chunk in self.chunks:
                if (
                    chunk.id not in known
                    and _metadata(chunk, "title").casefold() == context.casefold()
                ):
                    retrieved.append(
                        RetrievalHit(chunk=chunk, relevance_score=0.0, raw_score=0.0)
                    )
                    known.add(chunk.id)
                    expanded += 1
        resolution = resolve_semantic_targets(query, retrieved)
        selected = set(resolution.selected_hit_ids)
        ordered = [row for row in retrieved if row.chunk.id in selected]
        ordered.extend(row for row in retrieved if row.chunk.id not in selected)
        self.last_trace = SemanticTargetResolutionTraceV3(
            resolution=resolution,
            retrieved_hit_ids=tuple(row.chunk.id for row in retrieved),
            context_expanded_hit_count=expanded,
        )
        return ordered[:limit]


class SemanticTargetEvidenceGateV3:
    """Expose semantic target resolution as the repository evidence-gate API."""

    implementation_id = "semantic-target-evidence-gate-v3"
    version = "v3"

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        resolution = resolve_semantic_targets(query, hits)
        return EvidenceSufficiencyDecision(
            sufficient=resolution.action == "answer",
            score=resolution.minimum_selected_score,
            reason=resolution.reason,
            features={
                "semantic_action_answer": resolution.action == "answer",
                "semantic_action_clarify": resolution.action == "clarify",
                "semantic_action_abstain": resolution.action == "abstain",
                "requested_cardinality": resolution.plan.evidence.requested_cardinality,
                "resolved_cardinality": len(resolution.selected_hit_ids),
                "candidate_count": resolution.candidate_count,
                "minimum_margin": resolution.minimum_margin or 0.0,
            },
            selected_hit_ids=list(resolution.selected_hit_ids),
        )
