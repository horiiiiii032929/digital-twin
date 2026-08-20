#!/usr/bin/env python3
"""Evaluate selected M2 behavior across dependency environments."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import platform
import statistics
import subprocess
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.draft_cross_course_benchmark import ROOT, load_corpus
from scripts.run_cross_course_retrieval_qualification import (
    CONFIG_PATH,
    LEDGER_PATH,
    LOCAL_MODEL_ROOT,
    SEAL_PATH,
)
from services.embeddings import Qwen3TextEmbedder
from src.digital_twin.evaluation import (
    CourseScopedRetriever,
    assign_boundary_courses,
    load_provider_qualification_config,
    score_ranking,
)
from src.digital_twin.evaluation.retrieval_qualification import sha256_file
from src.digital_twin.grounding import (
    BM25Retriever,
    DenseRetriever,
    ReciprocalRankFusionRetriever,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
OUTPUT_ROOT = ROOT / "reports/generated"
MODEL_REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
MODEL_PATH = (
    LOCAL_MODEL_ROOT
    / "models--Qwen--Qwen3-Embedding-0.6B"
    / "snapshots"
    / MODEL_REVISION
)
POSITIVE_SLICES = {"answerable", "cross_course_confusion"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path.home() / "Documents" / "academia_vault",
    )
    parser.add_argument("--repeats", type=int, default=3)
    arguments = parser.parse_args()
    if arguments.repeats < 3:
        parser.error("dependency compatibility requires at least three trials")
    resolved = arguments.output.resolve()
    if not resolved.is_relative_to(OUTPUT_ROOT.resolve()):
        parser.error("output must stay under reports/generated")
    return arguments


def _git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _version(distribution: str) -> str:
    return importlib.metadata.version(distribution)


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [row for row in rows if row["is_positive"]]
    return {
        "cases": len(rows),
        "positive_cases": len(positives),
        "complete_evidence_success_at_3": _mean(
            [float(row["ranking"]["complete_evidence_at_3"]) for row in positives]
        ),
        "evidence_recall_at_3": (
            sum(row["ranking"]["covered_at_3"] for row in positives)
            / sum(row["ranking"]["gold_units"] for row in positives)
        ),
        "ndcg_at_10": _mean(
            [float(row["ranking"]["ndcg_at_10"]) for row in positives]
        ),
        "mrr": _mean([float(row["ranking"]["mrr"]) for row in positives]),
        "course_isolation_violations": sum(
            row["course_isolation_violations"] for row in rows
        ),
        "latency_p50_ms": _percentile(
            [float(row["latency_ms"]) for row in rows], 0.50
        ),
        "latency_p95_ms": _percentile(
            [float(row["latency_ms"]) for row in rows], 0.95
        ),
    }


def _profile_configuration() -> dict[str, Any]:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    selection = next(
        component
        for component in profile["components"]
        if component["component"] == "retriever"
    )
    implementation = selection["implementation"]
    configuration = implementation["configuration"]
    if (
        profile.get("profile_version") != "v1"
        or implementation.get("implementation_id") != "qwen3-hybrid-v1"
        or configuration.get("method") != "M2"
        or configuration.get("embedding_revision") != MODEL_REVISION
        or configuration.get("reranker") != "none"
    ):
        raise ValueError("selected M2 profile binding drifted")
    return configuration


def _load_development_only(config: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate seal/ledger metadata without opening the held-out file."""

    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    if (
        seal.get("seal_id") != config.dataset_seal_id
        or seal.get("development_sha256") != config.development_sha256
        or seal.get("heldout_sha256") != config.heldout_sha256
        or ledger.get("seal_id") != seal.get("seal_id")
        or ledger.get("heldout_sha256") != config.heldout_sha256
        or ledger.get("status") not in {"unopened", "completed"}
    ):
        raise ValueError("cross-course development seal or ledger metadata drifted")
    development_path = ROOT / seal["development_path"]
    if sha256_file(development_path) != config.development_sha256:
        raise ValueError("cross-course development dataset hash drifted")
    dataset = json.loads(development_path.read_text(encoding="utf-8"))
    if (
        dataset.get("dataset_status") != "sealed"
        or len(dataset.get("cases", [])) != 40
        or any(case.get("split") != "development" for case in dataset["cases"])
    ):
        raise ValueError("cross-course development dataset is invalid")
    return dataset, seal


def _build_runtimes(
    chunks_by_course: dict[str, list[DocumentChunk]],
    configuration: dict[str, Any],
) -> tuple[dict[str, CourseScopedRetriever], float, Qwen3TextEmbedder]:
    if not MODEL_PATH.is_dir():
        raise ValueError("pinned local Qwen3 embedding model is missing")
    embedder = Qwen3TextEmbedder(
        MODEL_PATH,
        instruction=str(configuration["query_instruction"]),
        device=str(configuration["device"]),
        dtype=str(configuration["dtype"]),
        batch_size=int(configuration["embedding_batch_size"]),
        max_length=int(configuration["embedding_max_length"]),
    )
    started = time.perf_counter()
    runtimes = {}
    for course_id in sorted(chunks_by_course):
        chunks = chunks_by_course[course_id]
        bm25 = BM25Retriever(
            chunks,
            k1=float(configuration["bm25_k1"]),
            b=float(configuration["bm25_b"]),
        )
        dense = DenseRetriever(chunks, embedder, minimum_similarity=-1.0)
        hybrid = ReciprocalRankFusionRetriever(
            [bm25, dense],
            rank_constant=int(configuration["fusion_rank_constant"]),
            candidate_limit=int(configuration["fusion_candidate_limit"]),
        )
        runtimes[course_id] = CourseScopedRetriever(course_id, hybrid, chunks)
    return runtimes, time.perf_counter() - started, embedder


