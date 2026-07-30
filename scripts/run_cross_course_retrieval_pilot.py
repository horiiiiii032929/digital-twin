#!/usr/bin/env python3
"""Run the private cross-course retrieval development pilot locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import resource
import subprocess
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.draft_cross_course_benchmark import ROOT, load_corpus, sha256_file
from services.embeddings import Qwen3TextEmbedder
from services.reranking import Qwen3Reranker
from src.digital_twin.grounding import (
    BM25Retriever,
    DenseRetriever,
    DocumentChunk,
    ReciprocalRankFusionRetriever,
    RerankingRetriever,
)


DATASET_PATH = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft_5.json"
)
OUTPUT_PATH = (
    ROOT
    / "experiments/runs/cross_course_retrieval_pilot_v1/"
    "development_result.json"
)
CHECKPOINT_PATH = OUTPUT_PATH.with_name("development_checkpoint.json")
EMBEDDING_REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
RERANKER_REVISION = "e61197ed45024b0ed8a2d74b80b4d909f1255473"
EMBEDDING_MODEL_PATH = (
    ROOT
    / "data/external/huggingface/hub/"
    "models--Qwen--Qwen3-Embedding-0.6B/snapshots"
    / EMBEDDING_REVISION
)
RERANKER_MODEL_PATH = (
    ROOT
    / "data/external/huggingface/hub/"
    "models--Qwen--Qwen3-Reranker-0.6B/snapshots"
    / RERANKER_REVISION
)
QUERY_INSTRUCTION = (
    "Given a student question within one authorized university course, "
    "retrieve passages that directly support a grounded answer."
)
METHODS = ("M0", "M1", "M2", "M3")
POSITIVE_SLICES = {"answerable", "cross_course_confusion"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path.home() / "Documents" / "academia_vault",
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument(
        "--limit-cases",
        type=int,
        help="smoke-test only; limited output must not be reported",
    )
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def synchronize() -> None:
    import torch

    if torch.backends.mps.is_available():
        torch.mps.synchronize()


def timed(operation: Any) -> tuple[Any, float]:
    synchronize()
    started = time.perf_counter()
    result = operation()
    synchronize()
    return result, (time.perf_counter() - started) * 1000


def build_runtime(
    chunks_by_course: dict[str, list[DocumentChunk]],
    *,
    batch_size: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, float], Qwen3Reranker]:
    require(EMBEDDING_MODEL_PATH.is_dir(), "local Qwen3 embedding model is missing")
    require(RERANKER_MODEL_PATH.is_dir(), "local Qwen3 reranker model is missing")
    embedder = Qwen3TextEmbedder(
        EMBEDDING_MODEL_PATH,
        instruction=QUERY_INSTRUCTION,
        device="mps",
        dtype="float16",
        batch_size=batch_size,
        max_length=2048,
    )
    runtimes: dict[str, dict[str, Any]] = {}
    index_seconds: dict[str, float] = {}
    for course_id in sorted(chunks_by_course):
        course_chunks = chunks_by_course[course_id]
        started = time.perf_counter()
        bm25 = BM25Retriever(course_chunks, k1=1.2, b=0.75)
        dense = DenseRetriever(
            course_chunks,
            embedder,
            minimum_similarity=-1.0,
        )
        hybrid = ReciprocalRankFusionRetriever(
            [bm25, dense],
            rank_constant=60,
            candidate_limit=20,
        )
        runtimes[course_id] = {
            "M0": bm25,
            "M1": dense,
            "M2": hybrid,
        }
        index_seconds[course_id] = time.perf_counter() - started
        print(
            f"index course={course_id} chunks={len(course_chunks)} complete=true",
            flush=True,
        )
    reranker = Qwen3Reranker(
        RERANKER_MODEL_PATH,
        instruction=QUERY_INSTRUCTION,
        device="mps",
        dtype="float16",
        batch_size=batch_size,
        max_length=2048,
    )
    for course_runtime in runtimes.values():
        course_runtime["M3"] = RerankingRetriever(
            course_runtime["M2"],
            reranker,
            candidate_limit=40,
        )
    model_seconds = {
        "embedding_model_load": embedder.model_load_seconds,
        "reranker_model_load": reranker.model_load_seconds,
        "embedding_index_build": sum(index_seconds.values()),
    }
    return runtimes, model_seconds, reranker


def score_ranking(
    gold_ids: list[str],
    ranked_ids: list[str],
) -> dict[str, float | bool | int]:
    gold = set(gold_ids)
    require(bool(gold), "positive case must contain gold evidence")
    gains = [1 if identifier in gold else 0 for identifier in ranked_ids[:10]]
    ideal = [1] * min(len(gold), 10)

    def dcg(values: list[int]) -> float:
        return sum(
            value / math.log2(rank + 2)
            for rank, value in enumerate(values)
        )

    first_rank = next(
        (
            rank
            for rank, identifier in enumerate(ranked_ids, start=1)
            if identifier in gold
        ),
        None,
    )
    result: dict[str, float | bool | int] = {
        "complete_evidence_at_3": gold.issubset(ranked_ids[:3]),
        "ndcg_at_10": dcg(gains) / dcg(ideal) if ideal else 0.0,
        "mrr": 1 / first_rank if first_rank else 0.0,
        "gold_units": len(gold),
    }
    for limit in (1, 3, 5):
        covered = len(gold.intersection(ranked_ids[:limit]))
        result[f"covered_at_{limit}"] = covered
        result[f"recall_at_{limit}"] = covered / len(gold)
    return result


def assign_boundary_courses(
    cases: list[dict[str, Any]],
    course_ids: list[str],
) -> dict[str, str]:
    require(bool(course_ids), "at least one course is required")
    boundary_cases = sorted(
        (
            case
            for case in cases
            if case["slice"] not in POSITIVE_SLICES
        ),
        key=lambda case: case["case_id"],
    )
    return {
        case["case_id"]: course_ids[index % len(course_ids)]
        for index, case in enumerate(boundary_cases)
    }


def aggregate(
    rows: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(row)
    overall: dict[str, Any] = {}
    slices: dict[str, Any] = {}
    for method in METHODS:
        members = by_method[method]
        positives = [row for row in members if row["is_positive"]]
        negatives = [row for row in members if not row["is_positive"]]
        threshold = thresholds[method]
        overall[method] = {
            "cases": len(members),
            "positive_cases": len(positives),
            "boundary_cases": len(negatives),
            "complete_evidence_success_at_3": mean(
                [float(row["ranking"]["complete_evidence_at_3"]) for row in positives]
            ),
            "evidence_recall_at_1": weighted_recall(positives, 1),
            "evidence_recall_at_3": weighted_recall(positives, 3),
            "evidence_recall_at_5": weighted_recall(positives, 5),
            "ndcg_at_10": mean(
                [float(row["ranking"]["ndcg_at_10"]) for row in positives]
            ),
            "mrr": mean([float(row["ranking"]["mrr"]) for row in positives]),
            "development_threshold": threshold,
            "no_evidence_accuracy_calibration": mean(
                [float(row["decision_score"] < threshold) for row in negatives]
            ),
            "positive_answer_rate_calibration": mean(
                [float(row["decision_score"] >= threshold) for row in positives]
            ),
            "action_accuracy_calibration": mean(
                [
                    float(
                        (row["decision_score"] >= threshold)
                        == row["is_positive"]
                    )
                    for row in members
                ]
            ),
            "course_isolation_violations": sum(
                row["course_isolation_violations"] for row in members
            ),
            "latency_p50_ms": percentile(
                [row["latency_ms"] for row in members],
                0.5,
            ),
            "latency_p95_ms": percentile(
                [row["latency_ms"] for row in members],
                0.95,
            ),
        }
        method_slices: dict[str, Any] = {}
        for slice_name in sorted({row["slice"] for row in members}):
            slice_members = [
                row
                for row in members
                if row["slice"] == slice_name
            ]
            slice_positives = [row for row in slice_members if row["is_positive"]]
            method_slices[slice_name] = {
                "cases": len(slice_members),
                "complete_evidence_success_at_3": (
                    mean(
                        [
                            float(row["ranking"]["complete_evidence_at_3"])
                            for row in slice_positives
                        ]
                    )
                    if slice_positives
                    else None
                ),
                "evidence_recall_at_5": (
                    weighted_recall(slice_positives, 5)
                    if slice_positives
                    else None
                ),
                "action_accuracy_calibration": mean(
                    [
                        float(
                            (row["decision_score"] >= threshold)
                            == row["is_positive"]
                        )
                        for row in slice_members
                    ]
                ),
            }
        slices[method] = method_slices
    return overall, slices


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def weighted_recall(rows: list[dict[str, Any]], limit: int) -> float:
    numerator = sum(row["ranking"][f"covered_at_{limit}"] for row in rows)
    denominator = sum(row["ranking"]["gold_units"] for row in rows)
    return numerator / denominator if denominator else 0.0


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def git_revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def git_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            text=True,
        ).strip()
    )


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def implementation_hash() -> str:
    paths = [
        ROOT / "scripts/run_cross_course_retrieval_pilot.py",
        ROOT / "scripts/draft_cross_course_benchmark.py",
        ROOT / "services/embeddings/qwen3_client.py",
        ROOT / "services/reranking/qwen3_client.py",
        ROOT / "src/digital_twin/grounding/retrieval.py",
        ROOT / "src/digital_twin/grounding/reranking.py",
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    require(args.batch_size >= 1, "batch size must be positive")
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    require(dataset["dataset_version"] == "draft-5", "pilot requires draft 5")
    development_cases = [
        case for case in dataset["cases"] if case["split"] == "development"
    ]
    require(len(development_cases) == 40, "pilot requires exactly 40 development cases")
    require(
        sum(case["split"] == "heldout_draft" for case in dataset["cases"]) == 60,
        "pilot requires 60 untouched heldout-draft cases",
    )
    if args.limit_cases:
        development_cases = development_cases[: args.limit_cases]

    corpus_started = time.perf_counter()
    _manifest, records = load_corpus(args.source_root)
    corpus_load_seconds = time.perf_counter() - corpus_started
    chunks_by_course: dict[str, list[DocumentChunk]] = defaultdict(list)
    chunk_course: dict[str, str] = {}
    for record in records:
        chunk = record["chunk"]
        course_id = record["course_id"]
        chunks_by_course[course_id].append(chunk)
        chunk_course[chunk.id] = course_id
    for case in development_cases:
        for evidence in case["gold_evidence"]:
            require(
                chunk_course.get(evidence["chunk_id"]) == case["target_course_id"],
                f"{case['case_id']} gold evidence is outside target course",
            )
    boundary_course_assignments = assign_boundary_courses(
        development_cases,
        sorted(chunks_by_course),
    )

    runtimes, model_seconds, _reranker = build_runtime(
        chunks_by_course,
        batch_size=args.batch_size,
    )
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(development_cases, start=1):
        is_positive = case["slice"] in POSITIVE_SLICES
        evaluation_course_id = (
            case["target_course_id"]
            if is_positive
            else boundary_course_assignments[case["case_id"]]
        )
        course_runtime = runtimes[evaluation_course_id]
        for method in METHODS:
            hits, latency_ms = timed(
                lambda method=method: course_runtime[method].retrieve(
                    case["query"],
                    limit=10,
                )
            )
            ranked_ids = [hit.chunk.id for hit in hits]
            score = (
                float(hits[0].raw_score or hits[0].relevance_score)
                if hits
                else 0.0
            )
            row: dict[str, Any] = {
                "case_id": case["case_id"],
                "slice": case["slice"],
                "difficulty": case["difficulty"],
                "target_course_id": case["target_course_id"],
                "evaluation_course_id": evaluation_course_id,
                "method": method,
                "is_positive": is_positive,
                "decision_score": score,
                "latency_ms": latency_ms,
                "ranked_chunk_ids": ranked_ids,
                "course_isolation_violations": sum(
                    chunk_course[identifier] != evaluation_course_id
                    for identifier in ranked_ids
                ),
            }
            if is_positive:
                row["ranking"] = score_ranking(
                    [item["chunk_id"] for item in case["gold_evidence"]],
                    ranked_ids,
                )
            rows.append(row)
        CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "run_id": (
                "cross-course-retrieval-pilot-v1-development-attempt-002"
            ),
            "dataset_sha256": sha256_file(args.dataset),
            "implementation_tree_sha256": implementation_hash(),
            "completed_cases": index,
            "rows": rows,
        }
        CHECKPOINT_PATH.write_text(
            f"{json.dumps(checkpoint, indent=2)}\n",
            encoding="utf-8",
        )
        print(
            f"case={index:02d}/{len(development_cases)} complete=true",
            flush=True,
        )

    thresholds = {
        method: math.nextafter(
            max(
                row["decision_score"]
                for row in rows
                if row["method"] == method and not row["is_positive"]
            ),
            math.inf,
        )
        for method in METHODS
    }
    overall, slices = aggregate(rows, thresholds)
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_bytes = peak_rss if platform.system() == "Darwin" else peak_rss * 1024
    result = {
        "run_id": "cross-course-retrieval-pilot-v1-development-attempt-002",
        "status": "development_pilot_not_method_selection",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": sha256_file(args.dataset),
        "development_case_count": len(development_cases),
        "heldout_cases_loaded": 0,
        "researcher_verified_at_run": sum(
            case["review"]["researcher_verified"] for case in dataset["cases"]
        ),
        "independently_reviewed_at_run": sum(
            case["review"]["second_reviewed"] for case in dataset["cases"]
        ),
        "configuration": {
            "methods": {
                "M0": "course-scoped BM25 k1=1.2 b=0.75",
                "M1": "course-scoped Qwen3-Embedding-0.6B dense",
                "M2": "M0+M1 reciprocal-rank fusion k=60",
                "M3": "M2 top-40 plus Qwen3-Reranker-0.6B",
            },
            "embedding_revision": EMBEDDING_REVISION,
            "reranker_revision": RERANKER_REVISION,
            "query_instruction": QUERY_INSTRUCTION,
            "device": "mps",
            "dtype": "float16",
            "batch_size": args.batch_size,
            "max_length": 2048,
            "external_provider_called": False,
            "boundary_course_assignments": boundary_course_assignments,
        },
        "aggregate": overall,
        "slices": slices,
        "cases": rows,
        "operational": {
            "corpus_load_seconds": corpus_load_seconds,
            **model_seconds,
            "peak_rss_bytes": peak_rss_bytes,
            "model_cache_bytes": (
                directory_size(EMBEDDING_MODEL_PATH)
                + directory_size(RERANKER_MODEL_PATH)
            ),
            "approximate_cost_usd": 0.0,
            "machine": platform.platform(),
            "python": platform.python_version(),
        },
        "implementation_tree_sha256": implementation_hash(),
        "git_revision": git_revision(),
        "git_dirty": git_dirty(),
        "limitations": [
            "The draft is assistant-QC and not fully researcher verified.",
            "Threshold metrics are calibrated and reported on the same development cases.",
            "Hardware latency is descriptive and not a quality-selection gate.",
            "No heldout-draft case was loaded or scored.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        f"{json.dumps(result, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "aggregate": overall}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
