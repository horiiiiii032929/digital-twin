from pathlib import Path

import pytest

from scripts.synthetic_course_corpus import build_retrieval_evaluation_chunks
from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    EmptyQueryError,
    InvalidRetrievalLimitError,
    RelevantChunkReference,
    RetrievalFailureCause,
    TermOverlapRetriever,
    evaluate_retriever,
    load_retrieval_evaluation_set,
)


def chunk(
    identifier: str,
    text: str,
    *,
    source: str | None = None,
    version: int = 1,
    allowed: bool = True,
    ordinal: int = 0,
) -> DocumentChunk:
    source_id = source or identifier
    return DocumentChunk(
        id=identifier,
        document_id=f"document-{source_id}-{version}",
        text=text,
        ordinal=ordinal,
        source_artifact_id=source_id,
        source_version=version,
        locator=f"section {ordinal + 1}",
        retrieval_allowed=allowed,
        metadata={"title": source_id},
    )


def test_retrievers_reject_invalid_inputs_and_return_explicit_no_match():
    chunks = [chunk("chunk-1", "cache coherence and memory latency")]

    for retriever in (TermOverlapRetriever(chunks), BM25Retriever(chunks)):
        with pytest.raises(EmptyQueryError, match="lexical token"):
            retriever.retrieve("---")
        with pytest.raises(InvalidRetrievalLimitError, match="at least 1"):
            retriever.retrieve("cache", limit=0)
        assert retriever.retrieve("photosynthesis") == []


def test_retrieval_filters_permissions_and_superseded_source_versions():
    chunks = [
        chunk("old", "superseded cache explanation", source="lecture", version=1),
        chunk("new", "current cache explanation", source="lecture", version=2),
        chunk("blocked", "private cache answer", source="private", allowed=False),
    ]

    hits = BM25Retriever(chunks).retrieve("cache explanation")

    assert [hit.chunk.id for hit in hits] == ["new"]
    explicitly_old = TermOverlapRetriever(
        chunks,
        active_source_versions={"lecture": 1},
    ).retrieve("cache")
    assert [hit.chunk.id for hit in explicitly_old] == ["old"]


def test_bm25_uses_term_rarity_to_break_overlap_baseline_tie():
    chunks = [
        chunk("cache-a", "cache lookup", source="a-cache"),
        chunk("latency", "latency measurement", source="b-latency"),
        chunk("cache-c", "cache policy", source="c-cache"),
    ]
    query = "cache latency"

    overlap = TermOverlapRetriever(chunks).retrieve(query)
    bm25 = BM25Retriever(chunks).retrieve(query)

    assert overlap[0].chunk.id == "cache-a"
    assert bm25[0].chunk.id == "latency"
    assert bm25[0].relevance_score == 1


def test_bm25_ranking_is_deterministic_and_exposes_source_evidence():
    chunks = [
        chunk("second", "cache mapping", source="source-b", ordinal=1),
        chunk("first", "cache mapping", source="source-a", ordinal=0),
    ]

    first = BM25Retriever(chunks).retrieve("cache")
    second = BM25Retriever(list(reversed(chunks))).retrieve("cache")

    assert [hit.chunk.id for hit in first] == ["first", "second"]
    assert first == second
    assert first[0].chunk.source_artifact_id == "source-a"
    assert first[0].chunk.locator == "section 1"


def test_versioned_evaluation_set_reports_metrics_and_failure_causes(
    tmp_path: Path,
):
    evaluation_path = (
        Path(__file__).resolve().parents[2]
        / "research"
        / "05_evaluation"
        / "retrieval_v1.json"
    )
    evaluation_set = load_retrieval_evaluation_set(evaluation_path)
    chunks = build_retrieval_evaluation_chunks(tmp_path)
    overlap = evaluate_retriever(
        "term-overlap",
        TermOverlapRetriever(chunks),
        chunks,
        evaluation_set,
    )
    bm25 = evaluate_retriever(
        "bm25",
        BM25Retriever(chunks),
        chunks,
        evaluation_set,
    )

    assert overlap.case_count == 25
    assert overlap.evidence_case_count == 20
    assert overlap.no_evidence_case_count == 5
    assert overlap.recall_at_5 == 1
    assert overlap.mean_reciprocal_rank == 0.975
    assert bm25.recall_at_5 == 1
    assert bm25.mean_reciprocal_rank == 1
    assert bm25.recall_at_1 > overlap.recall_at_1
    assert overlap.no_evidence_accuracy == bm25.no_evidence_accuracy == 1
    assert overlap.failures_by_cause == bm25.failures_by_cause == {}
    assert all(
        hit.source_artifact_id and hit.locator
        for result in bm25.cases
        for hit in result.hits
    )


def test_evaluator_distinguishes_source_chunking_query_and_ranking_failures():
    evaluation_path = (
        Path(__file__).resolve().parents[2]
        / "research"
        / "05_evaluation"
        / "retrieval_v1.json"
    )
    evaluation_set = load_retrieval_evaluation_set(evaluation_path)
    template = evaluation_set.cases[0]

    def failure_for(query, relevant, chunks):
        case = template.model_copy(update={"query": query, "relevant": relevant})
        reduced_set = evaluation_set.model_copy(update={"cases": [case]})
        summary = evaluate_retriever(
            "term-overlap",
            TermOverlapRetriever(chunks),
            chunks,
            reduced_set,
        )
        return summary.cases[0].failure_cause

    existing = chunk("existing", "cache relevant phrase", source="source-z")
    assert (
        failure_for(
            "cache",
            [
                RelevantChunkReference(
                    source_artifact_id="missing-source",
                    text_contains="relevant phrase",
                )
            ],
            [existing],
        )
        == RetrievalFailureCause.SOURCE
    )
    assert (
        failure_for(
            "cache",
            [
                RelevantChunkReference(
                    source_artifact_id="source-z",
                    text_contains="missing passage",
                )
            ],
            [existing],
        )
        == RetrievalFailureCause.CHUNKING
    )
    assert (
        failure_for(
            "photosynthesis",
            [
                RelevantChunkReference(
                    source_artifact_id="source-z",
                    text_contains="relevant phrase",
                )
            ],
            [existing],
        )
        == RetrievalFailureCause.QUERY
    )

    distractors = [
        chunk(f"distractor-{index}", "cache", source=f"source-{index}")
        for index in range(5)
    ]
    assert (
        failure_for(
            "cache",
            [
                RelevantChunkReference(
                    source_artifact_id="source-z",
                    text_contains="relevant phrase",
                )
            ],
            [*distractors, existing],
        )
        == RetrievalFailureCause.RANKING
    )
