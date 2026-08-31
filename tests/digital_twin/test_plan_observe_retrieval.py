from __future__ import annotations

import pytest

from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    PlanObserveRetrieverV1,
    decompose_evidence_queries,
)
from src.digital_twin.grounding.retrieval import InvalidRetrievalLimitError


def _chunk(identifier: str, text: str, ordinal: int) -> DocumentChunk:
    return DocumentChunk(
        id=identifier,
        document_id="course:source",
        text=text,
        ordinal=ordinal,
        source_artifact_id="course:source",
        source_version=1,
        source_checksum="a" * 64,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={"source_path": "source.txt"},
    )


def test_decomposition_is_bounded_and_stable() -> None:
    question = "Which two statements connect congestion control with flow control?"

    assert decompose_evidence_queries(question) == (
        question,
        "congestion control",
        "flow control",
    )


def test_simple_question_uses_one_observation_query() -> None:
    question = "What is congestion control?"
    assert decompose_evidence_queries(question) == (question,)


def test_plan_observe_fuses_distinct_subquery_evidence() -> None:
    chunks = [
        _chunk("congestion", "Congestion control protects the network.", 0),
        _chunk("flow", "Flow control protects the receiver.", 1),
        _chunk("noise", "A checksum detects corruption.", 2),
    ]
    retriever = PlanObserveRetrieverV1(BM25Retriever(chunks), observation_limit=5)

    hits = retriever.retrieve(
        "Which two statements connect congestion control with flow control?",
        limit=2,
    )

    assert {row.chunk.id for row in hits} == {"congestion", "flow"}
    assert retriever.last_trace is not None
    assert retriever.last_trace.queries == (
        "Which two statements connect congestion control with flow control?",
        "congestion control",
        "flow control",
    )


def test_unknown_or_duplicate_evidence_cannot_be_introduced() -> None:
    chunk = _chunk("only", "One approved fact.", 0)
    retriever = PlanObserveRetrieverV1(BM25Retriever([chunk]), observation_limit=5)

    hits = retriever.retrieve("What is the approved fact?", limit=5)

    assert [row.chunk.id for row in hits] == ["only"]


def test_invalid_limit_fails_closed() -> None:
    retriever = PlanObserveRetrieverV1(
        BM25Retriever([_chunk("only", "One approved fact.", 0)]),
        observation_limit=5,
    )
    with pytest.raises(InvalidRetrievalLimitError):
        retriever.retrieve("approved fact", limit=0)
