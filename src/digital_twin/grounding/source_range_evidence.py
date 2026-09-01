"""Source-range-aware evidence candidate sets and safe ambiguity handling."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
import re

from src.digital_twin.grounding.evidence_sufficiency import EvidenceSufficiencyDecision
from src.digital_twin.grounding.hierarchical_retrieval import concept_tokens
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.retrieval import EmptyQueryError, InvalidRetrievalLimitError
from src.digital_twin.grounding.target_evidence import (
    PublicEvidenceTargetPlanV1,
    plan_public_evidence_targets,
)


_CLUSTER_ANCHOR = re.compile(r'\bsource\s+cluster\s+["“]([^"”]+)["”]', re.IGNORECASE)
_CLUSTER_SUFFIX = re.compile(
    r'\s+(?:in|for|from)\s+source\s+cluster\s+["“][^"”]+["”](?=\??\s*$)',
    re.IGNORECASE,
)
_PUBLIC_SCOPE_PREFIX = re.compile(
    r'^\s*using\s+source\s+["“]([^"”]+)["”]\s+in\s+section\s+'
    r'["“]([^"”]+)["”]\s*,\s*',
    re.IGNORECASE,
)
_VISIBLE_COMMAND = re.compile(r"\\(?:emph|textit|textbf)\{([^{}]*)\}")
_INDEX_COMMAND = re.compile(r"\\index\{[^{}]*\}%?")
_HASH_IDENTIFIER = re.compile(r"#([^#\n]+)#")
_RST_ROLE = re.compile(r":[a-zA-Z0-9_-]+:`([^`]*)`")


@dataclass(frozen=True)
class PublicSourceRangePlanV2:
    evidence: PublicEvidenceTargetPlanV1
    cluster_anchor: str | None
    source_path_anchor: str | None = None


@dataclass(frozen=True)
class SourceRangeCandidateTraceV2:
    plan: PublicSourceRangePlanV2
    selected_hit_ids: tuple[str, ...]
    candidate_count: int
    title_scope_applied: bool
    cluster_scope_applied: bool


def plan_public_source_ranges(question: str) -> PublicSourceRangePlanV2:
    """Extend the public target plan with an explicit public cluster anchor."""

    cluster = _CLUSTER_ANCHOR.search(question)
    public_scope = _PUBLIC_SCOPE_PREFIX.match(question)
    source_path_anchor = None
    section_anchor = None
    evidence_question = question
    if public_scope:
        source_path_anchor = public_scope.group(1).strip()
        section_anchor = public_scope.group(2).strip()
        evidence_question = question[public_scope.end() :]
    evidence_question = _CLUSTER_SUFFIX.sub("", evidence_question)
    evidence = plan_public_evidence_targets(evidence_question)
    if section_anchor:
        evidence = replace(evidence, context=section_anchor)
    return PublicSourceRangePlanV2(
        evidence=evidence,
        cluster_anchor=cluster.group(1).strip() if cluster else None,
        source_path_anchor=source_path_anchor,
    )


def canonicalize_source_claim(text: str, *, modality: str | None = None) -> str:
    """Render authoring markup as student-visible claim text.

    Code, equations, and tables retain line boundaries. Text claims collapse
    layout whitespace after non-visible RST/LaTeX authoring directives are
    removed. The transformation is deterministic and does not use gold.
    """

    value = _INDEX_COMMAND.sub(" ", text)
    previous = None
    while previous != value:
        previous = value
        value = _VISIBLE_COMMAND.sub(r"\1", value)
    value = _HASH_IDENTIFIER.sub(r"\1", value)
    value = _RST_ROLE.sub(r"\1", value)
    value = value.replace(r"\ldots", "...")
    if modality and modality.startswith("structured-"):
        lines = [line.rstrip() for line in value.splitlines()]
        return "\n".join(lines).strip()
    return " ".join(value.split())


def _metadata_value(chunk: DocumentChunk, key: str) -> str:
    return str(chunk.metadata.get(key, "")).strip()


def _coverage(target: str, chunk: DocumentChunk) -> float:
    target_tokens = concept_tokens(target)
    if not target_tokens:
        return 0.0
    chunk_tokens = concept_tokens(
        f"{chunk.text} {_metadata_value(chunk, 'search_description')}"
    )
    return len(target_tokens & chunk_tokens) / len(target_tokens)


def _compactness(target: str, text: str) -> float:
    target_tokens = concept_tokens(target)
    ordered = re.findall(r"[a-z0-9]+", text.casefold())
    if not target_tokens or not ordered:
        return 0.0
    positions = [index for index, token in enumerate(ordered) if token in target_tokens]
    if len({ordered[index] for index in positions}) < len(target_tokens):
        return 0.0
    best = len(ordered) + 1
    for start in range(len(positions)):
        observed: set[str] = set()
        for end in range(start, len(positions)):
            observed.add(ordered[positions[end]])
            if target_tokens <= observed:
                best = min(best, positions[end] - positions[start] + 1)
                break
    return 1.0 / best if best <= len(ordered) else 0.0


def _scope(
    chunks: Sequence[DocumentChunk],
    plan: PublicSourceRangePlanV2,
) -> tuple[list[DocumentChunk], bool, bool]:
    scoped = list(chunks)
    cluster_scope = False
    title_scope = False
    if plan.source_path_anchor:
        scoped = [
            row
            for row in scoped
            if _metadata_value(row, "source_path") == plan.source_path_anchor
        ]
    if plan.cluster_anchor:
        matching = [
            row
            for row in scoped
            if _metadata_value(row, "parent_cluster_id") == plan.cluster_anchor
        ]
        if matching:
            scoped = matching
            cluster_scope = True
    context = plan.evidence.context
    if context and not cluster_scope:
        matching = [
            row
            for row in scoped
            if _metadata_value(row, "title").casefold() == context.casefold()
        ]
        if matching:
            scoped = matching
            title_scope = True
    modality = plan.evidence.modality
    if modality:
        matching = [
            row for row in scoped if _metadata_value(row, "modality") == modality
        ]
        if matching:
            scoped = matching
    return scoped, title_scope, cluster_scope


class SourceRangeCandidateRetrieverV2:
    """Rank complete public source-range candidate sets before selecting hits."""

    implementation_id = "source-range-candidate-retriever-v2"
    version = "v2"

    def __init__(
        self,
        base: Retriever,
        chunks: Sequence[DocumentChunk],
        *,
        candidate_limit: int = 30,
    ) -> None:
        if candidate_limit < 5:
            raise ValueError("source-range candidate limit must be at least five")
        identifiers = [row.id for row in chunks]
        if not chunks or len(identifiers) != len(set(identifiers)):
            raise ValueError("source-range chunks must be non-empty and unique")
        if any(not row.retrieval_allowed for row in chunks):
            raise ValueError("source-range retrieval accepts only approved chunks")
        self.base = base
        self.chunks = tuple(chunks)
        self.candidate_limit = candidate_limit
        self.last_trace: SourceRangeCandidateTraceV2 | None = None

    def _rank_target(
        self,
        plan: PublicSourceRangePlanV2,
        target: str,
    ) -> tuple[list[RetrievalHit], bool, bool]:
        scoped, title_scope, cluster_scope = _scope(self.chunks, plan)
        query = " ".join(
            value
            for value in (
                plan.evidence.context,
                plan.cluster_anchor,
                plan.source_path_anchor,
                target,
            )
            if value
        ).strip()
        if not query:
            raise EmptyQueryError("source-range plan produced no retrieval query")
        lexical = self.base.retrieve(query, limit=self.candidate_limit)
        lexical_by_id = {row.chunk.id: row for row in lexical}
        lexical_rank = {row.chunk.id: index for index, row in enumerate(lexical)}
        ranked = sorted(
            scoped,
            key=lambda chunk: (
                -_coverage(target, chunk),
                -_compactness(target, chunk.text),
                lexical_rank.get(chunk.id, self.candidate_limit + chunk.ordinal),
                chunk.ordinal,
                chunk.id,
            ),
        )
        hits = [
            lexical_by_id.get(
                chunk.id,
                RetrievalHit(chunk=chunk, relevance_score=0.0, raw_score=0.0),
            )
            for chunk in ranked
        ]
        return hits, title_scope, cluster_scope

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise InvalidRetrievalLimitError("retrieval limit must be at least one")
        plan = plan_public_source_ranges(query)
        ranked_sets: list[list[RetrievalHit]] = []
        title_scope = False
        cluster_scope = False
        for target in plan.evidence.targets:
            ranked, used_title, used_cluster = self._rank_target(plan, target)
            ranked_sets.append(ranked)
            title_scope = title_scope or used_title
            cluster_scope = cluster_scope or used_cluster
        selected: list[RetrievalHit] = []
        used: set[str] = set()
        for ranked in ranked_sets:
            candidate = next((row for row in ranked if row.chunk.id not in used), None)
            if candidate:
                selected.append(candidate)
                used.add(candidate.chunk.id)
        tail: dict[str, RetrievalHit] = {}
        for ranked in ranked_sets:
            for hit in ranked:
                if hit.chunk.id not in used:
                    tail.setdefault(hit.chunk.id, hit)
        ordered_tail = sorted(
            tail.values(),
            key=lambda hit: (
                -hit.relevance_score,
                hit.chunk.ordinal,
                hit.chunk.id,
            ),
        )
        output = [*selected, *ordered_tail][:limit]
        self.last_trace = SourceRangeCandidateTraceV2(
            plan=plan,
            selected_hit_ids=tuple(row.chunk.id for row in selected),
            candidate_count=sum(len(rows) for rows in ranked_sets),
            title_scope_applied=title_scope,
            cluster_scope_applied=cluster_scope,
        )
        return output


class SourceRangeEvidenceGateV2:
    """Select distinct ranges and optionally clarify ambiguous public targets."""

    implementation_id = "source-range-evidence-gate-v2"
    version = "v2"

    def __init__(
        self,
        *,
        clarify_ambiguous: bool,
        minimum_target_coverage: float = 0.75,
    ) -> None:
        if not 0 < minimum_target_coverage <= 1:
            raise ValueError("target coverage must be in (0, 1]")
        self.clarify_ambiguous = clarify_ambiguous
        self.minimum_target_coverage = minimum_target_coverage

    def _matching(
        self,
        plan: PublicSourceRangePlanV2,
        target: str,
        hits: Sequence[RetrievalHit],
    ) -> list[RetrievalHit]:
        scoped, _, _ = _scope([row.chunk for row in hits], plan)
        scoped_ids = {row.id for row in scoped}
        matching = [row for row in hits if row.chunk.id in scoped_ids]
        if target:
            matching = [
                row
                for row in matching
                if _coverage(target, row.chunk) >= self.minimum_target_coverage
            ]
        return matching

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        plan = plan_public_source_ranges(query)
        bounded = list(hits[:5])
        if any(
            not hit.chunk.retrieval_allowed
            or not hit.chunk.display_allowed
            or not hit.chunk.source_checksum
            for hit in bounded
        ):
            return EvidenceSufficiencyDecision(
                sufficient=False,
                score=0,
                reason="source-range evidence is not source-authorized",
                features={"hit_count": len(bounded)},
                selected_hit_ids=[],
            )
        selected: list[RetrievalHit] = []
        used: set[str] = set()
        for target in plan.evidence.targets:
            matching = [
                row for row in self._matching(plan, target, bounded) if row.chunk.id not in used
            ]
            if not matching:
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=len(selected) / plan.evidence.requested_cardinality,
                    reason="one or more public source-range targets are unresolved",
                    features={
                        "requested_cardinality": plan.evidence.requested_cardinality,
                        "resolved_cardinality": len(selected),
                    },
                    selected_hit_ids=[],
                )
            if self.clarify_ambiguous and len(matching) > 1:
                top = _coverage(target, matching[0].chunk) if target else 0.0
                second = _coverage(target, matching[1].chunk) if target else 0.0
                low_information = len(concept_tokens(target)) <= 1
                if not target or (low_information and abs(top - second) < 1e-12):
                    return EvidenceSufficiencyDecision(
                        sufficient=False,
                        score=len(selected) / plan.evidence.requested_cardinality,
                        reason="public target is ambiguous across source regions",
                        features={
                            "ambiguous_candidate_count": len(matching),
                            "requested_cardinality": plan.evidence.requested_cardinality,
                        },
                        selected_hit_ids=[],
                    )
            selected.append(matching[0])
            used.add(matching[0].chunk.id)
        return EvidenceSufficiencyDecision(
            sufficient=len(selected) == plan.evidence.requested_cardinality,
            score=1.0,
            reason="every public target resolves to a distinct canonical source range",
            features={
                "requested_cardinality": plan.evidence.requested_cardinality,
                "resolved_cardinality": len(selected),
            },
            selected_hit_ids=[row.chunk.id for row in selected],
        )
