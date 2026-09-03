"""Product evidence-gate wrapper for pre-generation reference ambiguity."""

from __future__ import annotations

from collections.abc import Sequence

from src.digital_twin.grounding.evidence_sufficiency import EvidenceSufficiencyDecision
from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.grounding.protocols import EvidenceSufficiencyGate
from src.digital_twin.grounding.reference_uniqueness import (
    analyze_public_reference_uniqueness,
    prefer_specific_source_regions,
)


class AmbiguitySafeEvidenceGateV1:
    """Compose an existing gate with deterministic reference uniqueness."""

    implementation_id = "ambiguity-safe-evidence-gate-v1"
    version = "v1"

    def __init__(
        self,
        base: EvidenceSufficiencyGate,
        *,
        minimum_target_coverage: float = 0.5,
        evidence_limit: int = 5,
    ) -> None:
        if not getattr(base, "implementation_id", ""):
            raise ValueError("base evidence gate must declare an implementation ID")
        if not 0 < minimum_target_coverage <= 1:
            raise ValueError("minimum target coverage must be in (0, 1]")
        if evidence_limit < 1:
            raise ValueError("evidence limit must be positive")
        self.base = base
        self.minimum_target_coverage = minimum_target_coverage
        self.evidence_limit = evidence_limit

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        # Page-level selected-text fallbacks and precise regions are alternate
        # representations of the same source content.  Remove the aggregate
        # fallback across the complete candidate set before applying the
        # evidence limit; otherwise a fallback inside the window can displace
        # its precise sibling immediately outside it.
        preferred_ids = {
            row.id
            for row in prefer_specific_source_regions(
                [hit.chunk for hit in hits]
            )
        }
        bounded = [
            hit for hit in hits if hit.chunk.id in preferred_ids
        ][: self.evidence_limit]
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
                        "base_gate_called": False,
                    },
                    selected_hit_ids=[],
                    recommended_action="clarify",
                )
        return self.base.assess(query, bounded)


__all__ = ["AmbiguitySafeEvidenceGateV1"]
