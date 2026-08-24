from __future__ import annotations

import pytest

from src.digital_twin.grounding import (
    CrossEncoderNliCompletenessVerifier,
    CrossEncoderSupportVerifier,
    DocumentChunk,
    InspectableFeatureSupportVerifier,
    NliProbabilities,
    RetrievalHit,
)


def hit(identifier: str, text: str) -> RetrievalHit:
    return RetrievalHit(
        chunk=DocumentChunk(
            id=identifier,
            document_id=f"document-{identifier}",
            text=text,
            ordinal=0,
            retrieval_allowed=True,
        ),
        relevance_score=1,
        raw_score=1,
    )


class StaticPairBackend:
    implementation_id = "static-pair-backend"
    version = "test-v1"

    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.calls: list[list[tuple[str, str]]] = []

    def score_pairs(self, pairs):
        self.calls.append(list(pairs))
        return self.scores


class StaticNliBackend:
    implementation_id = "static-nli-backend"
    version = "test-v1"

    def __init__(self, rows: list[NliProbabilities]) -> None:
        self.rows = rows
        self.calls: list[list[tuple[str, str]]] = []

    def score_pairs(self, pairs):
        self.calls.append(list(pairs))
        return self.rows


def test_inspectable_verifier_reports_only_existing_supporting_hits() -> None:
    verifier = InspectableFeatureSupportVerifier(supporting_hit_threshold=0.5)
    hits = [
        hit("support", "A password reset revokes every active session."),
        hit("noise", "Indexes improve some database access paths."),
    ]

    signals = verifier.verify("What does a password reset revoke?", hits)

    assert signals.supporting_hit_ids == ["support"]
    assert signals.direct_support == signals.completeness
    assert signals.contradiction == 0


def test_cross_encoder_verifier_keeps_model_scores_advisory() -> None:
    backend = StaticPairBackend([0.93, 0.15])
    verifier = CrossEncoderSupportVerifier(
        backend,
        supporting_hit_threshold=0.5,
    )
    hits = [
        hit("support", "A reset revokes all active sessions."),
        hit("noise", "A B-tree stores sorted keys."),
    ]

    signals = verifier.verify("What happens to sessions after a reset?", hits)

    assert signals.direct_support == 0.93
    assert signals.completeness == 0.93
    assert signals.supporting_hit_ids == ["support"]
    assert len(backend.calls) == 1


def test_nli_verifier_checks_only_pairs_of_supporting_evidence() -> None:
    support_backend = StaticPairBackend([0.92, 0.88, 0.1])
    nli_backend = StaticNliBackend(
        [NliProbabilities(contradiction=0.8, entailment=0.1, neutral=0.1)]
    )
    verifier = CrossEncoderNliCompletenessVerifier(
        CrossEncoderSupportVerifier(
            support_backend,
            supporting_hit_threshold=0.5,
        ),
        nli_backend,
    )
    hits = [
        hit("a", "The active policy allows one attempt."),
        hit("b", "The active policy allows two attempts."),
        hit("noise", "The course meets on Friday."),
    ]

    signals = verifier.verify("How many attempts does the policy allow?", hits)

    assert signals.supporting_hit_ids == ["a", "b"]
    assert signals.contradiction == 0.8
    assert nli_backend.calls == [[(hits[0].chunk.text, hits[1].chunk.text)]]


def test_backends_fail_closed_on_invalid_shapes_and_probabilities() -> None:
    verifier = CrossEncoderSupportVerifier(
        StaticPairBackend([0.9]),
        supporting_hit_threshold=0.5,
    )
    with pytest.raises(ValueError, match="wrong number"):
        verifier.verify("query", [hit("a", "one"), hit("b", "two")])

    with pytest.raises(ValueError, match="sum to one"):
        NliProbabilities(contradiction=0.4, entailment=0.4, neutral=0.4)
