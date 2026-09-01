from __future__ import annotations

from src.digital_twin.evaluation.factual_qa_scoring import (
    normalize_semantic_source_text,
)
from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    SourceRangeCandidateRetrieverV2,
    SourceRangeEvidenceGateV2,
    canonicalize_source_claim,
    plan_public_source_ranges,
)


def _chunk(
    identifier: str,
    text: str,
    *,
    ordinal: int,
    title: str = "Queue behavior",
    modality: str = "text",
    cluster: str = "cluster-1",
) -> DocumentChunk:
    return DocumentChunk(
        id=identifier,
        document_id="course:notes.md",
        text=text,
        ordinal=ordinal,
        source_artifact_id="course:notes.md",
        source_version=1,
        source_checksum="a" * 64,
        region_id=identifier,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={
            "course_id": "course",
            "source_path": "notes.md",
            "title": title,
            "modality": modality,
            "parent_cluster_id": cluster,
            "char_start": str(ordinal * 100),
            "char_end": str(ordinal * 100 + len(text)),
            "search_description": f"Section: {title} Semantic anchors: {text}",
        },
    )


def test_semantic_source_normalizer_ignores_authoring_markup() -> None:
    source = (
        r"An #ArrayStack# uses an array #a#, called the \emph{backing array}. "
        r"\index{array stack}%"
    )
    canonical = "An ArrayStack uses an array a, called the backing array."

    assert normalize_semantic_source_text(source) == normalize_semantic_source_text(
        canonical
    )


def test_claim_renderer_removes_non_visible_markup() -> None:
    rendered = canonicalize_source_claim(
        r"An #ArrayStack# uses \emph{backing storage}. \index{storage}%"
    )

    assert rendered == "An ArrayStack uses backing storage."


def test_source_range_plan_extracts_public_cluster_anchor() -> None:
    plan = plan_public_source_ranges(
        'How can the source point about enqueue be restated for source cluster "cluster-2"?'
    )

    assert plan.cluster_anchor == "cluster-2"
    assert plan.evidence.targets == ("enqueue",)


def test_source_range_plan_extracts_public_source_and_section_scope() -> None:
    plan = plan_public_source_ranges(
        'Using source "notes.md" in section "Queue behavior", '
        "how can the source point about enqueue be restated?"
    )

    assert plan.source_path_anchor == "notes.md"
    assert plan.evidence.context == "Queue behavior"
    assert plan.evidence.targets == ("enqueue",)


def test_explicit_source_section_is_target_for_broad_instructional_question() -> None:
    plan = plan_public_source_ranges(
        'Using source "notes.md" in section "Queue behavior", '
        "please explain this section with a grounded hint."
    )

    assert plan.source_path_anchor == "notes.md"
    assert plan.evidence.context == "Queue behavior"
    assert plan.evidence.targets == ("Queue behavior",)
    assert plan.evidence.extraction_rule == "explicit-source-section-scope"


def test_retriever_hard_scopes_exact_title_before_target_ranking() -> None:
    chunks = [
        _chunk("wrong", "Enqueue preserves order.", ordinal=0, title="Stack behavior"),
        _chunk("right", "Enqueue preserves arrival order.", ordinal=1),
        _chunk("other", "Dequeue removes the oldest item.", ordinal=2),
    ]
    retriever = SourceRangeCandidateRetrieverV2(BM25Retriever(chunks), chunks)

    hits = retriever.retrieve(
        'What fact does "Queue behavior" state about enqueue order?', limit=3
    )

    assert hits[0].chunk.id == "right"
    assert retriever.last_trace is not None
    assert retriever.last_trace.title_scope_applied


def test_gate_selects_distinct_specific_targets() -> None:
    chunks = [
        _chunk("enqueue", "Enqueue preserves arrival order.", ordinal=0),
        _chunk("dequeue", "Dequeue removes the oldest item.", ordinal=1),
        _chunk("other", "A queue stores items.", ordinal=2),
    ]
    query = (
        'Which two statements in "Queue behavior" connect enqueue order '
        "with dequeue oldest?"
    )
    hits = SourceRangeCandidateRetrieverV2(BM25Retriever(chunks), chunks).retrieve(
        query, limit=3
    )

    decision = SourceRangeEvidenceGateV2(clarify_ambiguous=True).assess(query, hits)

    assert decision.sufficient
    assert decision.selected_hit_ids == ["enqueue", "dequeue"]


def test_ambiguity_aware_gate_refuses_to_guess_generic_region() -> None:
    chunks = [
        _chunk("first", "A queue stores items.", ordinal=0),
        _chunk("second", "A queue preserves order.", ordinal=1),
    ]
    query = 'How does "Queue behavior" explain the selected source detail?'
    hits = SourceRangeCandidateRetrieverV2(BM25Retriever(chunks), chunks).retrieve(
        query, limit=2
    )

    strict = SourceRangeEvidenceGateV2(clarify_ambiguous=True).assess(query, hits)
    permissive = SourceRangeEvidenceGateV2(clarify_ambiguous=False).assess(query, hits)

    assert not strict.sufficient
    assert strict.reason == "public target is ambiguous across source regions"
    assert permissive.sufficient
    assert permissive.selected_hit_ids == ["first"]
