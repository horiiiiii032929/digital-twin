"""Dry-run or execute the budget-bounded hosted retrieval development preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from services.embeddings import JinaTextEmbedder
from services.jina_api import JinaUsageLedger, estimate_input_tokens
from services.reranking import JinaReranker
from src.digital_twin.grounding import (
    BM25Retriever,
    DenseRetriever,
    ReciprocalRankFusionRetriever,
    RerankingRetriever,
    RetrievalHit,
)

from scripts.it5002_rapid_common import (
    DEVELOPMENT_PATH,
    MANIFEST_PATH,
    RapidRetrievalCase,
    load_course_corpus,
    load_dataset,
    percentile,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = (
    ROOT
    / "experiments"
    / "runs"
    / "it5002_hosted_retrieval_v1"
    / "development_result.json"
)
PERMISSION_VALUE = "user_authorized_jina_retrieval_evaluation_2026-07-27"
CONDITIONS = ("H0", "H1", "H2", "H3")
PRICE_PER_MILLION_INPUT_TOKENS_USD = 0.05


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute-development",
        action="store_true",
        help="Make provider calls; omission performs an offline dry-run.",
    )
    parser.add_argument(
        "--allow-external-provider",
        action="store_true",
        help="Required acknowledgment before transmitting approved course content.",
    )
    parser.add_argument("--max-cost-usd", type=float, default=1.0)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()
    corpus = load_course_corpus()
    dataset = load_dataset(DEVELOPMENT_PATH)
    require_permission(corpus.manifest)
    estimate = estimate_preflight(corpus.structured_chunks, dataset.cases)
    estimate["max_cost_usd"] = arguments.max_cost_usd
    if estimate["estimated_cost_usd"] > arguments.max_cost_usd:
        raise ValueError("offline estimate exceeds the declared cost cap")

    if not arguments.execute_development:
        print(json.dumps({"mode": "dry-run", **estimate}, indent=2))
        return
    if not arguments.allow_external_provider:
        raise ValueError(
            "--allow-external-provider is required for a potentially billable call"
        )
    api_key = load_api_key()
    if not api_key:
        raise ValueError("JINA_API_KEY is not configured in the environment")

    result = execute_development(
        corpus=corpus,
        dataset=dataset,
        api_key=api_key,
        max_cost_usd=arguments.max_cost_usd,
        estimate=estimate,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "mode": "execute-development",
                "output": str(arguments.output),
                "run_id": result["run_id"],
                "provider_requests": result["operational"]["provider_requests"],
                "provider_input_tokens": result["operational"][
                    "provider_input_tokens"
                ],
                "approximate_cost_usd": result["operational"][
                    "approximate_cost_usd"
                ],
                "status": "completed",
            },
            indent=2,
        )
    )


def load_api_key(env_path: Path = ROOT / ".env") -> str:
    configured = os.environ.get("JINA_API_KEY", "").strip()
    if configured:
        return configured
    if not env_path.is_file():
        return ""
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == "JINA_API_KEY":
            return value.strip().strip("\"'")
    return ""


def require_permission(manifest: dict[str, Any]) -> None:
    observed = manifest["permissions"]["external_provider_use"]
    if observed != PERMISSION_VALUE:
        raise ValueError(
            "corpus manifest does not authorize the frozen Jina provider boundary"
        )


def estimate_preflight(
    chunks: list[Any],
    cases: list[RapidRetrievalCase],
) -> dict[str, Any]:
    chunk_texts = [chunk.text for chunk in chunks]
    document_tokens = estimate_input_tokens(*chunk_texts)
    query_tokens = 3 * estimate_input_tokens(*(case.query for case in cases))
    longest_candidates = sorted(
        (len(text) for text in chunk_texts),
        reverse=True,
    )[:40]
    rerank_characters = sum(
        sum(longest_candidates) + len(case.query) * len(longest_candidates)
        for case in cases
    )
    rerank_tokens = max(1, math.ceil(rerank_characters / 3))
    total_tokens = document_tokens + query_tokens + rerank_tokens
    return {
        "corpus_id": "it5002-lectures-v1",
        "dataset_id": "it5002-retrieval-rapid-v1-development",
        "document_count": 13,
        "chunk_count": len(chunks),
        "case_count": len(cases),
        "conditions": list(CONDITIONS),
        "estimated_input_tokens_upper_bound": total_tokens,
        "estimated_cost_usd": (
            total_tokens * PRICE_PER_MILLION_INPUT_TOKENS_USD / 1_000_000
        ),
        "permission": PERMISSION_VALUE,
        "provider": "Jina Search Foundation API",
        "embedding_model": "jina-embeddings-v3",
        "reranking_model": "jina-reranker-v3",
        "scope": "development-only",
        "sealed_split_accessed": False,
    }


def execute_development(
    *,
    corpus: Any,
    dataset: Any,
    api_key: str,
    max_cost_usd: float,
    estimate: dict[str, Any],
) -> dict[str, Any]:
    ledger = JinaUsageLedger(
        max_cost_usd=max_cost_usd,
        price_per_million_input_tokens_usd=PRICE_PER_MILLION_INPUT_TOKENS_USD,
    )
    bm25 = BM25Retriever(corpus.structured_chunks)
    embedder = JinaTextEmbedder(api_key, ledger=ledger)
    index_started = time.perf_counter()
    dense = DenseRetriever(corpus.structured_chunks, embedder)
    index_build_seconds = time.perf_counter() - index_started
    hybrid = ReciprocalRankFusionRetriever(
        [bm25, dense],
        rank_constant=60,
        candidate_limit=20,
    )
    reranked = RerankingRetriever(
        hybrid,
        JinaReranker(api_key, ledger=ledger),
        candidate_limit=40,
    )
    retrievers = {
        "H0": bm25,
        "H1": dense,
        "H2": hybrid,
        "H3": reranked,
    }

    raw_cases: list[dict[str, Any]] = []
    latencies: dict[str, list[float]] = {condition: [] for condition in CONDITIONS}
    for case in dataset.cases:
        for condition in CONDITIONS:
            started = time.perf_counter()
            hits = retrievers[condition].retrieve(case.query, limit=5)
            latency_ms = (time.perf_counter() - started) * 1000
            latencies[condition].append(latency_ms)
            raw_cases.append(serialize_hits(case, condition, hits, latency_ms))

    thresholds = {
        condition: calibrate_threshold(raw_cases, condition)
        for condition in CONDITIONS
    }
    scored = [
        {
            **item,
            "threshold": thresholds[item["condition"]],
            "scoring": score_case(
                _case_by_id(dataset.cases, item["case_id"]),
                item,
                thresholds[item["condition"]],
            ),
        }
        for item in raw_cases
    ]
    return {
        "run_id": "it5002-hosted-retrieval-v1-development",
        "phase": "development",
        "scope": "development-only; no final method selection",
        "created_at_epoch_seconds": int(time.time()),
        "dataset_id": dataset.dataset_id,
        "dataset_sha256": sha256_file(DEVELOPMENT_PATH),
        "corpus_id": corpus.manifest["corpus_id"],
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "permission": PERMISSION_VALUE,
        "provider": {
            "name": "Jina Search Foundation API",
            "embedding_model": "jina-embeddings-v3",
            "reranking_model": "jina-reranker-v3",
            "embedding_endpoint": "/v1/embeddings",
            "reranking_endpoint": "/v1/rerank",
        },
        "configuration": {
            "conditions": list(CONDITIONS),
            "final_k": 5,
            "scoring_k": 3,
            "hybrid_candidate_limit": 20,
            "reranking_candidate_limit": 40,
            "max_cost_usd": max_cost_usd,
            "price_per_million_input_tokens_usd": (
                PRICE_PER_MILLION_INPUT_TOKENS_USD
            ),
        },
        "aggregate": aggregate(scored, latencies),
        "primary_contrast": paired_contrast(scored),
        "cases": scored,
        "operational": {
            "document_index_build_seconds": index_build_seconds,
            "provider_requests": ledger.request_count,
            "provider_input_tokens": ledger.input_tokens,
            "approximate_cost_usd": ledger.approximate_cost_usd,
            "offline_estimate": estimate,
        },
        "code": repository_state(),
    }


def serialize_hits(
    case: RapidRetrievalCase,
    condition: str,
    hits: list[RetrievalHit],
    latency_ms: float,
) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "scenario": case.scenario,
        "lecture_id": case.lecture_id,
        "expected_action": case.expected_action,
        "condition": condition,
        "decision_score": decision_score(hits),
        "latency_ms": latency_ms,
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


def calibrate_threshold(cases: list[dict[str, Any]], condition: str) -> float:
    negative_scores = [
        item["decision_score"]
        for item in cases
        if item["condition"] == condition and item["expected_action"] == "abstain"
    ]
    if not negative_scores:
        return 0.0
    return math.nextafter(max(negative_scores), math.inf)


def score_case(
    case: RapidRetrievalCase,
    result: dict[str, Any],
    threshold: float,
) -> dict[str, Any]:
    predicted_answer = result["decision_score"] >= threshold
    selected_hits = result["hits"][:3] if predicted_answer else []
    if case.expected_action == "abstain":
        return {
            "predicted_action": "answer" if predicted_answer else "abstain",
            "correct_abstention": not predicted_answer,
            "complete_evidence": False,
            "covered_claims": 0,
            "total_claims": 0,
        }
    evidence_covered = [
        any(hit_covers_evidence(hit, evidence) for hit in selected_hits)
        for evidence in case.required_evidence
    ]
    claim_covered = [
        evidence_covered[min(index, len(evidence_covered) - 1)]
        for index, _claim in enumerate(case.claims)
    ]
    return {
        "predicted_action": "answer" if predicted_answer else "abstain",
        "correct_abstention": False,
        "complete_evidence": all(evidence_covered),
        "covered_claims": sum(claim_covered),
        "total_claims": len(claim_covered),
        "evidence_units_covered": sum(evidence_covered),
        "evidence_units_total": len(evidence_covered),
    }


def hit_covers_evidence(hit: dict[str, Any], evidence: Any) -> bool:
    return (
        hit["document_id"] == evidence.document_id
        and hit["page_start"] is not None
        and hit["page_end"] is not None
        and hit["page_start"] <= evidence.page <= hit["page_end"]
    )


def aggregate(
    scored: list[dict[str, Any]],
    latencies: dict[str, list[float]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for condition in CONDITIONS:
        members = [item for item in scored if item["condition"] == condition]
        answerable = [
            item for item in members if item["expected_action"] == "answer"
        ]
        no_evidence = [
            item for item in members if item["expected_action"] == "abstain"
        ]
        complete = sum(
            item["scoring"]["complete_evidence"] for item in answerable
        )
        covered_claims = sum(
            item["scoring"]["covered_claims"] for item in answerable
        )
        total_claims = sum(
            item["scoring"]["total_claims"] for item in answerable
        )
        abstained = sum(
            item["scoring"]["correct_abstention"] for item in no_evidence
        )
        output[condition] = {
            "complete_evidence": {
                "numerator": complete,
                "denominator": len(answerable),
                "rate": complete / len(answerable),
            },
            "claim_coverage": {
                "numerator": covered_claims,
                "denominator": total_claims,
                "rate": covered_claims / total_claims,
            },
            "development_abstention_calibration": {
                "numerator": abstained,
                "denominator": len(no_evidence),
                "rate": abstained / len(no_evidence),
            },
            "latency_ms": {
                "p50": percentile(latencies[condition], 0.5),
                "p95": percentile(latencies[condition], 0.95),
            },
        }
    return output


def paired_contrast(scored: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {
        (item["condition"], item["case_id"]): item
        for item in scored
        if item["condition"] in {"H0", "H3"}
        and item["expected_action"] == "answer"
    }
    case_ids = sorted(
        case_id for condition, case_id in by_key if condition == "H0"
    )
    pairs = [
        (
            bool(by_key[("H0", case_id)]["scoring"]["complete_evidence"]),
            bool(by_key[("H3", case_id)]["scoring"]["complete_evidence"]),
        )
        for case_id in case_ids
    ]
    wins = sum(not control and candidate for control, candidate in pairs)
    losses = sum(control and not candidate for control, candidate in pairs)
    return {
        "contrast": "H3-minus-H0",
        "candidate_wins": wins,
        "control_wins": losses,
        "net_additional_successes": wins - losses,
        "denominator": len(pairs),
    }


def decision_score(hits: list[RetrievalHit]) -> float:
    if not hits:
        return 0.0
    first = hits[0]
    return float(
        first.raw_score if first.raw_score is not None else first.relevance_score
    )


def repository_state() -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    implementation_files = [
        Path(__file__),
        ROOT / "services" / "jina_api.py",
        ROOT / "services" / "embeddings" / "jina_client.py",
        ROOT / "services" / "reranking" / "jina_client.py",
    ]
    implementation_hash = hashlib.sha256()
    for path in implementation_files:
        implementation_hash.update(path.read_bytes())
    return {
        "revision": revision,
        "working_tree_dirty": dirty,
        "implementation_sha256": implementation_hash.hexdigest(),
    }


def _case_by_id(
    cases: list[RapidRetrievalCase],
    case_id: str,
) -> RapidRetrievalCase:
    return next(case for case in cases if case.case_id == case_id)


if __name__ == "__main__":
    main()
