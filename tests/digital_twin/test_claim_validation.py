from __future__ import annotations

import pytest

from src.digital_twin.generation import (
    CitationValidationError,
    EvidenceBinding,
    ModelTutorOutputV2,
    resolve_atomic_claim_lineage,
)
from src.digital_twin.grounding import (
    AtomicAnswerClaim,
    AtomicClaimEvidenceValidator,
    ContiguousQuoteAtomicClaimVerifier,
    ExactQuoteAtomicClaimVerifier,
    NliAtomicClaimVerifier,
    NliProbabilities,
)
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit


def hit(identifier: str, text: str, *, allowed: bool = True) -> RetrievalHit:
    return RetrievalHit(
        chunk=DocumentChunk(
            id=identifier,
            document_id=f"document-{identifier}",
            text=text,
            ordinal=0,
            retrieval_allowed=allowed,
        ),
        relevance_score=1,
        raw_score=1,
    )


def claim(
    identifier: str,
    text: str,
    *evidence_hit_ids: str,
) -> AtomicAnswerClaim:
    return AtomicAnswerClaim(
        claim_id=identifier,
        text=text,
        evidence_hit_ids=list(evidence_hit_ids),
    )


class StaticNliBackend:
    implementation_id = "static-nli-backend"
    version = "test-v1"

    def __init__(self, rows: list[NliProbabilities]) -> None:
        self.rows = rows
        self.calls: list[list[tuple[str, str]]] = []

    def score_pairs(self, pairs):
        self.calls.append(list(pairs))
        return self.rows


class FailingVerifier:
    implementation_id = "failing-verifier"
    version = "test-v1"

    def verify(self, claims, hits):
        del claims, hits
        raise RuntimeError("synthetic verifier failure")


def validator(verifier=None) -> AtomicClaimEvidenceValidator:
    return AtomicClaimEvidenceValidator(
        verifier or ExactQuoteAtomicClaimVerifier(),
        minimum_entailment=0.8,
        maximum_contradiction=0.2,
    )


def test_exact_quote_control_releases_only_fully_supported_claim_sets() -> None:
    hits = [
        hit("chunk-a", "A password reset revokes every active session."),
        hit("chunk-b", "A reset token expires after fifteen minutes."),
    ]
    decision = validator().validate(
        [
            claim(
                "claim-session",
                "A password reset revokes every active session.",
                "chunk-a",
            ),
            claim(
                "claim-token",
                "A reset token expires after fifteen minutes.",
                "chunk-b",
            ),
        ],
        hits,
    )

    assert decision.releasable is True
    assert decision.supported_claim_count == 2
    assert decision.unsupported_claim_ids == []


def test_contiguous_quote_control_rejects_normalized_or_cross_hit_matches() -> None:
    candidate = AtomicClaimEvidenceValidator(
        ContiguousQuoteAtomicClaimVerifier(),
        minimum_entailment=1.0,
        maximum_contradiction=0.0,
    )
    hits = [
        hit("chunk-a", "A reset token expires"),
        hit("chunk-b", "after fifteen minutes."),
    ]

    punctuation_drift = candidate.validate(
        [claim("claim-drift", "A reset token expires after fifteen minutes", "chunk-b")],
        hits,
    )
    cross_hit_join = candidate.validate(
        [
            claim(
                "claim-joined",
                "A reset token expires after fifteen minutes.",
                "chunk-a",
                "chunk-b",
            )
        ],
        hits,
    )

    assert punctuation_drift.releasable is False
    assert cross_hit_join.releasable is False


def test_one_unsupported_claim_rejects_the_whole_answer() -> None:
    decision = validator().validate(
        [
            claim(
                "claim-supported",
                "A password reset revokes every active session.",
                "chunk-a",
            ),
            claim(
                "claim-invented",
                "A password reset deletes the user account.",
                "chunk-a",
            ),
        ],
        [hit("chunk-a", "A password reset revokes every active session.")],
    )

    assert decision.releasable is False
    assert decision.supported_claim_count == 1
    assert decision.unsupported_claim_ids == ["claim-invented"]


