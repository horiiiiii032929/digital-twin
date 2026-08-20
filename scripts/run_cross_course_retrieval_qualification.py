#!/usr/bin/env python3
"""Run one provider pair on the sealed development split only."""

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
from services.embeddings import JinaTextEmbedder, Qwen3TextEmbedder
from services.reranking import JinaReranker, Qwen3Reranker
from services.retrieval_provider import (
    RetrievalBudgetExceeded,
    RetrievalProviderError,
    RetrievalUsageLedger,
)
from src.digital_twin.evaluation import (
    ProviderExecution,
    ProviderPair,
    ProviderQualificationConfig,
    ProviderUsage,
    aggregate_rows,
    build_course_scoped_ladders,
    development_thresholds,
    evaluate_development_cases,
    load_provider_qualification_config,
    load_sealed_development,
)
from src.digital_twin.grounding import DocumentChunk
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


CONFIG_PATH = (
    ROOT / "research/05_evaluation/instruments/"
    "cross_course_provider_qualification_v1.json"
)
SEALED_ROOT = ROOT / "data/processed/cross_course_retrieval_v1/sealed_v1"
SEAL_PATH = SEALED_ROOT / "seal.json"
LEDGER_PATH = SEALED_ROOT / "heldout_once_ledger.json"
RUN_ROOT = ROOT / "experiments/runs/cross_course_provider_qualification_v1"
QUERY_OUTPUT_NAME = "development_result.json"
CHECKPOINT_NAME = "development_checkpoint.json"
LOCAL_MODEL_ROOT = ROOT / "data/external/huggingface/hub"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider-pair",
        required=True,
        choices=(
            "local-qwen3-0-6b",
            "hosted-jina-text-v5-reranker-v3",
        ),
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--seal", type=Path, default=SEAL_PATH)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path.home() / "Documents" / "academia_vault",
    )
    parser.add_argument("--output-root", type=Path, default=RUN_ROOT)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=None,
        help="Override the local embedding batch size independently.",
    )
    parser.add_argument(
        "--reranking-batch-size",
        type=int,
        default=None,
        help="Override the local reranking batch size independently.",
    )
    parser.add_argument("--embedding-max-length", type=int, default=2048)
    parser.add_argument("--reranking-max-length", type=int, default=2048)
    parser.add_argument(
        "--rerank-candidate-limit",
        type=int,
        default=None,
        help="Development-only override for an explicitly recorded M3 depth sweep.",
    )
    parser.add_argument("--device", default="mps")
    parser.add_argument("--dtype", default="float16")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="validate bindings and the development seal without provider calls",
    )
    return parser.parse_args()


def provider_pair(
    config: ProviderQualificationConfig,
    pair_id: str,
) -> ProviderPair:
    pair = next(
        (candidate for candidate in config.providers if candidate.pair_id == pair_id),
        None,
    )
    if pair is None:
        raise ValueError(f"unknown provider pair: {pair_id}")
    return pair


def model_path(model: str, revision: str) -> Path:
    repository = model.replace("/", "--")
    return LOCAL_MODEL_ROOT / f"models--{repository}" / "snapshots" / revision


