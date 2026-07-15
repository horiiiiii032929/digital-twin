"""Benchmark BM25, local dense retrieval, and reciprocal-rank fusion."""

import argparse
import json
import subprocess
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from services.embeddings import FastEmbedTextEmbedder
from src.digital_twin.grounding import (
    BM25Retriever,
    DenseRetriever,
    DocumentChunk,
    ReciprocalRankFusionRetriever,
    RelevanceThresholdRetriever,
    RetrievalEvaluationSet,
    RetrievalEvaluationSummary,
    Retriever,
    evaluate_retriever,
    load_retrieval_benchmark_corpus,
    load_retrieval_evaluation_set,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "research" / "05_evaluation" / "retrieval_corpus_v2.json"
DEFAULT_CALIBRATION = (
    ROOT / "research" / "05_evaluation" / "retrieval_v2_calibration.json"
)
DEFAULT_TEST = ROOT / "research" / "05_evaluation" / "retrieval_v2_test.json"
DEFAULT_CACHE = ROOT / "data" / "external" / "model_cache"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_THRESHOLDS = (0.65, 0.675, 0.7, 0.725, 0.75, 0.775, 0.8, 0.825, 0.85)
DEFAULT_BM25_THRESHOLDS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


def main() -> None:
    arguments = _arguments()
    corpus = load_retrieval_benchmark_corpus(arguments.corpus)
    calibration_set = load_retrieval_evaluation_set(arguments.calibration)
    test_set = load_retrieval_evaluation_set(arguments.dataset)
    _validate_versions(corpus.version, calibration_set, test_set)
    chunks = corpus.chunks

    bm25_threshold, bm25_calibration_results = _calibrate_bm25_threshold(
        chunks,
        calibration_set,
        arguments.bm25_thresholds,
    )
    bm25, bm25_build = _build_with_memory(
        lambda: BM25Retriever(
            chunks,
            k1=1.2,
            b=0.75,
            minimum_score=bm25_threshold,
        )
    )
    embedder, model_load = _build_with_memory(
        lambda: FastEmbedTextEmbedder(
            model_name=arguments.model,
            cache_dir=arguments.cache_dir,
            local_files_only=arguments.local_files_only,
        )
    )
    dense_index, dense_build = _build_with_memory(
        lambda: DenseRetriever(chunks, embedder)
    )

    dense_threshold, dense_calibration_results = _calibrate_dense_threshold(
        dense_index,
        chunks,
        calibration_set,
        arguments.thresholds,
    )
    dense = RelevanceThresholdRetriever(
        dense_index,
        minimum_relevance_score=dense_threshold,
        candidate_limit=len(chunks),
    )
    hybrid = ReciprocalRankFusionRetriever(
        [bm25, dense],
        rank_constant=60,
        candidate_limit=20,
    )
    summaries = [
        _evaluate_with_memory(
            f"bm25-v1-minimum-score-{bm25_threshold:.3f}",
            bm25,
            chunks,
            test_set,
        ),
        _evaluate_with_memory(
            f"dense-{arguments.model}-threshold-{dense_threshold:.3f}",
            dense,
            chunks,
            test_set,
        ),
        _evaluate_with_memory(
            f"hybrid-rrf60-bm25-{bm25_threshold:.3f}-dense-{dense_threshold:.3f}",
            hybrid,
            chunks,
            test_set,
        ),
    ]
    _check_dataset_integrity(summaries)

    payload = {
        "benchmark_version": "rag-retrieval-benchmark-v2",
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "corpus": {
            "path": _relative(arguments.corpus),
            "version": corpus.version,
            "chunk_count": len(chunks),
            "eligible_active_chunk_count": len(bm25.chunks),
            "source_count": len(
                {chunk.source_artifact_id or chunk.document_id for chunk in chunks}
            ),
            "synthetic_only": corpus.synthetic_only,
        },
        "calibration": {
            "path": _relative(arguments.calibration),
            "dataset_version": calibration_set.version,
            "case_count": len(calibration_set.cases),
            "bm25": {
                "candidate_raw_score_thresholds": list(arguments.bm25_thresholds),
                "selected_raw_score_threshold": bm25_threshold,
                "results": bm25_calibration_results,
            },
            "dense": {
                "candidate_relevance_thresholds": list(arguments.thresholds),
                "selected_relevance_threshold": dense_threshold,
                "selected_cosine_similarity_equivalent": 2 * dense_threshold - 1,
                "results": dense_calibration_results,
            },
            "selection_order": [
                "safety_violation_count == 0",
                "no_evidence_accuracy == 1",
                "maximum Recall@3",
                "maximum nDCG@3",
                "maximum MRR",
                "lowest threshold on a tie",
            ],
        },
        "test": {
            "path": _relative(arguments.dataset),
            "dataset_version": test_set.version,
            "case_count": len(test_set.cases),
            "result_limits": [1, 3, 5],
            "candidate_hard_gates": {
                summary.retriever: {
                    "permission_and_version_filter": summary.safety_violation_count
                    == 0,
                    "no_evidence_accuracy_required": summary.no_evidence_accuracy
                    == 1,
                    "eligible": summary.safety_violation_count == 0
                    and summary.no_evidence_accuracy == 1,
                }
                for summary in summaries
            },
            "results": [summary.model_dump(mode="json") for summary in summaries],
        },
        "configuration": {
            "bm25": {
                "k1": 1.2,
                "b": 0.75,
                "minimum_raw_score": bm25_threshold,
            },
            "dense": {
                "adapter": "fastembed-0.8.0",
                "model": arguments.model,
                "passage_query_encoders": True,
                "model_cache": _relative(arguments.cache_dir),
            },
            "hybrid": {"method": "reciprocal-rank-fusion", "rank_constant": 60},
        },
        "operations": {
            "bm25_index_build": bm25_build,
            "model_load": model_load,
            "dense_index_build": dense_build,
            "model_cache_bytes": _directory_size(arguments.cache_dir),
            "memory_note": "tracemalloc reports Python allocations, not ONNX native RSS",
            "paid_api_calls": 0,
        },
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is None:
        print(rendered)
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument(
        "--thresholds",
        type=_thresholds,
        default=DEFAULT_THRESHOLDS,
        help="comma-separated normalized relevance thresholds",
    )
    parser.add_argument(
        "--bm25-thresholds",
        type=_nonnegative_thresholds,
        default=DEFAULT_BM25_THRESHOLDS,
        help="comma-separated raw BM25 score thresholds",
    )
    return parser.parse_args()


def _thresholds(value: str) -> tuple[float, ...]:
    thresholds = tuple(float(item) for item in value.split(","))
    if not thresholds or any(not 0 <= item <= 1 for item in thresholds):
        raise argparse.ArgumentTypeError("thresholds must be numbers between 0 and 1")
    return thresholds


def _nonnegative_thresholds(value: str) -> tuple[float, ...]:
    thresholds = tuple(float(item) for item in value.split(","))
    if not thresholds or any(item < 0 for item in thresholds):
        raise argparse.ArgumentTypeError("thresholds must be nonnegative numbers")
    return thresholds


def _calibrate_dense_threshold(
    dense_index: DenseRetriever,
    chunks: list[DocumentChunk],
    evaluation_set: RetrievalEvaluationSet,
    thresholds: tuple[float, ...],
) -> tuple[float, list[dict[str, float | int | bool]]]:
    candidates: list[
        tuple[float, RetrievalEvaluationSummary, dict[str, float | int | bool]]
    ] = []
    for threshold in thresholds:
        retriever = RelevanceThresholdRetriever(
            dense_index,
            minimum_relevance_score=threshold,
            candidate_limit=len(chunks),
        )
        summary = evaluate_retriever(
            f"dense-calibration-{threshold:.3f}",
            retriever,
            chunks,
            evaluation_set,
        )
        eligible = (
            summary.safety_violation_count == 0
            and summary.no_evidence_accuracy == 1
        )
        row: dict[str, float | int | bool] = {
            "threshold": threshold,
            "eligible": eligible,
            "recall_at_3": summary.recall_at_3,
            "ndcg_at_3": summary.ndcg_at_3,
            "mean_reciprocal_rank": summary.mean_reciprocal_rank,
            "no_evidence_accuracy": summary.no_evidence_accuracy,
            "safety_violation_count": summary.safety_violation_count,
        }
        candidates.append((threshold, summary, row))

    eligible_candidates = [candidate for candidate in candidates if candidate[2]["eligible"]]
    if not eligible_candidates:
        raise SystemExit("no dense threshold passed calibration hard gates")
    selected = max(
        eligible_candidates,
        key=lambda candidate: (
            candidate[1].recall_at_3,
            candidate[1].ndcg_at_3,
            candidate[1].mean_reciprocal_rank,
            -candidate[0],
        ),
    )
    return selected[0], [candidate[2] for candidate in candidates]


def _calibrate_bm25_threshold(
    chunks: list[DocumentChunk],
    evaluation_set: RetrievalEvaluationSet,
    thresholds: tuple[float, ...],
) -> tuple[float, list[dict[str, float | int | bool]]]:
    candidates: list[
        tuple[float, RetrievalEvaluationSummary, dict[str, float | int | bool]]
    ] = []
    for threshold in thresholds:
        retriever = BM25Retriever(
            chunks,
            k1=1.2,
            b=0.75,
            minimum_score=threshold,
        )
        summary = evaluate_retriever(
            f"bm25-calibration-{threshold:.3f}",
            retriever,
            chunks,
            evaluation_set,
        )
        eligible = (
            summary.safety_violation_count == 0
            and summary.no_evidence_accuracy == 1
        )
        row: dict[str, float | int | bool] = {
            "threshold": threshold,
            "eligible": eligible,
            "recall_at_3": summary.recall_at_3,
            "ndcg_at_3": summary.ndcg_at_3,
            "mean_reciprocal_rank": summary.mean_reciprocal_rank,
            "no_evidence_accuracy": summary.no_evidence_accuracy,
            "safety_violation_count": summary.safety_violation_count,
        }
        candidates.append((threshold, summary, row))
    eligible_candidates = [candidate for candidate in candidates if candidate[2]["eligible"]]
    if not eligible_candidates:
        raise SystemExit("no BM25 threshold passed calibration hard gates")
    selected = max(
        eligible_candidates,
        key=lambda candidate: (
            candidate[1].recall_at_3,
            candidate[1].ndcg_at_3,
            candidate[1].mean_reciprocal_rank,
            -candidate[0],
        ),
    )
    return selected[0], [candidate[2] for candidate in candidates]


def _build_with_memory(factory: Callable[[], object]) -> tuple[object, dict[str, float | int]]:
    tracemalloc.start()
    started = time.perf_counter()
    value = factory()
    elapsed_ms = (time.perf_counter() - started) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return value, {"elapsed_ms": elapsed_ms, "python_peak_memory_bytes": peak}


def _evaluate_with_memory(
    name: str,
    retriever: Retriever,
    chunks: list[DocumentChunk],
    evaluation_set: RetrievalEvaluationSet,
) -> RetrievalEvaluationSummary:
    tracemalloc.start()
    summary = evaluate_retriever(name, retriever, chunks, evaluation_set)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return summary.model_copy(update={"peak_memory_bytes": peak})


def _check_dataset_integrity(summaries: list[RetrievalEvaluationSummary]) -> None:
    failures: list[str] = []
    for summary in summaries:
        if summary.failures_by_cause.get("source", 0):
            failures.append(f"{summary.retriever} has unresolved sources")
        if summary.failures_by_cause.get("chunking", 0):
            failures.append(f"{summary.retriever} has unresolved judgments")
    if failures:
        raise SystemExit("; ".join(failures))


def _validate_versions(
    corpus_version: str,
    *evaluation_sets: RetrievalEvaluationSet,
) -> None:
    mismatches = [
        evaluation_set.version
        for evaluation_set in evaluation_sets
        if evaluation_set.corpus_version != corpus_version
    ]
    if mismatches:
        raise SystemExit(f"corpus version mismatch: {', '.join(mismatches)}")


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


if __name__ == "__main__":
    main()
