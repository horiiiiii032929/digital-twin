from pathlib import Path

import pytest

from scripts.synthetic_course_corpus import build_retrieval_evaluation_chunks
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    BM25Retriever,
    DenseRetriever,
    DocumentChunk,
    EmptyQueryError,
    EvidenceGatedRetriever,
    InvalidRetrievalLimitError,
    LexicalCoverageEvidenceGate,
    MinimumRawScoreEvidenceGate,
    RelevantChunkReference,
    RetrievalFailureCause,
    SecondaryRetrieverAgreementGate,
    ReciprocalRankFusionRetriever,
    TermOverlapRetriever,
    evaluate_evidence_sufficiency,
    evaluate_retriever,
    load_retrieval_benchmark_corpus,
    load_retrieval_evaluation_set,
)


class KeywordEmbedder:
    """Small deterministic vector fixture; not a semantic-model substitute."""

    dimensions = ("credentials", "browser", "assignment")

    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def embed_query(self, text):
        return self._embed(text)

    def _embed(self, text):
        lowered = text.lower()
        aliases = {
            "credentials": ("credentials", "password", "logged-in"),
            "browser": ("browser", "cookie", "session"),
            "assignment": ("assignment", "graded", "submission"),
        }
        return [
            float(sum(term in lowered for term in aliases[dimension]))
            for dimension in self.dimensions
        ]


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


def test_bm25_can_suppress_weak_raw_scores_after_calibration():
    chunks = [chunk("policy", "course policy applies")]

    assert BM25Retriever(chunks).retrieve("monetary policy")
    assert BM25Retriever(chunks, minimum_score=2).retrieve("monetary policy") == []


def test_bm25_exposes_absolute_score_without_changing_normalized_ranking():
    chunks = [
        chunk("policy", "course policy applies"),
        chunk("other", "course schedule applies"),
    ]

    hits = BM25Retriever(chunks).retrieve("monetary policy")

    assert hits[0].relevance_score == 1
    assert hits[0].raw_score is not None
    assert hits[0].raw_score > 0


def test_evidence_gates_are_swappable_and_keep_the_control_explicit():
    chunks = [chunk("policy", "course policy applies to graded work")]
    retriever = BM25Retriever(chunks)

    assert EvidenceGatedRetriever(
        retriever,
        AnyHitEvidenceGate(),
    ).retrieve("monetary policy")
    assert EvidenceGatedRetriever(
        retriever,
        MinimumRawScoreEvidenceGate(minimum_raw_score=10),
    ).retrieve("monetary policy") == []

    lexical_gate = LexicalCoverageEvidenceGate(
        minimum_query_coverage=0.5,
        minimum_matching_terms=2,
    )
    gated = EvidenceGatedRetriever(retriever, lexical_gate)
    assert gated.retrieve("monetary policy") == []
    assert gated.retrieve("course policy for graded work")


def test_evidence_gate_configuration_rejects_invalid_thresholds():
    with pytest.raises(ValueError, match="between 0 and 1"):
        LexicalCoverageEvidenceGate(
            minimum_query_coverage=1.1,
            minimum_matching_terms=1,
        )
    with pytest.raises(ValueError, match="at least 1"):
        LexicalCoverageEvidenceGate(
            minimum_query_coverage=0.5,
            minimum_matching_terms=0,
        )
    with pytest.raises(ValueError, match="negative"):
        MinimumRawScoreEvidenceGate(-0.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        SecondaryRetrieverAgreementGate(
            BM25Retriever([]),
            minimum_relevance_score=1.1,
        )


def test_secondary_retriever_gate_can_require_source_level_agreement():
    chunks = [
        chunk("session", "browser session cookie", source="sessions"),
        chunk("policy", "course policy graded work", source="policy"),
    ]
    primary = BM25Retriever(chunks)
    secondary = DenseRetriever(chunks, KeywordEmbedder(), minimum_similarity=0.5)
    gate = SecondaryRetrieverAgreementGate(
        secondary,
        minimum_relevance_score=0.75,
        require_source_overlap=True,
    )

    assert EvidenceGatedRetriever(primary, gate).retrieve("logged-in browser")
    assert EvidenceGatedRetriever(primary, gate).retrieve("monetary policy") == []


def test_evidence_sufficiency_evaluator_keeps_abstention_and_ranking_visible(
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

    summary = evaluate_evidence_sufficiency(
        "any-hit-control",
        BM25Retriever(chunks),
        AnyHitEvidenceGate(),
        chunks,
        evaluation_set,
    )

    assert summary.answerable_recall == 1
    assert summary.no_evidence_accuracy == 1
    assert summary.balanced_accuracy == 1
    assert summary.false_answer_count == 0
    assert summary.false_abstention_count == 0
    assert summary.conditional_recall_at_3 == summary.unconditional_recall_at_3
    assert summary.answerability_by_category["no-evidence"]["accuracy"] == 1


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


def test_dense_retriever_uses_injected_embeddings_and_similarity_threshold():
    chunks = [
        chunk("credential", "Resetting a password revokes authentication tokens"),
        chunk("browser", "A cookie maintains browser session state"),
    ]
    retriever = DenseRetriever(chunks, KeywordEmbedder(), minimum_similarity=0.5)

    hits = retriever.retrieve("What happens to logged-in devices?")

    assert [hit.chunk.id for hit in hits] == ["credential"]
    assert retriever.retrieve("unrelated astronomy") == []


def test_reciprocal_rank_fusion_combines_ranks_and_preserves_no_match():
    chunks = [
        chunk("a", "browser authentication token"),
        chunk("b", "password credentials"),
        chunk("c", "graded assignment submission"),
    ]
    lexical = BM25Retriever(chunks)
    dense = DenseRetriever(chunks, KeywordEmbedder(), minimum_similarity=0.5)
    hybrid = ReciprocalRankFusionRetriever(
        [lexical, dense], rank_constant=60, candidate_limit=3
    )

    assert hybrid.retrieve("password for logged-in browser")[0].chunk.id in {"a", "b"}
    assert hybrid.retrieve("unrelated astronomy") == []


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
    assert bm25.recall_at_3 > 0.95
    assert bm25.ndcg_at_3 > 0.95
    assert bm25.mean_reciprocal_rank == 1
    assert bm25.recall_at_1 > overlap.recall_at_1
    assert overlap.no_evidence_accuracy == bm25.no_evidence_accuracy == 1
    assert overlap.failures_by_cause == bm25.failures_by_cause == {}
    assert overlap.safety_violation_count == bm25.safety_violation_count == 0
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


def test_v2_benchmark_data_is_synthetic_resolvable_and_materially_larger():
    root = Path(__file__).resolve().parents[2]
    corpus = load_retrieval_benchmark_corpus(
        root / "research" / "05_evaluation" / "retrieval_corpus_v2.json"
    )
    calibration = load_retrieval_evaluation_set(
        root / "research" / "05_evaluation" / "retrieval_v2_calibration.json"
    )
    test = load_retrieval_evaluation_set(
        root / "research" / "05_evaluation" / "retrieval_v2_test.json"
    )

    assert corpus.synthetic_only is True
    assert len(corpus.chunks) == 40
    assert len(calibration.cases) == 20
    assert len(test.cases) == 40
    for evaluation_set in (calibration, test):
        summary = evaluate_retriever(
            "data-validation",
            BM25Retriever(corpus.chunks),
            corpus.chunks,
            evaluation_set,
        )
        assert summary.failures_by_cause.get("source", 0) == 0
        assert summary.failures_by_cause.get("chunking", 0) == 0
