"""Source-side semantic evidence atoms with canonical citation lineage.

The atom representation is derived only from approved source ranges.  Public
questions may rank existing atom identifiers, but cannot author atom text,
relations, actions, claims, citations, or source versions.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
import json

from src.digital_twin.grounding.evidence_sufficiency import (
    EvidenceSufficiencyDecision,
)
from src.digital_twin.grounding.hierarchical_retrieval import concept_tokens
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.retrieval import (
    BM25Retriever,
    EmptyQueryError,
    InvalidRetrievalLimitError,
)
from src.digital_twin.grounding.reference_uniqueness import (
    analyze_public_reference_uniqueness,
    normalize_claim_class,
)
from src.digital_twin.grounding.source_range_evidence import (
    canonicalize_source_claim,
    plan_public_source_ranges,
)
from src.digital_twin.grounding.source_registration import semantic_anchors


ATOM_VERSION = "source-semantic-evidence-atom-v1"

_INSTRUCTIONAL_WRAPPER_TERMS = frozenset(
    {
        "about",
        "according",
        "am",
        "attempt",
        "can",
        "confused",
        "could",
        "detail",
        "does",
        "during",
        "explain",
        "give",
        "guide",
        "help",
        "hint",
        "inspect",
        "key",
        "next",
        "please",
        "point",
        "question",
        "reading",
        "restate",
        "source",
        "step",
        "still",
        "stuck",
        "understand",
        "unclear",
    }
)


@dataclass(frozen=True)
class SemanticEvidenceAtomTraceV1:
    selected_hit_ids: tuple[str, ...]
    candidate_count: int
    relation_constrained: bool
    title_scope_applied: bool
    cluster_scope_applied: bool


def _metadata(chunk: DocumentChunk, key: str) -> str:
    return str(chunk.metadata.get(key, "")).strip()


def _authorized(chunk: DocumentChunk) -> bool:
    return bool(
        chunk.retrieval_allowed
        and chunk.display_allowed
        and chunk.source_checksum
        and chunk.source_version >= 1
        and chunk.region_id
    )


def _range_start(chunk: DocumentChunk) -> int:
    try:
        return int(_metadata(chunk, "char_start"))
    except ValueError as error:
        raise ValueError("semantic evidence atom lacks canonical range") from error


def _json_ids(chunk: DocumentChunk, key: str) -> tuple[str, ...]:
    try:
        value = json.loads(_metadata(chunk, key) or "[]")
    except json.JSONDecodeError as error:
        raise ValueError(f"semantic evidence atom has malformed {key}") from error
    if not isinstance(value, list) or any(not isinstance(row, str) for row in value):
        raise ValueError(f"semantic evidence atom {key} must be a string list")
    if len(value) != len(set(value)):
        raise ValueError(f"semantic evidence atom {key} contains duplicates")
    return tuple(value)


def materialize_semantic_evidence_atoms(
    chunks: Sequence[DocumentChunk],
) -> list[DocumentChunk]:
    """Add deterministic atom-specific search metadata and source relations.

    The citable ``text`` and every provenance field remain unchanged.  Search
    projections use only the atom's own source text plus source-side context;
    they never use a question, answer key, or hidden-gold field.
    """

    if not chunks:
        raise ValueError("semantic evidence atom materialization requires chunks")
    identifiers = [row.id for row in chunks]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("semantic evidence atom identifiers must be unique")
    if any(not _authorized(row) for row in chunks):
        raise ValueError("semantic evidence atoms require approved canonical ranges")

    grouped: dict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        group = _metadata(chunk, "parent_cluster_id")
        if not group:
            raise ValueError("semantic evidence atom lacks a relation group")
        grouped[group].append(chunk)

    output: list[DocumentChunk] = []
    for group_id, rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: (_range_start(row), row.id))
        group_ids = [row.id for row in ordered]
        for index, chunk in enumerate(ordered):
            modality = _metadata(chunk, "modality") or "text"
            claim = canonicalize_source_claim(chunk.text, modality=modality)
            if not claim:
                raise ValueError("semantic evidence atom canonical claim is blank")
            anchors = semantic_anchors((claim,), limit=12)
            adjacent = [
                ordered[position].id
                for position in (index - 1, index + 1)
                if 0 <= position < len(ordered)
            ]
            related = [identifier for identifier in group_ids if identifier != chunk.id]
            title = _metadata(chunk, "title")
            source_path = _metadata(chunk, "source_path")
            search_rows = [
                f"Course: {_metadata(chunk, 'course_id')}",
                f"Section: {title}",
                f"Source: {source_path}",
                f"Modality: {modality}",
                f"Canonical source claim: {claim}",
            ]
            if anchors:
                search_rows.append("Atom anchors: " + ", ".join(anchors))
            metadata = dict(chunk.metadata)
            metadata.update(
                {
                    "semantic_atom_version": ATOM_VERSION,
                    "semantic_atom_claim": claim,
                    "semantic_atom_anchors": json.dumps(
                        anchors, separators=(",", ":"), sort_keys=True
                    ),
                    "semantic_relation_group_id": group_id,
                    "semantic_related_atom_ids": json.dumps(
                        related, separators=(",", ":"), sort_keys=True
                    ),
                    "semantic_adjacent_atom_ids": json.dumps(
                        adjacent, separators=(",", ":"), sort_keys=True
                    ),
                    "semantic_search_text": "\n".join(search_rows),
                }
            )
            output.append(chunk.model_copy(update={"metadata": metadata}))
    return sorted(
        output,
        key=lambda row: (_metadata(row, "course_id"), row.ordinal, row.id),
    )


def _coverage(needle: str, haystack: str) -> float:
    required = concept_tokens(needle)
    if not required:
        return 0.0
    return len(required & concept_tokens(haystack)) / len(required)


def _instructional_terms(value: str) -> set[str]:
    """Keep source-bearing terms while removing pedagogical request framing."""

    return concept_tokens(value) - _INSTRUCTIONAL_WRAPPER_TERMS


def _instructional_coverage(target: str, chunk: DocumentChunk) -> float:
    required = _instructional_terms(target)
    if not required:
        return 0.0
    observed = concept_tokens(
        " ".join(
            (
                _metadata(chunk, "semantic_atom_claim"),
                _metadata(chunk, "title"),
                _metadata(chunk, "semantic_atom_anchors"),
            )
        )
    )
    return len(required & observed) / len(required)


def _has_public_title_anchor(question: str, chunk: DocumentChunk) -> bool:
    """Return whether a non-generic public title is explicitly named."""

    title_terms = _instructional_terms(_metadata(chunk, "title"))
    question_terms = _instructional_terms(question)
    return len(title_terms) >= 2 and title_terms <= question_terms


def _scope(
    chunks: Sequence[DocumentChunk],
    *,
    source_path_anchor: str | None,
    cluster_anchor: str | None,
    context: str | None,
    modality: str | None,
) -> tuple[list[DocumentChunk], bool, bool]:
    scoped = list(chunks)
    cluster_scope = False
    title_scope = False
    if source_path_anchor:
        scoped = [
            row
            for row in scoped
            if _metadata(row, "source_path") == source_path_anchor
        ]
    if cluster_anchor:
        matching = [
            row
            for row in scoped
            if _metadata(row, "parent_cluster_id") == cluster_anchor
        ]
        if matching:
            scoped = matching
            cluster_scope = True
    if context and not cluster_scope:
        matching = [
            row
            for row in scoped
            if _metadata(row, "title").casefold() == context.casefold()
        ]
        if source_path_anchor or matching:
            scoped = matching
            title_scope = True
    if modality:
        matching = [
            row for row in scoped if _metadata(row, "modality") == modality
        ]
        if matching:
            scoped = matching
    return scoped, title_scope, cluster_scope


class SourceSemanticEvidenceAtomRetrieverV1:
    """Rank immutable atom projections and preserve original citable ranges."""

    implementation_id = "source-semantic-evidence-atom-retriever-v1"
    version = "v1"

    def __init__(
        self,
        chunks: Sequence[DocumentChunk],
        *,
        candidate_limit: int = 30,
    ) -> None:
        if candidate_limit < 5:
            raise ValueError("semantic atom candidate limit must be at least five")
        self.chunks = tuple(materialize_semantic_evidence_atoms(chunks))
        self.candidate_limit = candidate_limit
        self._by_id = {row.id: row for row in self.chunks}
        projections = [
            row.model_copy(
                update={
                    "text": _metadata(row, "semantic_search_text"),
                    "content_hash": None,
                }
            )
            for row in self.chunks
        ]
        self._index = BM25Retriever(projections)
        self.last_trace: SemanticEvidenceAtomTraceV1 | None = None

    def _rank(
        self,
        *,
        question: str,
        target: str,
        candidates: Sequence[DocumentChunk],
        context: str | None,
        already_selected: Sequence[DocumentChunk],
    ) -> list[RetrievalHit]:
        query = " ".join(value for value in (context, target) if value).strip()
        if not query:
            query = question.strip()
        base = self._index.retrieve(query, limit=self.candidate_limit)
        base_score = {row.chunk.id: row.relevance_score for row in base}
        selected_ids = {row.id for row in already_selected}
        related_ids = {
            identifier
            for row in already_selected
            for identifier in _json_ids(row, "semantic_related_atom_ids")
        }
        target_phrase = " ".join(target.casefold().split())
        rows: list[RetrievalHit] = []
        for chunk in candidates:
            if chunk.id in selected_ids:
                continue
            claim = _metadata(chunk, "semantic_atom_claim")
            projection = _metadata(chunk, "semantic_search_text")
            target_coverage = _coverage(target, claim) if target else 0.0
            question_coverage = _coverage(question, projection)
            exact_phrase = bool(target_phrase and target_phrase in claim.casefold())
            context_match = bool(
                context and _metadata(chunk, "title").casefold() == context.casefold()
            )
            relation_match = chunk.id in related_ids
            score = (
                0.50 * target_coverage
                + 0.20 * base_score.get(chunk.id, 0.0)
                + 0.12 * question_coverage
                + (0.08 if context_match else 0.0)
                + (0.06 if exact_phrase else 0.0)
                + (0.04 if relation_match else 0.0)
            )
            rows.append(
                RetrievalHit(
                    chunk=chunk,
                    relevance_score=max(0.0, min(1.0, score)),
                    raw_score=score,
                )
            )
        return sorted(
            rows,
            key=lambda row: (
                -float(row.raw_score or 0.0),
                -_coverage(target, _metadata(row.chunk, "semantic_atom_claim")),
                _range_start(row.chunk),
                row.chunk.id,
            ),
        )

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise InvalidRetrievalLimitError("retrieval limit must be at least one")
        if not query.strip():
            raise EmptyQueryError("question must not be empty")
        plan = plan_public_source_ranges(query)
        scoped, title_scope, cluster_scope = _scope(
            self.chunks,
            source_path_anchor=plan.source_path_anchor,
            cluster_anchor=plan.cluster_anchor,
            context=plan.evidence.context,
            modality=plan.evidence.modality,
        )
        selected: list[RetrievalHit] = []
        selected_chunks: list[DocumentChunk] = []
        all_ranked: list[list[RetrievalHit]] = []
        for target in plan.evidence.targets:
            ranked = self._rank(
                question=query,
                target=target,
                candidates=scoped,
                context=plan.evidence.context,
                already_selected=selected_chunks,
            )
            all_ranked.append(ranked)
            if ranked:
                selected.append(ranked[0])
                selected_chunks.append(ranked[0].chunk)
        used = {row.chunk.id for row in selected}
        tail: dict[str, RetrievalHit] = {}
        for ranked in all_ranked:
            for hit in ranked:
                if hit.chunk.id not in used:
                    current = tail.get(hit.chunk.id)
                    if current is None or hit.relevance_score > current.relevance_score:
                        tail[hit.chunk.id] = hit
        ordered_tail = sorted(
            tail.values(),
            key=lambda row: (-row.relevance_score, _range_start(row.chunk), row.chunk.id),
        )
        output = [*selected, *ordered_tail][:limit]
        relation_constrained = bool(
            len(selected_chunks) > 1
            and all(
                row.id in _json_ids(selected_chunks[0], "semantic_related_atom_ids")
                for row in selected_chunks[1:]
            )
        )
        self.last_trace = SemanticEvidenceAtomTraceV1(
            selected_hit_ids=tuple(row.chunk.id for row in selected),
            candidate_count=sum(len(rows) for rows in all_ranked),
            relation_constrained=relation_constrained,
            title_scope_applied=title_scope,
            cluster_scope_applied=cluster_scope,
        )
        return output


class SourceSemanticEvidenceAtomGateV1:
    """Require complete, unique, related source-side atoms before answering."""

    implementation_id = "source-semantic-evidence-atom-gate-v1"
    version = "v1"

    def __init__(self, *, minimum_target_coverage: float = 0.5) -> None:
        if not 0 < minimum_target_coverage <= 1:
            raise ValueError("semantic atom target coverage must be in (0, 1]")
        self.minimum_target_coverage = minimum_target_coverage

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        plan = plan_public_source_ranges(query)
        bounded = list(hits[:5])
        if not bounded or any(
            not _authorized(row.chunk)
            or _metadata(row.chunk, "semantic_atom_version") != ATOM_VERSION
            for row in bounded
        ):
            return EvidenceSufficiencyDecision(
                sufficient=False,
                score=0.0,
                reason="semantic evidence atoms are missing or unauthorized",
                features={"hit_count": len(bounded)},
                selected_hit_ids=[],
            )
        scoped, _, _ = _scope(
            [row.chunk for row in bounded],
            source_path_anchor=plan.source_path_anchor,
            cluster_anchor=plan.cluster_anchor,
            context=plan.evidence.context,
            modality=plan.evidence.modality,
        )
        scoped_ids = {row.id for row in scoped}
        selected: list[RetrievalHit] = []
        used: set[str] = set()
        for target in plan.evidence.targets:
            ranked = sorted(
                [
                    row
                    for row in bounded
                    if row.chunk.id in scoped_ids and row.chunk.id not in used
                ],
                key=lambda row: (
                    -_coverage(target, _metadata(row.chunk, "semantic_atom_claim")),
                    -row.relevance_score,
                    _range_start(row.chunk),
                    row.chunk.id,
                ),
            )
            if not ranked:
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=len(selected) / plan.evidence.requested_cardinality,
                    reason="one or more semantic evidence atoms are unresolved",
                    features={"resolved_cardinality": len(selected)},
                    selected_hit_ids=[],
                )
            coverage = _coverage(
                target, _metadata(ranked[0].chunk, "semantic_atom_claim")
            )
            if target and coverage < self.minimum_target_coverage:
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=len(selected) / plan.evidence.requested_cardinality,
                    reason="semantic evidence atom target coverage is incomplete",
                    features={
                        "resolved_cardinality": len(selected),
                        "minimum_target_coverage": coverage,
                    },
                    selected_hit_ids=[],
                )
            selected.append(ranked[0])
            used.add(ranked[0].chunk.id)
        if len(selected) > 1:
            first_related = set(
                _json_ids(selected[0].chunk, "semantic_related_atom_ids")
            )
            if any(row.chunk.id not in first_related for row in selected[1:]):
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=0.0,
                    reason="multi-atom evidence lacks an explicit source relation",
                    features={"resolved_cardinality": len(selected)},
                    selected_hit_ids=[],
                )
        return EvidenceSufficiencyDecision(
            sufficient=len(selected) == plan.evidence.requested_cardinality,
            score=1.0,
            reason="every public target resolves to a related canonical evidence atom",
            features={
                "requested_cardinality": plan.evidence.requested_cardinality,
                "resolved_cardinality": len(selected),
                "explicit_relation_required": len(selected) > 1,
            },
            selected_hit_ids=[row.chunk.id for row in selected],
        )


class SourceSemanticEvidenceAtomGateV2(SourceSemanticEvidenceAtomGateV1):
    """Reject non-unique public references before answer generation."""

    implementation_id = "source-semantic-evidence-atom-gate-v2"
    version = "v2"

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        bounded = list(hits[:5])
        if bounded:
            uniqueness = analyze_public_reference_uniqueness(
                query,
                [row.chunk for row in bounded],
                minimum_target_coverage=self.minimum_target_coverage,
            )
            if uniqueness.status == "ambiguous":
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=0.0,
                    reason="public reference is ambiguous across canonical answer classes",
                    features={
                        "ambiguous_target_count": sum(
                            row.status == "ambiguous" for row in uniqueness.targets
                        ),
                        "source_path_scoped": uniqueness.source_path_anchor is not None,
                        "section_scoped": uniqueness.section_anchor is not None,
                    },
                    selected_hit_ids=[],
                    recommended_action="clarify",
                )
            if uniqueness.status == "unresolved":
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=0.0,
                    reason="public reference does not resolve to canonical evidence",
                    features={
                        "unresolved_target_count": sum(
                            row.status == "unresolved" for row in uniqueness.targets
                        )
                    },
                    selected_hit_ids=[],
                    recommended_action="abstain",
                )
        return super().assess(query, bounded)


class SourceSemanticEvidenceAtomGateV3(SourceSemanticEvidenceAtomGateV1):
    """Resolve instructional questions through explicit public source anchors.

    V2 deliberately remains unchanged as historical evidence. V3 prevents
    pedagogical request language from diluting target coverage while preserving
    fail-closed ambiguity handling across distinct canonical claim classes.
    """

    implementation_id = "source-semantic-evidence-atom-gate-v3"
    version = "v3"

    def _contested_leaders(
        self,
        ranked: Sequence[RetrievalHit],
        *,
        query: str,
        target: str,
    ) -> list[RetrievalHit]:
        """Return the atoms whose canonical claims must agree.

        V3 contests every atom that cleared the target's coverage threshold.
        The extension point exists so a successor can narrow the contest
        without altering this class, whose decisions are recorded evidence.
        """

        return list(ranked)

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        plan = plan_public_source_ranges(query)
        bounded = list(hits[:5])
        if not bounded or any(
            not _authorized(row.chunk)
            or _metadata(row.chunk, "semantic_atom_version") != ATOM_VERSION
            for row in bounded
        ):
            return EvidenceSufficiencyDecision(
                sufficient=False,
                score=0.0,
                reason="semantic evidence atoms are missing or unauthorized",
                features={"hit_count": len(bounded)},
                selected_hit_ids=[],
            )
        scoped, _, _ = _scope(
            [row.chunk for row in bounded],
            source_path_anchor=plan.source_path_anchor,
            cluster_anchor=plan.cluster_anchor,
            context=plan.evidence.context,
            modality=plan.evidence.modality,
        )
        scoped_ids = {row.id for row in scoped}
        selected: list[RetrievalHit] = []
        for target in plan.evidence.targets:
            ranked = sorted(
                [
                    row
                    for row in bounded
                    if row.chunk.id in scoped_ids
                    and (
                        _has_public_title_anchor(query, row.chunk)
                        or _instructional_coverage(target, row.chunk)
                        >= self.minimum_target_coverage
                    )
                ],
                key=lambda row: (
                    -int(_has_public_title_anchor(query, row.chunk)),
                    -_instructional_coverage(target, row.chunk),
                    -row.relevance_score,
                    _range_start(row.chunk),
                    row.chunk.id,
                ),
            )
            if not ranked:
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=len(selected) / plan.evidence.requested_cardinality,
                    reason="instructional target does not resolve to canonical evidence",
                    features={"resolved_cardinality": len(selected)},
                    selected_hit_ids=[],
                    recommended_action="abstain",
                )
            contested = self._contested_leaders(ranked, query=query, target=target)
            claim_classes = {
                normalize_claim_class(_metadata(row.chunk, "semantic_atom_claim"))
                for row in contested
            }
            if len(claim_classes) > 1:
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=0.0,
                    reason=(
                        "instructional target is ambiguous across canonical "
                        "evidence claims"
                    ),
                    features={
                        "canonical_claim_class_count": len(claim_classes),
                        "contested_leader_count": len(contested),
                    },
                    selected_hit_ids=[],
                    recommended_action="clarify",
                )
            selected.append(ranked[0])
        unique_selected = list(dict.fromkeys(row.chunk.id for row in selected))
        selected_by_id = {row.chunk.id: row for row in selected}
        if len(unique_selected) > 1:
            first_related = set(
                _json_ids(selected[0].chunk, "semantic_related_atom_ids")
            )
            if any(identifier not in first_related for identifier in unique_selected[1:]):
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=0.0,
                    reason="multi-atom evidence lacks an explicit source relation",
                    features={"resolved_cardinality": len(selected)},
                    selected_hit_ids=[],
                )
        return EvidenceSufficiencyDecision(
            sufficient=len(selected) == plan.evidence.requested_cardinality,
            score=1.0,
            reason=(
                "every instructional target resolves to one canonical source claim"
            ),
            features={
                "requested_cardinality": plan.evidence.requested_cardinality,
                "resolved_cardinality": len(selected),
                "selected_region_count": len(unique_selected),
                "single_region_multi_target": (
                    len(selected) > 1 and len(unique_selected) == 1
                ),
                "public_title_anchor_used": any(
                    _has_public_title_anchor(query, row.chunk) for row in selected
                ),
            },
            selected_hit_ids=[
                selected_by_id[identifier].chunk.id for identifier in unique_selected
            ],
        )


class SourceSemanticEvidenceAtomGateV4(SourceSemanticEvidenceAtomGateV3):
    """Fail closed on a genuine tie, not on the presence of weaker regions.

    V3 compares canonical claim classes across every atom that clears the
    target's coverage threshold, yet it selects only the top-ranked atom.
    Because ``normalize_claim_class`` is the token set of the claim text, two
    distinct regions almost always carry distinct classes. On a single-chunk
    release the contest therefore never fires; on a product-scale corpus it
    fires on nearly every answerable question, and the tutor asks the learner
    to clarify a question it had already grounded correctly.

    V4 contests only the atoms that tie the leader on the dominance keys the
    ranking itself uses -- an explicit public title anchor and instructional
    coverage. When the leader strictly dominates there is no competing reading
    to resolve, so the target resolves. When the leaders genuinely tie and
    disagree, V4 fails closed exactly as V3 does.
    """

    implementation_id = "source-semantic-evidence-atom-gate-v4"
    version = "v4"

    def _contested_leaders(
        self,
        ranked: Sequence[RetrievalHit],
        *,
        query: str,
        target: str,
    ) -> list[RetrievalHit]:
        if not ranked:
            return []

        def dominance(row: RetrievalHit) -> tuple[int, float]:
            return (
                int(_has_public_title_anchor(query, row.chunk)),
                round(_instructional_coverage(target, row.chunk), 9),
            )

        leader = dominance(ranked[0])
        return [row for row in ranked if dominance(row) == leader]


__all__ = [
    "ATOM_VERSION",
    "SemanticEvidenceAtomTraceV1",
    "SourceSemanticEvidenceAtomGateV1",
    "SourceSemanticEvidenceAtomGateV2",
    "SourceSemanticEvidenceAtomGateV3",
    "SourceSemanticEvidenceAtomGateV4",
    "SourceSemanticEvidenceAtomRetrieverV1",
    "materialize_semantic_evidence_atoms",
]
