"""Characterize the selected V3 gate across the two corpus regimes.

Confirmation 024 published every case against a release holding exactly one
chunk (``governed_full_autonomy_v2_1_actual_product_runtime._install_release``
sets ``"chunks": [chunk]``). With one retrievable atom the gate's ambiguity
branch cannot fire, so the Keep decision never exercised it.

The sealed 10,000-case benchmark publishes a whole course corpus. Several
near-duplicate regions then clear the same instructional target's coverage
threshold while carrying different canonical claims, which is precisely the
condition the branch fails closed on. These tests pin both regimes so the
difference stays visible and cannot regress silently.

Nothing here proposes a gate change: the V3 gate is the frozen selected
architecture, and tuning it against the sealed set is prohibited.
"""

from __future__ import annotations

from typing import Sequence

from src.digital_twin.grounding import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.semantic_evidence_atoms import (
    SourceSemanticEvidenceAtomGateV3,
    materialize_semantic_evidence_atoms,
)
from src.digital_twin.tutor_policy import SourceLabel


CLAIM_A = (
    "Distance vector routing exchanges reachability tables between neighbouring "
    "routers until every route converges."
)
CLAIM_B = (
    "Distance vector routing exchanges reachability tables between neighbouring "
    "routers only after a link failure triggers an immediate update."
)


def _chunk(*, cluster: str, ordinal: int, text: str) -> DocumentChunk:
    identifier = f"source-region-{cluster}-{ordinal}"
    return DocumentChunk(
        id=identifier,
        document_id=f"course:{cluster}.rst",
        text=text,
        ordinal=ordinal,
        source_artifact_id=f"course:{cluster}.rst",
        source_version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        locator=f"{cluster}.rst characters 0–{len(text)}",
        source_checksum=f"{ordinal:064x}",
        region_id=identifier,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={
            "title": cluster.replace("-", " ").title(),
            "course_id": "computer-networking",
            "char_start": "0",
            "char_end": str(len(text)),
            "source_path": f"{cluster}.rst",
            "parent_cluster_id": cluster,
            "source_family_id": f"family-{cluster}",
            "modality": "text",
            "search_description": text,
        },
    )


def _hits(chunks: Sequence[DocumentChunk]) -> list[RetrievalHit]:
    materialized = materialize_semantic_evidence_atoms(list(chunks))
    return [
        RetrievalHit(chunk=row, relevance_score=1.0 - index / 100)
        for index, row in enumerate(materialized)
    ]


QUESTION = "What does the source state about reachability tables between neighbours?"


def test_a_single_chunk_release_never_reaches_the_ambiguity_branch() -> None:
    """The confirmation-024 regime: one atom, so claim classes cannot conflict."""

    gate = SourceSemanticEvidenceAtomGateV3()

    decision = gate.assess(QUESTION, _hits([_chunk(cluster="dv", ordinal=1, text=CLAIM_A)]))

    assert decision.recommended_action != "clarify"


def test_a_multi_cluster_corpus_reaches_the_ambiguity_branch() -> None:
    """The product regime: co-retrieved clusters carry distinct claim classes."""

    gate = SourceSemanticEvidenceAtomGateV3()
    hits = _hits(
        [
            _chunk(cluster="dv", ordinal=1, text=CLAIM_A),
            _chunk(cluster="scheduling", ordinal=2, text=CLAIM_B),
        ]
    )

    decision = gate.assess(QUESTION, hits)

    assert decision.sufficient is False
    assert decision.recommended_action == "clarify"
    assert decision.features["canonical_claim_class_count"] > 1


def test_the_benchmark_question_form_carries_no_gate_anchor() -> None:
    """The sealed questions quote a title, which is not a scoping anchor.

    ``plan_public_source_ranges`` recognises ``source cluster "X"`` and a
    ``using source "X" in section "Y",`` prefix. The sealed package asks
    ``What does "X" state about Y?``, so neither anchor is populated and the
    gate cannot narrow the candidate set before checking claim classes.
    """

    from src.digital_twin.grounding.source_range_evidence import (
        plan_public_source_ranges,
    )

    plan = plan_public_source_ranges(
        'What does "Cryptographic primitives" state about range techniques defined?'
    )

    assert plan.cluster_anchor is None
    assert plan.source_path_anchor is None
