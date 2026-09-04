"""The V4 gate contests only the leaders that are genuinely tied.

V3 compares canonical claim classes across every atom that clears the target's
coverage threshold, but it only ever selects ``ranked[0]``. Because
``normalize_claim_class`` is the token set of the claim text, two distinct
regions almost always carry distinct classes, so on a product-scale corpus the
branch reduces to "two or more regions cleared the threshold" and fails closed
on nearly every answerable question.

V4 keeps the fail-closed behaviour for a real tie and resolves the target when
the leader strictly dominates. V3 stays byte-for-byte behaviourally unchanged
as recorded evidence; the tests below pin both.
"""

from __future__ import annotations

from typing import Sequence

import pytest

from src.digital_twin.grounding import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.semantic_evidence_atoms import (
    SourceSemanticEvidenceAtomGateV3,
    SourceSemanticEvidenceAtomGateV4,
    materialize_semantic_evidence_atoms,
)
from src.digital_twin.tutor_policy import SourceLabel


TARGET_CLAIM = (
    "Adaptive review protocol 517 records the approved evidence version before "
    "an interruption and resumes with one bounded review step."
)
# Shares the target wording, so it clears the same coverage threshold, but
# states something different. This is the near-duplicate that V3 trips on.
RIVAL_CLAIM = (
    "Adaptive review protocol 517 records the approved evidence version before "
    "an interruption and then discards the learner goal entirely."
)
# Clears the 0.5 coverage threshold at 0.667 but ranks strictly below the
# leader's 0.833. This is the region V3 lets veto an already-grounded answer.
MID_CLAIM = "The approved evidence version is recorded in the module audit log."
# Below the threshold at 0.167, so it never enters the contest at all.
WEAK_CLAIM = (
    "Interruption handling is discussed later in the operating systems module."
)
QUESTION = (
    "What does the source state about the approved evidence version recorded "
    "before an interruption?"
)


def _chunk(*, cluster: str, ordinal: int, text: str, title: str) -> DocumentChunk:
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
            "title": title,
            "course_id": "operating-systems",
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


def _dominant_leader() -> list[RetrievalHit]:
    """A strong target plus a weaker region that still clears the threshold."""

    return _hits(
        [
            _chunk(cluster="target", ordinal=1, text=TARGET_CLAIM, title="Adaptive review protocol 517"),
            _chunk(cluster="mid", ordinal=2, text=MID_CLAIM, title="Audit logging"),
        ]
    )


def _genuine_tie() -> list[RetrievalHit]:
    """Two regions that cover the target equally but disagree."""

    return _hits(
        [
            _chunk(cluster="target", ordinal=1, text=TARGET_CLAIM, title="Adaptive review protocol 517"),
            _chunk(cluster="rival", ordinal=2, text=RIVAL_CLAIM, title="Adaptive review protocol 517"),
        ]
    )


def test_v4_resolves_when_the_leader_strictly_dominates() -> None:
    decision = SourceSemanticEvidenceAtomGateV4().assess(QUESTION, _dominant_leader())

    assert decision.recommended_action != "clarify"
    assert decision.sufficient is True


def test_v4_still_fails_closed_on_a_genuine_tie() -> None:
    decision = SourceSemanticEvidenceAtomGateV4().assess(QUESTION, _genuine_tie())

    assert decision.sufficient is False
    assert decision.recommended_action == "clarify"
    assert decision.features["canonical_claim_class_count"] > 1


def test_v4_reports_how_many_leaders_it_contested() -> None:
    """A refused decision must show the contest was between tied leaders."""

    decision = SourceSemanticEvidenceAtomGateV4().assess(QUESTION, _genuine_tie())

    assert decision.features["contested_leader_count"] == 2


def test_v4_keeps_the_v3_abstain_path() -> None:
    """Nothing clearing the threshold must still abstain, not clarify."""

    unrelated = _hits(
        [_chunk(cluster="weak", ordinal=1, text=WEAK_CLAIM, title="Module overview")]
    )

    decision = SourceSemanticEvidenceAtomGateV4().assess(QUESTION, unrelated)

    assert decision.sufficient is False
    assert decision.recommended_action == "abstain"


def test_v4_declares_its_own_identity() -> None:
    gate = SourceSemanticEvidenceAtomGateV4()

    assert gate.implementation_id == "source-semantic-evidence-atom-gate-v4"
    assert gate.version == "v4"


@pytest.mark.parametrize(
    "hits_factory", [_dominant_leader, _genuine_tie], ids=["dominant", "tie"]
)
def test_v3_behaviour_is_unchanged(hits_factory) -> None:
    """V3 fails closed in both regimes; the refactor must not alter that."""

    decision = SourceSemanticEvidenceAtomGateV3().assess(QUESTION, hits_factory())

    assert decision.sufficient is False
    assert decision.recommended_action == "clarify"