def test_unknown_stale_or_ineligible_lineage_fails_before_semantic_review() -> None:
    unknown = validator().validate(
        [claim("claim-a", "Supported text.", "missing")],
        [hit("chunk-a", "Supported text.")],
    )
    ineligible = validator().validate(
        [claim("claim-a", "Supported text.", "chunk-a")],
        [hit("chunk-a", "Supported text.", allowed=False)],
    )

    assert unknown.releasable is False
    assert unknown.features["lineage_valid"] is False
    assert ineligible.releasable is False
    assert ineligible.features["lineage_valid"] is False


def test_nli_uses_evidence_as_premise_and_claim_as_hypothesis() -> None:
    backend = StaticNliBackend(
        [NliProbabilities(contradiction=0.03, entailment=0.92, neutral=0.05)]
    )
    candidate = validator(NliAtomicClaimVerifier(backend))
    evidence = hit("chunk-a", "Every password reset invalidates active sessions.")
    paraphrase = claim(
        "claim-session",
        "Existing sessions stop working after a password reset.",
        "chunk-a",
    )

    decision = candidate.validate([paraphrase], [evidence])

    assert decision.releasable is True
    assert backend.calls == [[(evidence.chunk.text, paraphrase.text)]]


def test_contradiction_and_neutral_outputs_fail_closed() -> None:
    evidence = hit("chunk-a", "A reset token expires after fifteen minutes.")
    target = claim(
        "claim-token",
        "A reset token remains valid for one hour.",
        "chunk-a",
    )
    contradictory = validator(
        NliAtomicClaimVerifier(
            StaticNliBackend(
                [NliProbabilities(contradiction=0.91, entailment=0.03, neutral=0.06)]
            )
        )
    ).validate([target], [evidence])
    neutral = validator(
        NliAtomicClaimVerifier(
            StaticNliBackend(
                [NliProbabilities(contradiction=0.05, entailment=0.2, neutral=0.75)]
            )
        )
    ).validate([target], [evidence])

    assert contradictory.releasable is False
    assert neutral.releasable is False


def test_empty_duplicate_malformed_and_backend_failures_are_rejected() -> None:
    evidence = [hit("chunk-a", "Supported text.")]
    empty = validator().validate([], evidence)
    duplicate = validator().validate(
        [
            claim("claim-a", "Supported text.", "chunk-a"),
            claim("claim-a", "Supported text.", "chunk-a"),
        ],
        evidence,
    )
    failed = validator(FailingVerifier()).validate(
        [claim("claim-a", "Supported text.", "chunk-a")],
        evidence,
    )

    assert empty.releasable is False
    assert duplicate.releasable is False
    assert failed.releasable is False
    assert failed.features["verifier_error"] is True


def test_claim_output_resolves_short_ids_to_server_owned_hit_ids() -> None:
    evidence_hit = hit("chunk-a", "Supported text.")
    output = ModelTutorOutputV2.model_validate(
        {
            "claims": [
                {
                    "claim_id": "claim-a",
                    "text": "Supported text.",
                    "citation_ids": ["S1"],
                }
            ]
        }
    )

    claims = resolve_atomic_claim_lineage(
        output,
        [EvidenceBinding(citation_id="S1", hit=evidence_hit)],
    )

    assert claims == [
        AtomicAnswerClaim(
            claim_id="claim-a",
            text="Supported text.",
            evidence_hit_ids=["chunk-a"],
        )
    ]


def test_claim_output_cannot_escape_presented_or_eligible_evidence() -> None:
    output = ModelTutorOutputV2.model_validate(
        {
            "claims": [
                {
                    "claim_id": "claim-a",
                    "text": "Supported text.",
                    "citation_ids": ["S2"],
                }
            ]
        }
    )
    with pytest.raises(CitationValidationError, match="does not map"):
        resolve_atomic_claim_lineage(
            output,
            [EvidenceBinding(citation_id="S1", hit=hit("chunk-a", "Supported text."))],
        )

    ineligible = ModelTutorOutputV2.model_validate(
        {
            "claims": [
                {
                    "claim_id": "claim-a",
                    "text": "Supported text.",
                    "citation_ids": ["S1"],
                }
            ]
        }
    )
    with pytest.raises(CitationValidationError, match="ineligible"):
        resolve_atomic_claim_lineage(
            ineligible,
            [
                EvidenceBinding(
                    citation_id="S1",
                    hit=hit("chunk-a", "Supported text.", allowed=False),
                )
            ],
        )
