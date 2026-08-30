#!/usr/bin/env python3
"""Validate, simulate, preflight, and run the API-first retrieval successor."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.embeddings import OpenAITextEmbedder  # noqa: E402
from services.retrieval_provider import RetrievalUsageLedger  # noqa: E402
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
    evidence_ranges_overlap,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.finite_retrieval_evaluation import (  # noqa: E402
    select_untouched_retrieval_cases,
)
from src.digital_twin.evaluation.provider_json import (  # noqa: E402
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
)
from src.digital_twin.grounding import (  # noqa: E402
    ApiRetrievalIndexBindingV2,
    BM25Retriever,
    DocumentChunk,
    StreamingRetrievalIndexMaterializerV2,
    StructuredHierarchicalRetriever,
    deterministic_boundary_action,
    p95,
    should_use_semantic_reranking,
    source_set_sha256,
)
from src.digital_twin.tutor_policy import SourceLabel  # noqa: E402
from src.digital_twin.model_policy import (  # noqa: E402
    OPENAI_EMBEDDING_PRICING_USD_PER_MILLION,
    OPENAI_ROUTINE_REVIEW_MODEL,
    OPENAI_TEXT_EMBEDDING_LARGE_MODEL,
    OPENAI_TEXT_EMBEDDING_SMALL_MODEL,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-api-retrieval-selection-001"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_api_retrieval_selection_001.json"
)
DEFAULT_OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
EXPECTED_METHODS = {
    "M0": "bm25-v1",
    "M1": "openai-small-dense-v1",
    "M2": "bm25-openai-small-rrf-v1",
    "M3": "openai-large-dense-v1",
    "M4": "bm25-openai-large-rrf-v1",
    "M5": "openai-large-hybrid-hierarchy-v1",
    "M6": "M5-bounded-gpt-5.4-nano-rerank-v1",
}


class ApiRetrievalSelectionError(RuntimeError):
    """Raised when the successor cannot preserve its frozen contract."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApiRetrievalSelectionError(f"JSON package unavailable: {path.name}") from error
    if not isinstance(payload, dict):
        raise ApiRetrievalSelectionError(f"JSON package is not an object: {path.name}")
    return payload


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _instrument() -> dict[str, Any]:
    payload = _load_object(INSTRUMENT_PATH)
    expected = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != expected:
        raise ApiRetrievalSelectionError("API retrieval instrument hash drifted")
    return payload


def _verify_package(binding: dict[str, Any], *, rows_key: str) -> dict[str, Any]:
    path = ROOT / str(binding["path"])
    if _file_sha256(path) != binding["file_sha256"]:
        raise ApiRetrievalSelectionError(f"package file hash drifted: {path.name}")
    payload = _load_object(path)
    if payload.get("content_sha256") != binding["content_sha256"]:
        raise ApiRetrievalSelectionError(f"package content hash drifted: {path.name}")
    if not isinstance(payload.get(rows_key), list):
        raise ApiRetrievalSelectionError(f"package rows unavailable: {path.name}")
    return payload


