"""Run the sealed IT5002 rapid retrieval ablation without logging course text."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import resource
import subprocess
import time
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.embeddings import Qwen3TextEmbedder
from services.reranking import Qwen3Reranker
from src.digital_twin.grounding import (
    BM25Retriever,
    DenseRetriever,
    DocumentChunk,
    RetrievalHit,
)

from scripts.it5002_rapid_common import (
    DEVELOPMENT_PATH,
    HELDOUT_PATH,
    LOCAL_RUN_ROOT,
    QUERY_INSTRUCTION,
    SEAL_PATH,
    RapidRetrievalCase,
    RapidRetrievalDataset,
    dump_private_json,
    load_course_corpus,
    load_dataset,
    percentile,
    sha256_file,
)


EMBEDDING_REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
RERANKER_REVISION = "e61197ed45024b0ed8a2d74b80b4d909f1255473"
EMBEDDING_MODEL_PATH = (
    Path("data/external/huggingface/hub")
    / "models--Qwen--Qwen3-Embedding-0.6B"
    / "snapshots"
    / EMBEDDING_REVISION
)
RERANKER_MODEL_PATH = (
    Path("data/external/huggingface/hub")
    / "models--Qwen--Qwen3-Reranker-0.6B"
    / "snapshots"
    / RERANKER_REVISION
)
DECOMPOSITION_MODEL = "gemma3:4b"
DECOMPOSITION_DIGEST = "a2af6cc3eb7f"
RUNTIME_FREEZE_PATH = LOCAL_RUN_ROOT / "runtime_freeze.json"
DEVELOPMENT_RESULT_PATH = LOCAL_RUN_ROOT / "development_result.json"
HELDOUT_RESULT_PATH = LOCAL_RUN_ROOT / "heldout_result.json"
HELDOUT_LEDGER_PATH = LOCAL_RUN_ROOT / "heldout_once_ledger.json"
IMPLEMENTATION_FILES = (
    "scripts/it5002_rapid_common.py",
    "scripts/build_it5002_rapid_dataset.py",
    "scripts/run_it5002_retrieval_rapid.py",
    "pyproject.toml",
    "uv.lock",
    "services/embeddings/__init__.py",
    "services/embeddings/qwen3_client.py",
    "services/reranking/__init__.py",
    "services/reranking/qwen3_client.py",
    "src/digital_twin/grounding/__init__.py",
    "src/digital_twin/grounding/models.py",
    "src/digital_twin/grounding/protocols.py",
    "src/digital_twin/grounding/retrieval.py",
    "src/digital_twin/grounding/reranking.py",
)
CONDITIONS = ("R0", "R1", "R2", "R3", "R4", "R5")


class RapidRuntime:
    """Hold the frozen retrieval ladder and reuse its local model indexes."""

    def __init__(self, *, batch_size: int = 8) -> None:
        corpus_started = time.perf_counter()
        corpus = load_course_corpus()
        self.corpus_load_seconds = time.perf_counter() - corpus_started
        self.fixed_bm25 = BM25Retriever(corpus.fixed_chunks, k1=1.2, b=0.75)
        self.structured_bm25 = BM25Retriever(
            corpus.structured_chunks,
            k1=1.2,
            b=0.75,
        )
        self.contextual_bm25 = BM25Retriever(
            corpus.contextual_chunks,
            k1=1.2,
            b=0.75,
        )

        embedding_path = (Path.cwd() / EMBEDDING_MODEL_PATH).resolve()
        reranker_path = (Path.cwd() / RERANKER_MODEL_PATH).resolve()
        self.embedder = Qwen3TextEmbedder(
            embedding_path,
            instruction=QUERY_INSTRUCTION,
            device="mps",
            dtype="float16",
            batch_size=batch_size,
            max_length=2048,
        )
        index_started = time.perf_counter()
        self.structured_dense = DenseRetriever(
            corpus.structured_chunks,
            self.embedder,
            minimum_similarity=-1.0,
        )
        self.contextual_dense = DenseRetriever(
            corpus.contextual_chunks,
            self.embedder,
            minimum_similarity=-1.0,
        )
        self.index_build_seconds = time.perf_counter() - index_started
        self.reranker = Qwen3Reranker(
            reranker_path,
            instruction=QUERY_INSTRUCTION,
            device="mps",
            dtype="float16",
            batch_size=8,
            max_length=2048,
        )
        self.context_chunks = {chunk.id: chunk for chunk in corpus.contextual_chunks}

    def retrieve_all(
        self,
        query: str,
    ) -> tuple[dict[str, list[RetrievalHit]], dict[str, float]]:
        r0, r0_ms = _timed(lambda: self.fixed_bm25.retrieve(query, limit=5))
        structured_lexical, r1_ms = _timed(
            lambda: self.structured_bm25.retrieve(query, limit=20)
        )
        structured_dense, r2_ms = _timed(
            lambda: self.structured_dense.retrieve(query, limit=20)
        )
        r3, r3_fusion_ms = _timed(
            lambda: _fuse(structured_lexical, structured_dense, limit=5)
        )
        contextual_lexical, contextual_lexical_ms = _timed(
            lambda: self.contextual_bm25.retrieve(query, limit=20)
        )
        contextual_dense, contextual_dense_ms = _timed(
            lambda: self.contextual_dense.retrieve(query, limit=20)
        )
        r4_candidates, r4_fusion_ms = _timed(
            lambda: _fuse(
                contextual_lexical,
                contextual_dense,
                limit=40,
            )
        )
        standalone_dense_ms = max(r2_ms, contextual_dense_ms)
        r4_ms = contextual_lexical_ms + standalone_dense_ms + r4_fusion_ms
        r5, rerank_ms = _timed(lambda: self._rerank(query, r4_candidates, limit=5))
        results = {
            "R0": r0,
            "R1": structured_lexical[:5],
            "R2": structured_dense[:5],
            "R3": r3,
            "R4": r4_candidates[:5],
            "R5": r5,
        }
        latencies = {
            "R0": r0_ms,
            "R1": r1_ms,
            "R2": r2_ms,
            "R3": r1_ms + r2_ms + r3_fusion_ms,
            "R4": r4_ms,
            "R5": r4_ms + rerank_ms,
        }
        return results, latencies

    def retrieve_r6(self, query: str) -> tuple[list[RetrievalHit], int]:
        subqueries = _decompose(query)
        query_variants = [query, *subqueries]
        variant_hits: list[list[RetrievalHit]] = []
        for variant in query_variants:
            lexical = self.contextual_bm25.retrieve(variant, limit=20)
            dense = self.contextual_dense.retrieve(variant, limit=20)
            variant_hits.append(_fuse(lexical, dense, limit=40))
        candidates = _fuse_ranked_lists(variant_hits, limit=40)
        return self._rerank(query, candidates, limit=5), len(subqueries)

    def _rerank(
        self,
        query: str,
        candidates: list[RetrievalHit],
        *,
        limit: int,
    ) -> list[RetrievalHit]:
        if not candidates:
            return []
        scores = self.reranker.score(
            query,
            [candidate.chunk.text for candidate in candidates[:40]],
        )
        ranked = sorted(
            zip(candidates[:40], scores, strict=True),
            key=lambda item: (-item[1], item[0].chunk.id),
        )
        return [
            RetrievalHit(
                chunk=candidate.chunk,
                relevance_score=max(0.0, min(1.0, float(score))),
                raw_score=max(0.0, float(score)),
            )
            for candidate, score in ranked[:limit]
        ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        required=True,
        choices=("development", "heldout"),
    )
    parser.add_argument("--confirm-heldout-once", action="store_true")
    args = parser.parse_args()
    if args.phase == "heldout" and not args.confirm_heldout_once:
        raise SystemExit("heldout requires --confirm-heldout-once")

    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    _verify_dataset_hash(DEVELOPMENT_PATH, seal["development_sha256"])
    if args.phase == "development":
        _run_development(seal)
    else:
        _run_heldout(seal)


def _run_development(seal: dict[str, Any]) -> None:
    dataset = load_dataset(DEVELOPMENT_PATH)
    if dataset.split != "development":
        raise ValueError("development file has the wrong split")
    runtime = RapidRuntime(batch_size=8)
    raw = _run_standard_conditions(runtime, dataset)
    thresholds = {
        condition: _calibrate_threshold(raw["cases"], condition)
        for condition in CONDITIONS
    }
    result = _aggregate_result(
        phase="development",
        dataset=dataset,
        raw=raw,
        thresholds=thresholds,
        runtime=runtime,
    )
    dump_private_json(DEVELOPMENT_RESULT_PATH, result)
    runtime_freeze = {
        "freeze_id": "it5002-retrieval-rapid-v1-runtime",
        "frozen_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "development_sha256": seal["development_sha256"],
        "heldout_sha256": seal["heldout_sha256"],
        "implementation_tree_sha256": _implementation_tree_hash(),
        "thresholds": thresholds,
        "batch_size": 8,
        "reranker_batch_size": 8,
        "embedding_revision": EMBEDDING_REVISION,
        "reranker_revision": RERANKER_REVISION,
        "device": "mps",
        "dtype": "float16",
        "embedding_max_length": 2048,
        "reranker_max_length": 2048,
        "decomposition_model": DECOMPOSITION_MODEL,
        "decomposition_digest": DECOMPOSITION_DIGEST,
        "decomposition_prompt_version": "rapid-decomposition-v1",
        "maximum_decomposition_rounds": 1,
        "maximum_subqueries": 3,
        "rrf_k": 60,
        "candidate_limit_per_first_stage": 20,
        "final_limit": 5,
        "metric_limit": 3,
        "query_instruction": QUERY_INSTRUCTION,
        "package_versions": _package_versions(),
    }
    dump_private_json(RUNTIME_FREEZE_PATH, runtime_freeze)
    print(
        json.dumps(
            {
                "phase": "development",
                "status": "complete",
                "thresholds": thresholds,
                "aggregate": result["aggregate"],
                "runtime_freeze_sha256": sha256_file(RUNTIME_FREEZE_PATH),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _run_heldout(seal: dict[str, Any]) -> None:
    if not RUNTIME_FREEZE_PATH.exists():
        raise ValueError("runtime freeze is missing")
    if HELDOUT_LEDGER_PATH.exists():
        raise ValueError("heldout ledger already exists; rerun is prohibited")
    runtime_freeze = json.loads(RUNTIME_FREEZE_PATH.read_text(encoding="utf-8"))
    if runtime_freeze["heldout_sha256"] != seal["heldout_sha256"]:
        raise ValueError("runtime freeze heldout hash differs from the seal")
    if runtime_freeze["implementation_tree_sha256"] != _implementation_tree_hash():
        raise ValueError("implementation changed after development freeze")
    _verify_dataset_hash(HELDOUT_PATH, seal["heldout_sha256"])
    ledger = {
        "run_id": "it5002-retrieval-rapid-v1-heldout-001",
        "started_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": "started",
        "heldout_sha256": seal["heldout_sha256"],
        "runtime_freeze_sha256": sha256_file(RUNTIME_FREEZE_PATH),
        "implementation_tree_sha256": _implementation_tree_hash(),
    }
    dump_private_json(HELDOUT_LEDGER_PATH, ledger)

    dataset = load_dataset(HELDOUT_PATH)
    if dataset.split != "heldout":
        raise ValueError("heldout file has the wrong split")
    runtime = RapidRuntime(batch_size=int(runtime_freeze["batch_size"]))
    raw = _run_standard_conditions(runtime, dataset)
    _append_r6_and_oracle(runtime, dataset, raw)
    result = _aggregate_result(
        phase="heldout",
        dataset=dataset,
        raw=raw,
        thresholds=runtime_freeze["thresholds"],
        runtime=runtime,
    )
    result["runtime_freeze_sha256"] = sha256_file(RUNTIME_FREEZE_PATH)
    result["git_revision"] = _git_revision()
    result["git_dirty"] = _git_dirty()
    dump_private_json(HELDOUT_RESULT_PATH, result)
    ledger.update(
        {
            "completed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "status": "completed",
            "heldout_result_sha256": sha256_file(HELDOUT_RESULT_PATH),
        }
    )
    dump_private_json(HELDOUT_LEDGER_PATH, ledger)
    print(
        json.dumps(
            {
                "phase": "heldout",
                "status": "complete",
                "aggregate": result["aggregate"],
                "result_sha256": sha256_file(HELDOUT_RESULT_PATH),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _run_standard_conditions(
    runtime: RapidRuntime,
    dataset: RapidRetrievalDataset,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    latencies: dict[str, list[float]] = {condition: [] for condition in CONDITIONS}
    for index, case in enumerate(dataset.cases, start=1):
        all_hits, case_latencies = runtime.retrieve_all(case.query)
        for condition in CONDITIONS:
            hits = all_hits[condition]
            serialized = _serialize_case_condition(case, condition, hits)
            serialized["latency_ms"] = case_latencies[condition]
            latencies[condition].append(serialized["latency_ms"])
            cases.append(serialized)
        print(
            f"phase={dataset.split} case={index:02d}/{len(dataset.cases)} complete=true"
        )
    return {"cases": cases, "latencies": latencies}


def _append_r6_and_oracle(
    runtime: RapidRuntime,
    dataset: RapidRetrievalDataset,
    raw: dict[str, Any],
) -> None:
    raw["latencies"]["R6"] = []
    raw["latencies"]["O1"] = []
    multi_cases = [case for case in dataset.cases if case.scenario == "multi_evidence"]
    for index, case in enumerate(multi_cases, start=1):
        _mps_synchronize()
        started = time.perf_counter()
        hits, subquery_count = runtime.retrieve_r6(case.query)
        _mps_synchronize()
        latency_ms = (time.perf_counter() - started) * 1000
        value = _serialize_case_condition(case, "R6", hits)
        value["latency_ms"] = latency_ms
        value["subquery_count"] = subquery_count
        raw["cases"].append(value)
        raw["latencies"]["R6"].append(latency_ms)
        print(f"phase=heldout r6_case={index:02d}/{len(multi_cases)} complete=true")
    for case in dataset.cases:
        if case.expected_action != "answer":
            continue
        raw["cases"].append(
            {
                "case_id": case.case_id,
                "scenario": case.scenario,
                "lecture_id": case.lecture_id,
                "expected_action": "answer",
                "condition": "O1",
                "decision_score": 1.0,
                "latency_ms": 0.0,
                "hits": [
                    {
                        "chunk_id": evidence.chunk_id,
                        "document_id": evidence.document_id,
                        "page_start": evidence.page,
                        "page_end": evidence.page,
                        "content_hash": evidence.content_hash,
                        "relevance_score": 1.0,
                        "raw_score": 1.0,
                    }
                    for evidence in case.required_evidence
                ],
            }
        )
        raw["latencies"]["O1"].append(0.0)


def _serialize_case_condition(
    case: RapidRetrievalCase,
    condition: str,
    hits: list[RetrievalHit],
) -> dict[str, Any]:
    decision_score = _decision_score(hits)
    return {
        "case_id": case.case_id,
        "scenario": case.scenario,
        "lecture_id": case.lecture_id,
        "expected_action": case.expected_action,
        "condition": condition,
        "decision_score": decision_score,
        "hits": [
            {
                "chunk_id": hit.chunk.id,
                "document_id": hit.chunk.document_id,
                "source_artifact_id": hit.chunk.source_artifact_id,
                "source_version": hit.chunk.source_version,
                "page_start": hit.chunk.page_start,
                "page_end": hit.chunk.page_end,
                "content_hash": hit.chunk.content_hash,
                "relevance_score": hit.relevance_score,
                "raw_score": hit.raw_score,
            }
            for hit in hits
        ],
    }


def _aggregate_result(
    *,
    phase: str,
    dataset: RapidRetrievalDataset,
    raw: dict[str, Any],
    thresholds: dict[str, float],
    runtime: RapidRuntime,
) -> dict[str, Any]:
    case_lookup = {case.case_id: case for case in dataset.cases}
    aggregates: dict[str, dict[str, Any]] = {}
    condition_names = sorted({item["condition"] for item in raw["cases"]})
    for condition in condition_names:
        members = [item for item in raw["cases"] if item["condition"] == condition]
        threshold = (
            0.0
            if condition == "O1"
            else float(thresholds.get(condition, thresholds.get("R5", 0.0)))
        )
        scored = [
            _score_case(case_lookup[item["case_id"]], item, threshold)
            for item in members
        ]
        answerable = [item for item in scored if item["expected_action"] == "answer"]
        no_evidence = [item for item in scored if item["expected_action"] == "abstain"]
        complete_numerator = sum(item["complete_evidence"] for item in answerable)
        claim_numerator = sum(item["covered_claims"] for item in answerable)
        claim_denominator = sum(item["total_claims"] for item in answerable)
        no_evidence_numerator = sum(item["correct_abstention"] for item in no_evidence)
        latencies = raw["latencies"][condition]
        aggregates[condition] = {
            "eligible_cases": len(members),
            "answerable_denominator": len(answerable),
            "complete_evidence_numerator": complete_numerator,
            "complete_evidence_success_at_3": (
                complete_numerator / len(answerable) if answerable else None
            ),
            "claim_coverage_numerator": claim_numerator,
            "claim_coverage_denominator": claim_denominator,
            "gold_claim_context_coverage_at_3": (
                claim_numerator / claim_denominator if claim_denominator else None
            ),
            "no_evidence_numerator": no_evidence_numerator,
            "no_evidence_denominator": len(no_evidence),
            "no_evidence_accuracy": (
                no_evidence_numerator / len(no_evidence) if no_evidence else None
            ),
            "threshold": threshold,
            "latency_p50_ms": percentile(latencies, 0.5),
            "latency_p95_ms": percentile(latencies, 0.95),
            "operational_failures": 0,
        }
        for member, score in zip(members, scored, strict=True):
            member["scoring"] = score
            member["threshold"] = threshold

    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_bytes = peak_rss if platform.system() == "Darwin" else peak_rss * 1024
    model_cache_bytes = _directory_size(
        (Path.cwd() / EMBEDDING_MODEL_PATH).resolve()
    ) + _directory_size((Path.cwd() / RERANKER_MODEL_PATH).resolve())
    return {
        "run_id": f"it5002-retrieval-rapid-v1-{phase}",
        "phase": phase,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_id": dataset.dataset_id,
        "dataset_sha256": sha256_file(
            DEVELOPMENT_PATH if phase == "development" else HELDOUT_PATH
        ),
        "case_count": len(dataset.cases),
        "aggregate": aggregates,
        "cases": raw["cases"],
        "operational": {
            "corpus_load_seconds": runtime.corpus_load_seconds,
            "embedding_model_load_seconds": runtime.embedder.model_load_seconds,
            "embedding_index_build_seconds": runtime.index_build_seconds,
            "reranker_model_load_seconds": runtime.reranker.model_load_seconds,
            "peak_rss_bytes": peak_rss_bytes,
            "model_cache_bytes": model_cache_bytes,
            "approximate_cost_usd": 0.0,
            "machine": platform.platform(),
            "python": platform.python_version(),
        },
        "implementation_tree_sha256": _implementation_tree_hash(),
    }


def _score_case(
    case: RapidRetrievalCase,
    result: dict[str, Any],
    threshold: float,
) -> dict[str, Any]:
    predicted_answer = result["decision_score"] >= threshold
    selected_hits = result["hits"][:3] if predicted_answer else []
    if case.expected_action == "abstain":
        return {
            "expected_action": "abstain",
            "predicted_action": "answer" if predicted_answer else "abstain",
            "correct_abstention": not predicted_answer,
            "complete_evidence": False,
            "covered_claims": 0,
            "total_claims": 0,
        }
    evidence_covered = [
        any(_hit_covers_evidence(hit, evidence) for hit in selected_hits)
        for evidence in case.required_evidence
    ]
    claim_covered = [
        evidence_covered[min(index, len(evidence_covered) - 1)]
        for index, _claim in enumerate(case.claims)
    ]
    return {
        "expected_action": "answer",
        "predicted_action": "answer" if predicted_answer else "abstain",
        "correct_abstention": False,
        "complete_evidence": all(evidence_covered),
        "covered_claims": sum(claim_covered),
        "total_claims": len(claim_covered),
        "evidence_units_covered": sum(evidence_covered),
        "evidence_units_total": len(evidence_covered),
    }


def _hit_covers_evidence(hit: dict[str, Any], evidence: Any) -> bool:
    return (
        hit["document_id"] == evidence.document_id
        and hit["page_start"] is not None
        and hit["page_end"] is not None
        and hit["page_start"] <= evidence.page <= hit["page_end"]
    )


def _calibrate_threshold(cases: list[dict[str, Any]], condition: str) -> float:
    negatives = [
        item["decision_score"]
        for item in cases
        if item["condition"] == condition and item["expected_action"] == "abstain"
    ]
    if not negatives:
        return 0.0
    return math.nextafter(max(negatives), math.inf)


def _decision_score(hits: list[RetrievalHit]) -> float:
    if not hits:
        return 0.0
    first = hits[0]
    return float(
        first.raw_score if first.raw_score is not None else first.relevance_score
    )


def _timed(operation: Callable[[], Any]) -> tuple[Any, float]:
    _mps_synchronize()
    started = time.perf_counter()
    result = operation()
    _mps_synchronize()
    return result, (time.perf_counter() - started) * 1000


def _mps_synchronize() -> None:
    import torch

    if torch.backends.mps.is_available():
        torch.mps.synchronize()


def _fuse(
    lexical: list[RetrievalHit],
    dense: list[RetrievalHit],
    *,
    limit: int,
) -> list[RetrievalHit]:
    lists = [lexical[:20], dense[:20]]
    dense_confidence = {hit.chunk.id: hit.relevance_score for hit in dense}
    fused_scores: dict[str, float] = {}
    chunks: dict[str, DocumentChunk] = {}
    for hits in lists:
        for rank, hit in enumerate(hits, start=1):
            chunks[hit.chunk.id] = hit.chunk
            fused_scores[hit.chunk.id] = fused_scores.get(hit.chunk.id, 0.0) + (
                1 / (60 + rank)
            )
    ranked_ids = sorted(
        fused_scores,
        key=lambda identifier: (-fused_scores[identifier], identifier),
    )
    maximum = max(fused_scores.values(), default=1.0)
    return [
        RetrievalHit(
            chunk=chunks[identifier],
            relevance_score=fused_scores[identifier] / maximum,
            raw_score=dense_confidence.get(identifier, 0.0),
        )
        for identifier in ranked_ids[:limit]
    ]


def _fuse_ranked_lists(
    ranked_lists: list[list[RetrievalHit]],
    *,
    limit: int,
) -> list[RetrievalHit]:
    scores: dict[str, float] = {}
    chunks: dict[str, DocumentChunk] = {}
    confidence: dict[str, float] = {}
    for hits in ranked_lists:
        for rank, hit in enumerate(hits, start=1):
            identifier = hit.chunk.id
            chunks[identifier] = hit.chunk
            scores[identifier] = scores.get(identifier, 0.0) + 1 / (60 + rank)
            confidence[identifier] = max(
                confidence.get(identifier, 0.0),
                hit.raw_score or 0.0,
            )
    ranked = sorted(scores, key=lambda identifier: (-scores[identifier], identifier))
    maximum = max(scores.values(), default=1.0)
    return [
        RetrievalHit(
            chunk=chunks[identifier],
            relevance_score=scores[identifier] / maximum,
            raw_score=confidence[identifier],
        )
        for identifier in ranked[:limit]
    ]


def _decompose(query: str) -> list[str]:
    format_schema = {
        "type": "object",
        "properties": {
            "subqueries": {
                "type": "array",
                "items": {"type": "string", "minLength": 5},
                "minItems": 2,
                "maxItems": 3,
            }
        },
        "required": ["subqueries"],
        "additionalProperties": False,
    }
    prompt = f"""
