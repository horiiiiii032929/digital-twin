#!/usr/bin/env python3
"""Run the frozen cross-course retrieval comparison once on held-out data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import subprocess
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.draft_cross_course_benchmark import ROOT, load_corpus
from scripts.run_cross_course_retrieval_qualification import (
    build_providers,
    directory_size,
    implementation_hash,
    provider_pair,
    usage_record,
)
from src.digital_twin.evaluation import (
    ProviderUsage,
    RetrievalMethod,
    aggregate_rows,
    load_provider_qualification_config,
    load_sealed_development,
)
from src.digital_twin.evaluation.retrieval_runner import evaluate_cases
from src.digital_twin.grounding import DocumentChunk


FINAL_CONFIG_PATH = (
    ROOT / "research/05_evaluation/instruments/"
    "cross_course_retrieval_final_v1.json"
)
PROVIDER_CONFIG_PATH = (
    ROOT / "research/05_evaluation/instruments/"
    "cross_course_provider_qualification_v1.json"
)
SEALED_ROOT = ROOT / "data/processed/cross_course_retrieval_v1/sealed_v1"
SEAL_PATH = SEALED_ROOT / "seal.json"
LEDGER_PATH = SEALED_ROOT / "heldout_once_ledger.json"
RUN_ROOT = ROOT / "experiments/runs/cross_course_retrieval_v1/heldout-001"
MODEL_ROOT = ROOT / "data/external/huggingface/hub"
RUN_ID = "cross-course-retrieval-v1-heldout-001"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-heldout-once",
        action="store_true",
        help="explicitly authorize the one-time held-out read",
    )
    parser.add_argument("--source-root", type=Path, default=None)
    parser.add_argument("--seal", type=Path, default=SEAL_PATH)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument("--provider-config", type=Path, default=PROVIDER_CONFIG_PATH)
    parser.add_argument("--final-config", type=Path, default=FINAL_CONFIG_PATH)
    parser.add_argument("--output-root", type=Path, default=RUN_ROOT)
    return parser.parse_args()


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        f"{json.dumps(value, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_final_config(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "run_id",
        "dataset_seal_id",
        "development_sha256",
        "heldout_sha256",
        "provider_pair_id",
        "heldout_case_count",
        "runtime",
        "development_thresholds",
    }
    missing = required - value.keys()
    if missing:
        raise ValueError(f"final configuration missing fields: {sorted(missing)}")
    if value["run_id"] != RUN_ID:
        raise ValueError("final configuration has the wrong run ID")
    if value["provider_pair_id"] != "local-qwen3-0-6b":
        raise ValueError("final held-out run must use the local Qwen3 binding")
    if value["heldout_case_count"] != 60:
        raise ValueError("final held-out run requires 60 cases")
    runtime = value["runtime"]
    expected_runtime = {
        "device": "mps",
        "dtype": "float16",
        "batch_size": 8,
        "embedding_batch_size": 16,
        "reranking_batch_size": 8,
        "embedding_max_length": 2048,
        "reranking_max_length": 1024,
        "rerank_candidate_limit": 20,
        "result_limit": 10,
    }
    if runtime != expected_runtime:
        raise ValueError("final runtime differs from the frozen deployment study")
    if set(value["development_thresholds"]) != {
        method.value for method in RetrievalMethod
    }:
        raise ValueError("final configuration must freeze all method thresholds")
    return value


def load_pristine_metadata(
    *,
    final_config: dict[str, Any],
    provider_config_path: Path,
    seal_path: Path,
    ledger_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider_config = load_provider_qualification_config(provider_config_path)
    if provider_config.qualification_id != "cross-course-provider-qualification-v1":
        raise ValueError("unexpected provider qualification configuration")
    if provider_config.dataset_seal_id != final_config["dataset_seal_id"]:
        raise ValueError("provider and final seal IDs differ")
    if provider_config.development_sha256 != final_config["development_sha256"]:
        raise ValueError("provider and final development hashes differ")
    if provider_config.heldout_sha256 != final_config["heldout_sha256"]:
        raise ValueError("provider and final held-out hashes differ")
    _development, seal = load_sealed_development(
        root=ROOT,
        seal_path=seal_path,
        ledger_path=ledger_path,
        config=provider_config,
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if ledger["status"] != "unopened" or ledger["attempts"]:
        raise ValueError("held-out ledger is not pristine; rerun is prohibited")
    return seal, ledger


def mark_ledger_started(
    ledger_path: Path,
    ledger: dict[str, Any],
    *,
    code_revision: str,
    final_config_sha256: str,
) -> None:
    started_at = now()
    ledger["status"] = "started"
    ledger["opened_at"] = started_at
    ledger["attempts"] = [
        {
            "run_id": RUN_ID,
            "status": "started",
            "started_at": started_at,
            "code_revision": code_revision,
            "final_config_sha256": final_config_sha256,
        }
    ]
    write_json(ledger_path, ledger)


def mark_ledger_completed(
    ledger_path: Path,
    ledger: dict[str, Any],
    *,
    result_sha256: str,
    result_path: Path,
) -> None:
    completed_at = now()
    ledger["status"] = "completed"
    ledger["completed_at"] = completed_at
    ledger["attempts"][0].update(
        {
            "status": "completed",
            "completed_at": completed_at,
            "result_path": str(result_path.relative_to(ROOT)),
            "result_sha256": result_sha256,
        }
    )
    write_json(ledger_path, ledger)


def mark_ledger_failed(
    ledger_path: Path,
    ledger: dict[str, Any],
    *,
    error_type: str,
    error: str,
) -> None:
    ledger["status"] = "failed"
    ledger["attempts"][0].update(
        {
            "status": "failed",
            "failed_at": now(),
            "failure_type": error_type,
            "failure": error,
        }
    )
    write_json(ledger_path, ledger)


def load_heldout_once(
    *,
    seal: dict[str, Any],
    final_config: dict[str, Any],
) -> dict[str, Any]:
    heldout_path = ROOT / seal["heldout_path"]
    content = heldout_path.read_bytes()
    if sha256_bytes(content) != final_config["heldout_sha256"]:
        raise ValueError("held-out file hash does not match the frozen seal")
    dataset = json.loads(content.decode("utf-8"))
    if dataset["dataset_status"] != "sealed":
        raise ValueError("held-out dataset is not sealed")
    cases = dataset["cases"]
    if len(cases) != final_config["heldout_case_count"]:
        raise ValueError("held-out dataset has the wrong case count")
    if any(case["split"] != "heldout_draft" for case in cases):
        raise ValueError("held-out dataset contains a non-held-out case")
    return dataset


def build_implementation_hash(
    *,
    pair: Any,
    provider_config_path: Path,
    final_config_path: Path,
) -> str:
    base = implementation_hash(pair, provider_config_path)
    digest = hashlib.sha256()
    digest.update(base.encode("ascii"))
    digest.update(str(final_config_path.relative_to(ROOT)).encode())
    digest.update(final_config_path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    if not args.confirm_heldout_once:
        raise ValueError(
            "held-out execution requires --confirm-heldout-once; no data was read"
        )
    final_config = load_final_config(args.final_config)
    seal, ledger = load_pristine_metadata(
        final_config=final_config,
        provider_config_path=args.provider_config,
        seal_path=args.seal,
        ledger_path=args.ledger,
    )
    provider_config_model = load_provider_qualification_config(args.provider_config)
    pair = provider_pair(provider_config_model, final_config["provider_pair_id"])
    code_revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    final_config_sha256 = sha256_path(args.final_config)

    source_root = args.source_root or Path(
        os.environ.get("ACADEMIA_VAULT_ROOT", Path.home() / "Documents" / "academia_vault")
    )
    corpus_started = time.perf_counter()
    _manifest, records = load_corpus(source_root)
    corpus_load_seconds = time.perf_counter() - corpus_started
    chunks_by_course: dict[str, list[DocumentChunk]] = defaultdict(list)
    chunk_course: dict[str, str] = {}
    for record in records:
        course_id = record["course_id"]
        chunk = record["chunk"]
        if chunk.id in chunk_course:
            raise ValueError("corpus contains a duplicate chunk ID")
        chunks_by_course[course_id].append(chunk)
        chunk_course[chunk.id] = course_id

    runtime = final_config["runtime"]
    effective_ladder = provider_config_model.ladder.model_copy(
        update={
            "rerank_candidate_limit": runtime["rerank_candidate_limit"],
            "result_limit": runtime["result_limit"],
        }
    )
    embedder, reranker, provider_load, shared_ledger = build_providers(
        pair,
        provider_config_model,
        batch_size=runtime["batch_size"],
        embedding_batch_size=runtime["embedding_batch_size"],
        reranking_batch_size=runtime["reranking_batch_size"],
        embedding_max_length=runtime["embedding_max_length"],
        reranking_max_length=runtime["reranking_max_length"],
        device=runtime["device"],
        dtype=runtime["dtype"],
    )
    from src.digital_twin.evaluation.retrieval_runtime import build_course_scoped_ladders

    runtimes, index_seconds = build_course_scoped_ladders(
        chunks_by_course,
        embedder=embedder,
        reranker=reranker,
        config=effective_ladder,
    )
    implementation_sha256 = build_implementation_hash(
        pair=pair,
        provider_config_path=args.provider_config,
        final_config_path=args.final_config,
    )

    ledger_opened = False
    mark_ledger_started(
        args.ledger,
        ledger,
        code_revision=code_revision,
        final_config_sha256=final_config_sha256,
    )
    ledger_opened = True
    output_dir = args.output_root / pair.pair_id
    output_path = output_dir / "heldout_result.json"
    checkpoint_path = output_dir / "heldout_checkpoint.json"

    def checkpoint(index: int, rows: list[dict[str, Any]]) -> None:
        write_json(
            checkpoint_path,
            {
                "run_id": RUN_ID,
                "heldout_sha256": final_config["heldout_sha256"],
                "heldout_file_reads": 1,
                "completed_cases": index,
                "rows": rows,
            },
        )
        print(f"heldout_case={index:02d}/60 complete=true", flush=True)

    synchronize = None
    if runtime["device"] == "mps":
        import torch

        def synchronize() -> None:
            if torch.backends.mps.is_available():
                torch.mps.synchronize()

    try:
        heldout = load_heldout_once(seal=seal, final_config=final_config)
        rows, boundary_assignments = evaluate_cases(
            heldout["cases"],
            runtimes=runtimes,
            chunk_course=chunk_course,
            result_limit=runtime["result_limit"],
            expected_split="heldout_draft",
            expected_count=60,
            synchronize=synchronize,
            on_case_complete=checkpoint,
        )
        thresholds = final_config["development_thresholds"]
        aggregate, slices = aggregate_rows(rows, thresholds)
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_rss_bytes = peak_rss if platform.system() == "Darwin" else peak_rss * 1024
        embedding_usage = usage_record(embedder)
        reranking_usage = usage_record(reranker)
        total_usage = (
            shared_ledger.usage_snapshot()
            if shared_ledger is not None
            else ProviderUsage(
                request_count=embedding_usage.request_count + reranking_usage.request_count,
                input_items=embedding_usage.input_items + reranking_usage.input_items,
                input_characters=(
                    embedding_usage.input_characters + reranking_usage.input_characters
                ),
                input_tokens=embedding_usage.input_tokens + reranking_usage.input_tokens,
                retry_count=embedding_usage.retry_count + reranking_usage.retry_count,
                failure_count=(
                    embedding_usage.failure_count + reranking_usage.failure_count
                ),
                cache_hits=embedding_usage.cache_hits + reranking_usage.cache_hits,
                approximate_cost_usd=0,
            )
        )
        cache_bytes = directory_size(
            MODEL_ROOT
            / "models--Qwen--Qwen3-Embedding-0.6B"
            / "snapshots"
            / pair.embedding.revision
        ) + directory_size(
            MODEL_ROOT
            / "models--Qwen--Qwen3-Reranker-0.6B"
            / "snapshots"
            / pair.reranking.revision
        )
        isolation_violations = sum(
            row["course_isolation_violations"] for row in rows
        )
        hard_gates = {
            "complete_60_case_run": len(rows) == 60 * len(RetrievalMethod),
            "one_time_heldout_ledger_completed": True,
            "zero_course_isolation_violations": isolation_violations == 0,
            "zero_provider_failures": total_usage.failure_count == 0,
            "zero_retries": total_usage.retry_count == 0,
            "zero_external_calls": pair.embedding.execution.value == "local",
            "peak_process_memory_at_most_4_gib": peak_rss_bytes <= 4 * 1024**3,
        }
        result = {
            "run_id": RUN_ID,
            "status": "heldout_retrieval_comparison_completed",
            "created_at": now(),
            "dataset_id": heldout["dataset_id"],
            "dataset_version": heldout["dataset_version"],
            "dataset_seal_id": seal["seal_id"],
            "corpus_id": heldout["corpus_id"],
            "development_sha256": final_config["development_sha256"],
            "heldout_sha256": final_config["heldout_sha256"],
            "heldout_case_count": len(heldout["cases"]),
            "heldout_file_reads": 1,
            "heldout_ledger_status": "completed",
            "provider_pair": pair.model_dump(mode="json"),
            "configuration": {
                "runtime": runtime,
                "ladder": effective_ladder.model_dump(mode="json"),
                "query_instruction": provider_config_model.query_instruction,
                "development_thresholds": thresholds,
                "boundary_course_assignments": boundary_assignments,
            },
            "aggregate": aggregate,
            "slices": slices,
            "cases": rows,
            "operational": {
                "corpus_load_seconds": corpus_load_seconds,
                **provider_load,
                "embedding_index_build_seconds": sum(index_seconds.values()),
                "embedding_index_build_by_course_seconds": index_seconds,
                "peak_rss_bytes": peak_rss_bytes,
                "local_model_cache_bytes": cache_bytes,
                "embedding_usage": embedding_usage.model_dump(mode="json"),
                "reranking_usage": reranking_usage.model_dump(mode="json"),
                "total_provider_usage": total_usage.model_dump(mode="json"),
            },
            "hard_gates": hard_gates,
            "implementation_tree_sha256": implementation_sha256,
            "final_config_sha256": final_config_sha256,
            "git_revision": code_revision,
            "git_dirty": bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], cwd=ROOT, text=True
                ).strip()
            ),
            "limitations": [
                "This is the one-time held-out comparison for the frozen text benchmark.",
                "The benchmark excludes image-only claims; multimodal evidence remains separate.",
                "Thresholds were frozen from the declared development run and were not recalibrated.",
                "Latency and memory describe the declared local workstation, not concurrent capacity.",
            ],
        }
        write_json(output_path, result)
        result_sha256 = sha256_path(output_path)
        mark_ledger_completed(
            args.ledger,
            ledger,
            result_sha256=result_sha256,
            result_path=output_path,
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "run_id": RUN_ID,
                    "heldout_cases": len(heldout["cases"]),
                    "result_sha256": result_sha256,
                    "aggregate": aggregate,
                    "hard_gates": hard_gates,
                },
                indent=2,
            )
        )
        return 0
    except BaseException as error:
        if ledger_opened:
            mark_ledger_failed(
                args.ledger,
                ledger,
                error_type=type(error).__name__,
                error=str(error),
            )
        raise


def cli() -> int:
    try:
        return main()
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "heldout_run_failed",
                    "failure_type": type(error).__name__,
                    "failure": str(error),
                },
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
