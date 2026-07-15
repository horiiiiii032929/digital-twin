"""Evaluate deterministic lexical retrieval over the synthetic course corpus."""

import argparse
import json
import subprocess
import tempfile
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from scripts.synthetic_course_corpus import build_retrieval_evaluation_chunks
from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    Retriever,
    RetrievalEvaluationSet,
    RetrievalEvaluationSummary,
    TermOverlapRetriever,
    evaluate_retriever,
    load_retrieval_evaluation_set,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "research" / "05_evaluation" / "retrieval_v1.json"


def main() -> None:
    arguments = _arguments()
    evaluation_set = load_retrieval_evaluation_set(arguments.dataset)

    with tempfile.TemporaryDirectory(prefix="digital-twin-retrieval-") as temp:
        chunks = build_retrieval_evaluation_chunks(Path(temp))
        retrievers = [
            ("term-overlap-v1", lambda: TermOverlapRetriever(chunks)),
            (
                "bm25-v1-k1-1.2-b-0.75",
                lambda: BM25Retriever(chunks, k1=1.2, b=0.75),
            ),
        ]
        summaries = [
            _evaluate_with_memory(
                name,
                retriever_factory,
                chunks,
                evaluation_set,
            )
            for name, retriever_factory in retrievers
        ]

    payload = {
        "dataset": str(arguments.dataset.relative_to(ROOT)),
        "dataset_version": evaluation_set.version,
        "corpus_version": evaluation_set.corpus_version,
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "configuration": {
            "tokenizer": "lowercase alphanumeric lexical tokens",
            "chunk_max_chars": 220,
            "chunk_overlap_chars": 60,
            "result_limit": 5,
            "bm25_k1": 1.2,
            "bm25_b": 0.75,
        },
        "corpus": {
            "source_count": len({chunk.source_artifact_id for chunk in chunks}),
            "chunk_count": len(chunks),
            "synthetic_only": True,
        },
        "results": [summary.model_dump(mode="json") for summary in summaries],
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is None:
        print(rendered)
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")

    _check_regressions(summaries)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _check_regressions(summaries: list[RetrievalEvaluationSummary]) -> None:
    failures: list[str] = []
    for summary in summaries:
        if summary.recall_at_5 < 0.8:
            failures.append(f"{summary.retriever} Recall@5 below 0.8")
        if summary.mean_reciprocal_rank < 0.6:
            failures.append(f"{summary.retriever} MRR below 0.6")
        if summary.no_evidence_accuracy < 1.0:
            failures.append(f"{summary.retriever} no-evidence accuracy below 1.0")
        if summary.mean_latency_ms >= 5.0:
            failures.append(f"{summary.retriever} mean latency reached 5 ms")
        if summary.peak_memory_bytes is None or summary.peak_memory_bytes >= 5_000_000:
            failures.append(f"{summary.retriever} peak memory reached 5 MB")
        if summary.failures_by_cause.get("source", 0):
            failures.append(f"{summary.retriever} has unresolved sources")
        if summary.failures_by_cause.get("chunking", 0):
            failures.append(f"{summary.retriever} has unresolved chunk judgments")
    if failures:
        raise SystemExit("; ".join(failures))


def _evaluate_with_memory(
    name: str,
    retriever_factory: Callable[[], Retriever],
    chunks: list[DocumentChunk],
    evaluation_set: RetrievalEvaluationSet,
) -> RetrievalEvaluationSummary:
    tracemalloc.start()
    retriever = retriever_factory()
    summary = evaluate_retriever(name, retriever, chunks, evaluation_set)
    _, peak_memory_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return summary.model_copy(update={"peak_memory_bytes": peak_memory_bytes})


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