Split the following multi-evidence IT5002 student question into two or at most
three standalone retrieval subqueries. Preserve the original meaning, do not
answer the question, and do not add facts. Return only the required JSON.

Question:
{query}
""".strip()
    payload = json.dumps(
        {
            "model": DECOMPOSITION_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": format_schema,
            "options": {
                "temperature": 0,
                "seed": 5002,
                "num_predict": 300,
            },
            "keep_alive": "20m",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        value = json.loads(json.loads(response.read())["response"])
    subqueries = [
        str(item).strip() for item in value.get("subqueries", []) if str(item).strip()
    ]
    if not 2 <= len(subqueries) <= 3:
        raise ValueError("decomposer returned an invalid subquery count")
    return subqueries


def _verify_dataset_hash(path: Path, expected: str) -> None:
    if not path.exists() or sha256_file(path) != expected:
        raise ValueError(f"dataset hash mismatch: {path.name}")


def _implementation_tree_hash() -> str:
    digest = hashlib.sha256()
    for relative in IMPLEMENTATION_FILES:
        path = Path(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _directory_size(path: Path) -> int:
    seen: set[tuple[int, int]] = set()
    total = 0
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        stat = child.stat()
        identity = (stat.st_dev, stat.st_ino)
        if identity in seen:
            continue
        seen.add(identity)
        total += stat.st_size
    return total


def _package_versions() -> dict[str, str]:
    return {
        name: importlib.metadata.version(name)
        for name in (
            "numpy",
            "pymupdf",
            "sentence-transformers",
            "torch",
            "transformers",
        )
    }


def _git_revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _git_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True,
        ).strip()
    )


if __name__ == "__main__":
    main()