def _evaluate_trial(
    cases: list[dict[str, Any]],
    runtimes: dict[str, CourseScopedRetriever],
    chunk_course: dict[str, str],
    boundary_assignments: dict[str, str],
) -> list[dict[str, Any]]:
    import torch

    rows = []
    for case in cases:
        is_positive = case["slice"] in POSITIVE_SLICES
        course_id = (
            case["target_course_id"]
            if is_positive
            else boundary_assignments[case["case_id"]]
        )
        if torch.backends.mps.is_available():
            torch.mps.synchronize()
        started = time.perf_counter()
        hits = runtimes[course_id].retrieve(case["query"], limit=10)
        if torch.backends.mps.is_available():
            torch.mps.synchronize()
        ranked_ids = [hit.chunk.id for hit in hits]
        row: dict[str, Any] = {
            "case_id": case["case_id"],
            "is_positive": is_positive,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "top3_chunk_ids": ranked_ids[:3],
            "course_isolation_violations": sum(
                chunk_course.get(identifier) != course_id for identifier in ranked_ids
            ),
        }
        if is_positive:
            row["ranking"] = score_ranking(
                [evidence["chunk_id"] for evidence in case["gold_evidence"]],
                ranked_ids,
            )
        rows.append(row)
    return rows


def evaluate(arguments: argparse.Namespace) -> dict[str, Any]:
    if _git_value("status", "--porcelain"):
        raise ValueError("dependency compatibility evaluation requires a clean tree")
    config = load_provider_qualification_config(CONFIG_PATH)
    dataset, seal = _load_development_only(config)
    _manifest, records = load_corpus(arguments.source_root)
    chunks_by_course: dict[str, list[DocumentChunk]] = defaultdict(list)
    chunk_course: dict[str, str] = {}
    for record in records:
        course_id = record["course_id"]
        chunk = record["chunk"]
        if chunk.id in chunk_course:
            raise ValueError("corpus contains a duplicate chunk ID")
        chunks_by_course[course_id].append(chunk)
        chunk_course[chunk.id] = course_id
    configuration = _profile_configuration()
    runtimes, index_seconds, embedder = _build_runtimes(
        chunks_by_course, configuration
    )
    boundary_assignments = assign_boundary_courses(
        dataset["cases"], sorted(runtimes)
    )
    trials = []
    expected_top3: dict[str, list[str]] | None = None
    for trial in range(1, arguments.repeats + 1):
        rows = _evaluate_trial(
            dataset["cases"], runtimes, chunk_course, boundary_assignments
        )
        observed_top3 = {row["case_id"]: row["top3_chunk_ids"] for row in rows}
        if expected_top3 is not None and observed_top3 != expected_top3:
            raise ValueError("M2 top-three rankings changed between repeated trials")
        expected_top3 = observed_top3
        trials.append({"trial": trial, "metrics": _metrics(rows)})
    assert expected_top3 is not None
    metric_names = (
        "complete_evidence_success_at_3",
        "evidence_recall_at_3",
        "ndcg_at_10",
        "mrr",
    )
    aggregate = {
        name: statistics.median(
            float(trial["metrics"][name]) for trial in trials
        )
        for name in metric_names
    }
    aggregate.update(
        {
            "cases": len(dataset["cases"]),
            "course_isolation_violations": sum(
                int(trial["metrics"]["course_isolation_violations"])
                for trial in trials
            ),
            "latency_p95_ms_median": statistics.median(
                float(trial["metrics"]["latency_p95_ms"]) for trial in trials
            ),
        }
    )
    return {
        "evaluation_id": f"dependency-compatibility-{arguments.label}",
        "status": "complete",
        "label": arguments.label,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "code_revision": _git_value("rev-parse", "HEAD"),
        "working_tree_dirty": False,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "dependencies": {
                name: _version(name)
                for name in (
                    "torch",
                    "transformers",
                    "sentence-transformers",
                    "fastembed",
                    "open-clip-torch",
                )
            },
        },
        "binding": {
            "profile": "student-tutor-v1",
            "method": "M2",
            "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
            "embedding_revision": MODEL_REVISION,
            "development_sha256": config.development_sha256,
            "development_cases": len(dataset["cases"]),
            "seal_id": seal["seal_id"],
            "heldout_file_reads": 0,
            "external_provider_calls": 0,
            "configuration": configuration,
        },
        "index_build_seconds": index_seconds,
        "embedding_usage": embedder.usage_snapshot().model_dump(mode="json"),
        "aggregate": aggregate,
        "trials": trials,
        "top3_by_case": expected_top3,
    }


def main() -> None:
    arguments = parse_args()
    require_pre_evaluation_operation_allowed("local_model_evaluation")
    if arguments.output.exists():
        raise ValueError(f"refusing to overwrite compatibility result: {arguments.output}")
    result = evaluate(arguments)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        f"{json.dumps(result, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "evaluation_id": result["evaluation_id"],
                "runtime": result["runtime"],
                "aggregate": result["aggregate"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