def validate() -> dict[str, Any]:
    instrument = _instrument()
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ApiRetrievalSelectionError("API retrieval instrument identity drifted")
    if instrument.get("status") not in {
        "reviewed-provider-unauthorized",
        "frozen-pending-execution",
    }:
        raise ApiRetrievalSelectionError("API retrieval instrument status drifted")
    authorized = bool(instrument.get("provider_execution_authorized"))
    if authorized != bool(instrument.get("paid_execution_authorized")):
        raise ApiRetrievalSelectionError("API retrieval authority flags disagree")
    if authorized != (instrument.get("status") == "frozen-pending-execution"):
        raise ApiRetrievalSelectionError("API retrieval status and authority drifted")
    methods = {
        str(row["method_id"]): str(row["implementation"])
        for row in instrument.get("methods", [])
    }
    if methods != EXPECTED_METHODS:
        raise ApiRetrievalSelectionError("M0-M6 method bindings drifted")
    candidates = {
        row["model"]: (row["dimensions"], row["input_price_usd_per_million"])
        for row in instrument.get("embedding_candidates", [])
    }
    expected_candidates = {
        OPENAI_TEXT_EMBEDDING_SMALL_MODEL: (1_536, 0.02),
        OPENAI_TEXT_EMBEDDING_LARGE_MODEL: (3_072, 0.13),
    }
    if candidates != expected_candidates:
        raise ApiRetrievalSelectionError("embedding candidate bindings drifted")
    for model, (_, price) in candidates.items():
        if OPENAI_EMBEDDING_PRICING_USD_PER_MILLION.get(model) != price:
            raise ApiRetrievalSelectionError(f"model policy price drifted: {model}")

    source = _verify_package(instrument["source_plan"], rows_key="clusters")
    cases_payload = _verify_package(instrument["development_cases"], rows_key="cases")
    gold_payload = _verify_package(instrument["hidden_gold"], rows_key="gold")
    if len(source["clusters"]) != 2_100 or source.get("private_data_read") is not False:
        raise ApiRetrievalSelectionError("source-plan count or privacy boundary drifted")
    cases = [EvaluationCaseV1.model_validate(row) for row in cases_payload["cases"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in gold_payload["gold"]]
    if len(cases) != 500 or len(gold) != 500:
        raise ApiRetrievalSelectionError("development package count drifted")
    selected = select_untouched_retrieval_cases(cases)
    selected_hash = canonical_json_sha256(sorted(row.case_id for row in selected))
    if selected_hash != instrument["development_cases"]["selected_case_ids_sha256"]:
        raise ApiRetrievalSelectionError("untouched 300-case split drifted")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise ApiRetrievalSelectionError("public and hidden-gold IDs drifted")
    limits = instrument["execution_limits"]
    if (
        limits["maximum_total_calls"] != 104
        or limits["embedding_emergency_stop_usd"] != 1.0
        or limits["global_emergency_stop_usd"] != 2.0
    ):
        raise ApiRetrievalSelectionError("API retrieval execution bounds drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "source_cluster_count": 2_100,
        "selected_development_case_count": 300,
        "method_count": 7,
        "embedding_candidates": sorted(candidates),
        "maximum_total_calls": limits["maximum_total_calls"],
        "maximum_cost_usd": limits["global_emergency_stop_usd"],
        "provider_calls": 0,
        "paid_execution_authorized": authorized,
        "private_data_used": False,
    }


def preflight(*, output_root: Path, resume: bool = False) -> dict[str, Any]:
    instrument = _instrument()
    result = validate()
    technical: list[str] = []
    authority: list[str] = []
    verified_at = datetime.fromisoformat(instrument["metadata"]["verified_at"])
    age_hours = (datetime.now(UTC) - verified_at.astimezone(UTC)).total_seconds() / 3600
    if age_hours < 0 or age_hours > instrument["metadata"]["freshness_hours"]:
        technical.append("provider-metadata-older-than-24-hours")
    if _git_dirty():
        technical.append("working-tree-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        technical.append("openai-credential-missing")
    if output_root.exists() and not resume:
        technical.append("exclusive-output-path-already-exists")
    if resume and not output_root.is_dir():
        technical.append("resume-output-path-missing")
    if not instrument["provider_execution_authorized"]:
        authority.append("provider-execution-not-authorized")
    if not instrument["paid_execution_authorized"]:
        authority.append("paid-execution-not-authorized")
    status = (
        "ready"
        if not technical and not authority
        else "blocked-not-authorized"
        if not technical
        else "blocked-technical"
    )
    return {
        **result,
        "status": status,
        "technical_blockers": technical,
        "authority_blockers": authority,
        "metadata_age_hours": age_hours,
        "model_or_provider_called": False,
        "hidden_gold_opened": False,
    }


def _select_summary(rows: list[dict[str, Any]]) -> str | None:
    passing = [row for row in rows if row["passed"]]
    if not passing:
        return None
    best = max(row["complete_evidence_at_3"] for row in passing)
    near_best = [row for row in passing if best - row["complete_evidence_at_3"] <= 0.02]
    complexity = {identifier: index for index, identifier in enumerate(EXPECTED_METHODS)}
    return min(
        near_best,
        key=lambda row: (
            complexity[row["method_id"]],
            -row["evidence_recall_at_5"],
            row["latency_p95_ms"],
        ),
    )["method_id"]


def simulate(scenario: str) -> dict[str, Any]:
    validate()
    base = {
        "case_count": 300,
        "boundary_accuracy": 1.0,
        "severe_release_count": 0,
        "course_violation_count": 0,
        "source_version_violation_count": 0,
        "latency_p95_ms": 25.0,
    }
    if scenario == "quality-failure":
        rows = [
            {
                **base,
                "method_id": method_id,
                "complete_evidence_at_3": 0.80,
                "evidence_recall_at_5": 0.88,
                "passed": False,
            }
            for method_id in EXPECTED_METHODS
        ]
    else:
        quality = {
            "M0": (0.86, 0.92, False),
            "M1": (0.89, 0.94, False),
            "M2": (0.91, 0.96, True),
            "M3": (0.90, 0.95, True),
            "M4": (0.93, 0.97, True),
            "M5": (0.95, 0.98, True),
            "M6": (0.96, 0.98, True),
        }
        rows = [
            {
                **base,
                "method_id": method_id,
                "complete_evidence_at_3": quality[method_id][0],
                "evidence_recall_at_5": quality[method_id][1],
                "passed": quality[method_id][2],
            }
            for method_id in EXPECTED_METHODS
        ]
    selected = _select_summary(rows)
    if scenario == "identity-drift":
        status = "invalid-execution"
        selected = None
    elif selected is None:
        status = "completed-refine"
    else:
        status = "completed-keep"
    return {
        "instrument_id": INSTRUMENT_ID,
        "scenario": scenario,
        "status": status,
        "selected_method": selected,
        "method_summaries": rows,
        "provider_calls": 0,
        "model_or_provider_called": False,
        "hidden_gold_opened_after_rankings": True,
    }


def _chunks_by_course(source: dict[str, Any]) -> dict[str, list[DocumentChunk]]:
    grouped: dict[str, list[DocumentChunk]] = defaultdict(list)
    ordinals: dict[str, int] = defaultdict(int)
    for row in source["clusters"]:
        course_id = str(row["course_id"])
        grouped[course_id].append(
            DocumentChunk(
                id=str(row["cluster_id"]),
                document_id=str(row["source_artifact_id"]),
                text=str(row["text"]),
                ordinal=ordinals[course_id],
                source_artifact_id=str(row["source_artifact_id"]),
                source_version=int(row["source_version"]),
                source_label=SourceLabel.COURSE_APPROVED,
                locator=(
                    f"{row['source_path']} characters "
                    f"{row['char_start']}–{row['char_end']}"
                ),
                source_checksum=str(row["source_sha256"]),
                retrieval_allowed=True,
                display_allowed=True,
                metadata={
                    "title": str(row["section_heading"]),
                    "course_id": course_id,
                    "char_start": str(row["char_start"]),
                    "char_end": str(row["char_end"]),
                    "source_path": str(row["source_path"]),
                },
            )
        )
        ordinals[course_id] += 1
    return dict(grouped)


class _CachedQueryEmbedder:
    provider_id = "openai"
    endpoint = "https://api.openai.com/v1/embeddings"
    request_token_limit = 50_000
    batch_size = 64

    def __init__(self, *, model: str, dimensions: int, vectors: dict[str, list[float]]):
        self.model_name = model
        self.model = model
        self.model_revision = model
        self.dimensions = dimensions
        self._vectors = vectors

    def embed_documents(self, texts):
        raise AssertionError("runtime index loading must not re-embed documents")

    def embed_query(self, text):
        try:
            return self._vectors[text]
        except KeyError as error:
            raise ApiRetrievalSelectionError("query escaped the frozen cache") from error


def _pack_vector(vector: list[float]) -> bytes:
    import array

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0 or any(not math.isfinite(value) for value in vector):
        raise ApiRetrievalSelectionError("query embedding is invalid")
    values = array.array("f", (value / magnitude for value in vector))
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes()


def _unpack_vector(content: bytes) -> list[float]:
    import array

    values = array.array("f")
    values.frombytes(content)
    if sys.byteorder != "little":
        values.byteswap()
    return list(values)


def _query_vectors(
    *,
    path: Path,
    cases: list[EvaluationCaseV1],
    embedder: OpenAITextEmbedder,
    model: str,
    dimensions: int,
    instrument_sha256: str,
    resume: bool,
) -> tuple[dict[str, list[float]], dict[str, int | float]]:
    if resume and not path.is_file():
        raise ApiRetrievalSelectionError("query-cache resume path is unavailable")
    if not resume and path.exists():
        raise ApiRetrievalSelectionError("query-cache output already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not resume:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS vectors (
            case_id TEXT PRIMARY KEY,
            question_sha256 TEXT NOT NULL,
            vector_blob BLOB NOT NULL,
            vector_sha256 TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS batches (
            batch_index INTEGER PRIMARY KEY,
            case_ids_sha256 TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            cost_usd REAL NOT NULL
        );
        """
    )
    expected = {
        "schema_version": "1",
        "instrument_sha256": instrument_sha256,
        "model": model,
        "dimensions": str(dimensions),
        "case_ids_sha256": canonical_json_sha256([row.case_id for row in cases]),
    }
    actual = dict(connection.execute("SELECT key, value FROM metadata"))
    if resume:
        if any(actual.get(key) != value for key, value in expected.items()):
            connection.close()
            raise ApiRetrievalSelectionError("query-cache resume binding drifted")
    else:
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)", expected.items()
        )
        connection.commit()
    try:
        for batch_index, start in enumerate(range(0, len(cases), 64)):
            batch = cases[start : start + 64]
            batch_hash = canonical_json_sha256([row.case_id for row in batch])
            existing = connection.execute(
                "SELECT case_ids_sha256 FROM batches WHERE batch_index = ?",
                (batch_index,),
            ).fetchone()
            if existing is not None:
                if existing[0] != batch_hash:
                    raise ApiRetrievalSelectionError("query-cache batch binding drifted")
                continue
            before = embedder.usage_snapshot()
            vectors = embedder.embed_documents([row.question for row in batch])
            after = embedder.usage_snapshot()
            packed = [_pack_vector(vector) for vector in vectors]
            if any(len(value) != dimensions * 4 for value in packed):
                raise ApiRetrievalSelectionError("query-cache dimension drifted")
            with connection:
                connection.executemany(
                    "INSERT INTO vectors(case_id, question_sha256, vector_blob, vector_sha256) VALUES (?, ?, ?, ?)",
                    [
                        (
                            case.case_id,
                            hashlib.sha256(case.question.encode("utf-8")).hexdigest(),
                            value,
                            hashlib.sha256(value).hexdigest(),
                        )
                        for case, value in zip(batch, packed, strict=True)
                    ],
                )
                connection.execute(
                    "INSERT INTO batches(batch_index, case_ids_sha256, input_tokens, cost_usd) VALUES (?, ?, ?, ?)",
                    (
                        batch_index,
                        batch_hash,
                        after.input_tokens - before.input_tokens,
                        after.approximate_cost_usd - before.approximate_cost_usd,
                    ),
                )
        rows = connection.execute(
            "SELECT case_id, question_sha256, vector_blob, vector_sha256 FROM vectors"
        ).fetchall()
        if len(rows) != len(cases):
            raise ApiRetrievalSelectionError("query-cache vectors are incomplete")
        by_id = {row.case_id: row for row in cases}
        result: dict[str, list[float]] = {}
        for case_id, question_hash, content, vector_hash in rows:
            case = by_id.get(case_id)
            if (
                case is None
                or hashlib.sha256(case.question.encode("utf-8")).hexdigest() != question_hash
                or hashlib.sha256(content).hexdigest() != vector_hash
            ):
                raise ApiRetrievalSelectionError("query-cache content drifted")
            result[case.question] = _unpack_vector(content)
        if len(result) != len(cases):
            raise ApiRetrievalSelectionError("query-cache questions are not unique")
        totals = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(input_tokens), 0), COALESCE(SUM(cost_usd), 0) FROM batches"
        ).fetchone()
        return result, {
            "batch_count": int(totals[0]),
            "input_tokens": int(totals[1]),
            "cost_usd": float(totals[2]),
        }
    finally:
        connection.close()


def _embedding_binding(
    instrument: dict[str, Any],
    candidate: dict[str, Any],
    *,
    course_id: str,
    chunks: list[DocumentChunk],
) -> ApiRetrievalIndexBindingV2:
    return ApiRetrievalIndexBindingV2(
        instrument_id=INSTRUMENT_ID,
        course_id=course_id,
        release_id=f"{course_id}-academic-open-release-api-v1",
        profile_id="academic-factual-qa-api-retrieval-successor",
        profile_version="v1",
        chunker_id="source-range-clusterer",
        chunker_version="v1",
        source_set_sha256=source_set_sha256(chunks),
        chunk_count=len(chunks),
        embedding_model=candidate["model"],
        embedding_dimensions=candidate["dimensions"],
        embedding_batch_size=candidate["batch_size"],
        embedding_request_token_limit=candidate["request_token_limit"],
        input_price_usd_per_million=candidate["input_price_usd_per_million"],
        metadata_verified_at=datetime.fromisoformat(instrument["metadata"]["verified_at"]),
        bm25_k1=1.2,
        bm25_b=0.75,
        fusion_rank_constant=60,
        fusion_candidate_limit=30,
    )


def _rankings_without_rerank(
    *,
    cases: list[EvaluationCaseV1],
    bm25: dict[str, Any],
    small_dense: dict[str, Any],
    small_hybrid: dict[str, Any],
    large_dense: dict[str, Any],
    large_hybrid: dict[str, Any],
    hierarchy: dict[str, StructuredHierarchicalRetriever],
) -> tuple[
    dict[str, dict[str, list[str]]],
    dict[str, dict[str, float]],
    dict[str, float],
]:
    rankings = {method: {} for method in EXPECTED_METHODS if method != "M6"}
    latencies = {method: {} for method in EXPECTED_METHODS if method != "M6"}
    m5_margins: dict[str, float] = {}
    for case in cases:
        direct = {
            "M0": bm25[case.course_id],
            "M1": small_dense[case.course_id],
            "M2": small_hybrid[case.course_id],
            "M3": large_dense[case.course_id],
            "M4": large_hybrid[case.course_id],
        }
        for method_id, retriever in direct.items():
            started = time.perf_counter()
            hits = retriever.retrieve(case.question, limit=5)
            latencies[method_id][case.case_id] = (time.perf_counter() - started) * 1000
            rankings[method_id][case.case_id] = [row.chunk.id for row in hits]
        started = time.perf_counter()
        plan = hierarchy[case.course_id].plan(case.question, limit=5)
        latencies["M5"][case.case_id] = (time.perf_counter() - started) * 1000
        rankings["M5"][case.case_id] = [row.chunk.id for row in plan.hits]
        m5_margins[case.case_id] = (
            plan.hits[0].relevance_score - plan.hits[1].relevance_score
            if len(plan.hits) > 1
            else (plan.hits[0].relevance_score if plan.hits else 0.0)
        )
    return rankings, latencies, m5_margins


def _rerank_schema(expected_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": len(expected_ids),
                "maxItems": len(expected_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["case_id", "ranked_chunk_ids"],
                    "properties": {
                        "case_id": {"type": "string", "enum": sorted(expected_ids)},
                        "ranked_chunk_ids": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 5,
                            "items": {"type": "string"},
                        },
                    },
                },
            }
        },
    }


async def _nano_rerank(
    *,
    cases: list[EvaluationCaseV1],
    rankings: dict[str, dict[str, list[str]]],
    score_margins: dict[str, float],
    chunks_by_id: dict[str, DocumentChunk],
    output_root: Path,
    resume: bool,
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    candidates = []
    cases_by_id = {row.case_id: row for row in cases}
    for case in cases:
        identifiers = rankings["M5"][case.case_id]
        if should_use_semantic_reranking(
            case.question,
            top_score_margin=score_margins[case.case_id],
        ):
            candidates.append(case.case_id)
    selected = sorted(
        candidates,
        key=lambda value: hashlib.sha256(f"api-rerank-v1:{value}".encode()).hexdigest(),
    )[: math.floor(len(cases) * 0.4)]
    output = {case_id: list(values) for case_id, values in rankings["M5"].items()}
    if not selected:
        return output, {"provider_calls": 0, "reported_cost_usd": 0.0}
    binding = {
        "binding_id": f"{INSTRUMENT_ID}-nano-rerank-v1",
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "first_party_endpoint": True,
        "api_url": "https://api.openai.com/v1/responses",
        "credential_environment_variable": "OPENAI_API_KEY",
        "provider_model": OPENAI_ROUTINE_REVIEW_MODEL,
        "documented_revision": OPENAI_ROUTINE_REVIEW_MODEL,
        "reasoning_effort": "low",
        "max_output_tokens": 1_400,
        "temperature": 0,
        "seed": 20260830,
        "timeout_seconds": 60,
        "maximum_transport_retries": 0,
        "pricing_usd_per_million_input_tokens": 0.20,
        "pricing_usd_per_million_output_tokens": 1.25,
    }
    ledger_path = output_root / "nano-reranking.sqlite3"
    ledger = ProviderCallLedgerV1(
        ledger_path,
        run_binding={
            "instrument_id": INSTRUMENT_ID,
            "instrument_sha256": _instrument()["content_sha256"],
            "case_ids": selected,
            "binding": binding,
        },
        maximum_calls=12,
        maximum_cost_usd=1.0,
        maximum_transport_retries_total=0,
        resume=resume and ledger_path.exists(),
    )
    transport = DirectProviderJsonTransport(binding)
    try:
        semantic_failure: dict[str, Any] | None = None
        for number, start in enumerate(range(0, len(selected), 10), start=1):
            batch_ids = selected[start : start + 10]
            expected = {case_id: rankings["M5"][case_id] for case_id in batch_ids}
            prompt = [
                {
                    "case_id": case_id,
                    "question": cases_by_id[case_id].question,
                    "candidates": [
                        {
                            "chunk_id": chunk_id,
                            "text": chunks_by_id[chunk_id].text[:1_000],
                        }
                        for chunk_id in expected[case_id]
                    ],
                }
                for case_id in batch_ids
            ]
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"rerank-{number:03d}",
                provider_role="bounded-evidence-ranker",
                system=(
                    "Rank only the supplied chunk IDs by complete support for each "
                    "question. Do not answer and never introduce an ID."
                ),
                prompt=json.dumps(prompt, sort_keys=True),
                task="api-first-retrieval-selection-rerank",
                schema=_rerank_schema(batch_ids),
            )
            rows = response.content["items"]
            if {row["case_id"] for row in rows} != set(batch_ids):
                semantic_failure = {
                    "request_key": f"rerank-{number:03d}",
                    "reason": "case-id-set-drift",
                }
                break
            for row in rows:
                identifiers = list(row["ranked_chunk_ids"])
                if (
                    len(identifiers) != len(set(identifiers))
                    or set(identifiers) != set(expected[row["case_id"]])
                ):
                    semantic_failure = {
                        "request_key": f"rerank-{number:03d}",
                        "case_id": row["case_id"],
                        "reason": "chunk-id-set-drift",
                    }
                    break
                output[row["case_id"]] = identifiers
            if semantic_failure is not None:
                # The optional M6 method fails closed after its first semantic
                # defect. Preserve its response, make no retry or later M6 call,
                # and retain M5 rankings only as diagnostic placeholders.
                output = {
                    case_id: list(values)
                    for case_id, values in rankings["M5"].items()
                }
                break
        ledger.mark_complete()
        snapshot = ledger.snapshot()
        snapshot["reranked_case_ids"] = selected
        snapshot["method_status"] = (
            "failed-semantic-output" if semantic_failure else "completed"
        )
        snapshot["semantic_failure"] = semantic_failure
        return output, snapshot
    except BaseException:
        if ledger.snapshot()["status"] == "running":
            ledger.mark_interrupted()
        raise
    finally:
        ledger.close()


def _covered(required, chunks: list[DocumentChunk]) -> bool:
    for chunk in chunks:
        try:
            candidate = required.model_copy(
                update={
                    "source_artifact_id": chunk.source_artifact_id or chunk.document_id,
                    "source_version": chunk.source_version,
                    "source_sha256": chunk.source_checksum,
                    "char_start": int(chunk.metadata["char_start"]),
                    "char_end": int(chunk.metadata["char_end"]),
                    "region_id": chunk.region_id,
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
        if evidence_ranges_overlap(required, candidate):
            return True
    return False


def _score(
    *,
    cases: list[EvaluationCaseV1],
    gold: dict[str, EvaluationGoldV1],
    rankings: dict[str, dict[str, list[str]]],
    latencies: dict[str, dict[str, float]],
    chunks_by_id: dict[str, DocumentChunk],
    unavailable_methods: set[str] | None = None,
) -> list[dict[str, Any]]:
    unavailable_methods = unavailable_methods or set()
    summaries = []
    for method_id in EXPECTED_METHODS:
        observations = []
        for case in cases:
            reference = gold[case.case_id]
            chunks = [chunks_by_id[value] for value in rankings[method_id][case.case_id]]
            required = [item for claim in reference.claims for item in claim.evidence_refs]
            action = deterministic_boundary_action(case.question) or (
                "answer" if chunks else "abstain"
            )
            boundary = reference.expected_action != EvaluationAction.ANSWER
            observations.append(
                {
                    "answerable": not boundary,
                    "evidence_at_3": bool(required)
                    and all(_covered(item, chunks[:3]) for item in required),
                    "recall_at_5": (
                        sum(_covered(item, chunks[:5]) for item in required) / len(required)
                        if required
                        else 1.0
                    ),
                    "boundary_correct": not boundary
                    or action == reference.expected_action.value,
                    "severe": boundary and action == "answer",
                    "course_violation": any(
                        chunk.metadata.get("course_id") != case.course_id for chunk in chunks
                    ),
                    "version_violation": any(
                        chunk.source_version < 1 for chunk in chunks
                    ),
                    "latency_ms": latencies[method_id][case.case_id],
                }
            )
        answerable = [row for row in observations if row["answerable"]]
        boundary = [row for row in observations if not row["answerable"]]
        complete = sum(row["evidence_at_3"] for row in answerable) / len(answerable)
        recall = sum(row["recall_at_5"] for row in answerable) / len(answerable)
        boundary_accuracy = sum(row["boundary_correct"] for row in boundary) / len(boundary)
        latency = p95([row["latency_ms"] for row in observations])
        severe = sum(row["severe"] for row in observations)
        course = sum(row["course_violation"] for row in observations)
        version = sum(row["version_violation"] for row in observations)
        summaries.append(
            {
                "method_id": method_id,
                "case_count": len(observations),
                "complete_evidence_at_3": complete,
                "evidence_recall_at_5": recall,
                "boundary_accuracy": boundary_accuracy,
                "severe_release_count": severe,
                "course_violation_count": course,
                "source_version_violation_count": version,
                "latency_p95_ms": latency,
                "operational_failure_count": int(method_id in unavailable_methods),
                "passed": (
                    method_id not in unavailable_methods
                    and complete >= 0.90
                    and recall >= 0.95
                    and boundary_accuracy >= 0.98
                    and severe == 0
                    and course == 0
                    and version == 0
                    and latency <= 2_000
                ),
            }
        )
    return summaries


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    payload = dict(payload)
    payload["content_sha256"] = canonical_json_sha256(payload)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def execute(*, output_root: Path, resume: bool) -> dict[str, Any]:
    instrument = _instrument()
    check = preflight(output_root=output_root, resume=resume)
    if check["status"] != "ready":
        raise ApiRetrievalSelectionError(
            "live API retrieval preflight is not ready: "
            + ", ".join(check["technical_blockers"] + check["authority_blockers"])
        )
    output_root.mkdir(parents=True, exist_ok=resume)
    source = _verify_package(instrument["source_plan"], rows_key="clusters")
    cases_payload = _verify_package(instrument["development_cases"], rows_key="cases")
    all_cases = [EvaluationCaseV1.model_validate(row) for row in cases_payload["cases"]]
    cases = select_untouched_retrieval_cases(all_cases)
    chunks_by_course = _chunks_by_course(source)
    chunks_by_id = {
        chunk.id: chunk for rows in chunks_by_course.values() for chunk in rows
    }
    bm25 = {course: BM25Retriever(rows) for course, rows in chunks_by_course.items()}
    loaded_by_model: dict[str, dict[str, Any]] = {}
    usage_by_model: dict[str, dict[str, Any]] = {}
    index_root = output_root / "indexes"
    store = StreamingRetrievalIndexMaterializerV2(index_root)
    for candidate in instrument["embedding_candidates"]:
        ledger = RetrievalUsageLedger(
            max_cost_usd=instrument["execution_limits"]["embedding_emergency_stop_usd"],
            price_per_million_input_tokens_usd=candidate["input_price_usd_per_million"],
        )
        live = OpenAITextEmbedder(
            os.environ["OPENAI_API_KEY"],
            ledger=ledger,
            model=candidate["model"],
            dimensions=candidate["dimensions"],
            batch_size=candidate["batch_size"],
            request_token_limit=candidate["request_token_limit"],
        )
        bindings = {}
        manifests = {}
        for course_id, chunks in sorted(chunks_by_course.items()):
            binding = _embedding_binding(
                instrument, candidate, course_id=course_id, chunks=chunks
            )
            bindings[course_id] = binding
            ledger_path = store.work_root / f"{binding.binding_sha256}.sqlite3"
            manifests[course_id] = store.materialize(
                binding,
                chunks,
                live,
                resume=resume and ledger_path.exists(),
            )
        query_path = output_root / f"query-vectors-{candidate['model']}.sqlite3"
        query_vectors, query_usage = _query_vectors(
            path=query_path,
            cases=cases,
            embedder=live,
            model=candidate["model"],
            dimensions=candidate["dimensions"],
            instrument_sha256=instrument["content_sha256"],
            resume=resume and query_path.exists(),
        )
        cache = _CachedQueryEmbedder(
            model=candidate["model"],
            dimensions=candidate["dimensions"],
            vectors=query_vectors,
        )
        loaded_by_model[candidate["model"]] = {
            course_id: store.load(
                manifests[course_id].artifact_id,
                expected_binding=bindings[course_id],
                embedder=cache,
            )
            for course_id in sorted(chunks_by_course)
        }
        usage_by_model[candidate["model"]] = {
            "request_count": sum(
                int(manifest.materialization["batch_count"])
                for manifest in manifests.values()
            )
            + int(query_usage["batch_count"]),
            "input_tokens": sum(
                int(manifest.materialization["input_tokens"])
                for manifest in manifests.values()
            )
            + int(query_usage["input_tokens"]),
            "approximate_cost_usd": sum(
                float(manifest.materialization["cost_usd"])
                for manifest in manifests.values()
            )
            + float(query_usage["cost_usd"]),
            "query_batch_count": int(query_usage["batch_count"]),
            "artifact_ids": {
                course_id: manifest.artifact_id
                for course_id, manifest in sorted(manifests.items())
            },
        }

    small = loaded_by_model[OPENAI_TEXT_EMBEDDING_SMALL_MODEL]
    large = loaded_by_model[OPENAI_TEXT_EMBEDDING_LARGE_MODEL]
    hierarchy = {
        course_id: StructuredHierarchicalRetriever(
            large[course_id].retriever,
            chunks_by_course[course_id],
        )
        for course_id in chunks_by_course
    }
    rankings, latencies, score_margins = _rankings_without_rerank(
        cases=cases,
        bm25=bm25,
        small_dense={key: value.dense_retriever for key, value in small.items()},
        small_hybrid={key: value.retriever for key, value in small.items()},
        large_dense={key: value.dense_retriever for key, value in large.items()},
        large_hybrid={key: value.retriever for key, value in large.items()},
        hierarchy=hierarchy,
    )
    reranked, rerank_usage = asyncio.run(
        _nano_rerank(
            cases=cases,
            rankings=rankings,
            score_margins=score_margins,
            chunks_by_id=chunks_by_id,
            output_root=output_root,
            resume=resume,
        )
    )
    rankings["M6"] = reranked
    unavailable_methods = (
        {"M6"} if rerank_usage.get("method_status") != "completed" else set()
    )
    latencies["M6"] = dict(latencies["M5"])
    for case_id in rerank_usage.get("reranked_case_ids", []):
        latencies["M6"][case_id] += float(
            rerank_usage.get("maximum_latency_ms", 0.0)
        )
    embedding_calls = sum(
        int(row["request_count"]) for row in usage_by_model.values()
    )
    embedding_cost = sum(
        float(row["approximate_cost_usd"]) for row in usage_by_model.values()
    )
    total_calls = embedding_calls + int(rerank_usage.get("provider_calls", 0))
    total_cost = embedding_cost + float(rerank_usage.get("reported_cost_usd", 0.0))
    if (
        embedding_calls > instrument["execution_limits"]["maximum_embedding_and_query_calls"]
        or total_calls > instrument["execution_limits"]["maximum_total_calls"]
        or embedding_cost > instrument["execution_limits"]["embedding_emergency_stop_usd"]
        or total_cost > instrument["execution_limits"]["global_emergency_stop_usd"]
    ):
        raise ApiRetrievalSelectionError("API retrieval accounting exceeded a frozen limit")
    ranking_payload = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "code_revision": _git_revision(),
        "case_ids": [row.case_id for row in cases],
        "methods": rankings,
        "latencies_ms": latencies,
        "m5_score_margins": score_margins,
        "method_statuses": {
            method_id: (
                rerank_usage.get("method_status")
                if method_id == "M6"
                else "completed"
            )
            for method_id in EXPECTED_METHODS
        },
        "gold_loaded": False,
    }
    ranking_path = output_root / "public-rankings.json"
    _atomic_json(ranking_path, ranking_payload)

    gold_payload = _verify_package(instrument["hidden_gold"], rows_key="gold")
    selected_ids = {row.case_id for row in cases}
    gold = {
        row.case_id: row
        for row in (
            EvaluationGoldV1.model_validate(value) for value in gold_payload["gold"]
        )
        if row.case_id in selected_ids
    }
    summaries = _score(
        cases=cases,
        gold=gold,
        rankings=rankings,
        latencies=latencies,
        chunks_by_id=chunks_by_id,
        unavailable_methods=unavailable_methods,
    )
    selected = _select_summary(summaries)
    result = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "status": "completed-keep" if selected else "completed-refine",
        "selected_method": selected or "none",
        "method_summaries": summaries,
        "embedding_usage": usage_by_model,
        "reranking_usage": rerank_usage,
        "provider_calls": total_calls,
        "reported_cost_usd": total_cost,
        "rankings_sha256": _file_sha256(ranking_path),
        "gold_loaded_only_after_rankings_persisted": True,
        "private_data_used": False,
    }
    _atomic_json(output_root / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--simulate", choices=("pass", "quality-failure", "identity-drift"))
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    if args.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
        result = execute(output_root=args.output_root, resume=args.resume)
    elif args.preflight:
        result = preflight(output_root=args.output_root, resume=args.resume)
    elif args.simulate:
        result = simulate(args.simulate)
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
