"""A strictly weaker candidate must not veto a target its leader dominates.

`analyze_public_reference_uniqueness` gives every candidate clearing the
coverage threshold an equal vote on whether a public reference is ambiguous.
There is no ranking, so one weaker passage carrying a different claim class
refuses a target whose leading passage dominates it outright.

Measured on 263 ambiguous targets at region granularity: 76 have a strictly
dominant leader, and in all 76 that leader is the region the gold cites. The
other 187 are genuine ties and stay refused -- gold sits inside the tied leader
set in 184 of them, but the best secondary tiebreaker picks a wrong region in
61, which would buy coverage with unsupported releases.

So the successor narrows the contest to the leaders that actually tie, and
changes nothing else. V1 keeps its behaviour.
"""

from __future__ import annotations

from src.digital_twin.grounding import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.ambiguity_safe_evidence import (
    AmbiguitySafeEvidenceGateV1,
    DominanceScopedAmbiguitySafeEvidenceGateV3,
)
from src.digital_twin.grounding import (
    QuestionTargetedAtomicEvidenceGate,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.grounding.reference_uniqueness import (
    analyze_public_reference_uniqueness,
)
from src.digital_twin.tutor_policy import SourceLabel


QUESTION = 'What does the source state about the approved evidence version recorded before an interruption?'

LEADER = (
    "The approved evidence version is recorded before an interruption and the "
    "learner goal version is recorded with it."
)
# Clears the coverage threshold, ranks strictly below the leader, and says
# something else. Under V1 this one passage refuses the whole target.
WEAKER = "The approved evidence version is stored in the module audit log."
# Ties the leader on coverage and disagrees. A genuine ambiguity.
RIVAL = (
    "The approved evidence version is recorded before an interruption and the "
    "learner goal version is discarded with it."
)


def _chunk(name: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        id=f"region-{name}",
        document_id="course:topic.rst",
        text=text,
        ordinal=0,
        source_artifact_id="course:topic.rst",
        source_version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        locator=f"topic.rst {name}",
        source_checksum="0" * 64,
        region_id=f"region-{name}",
        retrieval_allowed=True,
        display_allowed=True,
        metadata={
            "title": "Adaptive review",
            "course_id": "operating-systems",
            "char_start": "0",
            "char_end": str(len(text)),
            "source_path": "topic.rst",
            "parent_cluster_id": f"cluster-{name}",
            "modality": "text",
        },
    )


def _hits(*chunks: DocumentChunk) -> list[RetrievalHit]:
    return [RetrievalHit(chunk=row, relevance_score=1.0) for row in chunks]


def _base():
    """The base gate the product actually stacks underneath."""

    return QuestionTargetedAtomicEvidenceGate(
        base_gate=StructuredLexicalCoverageEvidenceGate(
            minimum_content_matching_terms=2, evidence_limit=5
        )
    )


DOMINATED = (_chunk("leader", LEADER), _chunk("weaker", WEAKER))
TIED = (_chunk("leader", LEADER), _chunk("rival", RIVAL))


def test_v1_refuses_when_a_weaker_candidate_disagrees() -> None:
    """The behaviour being corrected, pinned so the successor is comparable."""

    decision = AmbiguitySafeEvidenceGateV1(_base(), evidence_limit=5).assess(QUESTION, _hits(*DOMINATED))

    assert decision.sufficient is False
    assert "ambiguous" in decision.reason


def test_successor_resolves_when_the_leader_dominates() -> None:
    decision = DominanceScopedAmbiguitySafeEvidenceGateV3(_base(), evidence_limit=5).assess(
        QUESTION, _hits(*DOMINATED)
    )

    assert decision.sufficient is True


def test_successor_still_refuses_a_genuine_tie() -> None:
    """The safety property: equal coverage plus disagreement stays closed."""

    decision = DominanceScopedAmbiguitySafeEvidenceGateV3(_base(), evidence_limit=5).assess(
        QUESTION, _hits(*TIED)
    )

    assert decision.sufficient is False
    assert "ambiguous" in decision.reason


def test_v1_also_refuses_the_genuine_tie() -> None:
    """Both gates agree wherever the tie is real; only the veto case differs."""

    decision = AmbiguitySafeEvidenceGateV1(_base(), evidence_limit=5).assess(QUESTION, _hits(*TIED))

    assert decision.sufficient is False


def test_the_analyzer_can_scope_the_contest_without_changing_its_default() -> None:
    """The shared analyzer keeps its behaviour unless dominance scoping is asked for."""

    default = analyze_public_reference_uniqueness(
        QUESTION, [row.chunk for row in _hits(*DOMINATED)]
    )
    scoped = analyze_public_reference_uniqueness(
        QUESTION,
        [row.chunk for row in _hits(*DOMINATED)],
        dominance_scoped=True,
    )

    assert default.status == "ambiguous"
    assert scoped.status != "ambiguous"


def test_the_successor_declares_its_own_identity() -> None:
    gate = DominanceScopedAmbiguitySafeEvidenceGateV3(_base(), evidence_limit=5)

    assert gate.implementation_id == "dominance-scoped-ambiguity-safe-v3"
    assert AmbiguitySafeEvidenceGateV1(_base(), evidence_limit=5).implementation_id != gate.implementation_id
