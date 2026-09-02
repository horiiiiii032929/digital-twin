"""Deterministic public-question reference uniqueness checks.

The checker uses only the public question and approved source-side semantic
atoms.  It does not inspect expected actions, answers, hidden gold, model
output, or runtime chunk identifiers.  Repeated source regions are acceptable
only when they independently express the same canonical claim.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.grounding.hierarchical_retrieval import concept_tokens
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.source_range_evidence import (
    canonicalize_source_claim,
    plan_public_source_ranges,
)


ReferenceUniquenessStatus = Literal[
    "unique",
    "alternate-valid",
    "ambiguous",
    "unresolved",
]
CandidateRelationship = Literal[
    "exact-supported",
    "alternate-supported",
    "partial-supported",
    "conflicting-supported",
    "unrelated-supported",
]


class ReferenceTargetUniquenessV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    status: ReferenceUniquenessStatus
    candidate_region_ids: list[str] = Field(default_factory=list)
    canonical_claim_classes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_status(self) -> "ReferenceTargetUniquenessV1":
        if len(self.candidate_region_ids) != len(set(self.candidate_region_ids)):
            raise ValueError("candidate region identifiers must be unique")
        if self.status == "unresolved" and self.candidate_region_ids:
            raise ValueError("an unresolved target cannot contain candidates")
        if self.status == "unique" and len(self.candidate_region_ids) != 1:
            raise ValueError("a unique target requires one candidate region")
        if self.status == "alternate-valid" and (
            len(self.candidate_region_ids) < 2
            or len(self.canonical_claim_classes) != 1
        ):
            raise ValueError("alternate-valid requires equivalent source regions")
        if self.status == "ambiguous" and len(self.canonical_claim_classes) < 2:
            raise ValueError("an ambiguous target requires competing claim classes")
        return self


class QuestionReferenceUniquenessV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReferenceUniquenessStatus
    source_path_anchor: str | None
    section_anchor: str | None
    targets: list[ReferenceTargetUniquenessV1] = Field(min_length=1)


def normalize_claim_class(value: str) -> str:
    """Return a stable semantic class key without provider assistance."""

    return " ".join(sorted(concept_tokens(canonicalize_source_claim(value))))


def _metadata(chunk: DocumentChunk, key: str) -> str:
    return str(chunk.metadata.get(key, "")).strip()


def _claim(chunk: DocumentChunk) -> str:
    return _metadata(chunk, "semantic_atom_claim") or canonicalize_source_claim(
        chunk.text,
        modality=_metadata(chunk, "modality"),
    )


def _coverage(target: str, claim: str) -> float:
    expected = concept_tokens(target)
    if not expected:
        return 0.0
    observed = concept_tokens(claim)
    return len(expected & observed) / len(expected)


def derive_unique_public_cue(
    authoritative_claim: str,
    scoped_claims: Sequence[str],
    *,
    minimum_target_coverage: float = 0.5,
    maximum_tokens: int = 6,
) -> str | None:
    """Choose the smallest source-derived cue that has one answer class.

    The cue is only a public retrieval target.  It cannot alter the canonical
    answer or evidence, and a source cluster is rejected when no bounded cue is
    unique.
    """

    if not 0 < minimum_target_coverage <= 1:
        raise ValueError("minimum target coverage must be in (0, 1]")
    if maximum_tokens < 1:
        raise ValueError("maximum_tokens must be positive")
    semantic = concept_tokens(authoritative_claim)
    ordered = []
    for token in re.findall(r"[A-Za-z0-9_]+", authoritative_claim):
        normalized = token.casefold()
        if normalized in semantic and normalized not in ordered:
            ordered.append(normalized)
    if not ordered:
        return None
    authoritative_class = normalize_claim_class(authoritative_claim)
    competitors = [
        value
        for value in scoped_claims
        if normalize_claim_class(value) != authoritative_class
    ]
    document_frequency = {
        token: sum(token in concept_tokens(value) for value in competitors)
        for token in ordered
    }
    ranked = sorted(
        ordered,
        key=lambda token: (document_frequency[token], -len(token), ordered.index(token)),
    )
    for size in range(1, min(maximum_tokens, len(ranked)) + 1):
        choices = sorted(
            combinations(ranked, size),
            key=lambda values: (
                sum(document_frequency[value] for value in values),
                tuple(ordered.index(value) for value in values),
            ),
        )
        for values in choices:
            cue = " ".join(values)
            if all(
                _coverage(cue, candidate) < minimum_target_coverage
                for candidate in competitors
            ):
                return cue
    return None


def _authorized(chunk: DocumentChunk) -> bool:
    return bool(
        chunk.retrieval_allowed
        and chunk.display_allowed
        and chunk.source_checksum
        and chunk.source_version >= 1
        and chunk.region_id
    )


def prefer_specific_source_regions(
    chunks: Sequence[DocumentChunk],
) -> list[DocumentChunk]:
    """Remove explicit page-level ingestion fallbacks when regions are available.

    Region-aware PDF ingestion intentionally persists both precise regions and a
    selected-text page fallback. They are alternate representations of the same
    source page, not independent claims. Treating the aggregate page text as a
    competing answer class creates false ambiguity whenever it contains the
    precise answer plus headings or captions.

    The fallback is retained when no authorized, non-page region from the same
    source page is present, so page-only ingestion remains usable.
    """

    rows = list(chunks)

    def contains_specific_region(
        aggregate: DocumentChunk,
        candidate: DocumentChunk,
    ) -> bool:
        aggregate_text = " ".join(aggregate.text.split()).casefold()
        candidate_text = " ".join(candidate.text.split()).casefold()
        if candidate_text and candidate_text in aggregate_text:
            return True
        if aggregate.bounding_box is None or candidate.bounding_box is None:
            return False
        aggregate_x0, aggregate_y0, aggregate_x1, aggregate_y1 = aggregate.bounding_box
        candidate_x0, candidate_y0, candidate_x1, candidate_y1 = candidate.bounding_box
        return (
            aggregate_x0 <= candidate_x0
            and aggregate_y0 <= candidate_y0
            and candidate_x1 <= aggregate_x1
            and candidate_y1 <= aggregate_y1
        )

    def has_specific_sibling(aggregate: DocumentChunk) -> bool:
        for candidate in rows:
            if candidate.id == aggregate.id or not _authorized(candidate):
                continue
            if candidate.region_kind == "page":
                continue
            if (
                candidate.source_artifact_id != aggregate.source_artifact_id
                or candidate.source_version != aggregate.source_version
            ):
                continue
            if (
                candidate.page_start is None
                or candidate.page_end is None
                or aggregate.page_start is None
                or aggregate.page_end is None
            ):
                continue
            if (
                candidate.page_start <= aggregate.page_end
                and aggregate.page_start <= candidate.page_end
                and contains_specific_region(aggregate, candidate)
            ):
                return True
        return False

    return [
        row
        for row in rows
        if not (
            row.region_kind == "page"
            and _metadata(row, "fallback") == "selected-text"
            and has_specific_sibling(row)
        )
    ]


def _scope(question: str, chunks: Sequence[DocumentChunk]) -> tuple[
    list[DocumentChunk], str | None, str | None
]:
    plan = plan_public_source_ranges(question)
    scoped = [row for row in chunks if _authorized(row)]
    if plan.source_path_anchor:
        scoped = [
            row
            for row in scoped
            if _metadata(row, "source_path") == plan.source_path_anchor
        ]
    if plan.cluster_anchor:
        scoped = [
            row
            for row in scoped
            if _metadata(row, "parent_cluster_id") == plan.cluster_anchor
        ]
    section = plan.evidence.context
    if section:
        matching = [
            row
            for row in scoped
            if _metadata(row, "title").casefold() == section.casefold()
        ]
        if plan.source_path_anchor or plan.cluster_anchor or matching:
            scoped = matching
    if plan.evidence.modality:
        scoped = [
            row
            for row in scoped
            if _metadata(row, "modality") == plan.evidence.modality
        ]
    return scoped, plan.source_path_anchor, section


def analyze_public_reference_uniqueness(
    question: str,
    chunks: Sequence[DocumentChunk],
    *,
    minimum_target_coverage: float = 0.5,
) -> QuestionReferenceUniquenessV1:
    """Classify whether every public target resolves to one answer class."""

    if not 0 < minimum_target_coverage <= 1:
        raise ValueError("minimum target coverage must be in (0, 1]")
    plan = plan_public_source_ranges(question)
    scoped, source_path, section = _scope(
        question,
        prefer_specific_source_regions(chunks),
    )
    target_results: list[ReferenceTargetUniquenessV1] = []
    for target in plan.evidence.targets:
        matching = [
            row
            for row in scoped
            if target and _coverage(target, _claim(row)) >= minimum_target_coverage
        ]
        classes = sorted({normalize_claim_class(_claim(row)) for row in matching})
        identifiers = sorted(row.region_id or row.id for row in matching)
        if not matching:
            status: ReferenceUniquenessStatus = "unresolved"
        elif len(classes) > 1:
            status = "ambiguous"
        elif len(matching) > 1:
            status = "alternate-valid"
        else:
            status = "unique"
        target_results.append(
            ReferenceTargetUniquenessV1(
                target=target,
                status=status,
                candidate_region_ids=identifiers,
                canonical_claim_classes=classes,
            )
        )
    statuses = {row.status for row in target_results}
    if "ambiguous" in statuses:
        overall: ReferenceUniquenessStatus = "ambiguous"
    elif "unresolved" in statuses:
        overall = "unresolved"
    elif "alternate-valid" in statuses:
        overall = "alternate-valid"
    else:
        overall = "unique"
    return QuestionReferenceUniquenessV1(
        status=overall,
        source_path_anchor=source_path,
        section_anchor=section,
        targets=target_results,
    )


def classify_candidate_relationship(
    authoritative_claim: str,
    candidate_claim: str,
    *,
    same_region: bool = False,
) -> CandidateRelationship:
    """Classify planted candidate evidence against source truth."""

    authoritative = concept_tokens(authoritative_claim)
    candidate = concept_tokens(candidate_claim)
    if normalize_claim_class(authoritative_claim) == normalize_claim_class(candidate_claim):
        return "exact-supported" if same_region else "alternate-supported"
    if not authoritative or not candidate:
        return "unrelated-supported"
    overlap = len(authoritative & candidate) / len(authoritative)
    negations = {"not", "never", "no", "without"}
    if overlap >= 0.6 and bool(authoritative & negations) != bool(candidate & negations):
        return "conflicting-supported"
    if overlap >= 0.5:
        return "partial-supported"
    return "unrelated-supported"


__all__ = [
    "CandidateRelationship",
    "QuestionReferenceUniquenessV1",
    "ReferenceTargetUniquenessV1",
    "ReferenceUniquenessStatus",
    "analyze_public_reference_uniqueness",
    "classify_candidate_relationship",
    "derive_unique_public_cue",
    "normalize_claim_class",
]