def build_providers(
    pair: ProviderPair,
    config: ProviderQualificationConfig,
    *,
    batch_size: int,
    embedding_batch_size: int | None = None,
    reranking_batch_size: int | None = None,
    embedding_max_length: int = 2048,
    reranking_max_length: int = 2048,
    device: str,
    dtype: str,
) -> tuple[Any, Any, dict[str, float], Any]:
    if batch_size < 1:
        raise ValueError("batch size must be positive")
    resolved_embedding_batch_size = embedding_batch_size or batch_size
    resolved_reranking_batch_size = reranking_batch_size or max(1, batch_size // 2)
    if resolved_embedding_batch_size < 1 or resolved_reranking_batch_size < 1:
        raise ValueError("provider batch sizes must be positive")
    if embedding_max_length < 32:
        raise ValueError("embedding max length must be at least 32")
    if reranking_max_length < 64:
        raise ValueError("reranking max length must be at least 64")
    started = time.perf_counter()
    if pair.embedding.execution == ProviderExecution.LOCAL:
        embedding_path = model_path(
            pair.embedding.model,
            pair.embedding.revision,
        )
        reranking_path = model_path(
            pair.reranking.model,
            pair.reranking.revision,
        )
        if not embedding_path.is_dir():
            raise ValueError("local embedding model is missing")
        if not reranking_path.is_dir():
            raise ValueError("local reranking model is missing")
        embedder = Qwen3TextEmbedder(
            embedding_path,
            instruction=config.query_instruction,
            device=device,
            dtype=dtype,
            batch_size=resolved_embedding_batch_size,
            max_length=embedding_max_length,
        )
        reranker = Qwen3Reranker(
            reranking_path,
            instruction=config.query_instruction,
            device=device,
            dtype=dtype,
            batch_size=resolved_reranking_batch_size,
            max_length=reranking_max_length,
        )
        load_seconds = {
            "embedding_model_load": embedder.model_load_seconds,
            "reranking_model_load": reranker.model_load_seconds,
        }
        return embedder, reranker, load_seconds, None

    api_key = os.environ.get("JINA_API_KEY", "")
    if not api_key:
        raise ValueError("JINA_API_KEY is required for the hosted candidate")
    shared_ledger = RetrievalUsageLedger(
        max_cost_usd=config.spend_cap_usd,
        price_per_million_input_tokens_usd=(
            config.budget_rate_usd_per_million_input_tokens
        ),
    )
    embedder = JinaTextEmbedder(
        api_key,
        ledger=shared_ledger,
        model=pair.embedding.model,
        endpoint=pair.embedding.endpoint or "",
        dimensions=pair.embedding.dimensions or 1024,
        batch_size=64,
    )
    reranker = JinaReranker(
        api_key,
        ledger=shared_ledger,
        model=pair.reranking.model,
        endpoint=pair.reranking.endpoint or "",
    )
    return (
        embedder,
        reranker,
        {"provider_adapter_load": time.perf_counter() - started},
        shared_ledger,
    )


def preflight_provider(pair: ProviderPair) -> dict[str, Any]:
    if pair.embedding.execution == ProviderExecution.LOCAL:
        embedding_path = model_path(
            pair.embedding.model,
            pair.embedding.revision,
        )
        reranking_path = model_path(
            pair.reranking.model,
            pair.reranking.revision,
        )
        if not embedding_path.is_dir():
            raise ValueError("local embedding model is missing")
        if not reranking_path.is_dir():
            raise ValueError("local reranking model is missing")
        return {
            "execution": "local",
            "embedding_model_present": True,
            "reranking_model_present": True,
            "provider_calls": 0,
        }
    if not os.environ.get("JINA_API_KEY", ""):
        raise ValueError("JINA_API_KEY is required for the hosted candidate")
    return {
        "execution": "hosted",
        "credential_present": True,
        "provider_calls": 0,
    }


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


def implementation_hash(pair: ProviderPair, config_path: Path) -> str:
    paths = [
        ROOT / "scripts/run_cross_course_retrieval_qualification.py",
        ROOT / "src/digital_twin/evaluation/retrieval_qualification.py",
        ROOT / "src/digital_twin/evaluation/retrieval_runtime.py",
        ROOT / "src/digital_twin/evaluation/retrieval_runner.py",
        ROOT / "src/digital_twin/grounding/retrieval.py",
        ROOT / "src/digital_twin/grounding/reranking.py",
        ROOT / "services/retrieval_provider.py",
        config_path,
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
    ]
    paths.extend(
        [
            ROOT / "services/embeddings/qwen3_client.py",
            ROOT / "services/reranking/qwen3_client.py",
        ]
        if pair.embedding.execution == ProviderExecution.LOCAL
        else [
            ROOT / "services/embeddings/jina_client.py",
            ROOT / "services/reranking/jina_client.py",
        ]
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def usage_record(provider: Any) -> ProviderUsage:
    reporter = getattr(provider, "usage_snapshot", None)
    return reporter() if reporter else ProviderUsage()


def main() -> int:
    args = parse_args()
    config = load_provider_qualification_config(args.config)
    pair = provider_pair(config, args.provider_pair)
    dataset, seal = load_sealed_development(
        root=ROOT,
        seal_path=args.seal,
        ledger_path=args.ledger,
        config=config,
    )
    preflight = preflight_provider(pair)
    if args.preflight:
        print(
            json.dumps(
                {
                    "status": "preflight_passed",
                    "qualification_id": config.qualification_id,
                    "provider_pair": pair.pair_id,
                    "development_cases": len(dataset["cases"]),
                    "heldout_file_reads": 0,
                    "heldout_ledger_status": "unopened",
                    **preflight,
                },
                indent=2,
            )
        )
        return 0

    require_pre_evaluation_operation_allowed("method_evaluation_execution")
    corpus_started = time.perf_counter()
    _manifest, records = load_corpus(args.source_root)
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

    embedder, reranker, provider_load, shared_ledger = build_providers(
        pair,
        config,
        batch_size=args.batch_size,
        embedding_batch_size=args.embedding_batch_size,
        reranking_batch_size=args.reranking_batch_size,
        embedding_max_length=args.embedding_max_length,
        reranking_max_length=args.reranking_max_length,
        device=args.device,
        dtype=args.dtype,
    )
    effective_ladder = config.ladder
    if args.rerank_candidate_limit is not None:
        if args.rerank_candidate_limit < config.ladder.result_limit:
            raise ValueError(
                "rerank candidate limit cannot be smaller than the result limit"
            )
        effective_ladder = config.ladder.model_copy(
            update={"rerank_candidate_limit": args.rerank_candidate_limit}
        )
    runtimes, index_seconds = build_course_scoped_ladders(
        chunks_by_course,
        embedder=embedder,
        reranker=reranker,
        config=effective_ladder,
    )
    run_dir = args.output_root / pair.pair_id
    output_path = run_dir / QUERY_OUTPUT_NAME
    checkpoint_path = run_dir / CHECKPOINT_NAME
    implementation_sha256 = implementation_hash(pair, args.config)

    def checkpoint(index: int, rows: list[dict[str, Any]]) -> None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        value = {
            "qualification_id": config.qualification_id,
            "provider_pair": pair.pair_id,
            "development_sha256": config.development_sha256,
            "heldout_file_reads": 0,
            "implementation_tree_sha256": implementation_sha256,
            "completed_cases": index,
            "rows": rows,
        }
        checkpoint_path.write_text(
            f"{json.dumps(value, indent=2)}\n",
            encoding="utf-8",
        )
        print(f"case={index:02d}/40 complete=true", flush=True)

    synchronize = None
    if pair.embedding.execution == ProviderExecution.LOCAL:
        import torch

        def synchronize() -> None:
            if args.device == "mps" and torch.backends.mps.is_available():
                torch.mps.synchronize()

    rows, boundary_assignments = evaluate_development_cases(
        dataset["cases"],
        runtimes=runtimes,
        chunk_course=chunk_course,
        result_limit=config.ladder.result_limit,
        synchronize=synchronize,
        on_case_complete=checkpoint,
    )
    thresholds = development_thresholds(rows)
    aggregate, slices = aggregate_rows(rows, thresholds)
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_bytes = peak_rss if platform.system() == "Darwin" else peak_rss * 1024
    embedding_usage = usage_record(embedder)
    reranking_usage = usage_record(reranker)
    total_usage = (
        shared_ledger.usage_snapshot()
        if shared_ledger is not None
        else ProviderUsage(
            request_count=(
                embedding_usage.request_count + reranking_usage.request_count
            ),
            input_items=embedding_usage.input_items + reranking_usage.input_items,
            input_characters=(
                embedding_usage.input_characters + reranking_usage.input_characters
            ),
            input_tokens=(embedding_usage.input_tokens + reranking_usage.input_tokens),
            retry_count=(embedding_usage.retry_count + reranking_usage.retry_count),
            failure_count=(
                embedding_usage.failure_count + reranking_usage.failure_count
            ),
            cache_hits=embedding_usage.cache_hits + reranking_usage.cache_hits,
            approximate_cost_usd=0,
        )
    )
    cache_bytes = 0
    if pair.embedding.execution == ProviderExecution.LOCAL:
        cache_bytes = directory_size(
            model_path(pair.embedding.model, pair.embedding.revision)
        ) + directory_size(model_path(pair.reranking.model, pair.reranking.revision))
    result = {
        "qualification_id": config.qualification_id,
        "provider_pair": pair.model_dump(mode="json"),
        "status": "development_provider_qualification",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "dataset_seal_id": seal["seal_id"],
        "development_sha256": config.development_sha256,
        "development_case_count": len(dataset["cases"]),
        "heldout_sha256": config.heldout_sha256,
        "heldout_file_reads": 0,
        "heldout_ledger_status": "unopened",
        "configuration": {
            "ladder": effective_ladder.model_dump(mode="json"),
            "query_instruction": config.query_instruction,
            "boundary_course_assignments": boundary_assignments,
            "device": (
                args.device
                if pair.embedding.execution == ProviderExecution.LOCAL
                else "hosted"
            ),
            "dtype": (
                args.dtype
                if pair.embedding.execution == ProviderExecution.LOCAL
                else "provider-managed"
            ),
            "batch_size": args.batch_size,
            "embedding_batch_size": embedder.batch_size
            if pair.embedding.execution == ProviderExecution.LOCAL
            else None,
            "reranking_batch_size": reranker.batch_size
            if pair.embedding.execution == ProviderExecution.LOCAL
            else None,
            "embedding_max_length": embedder.max_length
            if pair.embedding.execution == ProviderExecution.LOCAL
            else None,
            "reranking_max_length": reranker.max_length
            if pair.embedding.execution == ProviderExecution.LOCAL
            else None,
            "spend_cap_usd": config.spend_cap_usd,
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
        "failures_by_category": {},
        "hard_gates": {
            "complete_40_case_run": True,
            "heldout_file_reads": 0,
            "course_isolation_violations": sum(
                row["course_isolation_violations"] for row in rows
            ),
            "provider_failures": total_usage.failure_count,
            "cost_cap_passed": (
                total_usage.approximate_cost_usd <= config.spend_cap_usd
            ),
        },
        "implementation_tree_sha256": implementation_sha256,
        "git_revision": git_revision(),
        "git_dirty": git_dirty(),
        "limitations": [
            "This is development-only provider qualification.",
            "Threshold action metrics are calibration diagnostics.",
            "Hardware latency is descriptive, not a quality-selection gate.",
            "No held-out case or held-out result was loaded or scored.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"{json.dumps(result, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "provider_pair": pair.pair_id,
                "heldout_file_reads": 0,
                "aggregate": aggregate,
                "total_provider_usage": total_usage.model_dump(mode="json"),
            },
            indent=2,
        )
    )
    return 0


def cli() -> int:
    try:
        return main()
    except (
        OSError,
        ValueError,
        RetrievalBudgetExceeded,
        RetrievalProviderError,
    ) as error:
        print(
            json.dumps(
                {
                    "status": "preflight_or_run_failed",
                    "failure_type": type(error).__name__,
                    "failure": str(error),
                },
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
