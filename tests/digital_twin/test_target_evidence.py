from __future__ import annotations

from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    TargetAwareEvidenceRetrieverV1,
    TargetEvidenceGateV1,
    plan_public_evidence_targets,
)


def _chunk(
    identifier: str,
    text: str,
    *,
    ordinal: int,
    title: str = "Queue behavior",
    modality: str = "text",
) -> DocumentChunk:
    return DocumentChunk(
        id=identifier,
        document_id="course:notes.md",
        text=text,
        ordinal=ordinal,
        token_count=max(1, len(text.split())),
        source_artifact_id="course:notes.md",
        source_version=1,
        source_checksum="a" * 64,
        region_id=identifier,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={
            "course_id": "course",
            "title": title,
            "modality": modality,
            "char_start": str(ordinal * 100),
            "char_end": str(ordinal * 100 + len(text)),
            "search_description": f"Section: {title} Semantic anchors: {text}",
        },
    )


def test_planner_extracts_two_public_targets_and_cardinality() -> None:
    plan = plan_public_evidence_targets(
        'Which two statements in "Queue behavior" connect enqueue order with dequeue order?'
    )

    assert plan.context == "Queue behavior"
    assert plan.targets == ("enqueue order", "dequeue order")
    assert plan.requested_cardinality == 2
    assert plan.extraction_rule == "explicit-two-target-connection"


def test_planner_extracts_structured_modality_and_generic_target() -> None:
    plan = plan_public_evidence_targets(
        'What code detail in "Queue behavior" concerns the selected source detail?'
    )

    assert plan.targets == ("",)
    assert plan.modality == "structured-code"


def test_retriever_places_one_distinct_region_per_target_first() -> None:
    chunks = [
        _chunk("enqueue", "Enqueue preserves arrival order.", ordinal=0),
        _chunk("dequeue", "Dequeue removes the oldest item.", ordinal=1),
        _chunk("other", "A stack removes the newest item.", ordinal=2),
    ]
    retriever = TargetAwareEvidenceRetrieverV1(BM25Retriever(chunks), chunks)

    hits = retriever.retrieve(
        'Which two statements in "Queue behavior" connect enqueue order with dequeue order?',
        limit=3,
    )

    assert [row.chunk.id for row in hits[:2]] == ["enqueue", "dequeue"]
    assert retriever.last_trace is not None
    assert retriever.last_trace.selected_hit_ids == ("enqueue", "dequeue")


def test_gate_requires_every_distinct_target() -> None:
    chunks = [
        _chunk("enqueue", "Enqueue preserves arrival order.", ordinal=0),
        _chunk("dequeue", "Dequeue removes the oldest item.", ordinal=1),
    ]
    query = (
        'Which two statements in "Queue behavior" connect enqueue order with dequeue order?'
    )
    hits = TargetAwareEvidenceRetrieverV1(BM25Retriever(chunks), chunks).retrieve(
        query, limit=2
    )

    complete = TargetEvidenceGateV1().assess(query, hits)
    incomplete = TargetEvidenceGateV1().assess(query, hits[:1])

    assert complete.sufficient
    assert complete.selected_hit_ids == ["enqueue", "dequeue"]
    assert not incomplete.sufficient
    assert incomplete.selected_hit_ids == []


def test_generic_structured_target_requires_title_and_modality() -> None:
    chunks = [
        _chunk(
            "code",
            "queue.append(item)",
            ordinal=0,
            modality="structured-code",
        ),
        _chunk("text", "A queue stores items.", ordinal=1),
    ]
    query = 'What code detail in "Queue behavior" concerns the selected source detail?'
    hits = TargetAwareEvidenceRetrieverV1(
        BM25Retriever(chunks), chunks, metadata_ranking_enabled=True
    ).retrieve(query, limit=2)

    decision = TargetEvidenceGateV1().assess(query, hits)

    assert decision.sufficient
    assert decision.selected_hit_ids == ["code"]
