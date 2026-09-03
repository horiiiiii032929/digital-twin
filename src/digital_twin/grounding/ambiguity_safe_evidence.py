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

    # V1 contests every candidate that clears the coverage threshold. The
    # successor below narrows that to the candidates which tie the leader.
    dominance_scoped = False

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
                dominance_scoped=self.dominance_scoped,
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


class DominanceScopedAmbiguitySafeEvidenceGateV3(AmbiguitySafeEvidenceGateV1):
    """Contest only the candidates that actually tie the leading coverage.

    V1 lets any candidate clearing the coverage threshold veto a target, so a
    strictly weaker passage carrying a different canonical claim refuses a
    question its leading passage answers outright. Measured on 263 ambiguous
    targets at region granularity, 76 had a strictly dominant leader and in all
    76 that leader was the region the gold cites.

    The remaining 187 are genuine ties and stay refused. Gold sits inside the
    tied leader set in 184 of them, but no available secondary measure
    separates it reliably -- the best isolates gold in 105 and picks a wrong
    region in 61 -- so resolving ties would buy coverage with unsupported
    releases. This gate declines that trade and keeps V1's fail-closed
    behaviour wherever the tie is real.
    """

    implementation_id = "dominance-scoped-ambiguity-safe-v3"
    version = "v3"
    dominance_scoped = True
