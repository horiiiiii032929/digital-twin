import hashlib

import pytest

from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.retrieval import BM25Retriever
from src.digital_twin.grounding.semantic_target_resolution import (
    SemanticTargetEvidenceGateV3,
    SemanticTargetEvidenceRetrieverV3,
    resolve_semantic_targets,
)


CHECKSUM = hashlib.sha256(b"semantic-target-test").hexdigest()


def _chunk(
    identifier: str,
    text: str,
    *,
    title: str,
    cluster: str,
    ordinal: int,
    retrieval_allowed: bool = True,
) -> DocumentChunk:
    return DocumentChunk(
        id=identifier,
        document_id="course:notes.md",
        source_artifact_id="course:notes.md",
        source_version=1,
        source_checksum=CHECKSUM,
        source_label="course-approved",
        text=text,
        locator=f"notes.md:{ordinal}",
        ordinal=ordinal,
        retrieval_allowed=retrieval_allowed,
        display_allowed=True,
        metadata={
            "title": title,
            "parent_cluster_id": cluster,
            "course_id": "course",
            "source_path": "notes.md",
            "char_start": str(ordinal * 100),
            "char_end": str(ordinal * 100 + len(text)),
            "modality": "text",
            "search_description": f"Section: {title}",
        },
    )


def _hit(chunk: DocumentChunk, score: float = 1.0) -> RetrievalHit:
    return RetrievalHit(chunk=chunk, relevance_score=score, raw_score=score)


def test_exact_public_section_context_resolves_low_information_target():
    correct = _chunk(
        "correct",
        "A blocked process becomes runnable when the awaited event occurs.",
        title="Process states",
        cluster="process-states",
        ordinal=0,
    )
    distractor = _chunk(
        "distractor",
        "A blocked cache line becomes valid after a fill completes.",
        title="Cache states",
        cluster="cache-states",
        ordinal=1,
    )

    result = resolve_semantic_targets(
        'How does "Process states" explain blocked process runnable event?',
        [_hit(distractor), _hit(correct)],
    )

    assert result.action == "answer"
    assert result.selected_hit_ids == ("correct",)


def test_close_cross_cluster_candidates_require_clarification_without_context():
    first = _chunk(
        "first",
        "A cache stores recently accessed blocks to reduce access latency.",
        title="CPU cache",
        cluster="cpu-cache",
        ordinal=0,
    )
    second = _chunk(
        "second",
        "A cache stores recently accessed pages to reduce access latency.",
        title="Page cache",
        cluster="page-cache",
        ordinal=1,
    )

    result = resolve_semantic_targets(
        "How can the source point about cache access latency be restated?",
        [_hit(first), _hit(second)],
    )

    assert result.action == "clarify"
    assert result.selected_hit_ids == ()


def test_multi_evidence_resolves_two_distinct_ranges():
    scheduling = _chunk(
        "scheduling",
        "Round-robin scheduling rotates runnable processes after a time slice.",
        title="Scheduling",
        cluster="scheduling",
        ordinal=0,
    )
    context_switch = _chunk(
        "context-switch",
        "A context switch saves one process state before restoring another.",
        title="Scheduling",
        cluster="scheduling",
        ordinal=1,
    )
    unrelated = _chunk(
        "unrelated",
        "Virtual memory maps process addresses through page tables.",
        title="Virtual memory",
        cluster="virtual-memory",
        ordinal=2,
    )
    question = (
        'Which two statements in "Scheduling" connect round-robin time slice '
        "with context switch process state?"
    )

    result = resolve_semantic_targets(
        question,
        [_hit(unrelated), _hit(context_switch), _hit(scheduling)],
    )
    decision = SemanticTargetEvidenceGateV3().assess(
        question,
        [_hit(unrelated), _hit(context_switch), _hit(scheduling)],
    )

    assert result.action == "answer"
    assert set(result.selected_hit_ids) == {"scheduling", "context-switch"}
    assert len(result.selected_hit_ids) == 2
    assert decision.sufficient is True
    assert set(decision.selected_hit_ids) == {"scheduling", "context-switch"}


def test_retriever_expands_exact_public_context_and_places_selection_first():
    correct = _chunk(
        "correct",
        "A mutex enforces mutual exclusion around a critical section.",
        title="Mutex",
        cluster="mutex",
        ordinal=0,
    )
    unrelated = _chunk(
        "unrelated",
        "A process owns an independent virtual address space.",
        title="Processes",
        cluster="processes",
        ordinal=1,
    )
    base = BM25Retriever([unrelated, correct])
    retriever = SemanticTargetEvidenceRetrieverV3(base, [unrelated, correct])

    hits = retriever.retrieve('What fact does "Mutex" state about exclusion?', limit=2)

    assert hits[0].chunk.id == "correct"
    assert retriever.last_trace is not None
    assert retriever.last_trace.resolution.action == "answer"


def test_unauthorized_source_range_fails_closed():
    unauthorized = _chunk(
        "unauthorized",
        "A hidden answer should never be released.",
        title="Restricted",
        cluster="restricted",
        ordinal=0,
        retrieval_allowed=False,
    )

    result = resolve_semantic_targets(
        'What fact does "Restricted" state about hidden answer?',
        [_hit(unauthorized)],
    )

    assert result.action == "abstain"
    assert result.selected_hit_ids == ()
    with pytest.raises(ValueError, match="approved chunks"):
        SemanticTargetEvidenceRetrieverV3(
            BM25Retriever([unauthorized]),
            [unauthorized],
        )
