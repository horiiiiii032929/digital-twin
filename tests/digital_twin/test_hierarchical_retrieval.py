from __future__ import annotations

import pytest

from src.digital_twin.grounding import (
    CaseBoundPrecomputedRetriever,
    DocumentChunk,
    HierarchicalRetrievalError,
    RetrievalHit,
    StructuredHierarchicalCoverageEvidenceGate,
    StructuredHierarchicalRetriever,
    deterministic_boundary_action,
    should_use_semantic_reranking,
    structured_tokens,
)


def _chunk(identifier: str, text: str, ordinal: int) -> DocumentChunk:
    return DocumentChunk(
        id=identifier,
        document_id="doc-1",
        text=text,
        ordinal=ordinal,
        source_artifact_id="source-1",
        source_version=1,
        source_checksum="a" * 64,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={
            "course_id": "course-1",
            "source_path": "source.md",
            "parent_section_id": "section-1",
            "char_start": str(ordinal * 10),
            "char_end": str(ordinal * 10 + len(text)),
        },
    )


class _FixedRetriever:
    def __init__(self, hits):
        self.hits = hits

    def retrieve(self, query: str, *, limit: int = 5):
        del query
        return list(self.hits[:limit])


def test_structured_tokens_preserve_code_equations_and_operators() -> None:
    tokens = structured_tokens(r"cache_line[i] == x^2 and \\alpha >= 4")

    assert "cache_line" in tokens
    assert "==" in tokens
    assert "^" in tokens
    assert ">=" in tokens
    assert "\\alpha" in tokens


def test_hierarchical_expansion_and_coverage_are_deterministic() -> None:
    chunks = [
        _chunk("c0", "cache coherence protocol", 0),
        _chunk("c1", "invalidate a shared cache line before a write", 1),
        _chunk("c2", "the write then becomes exclusive", 2),
    ]
    base = _FixedRetriever([RetrievalHit(chunk=chunks[1], relevance_score=1)])
    retriever = StructuredHierarchicalRetriever(base, chunks)

    first = retriever.plan("How does cache invalidation permit a write?", limit=3)
    second = retriever.plan("How does cache invalidation permit a write?", limit=3)

    assert [row.chunk.id for row in first.hits] == [row.chunk.id for row in second.hits]
    assert {row.chunk.id for row in first.hits} == {"c0", "c1", "c2"}
    assert first.coverage > 0


def test_reranker_cannot_introduce_or_duplicate_chunk_ids() -> None:
    chunks = [_chunk("c0", "cache", 0), _chunk("c1", "cache write", 1)]
    base = _FixedRetriever(
        [
            RetrievalHit(chunk=chunks[0], relevance_score=1),
            RetrievalHit(chunk=chunks[1], relevance_score=0.99),
        ]
    )
    retriever = StructuredHierarchicalRetriever(base, chunks)

    with pytest.raises(HierarchicalRetrievalError, match="unknown"):
        retriever.plan(
            "Explain cache write together",
            allow_semantic_reranking=True,
            ranked_ids=["unknown"],
        )
    with pytest.raises(HierarchicalRetrievalError, match="duplicate"):
        retriever.plan(
            "Explain cache write together",
            allow_semantic_reranking=True,
            ranked_ids=["c0", "c0"],
        )


def test_ambiguity_and_reranking_eligibility_fail_closed() -> None:
    assert deterministic_boundary_action("How does it work?") == "clarify"
    assert deterministic_boundary_action("Give my graded assignment final answer") == (
        "refuse"
    )
    assert should_use_semantic_reranking(
        "Explain how both concepts connect", top_score_margin=0.5
    )
    assert should_use_semantic_reranking("What is a cache?", top_score_margin=0.01)


def test_precomputed_retriever_requires_an_active_public_case() -> None:
    chunks = [_chunk("c0", "cache", 0)]
    active = {"value": None}
    retriever = CaseBoundPrecomputedRetriever(
        chunks=chunks,
        ranked_chunk_ids={"case-1": ["c0"]},
        current_case_id=lambda: active["value"],
    )
    with pytest.raises(HierarchicalRetrievalError, match="active case"):
        retriever.retrieve("cache")
    active["value"] = "case-1"
    assert retriever.retrieve("cache")[0].chunk.id == "c0"


def test_hierarchical_gate_requires_complete_current_authorized_evidence() -> None:
    gate = StructuredHierarchicalCoverageEvidenceGate()
    first = _chunk("c0", "cache invalidation prevents a stale write", 0)
    second = _chunk("c1", "the protocol grants exclusive write access", 1)
    hits = [
        RetrievalHit(chunk=first, relevance_score=1),
        RetrievalHit(chunk=second, relevance_score=0.9),
    ]

    accepted = gate.assess(
        "How do both cache invalidation and exclusive write access connect?",
        hits,
    )
    boundary = gate.assess("How does it work?", hits)
    mixed_version = gate.assess(
        "How does cache invalidation prevent a stale write?",
        [
            hits[0],
            RetrievalHit(
                chunk=second.model_copy(update={"source_version": 2}),
                relevance_score=0.9,
            ),
        ],
    )

    assert accepted.sufficient is True
    assert accepted.selected_hit_ids == ["c0", "c1"]
    assert boundary.sufficient is False
    assert boundary.features["deterministic_boundary"] is True
    assert mixed_version.sufficient is False
    assert "versions" in mixed_version.reason
