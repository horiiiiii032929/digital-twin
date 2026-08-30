#!/usr/bin/env python3
"""Run the one finite fresh 500+100 action-router product checkpoint."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from contextlib import contextmanager
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterator

from dotenv import load_dotenv

from scripts import academic_factual_qa_atomic_m2_t0_adapter as adapter
from scripts import build_academic_factual_qa_action_router_product_checkpoint as builder
from scripts import run_academic_factual_qa_atomic_m2_product_checkpoint as product
from scripts.run_academic_factual_qa_api_retrieval_selection import _query_vectors
from services.embeddings.openai_client import OpenAITextEmbedder
from services.retrieval_provider import RetrievalUsageLedger
from src.digital_twin.evaluation.factual_qa_contract import EvaluationCaseV1
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.grounding.api_retrieval_index import (
    ApiRetrievalIndexBindingV2,
    StreamingRetrievalIndexMaterializerV2,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.retrieval_index import source_set_sha256
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = builder.INSTRUMENT_ID
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
CANDIDATE_RESPONSES = OUTPUT_ROOT / "candidate-responses.sqlite3"
CANDIDATE_PROVIDER = OUTPUT_ROOT / "candidate-provider.sqlite3"
CANDIDATE_STATE = OUTPUT_ROOT / "candidate-product-state.sqlite3"
CONTROL_RESPONSES = OUTPUT_ROOT / "control-responses.sqlite3"
CONTROL_PROVIDER = OUTPUT_ROOT / "control-provider.sqlite3"
CONTROL_STATE = OUTPUT_ROOT / "control-product-state.sqlite3"
CANDIDATE_RESULT = OUTPUT_ROOT / "candidate-result.json"
CONTROL_RESULT = OUTPUT_ROOT / "control-result.json"
PAIRED_RESULT = OUTPUT_ROOT / "paired-result.json"
CHECKPOINT_STATE = OUTPUT_ROOT / "checkpoint-state.json"
INDEX_ROOT = OUTPUT_ROOT / "indexes"
QUERY_CACHE = OUTPUT_ROOT / "query-vectors.sqlite3"
ALL_OUTPUTS = (
    CANDIDATE_RESPONSES,
    CANDIDATE_PROVIDER,
    CANDIDATE_STATE,
    CONTROL_RESPONSES,
    CONTROL_PROVIDER,
    CONTROL_STATE,
    CANDIDATE_RESULT,
    CONTROL_RESULT,
    PAIRED_RESULT,
    CHECKPOINT_STATE,
    builder.RETRIEVAL_RUNTIME,
    QUERY_CACHE,
    INDEX_ROOT,
)


class ActionRouterCheckpointError(RuntimeError):
    """Raised when the bounded successor violates its frozen contract."""


def _load_hashed(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise ActionRouterCheckpointError(f"content hash drifted: {path.name}")
    return payload


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def validate() -> dict[str, Any]:
    builder.check()
    instrument = _load_hashed(builder.INSTRUMENT)
    binding = _load_hashed(builder.BINDING)
    candidate = json.loads(builder.CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    control = json.loads(builder.CONTROL_MANIFEST.read_text(encoding="utf-8"))
    if (
        instrument["execution"]["maximum_embedding_calls"] != 20
        or instrument["execution"]["maximum_product_calls"] != 600
        or instrument["execution"]["maximum_total_calls"] != 620
        or instrument["execution"]["maximum_transport_retries"] != 0
        or instrument["execution"]["maximum_cost_usd"] != 8.0
        or instrument["boundaries"]["final_10000_opened"] is not False
    ):
        raise ActionRouterCheckpointError("execution boundary drifted")
    provider = binding["providers"]["high-volume-generator"]
    embedding = binding["providers"]["embedding"]
    if (
        provider["provider_model"] != "gpt-5.4-mini-2026-03-17"
        or provider["request_store"] is not False
        or provider["maximum_transport_retries"] != 0
        or embedding["provider_model"] != "text-embedding-3-small"
        or embedding["dimensions"] != 1536
    ):
        raise ActionRouterCheckpointError("OpenAI binding drifted")
    if (
        candidate["evidence_gate"] != "question-targeted-atomic-evidence-gate-v1"
        or candidate["model_bindings"]["action-router"]
        != "deterministic-tutor-action-router-v1"
        or control["evidence_gate"] != "atomic-structured-coverage-control-v1"
        or control["model_bindings"]["action-router"] != "none-historical-control"
    ):
        raise ActionRouterCheckpointError("candidate/control method drifted")
    source = _load_hashed(builder.dataset.SOURCE_PATH)
    if (
        source["source_range_disjoint_from_all_prior_development"] is not True
        or source["source_family_disjoint_from_prior_development"] is not False
        or source["final_split_opened"] is not False
    ):
        raise ActionRouterCheckpointError("fresh-source limitation drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "candidate_case_count": 500,
        "control_case_count": 100,
        "source_range_disjoint": True,
        "source_family_disjoint": False,
        "provider_execution_authorized": binding["authorization"][
            "provider_execution_authorized"
        ],
        "provider_calls": 0,
        "final_10000_opened": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate()
    except Exception as error:  # noqa: BLE001
        blockers.append(f"validation:{type(error).__name__}:{error}")
    try:
        binding = _load_hashed(builder.BINDING)
        if not binding["authorization"]["provider_execution_authorized"]:
            blockers.append("provider-execution-not-authorized")
        if not binding["authorization"]["paid_execution_authorized"]:
            blockers.append("paid-execution-not-authorized")
        if binding.get("metadata_status") != "fresh" or not binding.get("verified_at"):
            blockers.append("provider-metadata-refresh-required")
        else:
            checked_at = datetime.fromisoformat(binding["verified_at"])
            age = (datetime.now(UTC) - checked_at.astimezone(UTC)).total_seconds() / 3600
            if age < 0 or age > 24:
                blockers.append("provider-metadata-stale")
    except Exception as error:  # noqa: BLE001
        blockers.append(f"provider-binding:{type(error).__name__}:{error}")
    try:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    except Exception:
        blockers.append("repository-freeze-authorization-missing")
    if _dirty():
        blockers.append("working-tree-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-credential-missing")
    if resume:
        if not OUTPUT_ROOT.is_dir():
            blockers.append("resume-output-path-missing")
    else:
        used = [path.name for path in ALL_OUTPUTS if path.exists()]
        if used:
            blockers.append("exclusive-output-used:" + ",".join(sorted(used)))
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "provider_calls": 0,
        "maximum_total_calls": 620,
        "maximum_cost_usd": 8.0,
        "hidden_gold_loaded": False,
        "final_10000_opened": False,
    }


def simulate(*, scenario: str) -> dict[str, Any]:
    if scenario not in {"pass", "quality-failure", "provider-failure", "resume"}:
        raise ActionRouterCheckpointError("unknown simulation scenario")
    validate()
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": {
            "pass": "completed-keep",
            "quality-failure": "completed-refine",
            "provider-failure": "invalid-execution",
            "resume": "completed-keep",
        }[scenario],
        "scenario": scenario,
        "stage_order": [
            "embedding-materialization",
            "candidate-500",
            "control-100",
            "hidden-gold-score",
            "paired-decision",
        ],
        "provider_calls": 0,
        "network_calls": 0,
        "gold_opened_before_responses": False,
    }


def _index_binding(
    *,
    course_id: str,
    chunks: list[DocumentChunk],
    binding: dict[str, Any],
) -> ApiRetrievalIndexBindingV2:
    embedding = binding["providers"]["embedding"]
    return ApiRetrievalIndexBindingV2(
        instrument_id=INSTRUMENT_ID,
        course_id=course_id,
        release_id=f"{course_id}-action-router-confirmation-v1",
        profile_id="action-router-targeted-atomic-confirmation",
        profile_version="v1",
        chunker_id="unique-atomic-source-registration",
        chunker_version="v1",
        source_set_sha256=source_set_sha256(chunks),
        chunk_count=len(chunks),
        embedding_model=embedding["provider_model"],
        embedding_dimensions=embedding["dimensions"],
        embedding_batch_size=embedding["batch_size"],
        embedding_request_token_limit=embedding["request_token_limit"],
        input_price_usd_per_million=embedding["input_price_usd_per_million"],
        metadata_verified_at=datetime.fromisoformat(binding["verified_at"]),
        bm25_k1=1.2,
        bm25_b=0.75,
        fusion_rank_constant=60,
        fusion_candidate_limit=30,
    )


def _materialize(*, resume: bool) -> dict[str, Any]:
    source = _load_hashed(builder.dataset.SOURCE_PATH)
    public = _load_hashed(builder.CASES)
    binding = _load_hashed(builder.BINDING)
    chunks = [DocumentChunk.model_validate(row) for row in source["chunks"]]
    cases = [EvaluationCaseV1.model_validate(row) for row in public["cases"]]
    by_course: dict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        by_course[str(chunk.metadata["course_id"])].append(chunk)
    embedding = binding["providers"]["embedding"]
    ledger = RetrievalUsageLedger(
        max_cost_usd=1.0,
        price_per_million_input_tokens_usd=embedding[
            "input_price_usd_per_million"
        ],
    )
    embedder = OpenAITextEmbedder(
        os.environ["OPENAI_API_KEY"],
        ledger=ledger,
        model=embedding["provider_model"],
        dimensions=embedding["dimensions"],
        batch_size=embedding["batch_size"],
        request_token_limit=embedding["request_token_limit"],
    )
    store = StreamingRetrievalIndexMaterializerV2(INDEX_ROOT)
    courses: dict[str, Any] = {}
    calls = 0
    cost = 0.0
    for course_id, course_chunks in sorted(by_course.items()):
        course_chunks.sort(key=lambda row: row.id)
        index_binding = _index_binding(
            course_id=course_id,
            chunks=course_chunks,
            binding=binding,
        )
        work_path = store.work_root / f"{index_binding.binding_sha256}.sqlite3"
        manifest = store.materialize(
            index_binding,
            course_chunks,
            embedder,
            resume=resume and work_path.exists(),
        )
        calls += int(manifest.materialization["batch_count"])
        cost += float(manifest.materialization["cost_usd"])
        courses[course_id] = {
            "binding": index_binding.model_dump(mode="json"),
            "artifact_id": manifest.artifact_id,
        }
    _, query_usage = _query_vectors(
        path=QUERY_CACHE,
        cases=cases,
        embedder=embedder,
        model=embedding["provider_model"],
        dimensions=embedding["dimensions"],
        instrument_sha256=_load_hashed(builder.INSTRUMENT)["content_sha256"],
        resume=resume and QUERY_CACHE.exists(),
    )
    calls += int(query_usage["batch_count"])
    cost += float(query_usage["cost_usd"])
    if calls > 20 or cost > 1.0:
        raise ActionRouterCheckpointError("embedding materialization limit exceeded")
    runtime = {
        "schema_version": 1,
        "runtime_id": "academic-factual-qa-action-router-retrieval-runtime-001",
        "instrument_id": INSTRUMENT_ID,
        "source_package": {
            "path": str(builder.dataset.SOURCE_PATH.relative_to(ROOT)),
            "file_sha256": _file_sha256(builder.dataset.SOURCE_PATH),
            "content_sha256": source["content_sha256"],
        },
        "query_cache": {
            "path": str(QUERY_CACHE.relative_to(ROOT)),
            "file_sha256": _file_sha256(QUERY_CACHE),
            "model": embedding["provider_model"],
            "dimensions": embedding["dimensions"],
            "vector_count": 500,
        },
        "index_root": str(INDEX_ROOT.relative_to(ROOT)),
        "courses": courses,
        "embedding_calls": calls,
        "embedding_cost_usd": cost,
        "hidden_gold_path_present": False,
    }
    runtime["content_sha256"] = canonical_json_sha256(runtime)
    product._atomic_write(builder.RETRIEVAL_RUNTIME, runtime)  # noqa: SLF001
    return runtime


@contextmanager
def _configured_product_runner() -> Iterator[None]:
    values = {
        "builder": builder,
        "PROGRAM_ID": INSTRUMENT_ID,
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "OUTPUT_ROOT": OUTPUT_ROOT,
        "CANDIDATE_RESPONSES": CANDIDATE_RESPONSES,
        "CANDIDATE_PROVIDER": CANDIDATE_PROVIDER,
        "CANDIDATE_STATE": CANDIDATE_STATE,
        "CONTROL_RESPONSES": CONTROL_RESPONSES,
        "CONTROL_PROVIDER": CONTROL_PROVIDER,
        "CONTROL_STATE": CONTROL_STATE,
        "CANDIDATE_RESULT": CANDIDATE_RESULT,
        "CONTROL_RESULT": CONTROL_RESULT,
        "PAIRED_RESULT": PAIRED_RESULT,
        "CHECKPOINT_STATE": CHECKPOINT_STATE,
        "ALL_OUTPUTS": ALL_OUTPUTS,
        "preflight": lambda **_: {"status": "ready", "blockers": []},
    }
    previous = {key: getattr(product, key) for key in values}
    old_source = adapter.ACTION_ROUTER_SOURCE_PATH
    old_runtime = adapter.ACTION_ROUTER_RETRIEVAL_RUNTIME_PATH
    try:
        for key, value in values.items():
            setattr(product, key, value)
        adapter.ACTION_ROUTER_SOURCE_PATH = builder.dataset.SOURCE_PATH
        adapter.ACTION_ROUTER_RETRIEVAL_RUNTIME_PATH = builder.RETRIEVAL_RUNTIME
        yield
    finally:
        for key, value in previous.items():
            setattr(product, key, value)
        adapter.ACTION_ROUTER_SOURCE_PATH = old_source
        adapter.ACTION_ROUTER_RETRIEVAL_RUNTIME_PATH = old_runtime


async def execute(*, resume: bool = False) -> dict[str, Any]:
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise ActionRouterCheckpointError(
            "checkpoint preflight blocked: " + ", ".join(readiness["blockers"])
        )
    runtime = _materialize(resume=resume)
    with _configured_product_runner():
        result = await product.execute(resume=resume)
    accounting = dict(result.get("accounting", {}))
    accounting["embedding_calls"] = runtime["embedding_calls"]
    accounting["embedding_cost_usd"] = runtime["embedding_cost_usd"]
    accounting["total_calls"] = int(accounting.get("provider_calls", 0)) + int(
        runtime["embedding_calls"]
    )
    accounting["total_cost_usd"] = float(
        accounting.get("reported_cost_usd", 0.0)
    ) + float(runtime["embedding_cost_usd"])
    result["accounting"] = accounting
    if accounting["total_calls"] > 620 or accounting["total_cost_usd"] > 8.0:
        result["status"] = "invalid-execution"
        result["decision"] = None
    result["source_range_disjoint"] = True
    result["source_family_disjoint"] = False
    result["final_10000_opened"] = False
    state = json.loads(CHECKPOINT_STATE.read_text(encoding="utf-8"))
    state["terminal_result"] = result
    state["status"] = result["status"]
    product._atomic_write(CHECKPOINT_STATE, state)  # noqa: SLF001
    return result


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument(
        "--simulate", choices=("pass", "quality-failure", "provider-failure", "resume")
    )
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
        result = asyncio.run(execute(resume=arguments.resume))
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.simulate:
        result = simulate(scenario=arguments.simulate)
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
