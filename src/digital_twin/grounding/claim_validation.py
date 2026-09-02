"""Fail-closed post-generation validation of atomic answer claims.

The generator may propose claim text and cite retrieved hit IDs.  It cannot
decide whether a response is releasable.  This module validates lineage first,
then applies an inspectable claim-support verifier, and releases only when
every declared factual claim is supported by its cited evidence.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from src.digital_twin.grounding.evidence_verifiers import (
    NliScoreBackend,
)
from src.digital_twin.grounding.models import AtomicAnswerClaim, RetrievalHit


_SPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^a-z0-9 ]+")


def _probability(value: float, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or not 0 <= numeric <= 1:
        raise ValueError(f"{name} must be a finite probability")
    return numeric


def _normalized_text(value: str) -> str:
    lowered = value.casefold().replace("-", " ")
    return _SPACE.sub(" ", _NON_WORD.sub(" ", lowered)).strip()


class AtomicClaimSupportSignal(BaseModel):
    claim_id: str = Field(pattern=r"^claim-[a-z0-9-]+$")
    entailment: float = Field(ge=0, le=1, allow_inf_nan=False)
    contradiction: float = Field(ge=0, le=1, allow_inf_nan=False)
    supporting_hit_ids: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)

    @field_validator("supporting_hit_ids")
    @classmethod
    def supporting_ids_must_be_unique(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("supporting_hit_ids cannot contain blank IDs")
        if len(values) != len(set(values)):
            raise ValueError("supporting_hit_ids must be unique")
        return values


class AtomicClaimValidationDecision(BaseModel):
    releasable: bool
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    reason: str = Field(min_length=1)
    claim_count: int = Field(ge=0)
    supported_claim_count: int = Field(ge=0)
    unsupported_claim_ids: list[str] = Field(default_factory=list)
    features: dict[str, float | int | bool | str] = Field(default_factory=dict)


class AtomicClaimSupportVerifier(Protocol):
    implementation_id: str
    version: str

    def verify(
        self,
        claims: Sequence[AtomicAnswerClaim],
        hits: Sequence[RetrievalHit],
    ) -> list[AtomicClaimSupportSignal]:
        """Score each claim against only its declared retrieved evidence."""


class ExactQuoteAtomicClaimVerifier:
    """Inspectable high-precision control for normalized evidence containment."""

    implementation_id = "exact-quote-atomic-claim-verifier-v1"
    version = "1.0.0"

    def verify(
        self,
        claims: Sequence[AtomicAnswerClaim],
        hits: Sequence[RetrievalHit],
    ) -> list[AtomicClaimSupportSignal]:
        by_id = {hit.chunk.id: hit for hit in hits}
        signals: list[AtomicClaimSupportSignal] = []
        for claim in claims:
            evidence = " ".join(by_id[hit_id].chunk.text for hit_id in claim.evidence_hit_ids)
            supported = _normalized_text(claim.text) in _normalized_text(evidence)
            signals.append(
                AtomicClaimSupportSignal(
                    claim_id=claim.claim_id,
                    entailment=1.0 if supported else 0.0,
                    contradiction=0.0,
                    supporting_hit_ids=list(claim.evidence_hit_ids) if supported else [],
                    reason="normalized exact claim containment",
                )
            )
        return signals


class ContiguousQuoteAtomicClaimVerifier:
    """Require each claim to be a literal contiguous span of one cited hit."""

    implementation_id = "contiguous-quote-atomic-claim-verifier-v1"
    version = "1.0.0"

    def verify(
        self,
        claims: Sequence[AtomicAnswerClaim],
        hits: Sequence[RetrievalHit],
    ) -> list[AtomicClaimSupportSignal]:
        by_id = {hit.chunk.id: hit for hit in hits}
        signals: list[AtomicClaimSupportSignal] = []
        for claim in claims:
            supporting_hit_ids = [
                hit_id
                for hit_id in claim.evidence_hit_ids
                if claim.text in by_id[hit_id].chunk.text
            ]
            supported = bool(supporting_hit_ids)
            signals.append(
                AtomicClaimSupportSignal(
                    claim_id=claim.claim_id,
                    entailment=1.0 if supported else 0.0,
                    contradiction=0.0,
                    supporting_hit_ids=supporting_hit_ids,
                    reason="literal contiguous claim containment in cited evidence",
                )
            )
        return signals


class CanonicalSourceAtomicClaimVerifier:
    """Verify claims against server-owned canonical source atoms when present.

    Registered semantic atoms may carry a normalized, display-safe claim that
    is deterministically derived from the same immutable source range.  The
    validator must use that contract consistently instead of asking an NLI
    model to rediscover equivalence with authoring markup.  Ordinary chunks
    remain on the normalized source-containment path.
    """

    implementation_id = "canonical-source-atomic-claim-verifier-v1"
    version = "1.0.0"
    semantic_atom_version = "source-semantic-evidence-atom-v1"

    @classmethod
    def _supported(cls, claim_text: str, hit: RetrievalHit) -> bool:
        metadata = hit.chunk.metadata
        if metadata.get("semantic_atom_version") == cls.semantic_atom_version:
            canonical = metadata.get("semantic_atom_claim")
            return (
                isinstance(canonical, str)
                and bool(canonical.strip())
                and _normalized_text(claim_text) == _normalized_text(canonical)
            )
        return _normalized_text(claim_text) in _normalized_text(hit.chunk.text)

    def verify(
        self,
        claims: Sequence[AtomicAnswerClaim],
        hits: Sequence[RetrievalHit],
    ) -> list[AtomicClaimSupportSignal]:
        by_id = {hit.chunk.id: hit for hit in hits}
        signals: list[AtomicClaimSupportSignal] = []
        for claim in claims:
            supporting_hit_ids = [
                hit_id
                for hit_id in claim.evidence_hit_ids
                if self._supported(claim.text, by_id[hit_id])
            ]
            supported = bool(supporting_hit_ids)
            signals.append(
                AtomicClaimSupportSignal(
                    claim_id=claim.claim_id,
                    entailment=1.0 if supported else 0.0,
                    contradiction=0.0,
                    supporting_hit_ids=supporting_hit_ids,
                    reason="canonical registered source-claim equivalence",
                )
            )
        return signals


class NliAtomicClaimVerifier:
    """Apply NLI in its intended evidence-premise, claim-hypothesis direction."""

    implementation_id = "nli-atomic-claim-verifier-v1"
    version = "1.0.0"

    def __init__(self, backend: NliScoreBackend) -> None:
        self.backend = backend

    def verify(
        self,
        claims: Sequence[AtomicAnswerClaim],
        hits: Sequence[RetrievalHit],
    ) -> list[AtomicClaimSupportSignal]:
        by_id = {hit.chunk.id: hit for hit in hits}
        pairs = [
            (
                " ".join(by_id[hit_id].chunk.text for hit_id in claim.evidence_hit_ids),
                claim.text,
            )
            for claim in claims
        ]
        rows = self.backend.score_pairs(pairs)
        if len(rows) != len(claims):
            raise ValueError("NLI backend returned the wrong number of rows")
        return [
            AtomicClaimSupportSignal(
                claim_id=claim.claim_id,
                entailment=_probability(row.entailment, "entailment"),
                contradiction=_probability(row.contradiction, "contradiction"),
                supporting_hit_ids=(
                    list(claim.evidence_hit_ids)
                    if row.entailment >= row.neutral
                    and row.entailment >= row.contradiction
                    else []
                ),
                reason="revision-pinned NLI evidence entailment",
            )
            for claim, row in zip(claims, rows, strict=True)
        ]


class AtomicClaimEvidenceValidator:
    """Deterministic owner of the final post-generation release decision."""

    implementation_id = "atomic-claim-evidence-validator-v1"
    version = "1.0.0"

    def __init__(
        self,
        verifier: AtomicClaimSupportVerifier,
        *,
        minimum_entailment: float,
        maximum_contradiction: float,
        maximum_claims: int = 8,
        evidence_limit: int = 5,
    ) -> None:
        self.minimum_entailment = _probability(
            minimum_entailment,
            "minimum_entailment",
        )
        self.maximum_contradiction = _probability(
            maximum_contradiction,
            "maximum_contradiction",
        )
        if isinstance(maximum_claims, bool) or not 1 <= maximum_claims <= 32:
            raise ValueError("maximum_claims must be between 1 and 32")
        if isinstance(evidence_limit, bool) or not 1 <= evidence_limit <= 20:
            raise ValueError("evidence_limit must be between 1 and 20")
        if not getattr(verifier, "implementation_id", ""):
            raise ValueError("verifier must declare implementation_id")
        if not getattr(verifier, "version", ""):
            raise ValueError("verifier must declare version")
        self.verifier = verifier
        self.maximum_claims = maximum_claims
        self.evidence_limit = evidence_limit

    def validate(
        self,
        claims: Sequence[AtomicAnswerClaim],
        hits: Sequence[RetrievalHit],
    ) -> AtomicClaimValidationDecision:
        bounded_hits = list(hits[: self.evidence_limit])
        parsed_claims = [AtomicAnswerClaim.model_validate(claim) for claim in claims]
        if not parsed_claims:
            return self._rejected("answer contains no declared factual claims", 0)
        if len(parsed_claims) > self.maximum_claims:
            return self._rejected(
                "answer exceeds the bounded atomic-claim count",
                len(parsed_claims),
            )
        claim_ids = [claim.claim_id for claim in parsed_claims]
        if len(claim_ids) != len(set(claim_ids)):
            return self._rejected("claim IDs are not unique", len(parsed_claims))

        eligible_ids = {
            hit.chunk.id for hit in bounded_hits if hit.chunk.retrieval_allowed
        }
        cited_ids = {
            hit_id for claim in parsed_claims for hit_id in claim.evidence_hit_ids
        }
        if not cited_ids.issubset(eligible_ids):
            return self._rejected(
                "claim references unknown or ineligible evidence",
                len(parsed_claims),
                lineage_valid=False,
            )

        try:
            raw_signals = self.verifier.verify(parsed_claims, bounded_hits)
            signals = [AtomicClaimSupportSignal.model_validate(row) for row in raw_signals]
        except Exception as error:  # The release boundary must fail closed.
            return self._rejected(
                "claim-support verifier failed closed",
                len(parsed_claims),
                verifier_error=True,
                verifier_error_type=type(error).__name__,
            )

        by_claim_id: dict[str, AtomicClaimSupportSignal] = {}
        for signal in signals:
            if signal.claim_id in by_claim_id:
                return self._rejected(
                    "claim-support verifier returned duplicate claim IDs",
                    len(parsed_claims),
                    verifier_output_valid=False,
                )
            by_claim_id[signal.claim_id] = signal
        if set(by_claim_id) != set(claim_ids):
            return self._rejected(
                "claim-support verifier did not cover the exact claim set",
                len(parsed_claims),
                verifier_output_valid=False,
            )

        supported: list[str] = []
        unsupported: list[str] = []
        scores: list[float] = []
        for claim in parsed_claims:
            signal = by_claim_id[claim.claim_id]
            if not set(signal.supporting_hit_ids).issubset(
                set(claim.evidence_hit_ids)
            ):
                return self._rejected(
                    "claim-support verifier escaped declared lineage",
                    len(parsed_claims),
                    verifier_output_valid=False,
                )
            passed = (
                signal.entailment >= self.minimum_entailment
                and signal.contradiction <= self.maximum_contradiction
                and bool(signal.supporting_hit_ids)
            )
            score = min(signal.entailment, 1 - signal.contradiction)
            scores.append(score)
            (supported if passed else unsupported).append(claim.claim_id)

        releasable = not unsupported
        return AtomicClaimValidationDecision(
            releasable=releasable,
            score=min(scores),
            reason=(
                "every atomic claim is supported by its declared evidence"
                if releasable
                else "one or more atomic claims are not supported"
            ),
            claim_count=len(parsed_claims),
            supported_claim_count=len(supported),
            unsupported_claim_ids=unsupported,
            features={
                "lineage_valid": True,
                "verifier_called": True,
                "verifier_error": False,
                "verifier_output_valid": True,
                "minimum_entailment": self.minimum_entailment,
                "maximum_contradiction": self.maximum_contradiction,
                "evidence_hit_count": len(bounded_hits),
            },
        )

    @staticmethod
    def _rejected(
        reason: str,
        claim_count: int,
        **features: float | int | bool | str,
    ) -> AtomicClaimValidationDecision:
        return AtomicClaimValidationDecision(
            releasable=False,
            score=0.0,
            reason=reason,
            claim_count=claim_count,
            supported_claim_count=0,
            unsupported_claim_ids=[],
            features=features,
        )
