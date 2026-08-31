"""Typed public-question evidence targets and deterministic evidence assembly.

The planner sees only the student-visible question. It extracts requested
concepts, cardinality, section context, and structured modality; authoritative
actions and source truth remain outside this module.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import re

from src.digital_twin.grounding.evidence_sufficiency import EvidenceSufficiencyDecision
from src.digital_twin.grounding.hierarchical_retrieval import concept_tokens
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.retrieval import EmptyQueryError, InvalidRetrievalLimitError


_QUOTED = re.compile(r'["“](.*?)["”]')
_MULTI = re.compile(r"\bconnect\s+(.+?)\s+with\s+(.+?)\?\s*$", re.IGNORECASE)
_PARAPHRASE = re.compile(
    r"\bsource\s+point\s+about\s+(.+?)\s+be\s+restated\?\s*$",
    re.IGNORECASE,
)
_SINGLE = re.compile(
    r"\b(?:state\s+about|explain|concerns)\s+(.+?)\?\s*$",
    re.IGNORECASE,
)
_GENERIC_TARGETS = frozenset(
    {"the selected source detail", "selected source detail", "the source detail"}
)


@dataclass(frozen=True)
class PublicEvidenceTargetPlanV1:
    context: str | None
    targets: tuple[str, ...]
    requested_cardinality: int
    modality: str | None
    extraction_rule: str


@dataclass(frozen=True)
class TargetRetrievalTraceV1:
    plan: PublicEvidenceTargetPlanV1
    selected_hit_ids: tuple[str, ...]
    candidate_count: int
    metadata_ranking_enabled: bool


def plan_public_evidence_targets(question: str) -> PublicEvidenceTargetPlanV1:
    """Derive an inspectable evidence request without source or gold access."""

    normalized = " ".join(question.split())
    if not normalized:
        raise EmptyQueryError("question must not be empty")
    quoted = _QUOTED.findall(normalized)
    context = quoted[0].strip() if quoted else None
    modality = next(
        (
            name
            for phrase, name in (
                ("code detail", "structured-code"),
                ("equation", "structured-equation"),
                ("table entry", "structured-table"),
            )
            if phrase in normalized.casefold()
        ),
        None,
    )
    multi = _MULTI.search(normalized)
    if multi:
        targets = tuple(value.strip(" .") for value in multi.groups())
        return PublicEvidenceTargetPlanV1(
            context=context,
            targets=targets,
            requested_cardinality=2,
            modality=modality,
            extraction_rule="explicit-two-target-connection",
        )
    for pattern, rule in (
        (_PARAPHRASE, "source-point-target"),
        (_SINGLE, "single-evidence-target"),
    ):
        match = pattern.search(normalized)
        if match:
            target = match.group(1).strip(" .")
            if target.casefold() in _GENERIC_TARGETS:
                target = ""
            return PublicEvidenceTargetPlanV1(
                context=context,
                targets=(target,),
                requested_cardinality=1,
                modality=modality,
                extraction_rule=rule,
            )
    fallback = context or normalized
    return PublicEvidenceTargetPlanV1(
        context=context,
        targets=(fallback,),
        requested_cardinality=1,
        modality=modality,
        extraction_rule="bounded-question-fallback",
    )


def _normalized(value: str) -> str:
    return " ".join(sorted(concept_tokens(value)))


def _coverage(needle: str, haystack: str) -> float:
    expected = concept_tokens(needle)
    if not expected:
        return 0.0
    return len(expected & concept_tokens(haystack)) / len(expected)


def _target_score(
    *,
    plan: PublicEvidenceTargetPlanV1,
    target: str,
    hit: RetrievalHit,
    lexical_rank: int,
    metadata_enabled: bool,
) -> float:
    chunk = hit.chunk
    metadata = chunk.metadata
    target_exact = bool(target and _normalized(target) in _normalized(chunk.text))
    target_coverage = _coverage(target, chunk.text) if target else 0.0
    title = str(metadata.get("title", ""))
    context_exact = bool(
        plan.context and plan.context.casefold().strip() == title.casefold().strip()
    )
    modality_match = bool(
        plan.modality and plan.modality == str(metadata.get("modality", ""))
    )
    score = max(0.0, hit.relevance_score) + (1 / (lexical_rank + 1))
    score += 8.0 if target_exact else 5.0 * target_coverage
    score += 3.0 if context_exact else 0.0
    score += 2.0 if modality_match else 0.0
    if metadata_enabled:
        description = str(metadata.get("search_description", ""))
        score += 1.5 * _coverage(target or plan.context or "", description)
        score += _coverage(plan.context or "", title)
    return score


class TargetAwareEvidenceRetrieverV1:
    """Retrieve one distinct, source-range-sized region for each public target."""

    implementation_id = "target-aware-evidence-retriever-v1"
    version = "v1"

    def __init__(
        self,
        base: Retriever,
        chunks: Sequence[DocumentChunk],
        *,
        candidate_limit: int = 30,
        metadata_ranking_enabled: bool = False,
    ) -> None:
        if candidate_limit < 5:
            raise ValueError("target-aware candidate limit must be at least five")
        identifiers = [row.id for row in chunks]
        if not chunks or len(identifiers) != len(set(identifiers)):
            raise ValueError("target-aware chunks must be non-empty and unique")
        if any(not row.retrieval_allowed for row in chunks):
            raise ValueError("target-aware retrieval accepts only approved chunks")
        self.base = base
        self.chunks = tuple(chunks)
        self.candidate_limit = candidate_limit
        self.metadata_ranking_enabled = metadata_ranking_enabled
        self.last_trace: TargetRetrievalTraceV1 | None = None

    def _rank_for_target(
        self,
        plan: PublicEvidenceTargetPlanV1,
        target: str,
    ) -> list[RetrievalHit]:
        query = " ".join(value for value in (plan.context, target) if value).strip()
        if not query:
            raise EmptyQueryError("target plan produced no retrieval query")
        candidates = self.base.retrieve(query, limit=self.candidate_limit)
        rank_by_id = {row.chunk.id: rank for rank, row in enumerate(candidates)}
        return sorted(
            candidates,
            key=lambda hit: (
                -_target_score(
                    plan=plan,
                    target=target,
                    hit=hit,
                    lexical_rank=rank_by_id[hit.chunk.id],
                    metadata_enabled=self.metadata_ranking_enabled,
                ),
                hit.chunk.ordinal,
                hit.chunk.id,
            ),
        )

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        if isinstance(limit, bool) or limit < 1:
            raise InvalidRetrievalLimitError("retrieval limit must be at least one")
        plan = plan_public_evidence_targets(query)
        ranked_by_target = [self._rank_for_target(plan, target) for target in plan.targets]
        selected: list[RetrievalHit] = []
        selected_ids: set[str] = set()
        for ranked in ranked_by_target:
            chosen = next((row for row in ranked if row.chunk.id not in selected_ids), None)
            if chosen is not None:
                selected.append(chosen)
                selected_ids.add(chosen.chunk.id)
        tail: dict[str, RetrievalHit] = {}
        for ranked in ranked_by_target:
            for hit in ranked:
                if hit.chunk.id not in selected_ids:
                    tail.setdefault(hit.chunk.id, hit)
        ordered_tail = sorted(
            tail.values(),
            key=lambda hit: (-hit.relevance_score, hit.chunk.ordinal, hit.chunk.id),
        )
        output = [*selected, *ordered_tail][:limit]
        self.last_trace = TargetRetrievalTraceV1(
            plan=plan,
            selected_hit_ids=tuple(row.chunk.id for row in selected),
            candidate_count=sum(len(rows) for rows in ranked_by_target),
            metadata_ranking_enabled=self.metadata_ranking_enabled,
        )
        return output


class TargetEvidenceGateV1:
    """Require one current, authorized, matching region for every public target."""

    implementation_id = "target-evidence-cardinality-gate-v1"
    version = "v1"

    def __init__(self, *, minimum_target_coverage: float = 0.5) -> None:
        if not 0 < minimum_target_coverage <= 1:
            raise ValueError("target coverage must be in (0, 1]")
        self.minimum_target_coverage = minimum_target_coverage

    def _matches(
        self,
        plan: PublicEvidenceTargetPlanV1,
        target: str,
        hit: RetrievalHit,
    ) -> bool:
        metadata = hit.chunk.metadata
        if target:
            target_matches = _coverage(target, hit.chunk.text) >= self.minimum_target_coverage
        else:
            target_matches = bool(
                plan.context
                and _coverage(plan.context, str(metadata.get("title", ""))) >= 0.75
            )
        modality_matches = not plan.modality or (
            plan.modality == str(metadata.get("modality", ""))
        )
        return target_matches and modality_matches

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        plan = plan_public_evidence_targets(query)
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
                reason="target evidence is not source-authorized",
                features={"hit_count": len(bounded)},
                selected_hit_ids=[],
            )
        selected: list[RetrievalHit] = []
        used: set[str] = set()
        for target in plan.targets:
            match = next(
                (
                    hit
                    for hit in bounded
                    if hit.chunk.id not in used and self._matches(plan, target, hit)
                ),
                None,
            )
            if match is None:
                return EvidenceSufficiencyDecision(
                    sufficient=False,
                    score=len(selected) / plan.requested_cardinality,
                    reason="one or more public evidence targets are unresolved",
                    features={
                        "requested_cardinality": plan.requested_cardinality,
                        "resolved_cardinality": len(selected),
                    },
                    selected_hit_ids=[],
                )
            selected.append(match)
            used.add(match.chunk.id)
        return EvidenceSufficiencyDecision(
            sufficient=len(selected) == plan.requested_cardinality,
            score=1.0,
            reason="every public evidence target has a distinct authorized region",
            features={
                "requested_cardinality": plan.requested_cardinality,
                "resolved_cardinality": len(selected),
            },
            selected_hit_ids=[row.chunk.id for row in selected],
        )
