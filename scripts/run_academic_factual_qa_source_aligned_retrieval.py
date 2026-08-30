#!/usr/bin/env python3
"""Run the AFQC-101 source-aligned multi-method retrieval confirmation."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.embeddings.openai_client import OpenAITextEmbedder  # noqa: E402
from services.retrieval_provider import RetrievalUsageLedger  # noqa: E402
from scripts.run_academic_factual_qa_api_retrieval_selection import (  # noqa: E402
    _CachedQueryEmbedder,
    _query_vectors,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    CanonicalEvidenceRefV1,
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
    evidence_ranges_overlap,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.models import ComponentEvaluationRecord  # noqa: E402
from src.digital_twin.evaluation.finite_retrieval_evaluation import (  # noqa: E402
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.api_retrieval_index import (  # noqa: E402
    ApiRetrievalIndexBindingV2,
    StreamingRetrievalIndexMaterializerV2,
)
from src.digital_twin.grounding.hierarchical_retrieval import (  # noqa: E402
    StructuredHierarchicalRetriever,
    deterministic_boundary_action,
    p95,
)
from src.digital_twin.grounding.models import DocumentChunk  # noqa: E402
from src.digital_twin.grounding.retrieval import BM25Retriever  # noqa: E402
from src.digital_twin.grounding.retrieval_index import source_set_sha256  # noqa: E402
from src.digital_twin.model_policy import (  # noqa: E402
    OPENAI_EMBEDDING_PRICING_USD_PER_MILLION,
    OPENAI_TEXT_EMBEDDING_LARGE_MODEL,
    OPENAI_TEXT_EMBEDDING_SMALL_MODEL,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


PROGRAM_ID = "course-digital-twin-nonhuman-evaluation-program-002"
INSTRUMENT_ID = "academic-factual-qa-source-aligned-retrieval-confirmation-001"
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_source_aligned_retrieval_confirmation_001.json"
)
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
RESULT_PATH = ROOT / "research/05_evaluation/records" / f"{INSTRUMENT_ID}.json"
METHODS = {
    "M0": "source-aligned-bm25-v1",
    "M1": "source-aligned-openai-small-dense-v1",
    "M2": "source-aligned-bm25-openai-small-rrf-v1",
    "M3": "source-aligned-openai-large-dense-v1",
    "M4": "source-aligned-bm25-openai-large-rrf-v1",
    "M5": "source-aligned-large-hybrid-hierarchy-v1",
}


class SourceAlignedRetrievalError(RuntimeError):
    """Raised when the frozen retrieval confirmation cannot be interpreted."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourceAlignedRetrievalError(f"JSON package unavailable: {path.name}") from error
    if not isinstance(value, dict):
        raise SourceAlignedRetrievalError(f"JSON package is not an object: {path.name}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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


def _verify_package(binding: dict[str, Any], *, rows_key: str) -> dict[str, Any]:
    path = ROOT / str(binding["path"])
    if _file_sha256(path) != binding["file_sha256"]:
        raise SourceAlignedRetrievalError(f"package file hash drifted: {path.name}")
    payload = _load_object(path)
    if payload.get("content_sha256") != binding["content_sha256"]:
        raise SourceAlignedRetrievalError(f"package content hash drifted: {path.name}")
    if not isinstance(payload.get(rows_key), list):
        raise SourceAlignedRetrievalError(f"package rows unavailable: {path.name}")
    return payload


def _instrument() -> dict[str, Any]:
    value = _load_object(INSTRUMENT_PATH)
    observed = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise SourceAlignedRetrievalError("retrieval instrument hash drifted")
    return value


def _public_packages(instrument: dict[str, Any]):
    source = _verify_package(instrument["source_package"], rows_key="chunks")
    cases_payload = _verify_package(instrument["public_cases"], rows_key="cases")
    chunks = [DocumentChunk.model_validate(row) for row in source["chunks"]]
    cases = [EvaluationCaseV1.model_validate(row) for row in cases_payload["cases"]]
    return source, cases_payload, chunks, cases


def _packages(instrument: dict[str, Any]):
    source, cases_payload, chunks, cases = _public_packages(instrument)
    gold_payload = _verify_package(instrument["hidden_gold"], rows_key="gold")
    gold = [EvaluationGoldV1.model_validate(row) for row in gold_payload["gold"]]
    return source, cases_payload, gold_payload, chunks, cases, gold


def _validate_public(instrument: dict[str, Any]) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[DocumentChunk],
    list[EvaluationCaseV1],
]:
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise SourceAlignedRetrievalError("retrieval instrument identity drifted")
    if instrument.get("program_id") != PROGRAM_ID:
        raise SourceAlignedRetrievalError("retrieval program binding drifted")
    if instrument.get("status") != "frozen-authorized-by-program":
        raise SourceAlignedRetrievalError("retrieval instrument is not frozen")
    if not instrument.get("provider_execution_authorized_by_program"):
        raise SourceAlignedRetrievalError("program provider authority drifted")
    methods = {
        str(row["method_id"]): str(row["implementation"])
        for row in instrument.get("methods", [])
    }
    if methods != METHODS:
        raise SourceAlignedRetrievalError("retrieval method ladder drifted")
    candidates = {
        row["model"]: (row["dimensions"], row["input_price_usd_per_million"])
        for row in instrument.get("embedding_candidates", [])
    }
    expected = {
        OPENAI_TEXT_EMBEDDING_SMALL_MODEL: (1_536, 0.02),
        OPENAI_TEXT_EMBEDDING_LARGE_MODEL: (3_072, 0.13),
    }
    if candidates != expected:
        raise SourceAlignedRetrievalError("embedding candidates drifted")
    if any(
        OPENAI_EMBEDDING_PRICING_USD_PER_MILLION[model] != price
        for model, (_, price) in candidates.items()
    ):
        raise SourceAlignedRetrievalError("embedding pricing drifted from model policy")
    source, cases_payload, chunks, cases = _public_packages(instrument)
    if (
        len(chunks) != 350
        or len(cases) != 500
        or len({row.case_id for row in cases}) != 500
    ):
        raise SourceAlignedRetrievalError("public source/case count or identity drifted")
    if cases_payload.get("source_plan_sha256") != source["content_sha256"]:
        raise SourceAlignedRetrievalError("public source/case binding drifted")
    limits = instrument["execution_limits"]
    if (
        limits["maximum_embedding_and_query_calls"] != 40
        or limits["maximum_transport_retries"] != 0
        or limits["emergency_stop_usd"] != 2.0
    ):
        raise SourceAlignedRetrievalError("retrieval execution limits drifted")
    return source, cases_payload, chunks, cases


def validate() -> dict[str, Any]:
    instrument = _instrument()
    source, cases_payload, chunks, cases = _validate_public(instrument)
    gold_payload = _verify_package(instrument["hidden_gold"], rows_key="gold")
    gold = [EvaluationGoldV1.model_validate(row) for row in gold_payload["gold"]]
    if (
        len(gold) != 500
        or {row.case_id for row in cases} != {row.case_id for row in gold}
    ):
        raise SourceAlignedRetrievalError("hidden-gold count or identity drifted")
    source_hash = source["content_sha256"]
    if (
        cases_payload.get("source_plan_sha256") != source_hash
        or gold_payload.get("source_plan_sha256") != source_hash
    ):
        raise SourceAlignedRetrievalError("source/case/gold binding drifted")
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "case_count": len(cases),
        "answerable_count": sum(
            row.expected_action == EvaluationAction.ANSWER for row in gold
        ),
        "boundary_count": sum(
            row.expected_action != EvaluationAction.ANSWER for row in gold
        ),
        "registered_region_count": len(chunks),
        "method_count": len(METHODS),
        "matchability": matchability,
        "provider_calls": 0,
        "private_data_used": False,
        "automatic_progression_on_pass": True,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _instrument()
    _, _, chunks, cases = _validate_public(instrument)
    blockers: list[str] = []
    verified_at = datetime.fromisoformat(instrument["metadata"]["verified_at"])
    age_hours = (datetime.now(UTC) - verified_at.astimezone(UTC)).total_seconds() / 3600
    if age_hours < 0 or age_hours > instrument["metadata"]["freshness_hours"]:
        blockers.append("provider-metadata-older-than-24-hours")
    if _git_dirty():
        blockers.append("working-tree-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-credential-missing")
    if resume and not OUTPUT_ROOT.is_dir():
        blockers.append("resume-output-path-missing")
    if not resume and (OUTPUT_ROOT.exists() or RESULT_PATH.exists()):
        blockers.append("exclusive-output-path-already-exists")
    return {
        "instrument_id": INSTRUMENT_ID,
        "case_count": len(cases),
        "registered_region_count": len(chunks),
        "status": "ready" if not blockers else "blocked-technical",
        "technical_blockers": blockers,
        "authority_blockers": [],
        "metadata_age_hours": age_hours,
        "model_or_provider_called": False,
        "hidden_gold_opened": False,
    }


def simulate(scenario: str) -> dict[str, Any]:
    validate()
    passed = scenario == "pass"
    methods = [
        {
            "method_id": method_id,
            "complete_evidence_at_3": 0.92 if passed and method_id == "M2" else 0.86,
            "evidence_recall_at_5": 0.97 if passed and method_id == "M2" else 0.93,
            "boundary_accuracy": 0.99,
            "severe_release_count": 0,
            "course_violation_count": 0,
            "source_version_violation_count": 0,
            "latency_p95_ms": 20.0,
            "passed": passed and method_id == "M2",
        }
        for method_id in METHODS
    ]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "completed-keep" if passed else "completed-refine",
        "selected_method": "M2" if passed else "none",
        "method_summaries": methods,
        "provider_calls": 0,
        "reported_cost_usd": 0.0,
        "simulation": True,
    }


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
        release_id=f"{course_id}-source-aligned-confirmation-v1",
        profile_id="source-aligned-retrieval-confirmation",
        profile_version="v1",
        chunker_id="complete-source-region-registration",
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


def _atomic_json(path: Path, payload: dict[str, Any], *, add_hash: bool = True) -> None:
    value = dict(payload)
    if add_hash:
        value["content_sha256"] = canonical_json_sha256(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _rank(
    *,
    cases: list[EvaluationCaseV1],
    bm25: dict[str, Any],
    small: dict[str, Any],
    large: dict[str, Any],
    hierarchy: dict[str, StructuredHierarchicalRetriever],
) -> tuple[dict[str, dict[str, list[str]]], dict[str, dict[str, float]]]:
    rankings = {method_id: {} for method_id in METHODS}
    latencies = {method_id: {} for method_id in METHODS}
    for case in cases:
        retrievers = {
            "M0": bm25[case.course_id],
            "M1": small[case.course_id].dense_retriever,
            "M2": small[case.course_id].retriever,
            "M3": large[case.course_id].dense_retriever,
            "M4": large[case.course_id].retriever,
            "M5": hierarchy[case.course_id],
        }
        for method_id, retriever in retrievers.items():
            started = time.perf_counter()
            hits = retriever.retrieve(case.question, limit=5)
            latencies[method_id][case.case_id] = (time.perf_counter() - started) * 1_000
            rankings[method_id][case.case_id] = [row.chunk.id for row in hits]
    return rankings, latencies


def _hit_reference(chunk: DocumentChunk) -> CanonicalEvidenceRefV1 | None:
    try:
        return CanonicalEvidenceRefV1(
            source_artifact_id=chunk.source_artifact_id or chunk.document_id,
            source_version=chunk.source_version,
            source_sha256=chunk.source_checksum,
            char_start=int(chunk.metadata["char_start"]),
            char_end=int(chunk.metadata["char_end"]),
            region_id=chunk.region_id,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _covered(reference: CanonicalEvidenceRefV1, chunks: list[DocumentChunk]) -> bool:
    return any(
        candidate is not None and evidence_ranges_overlap(reference, candidate)
        for candidate in (_hit_reference(chunk) for chunk in chunks)
    )


def _score(
    *,
    cases: list[EvaluationCaseV1],
    gold: dict[str, EvaluationGoldV1],
    rankings: dict[str, dict[str, list[str]]],
    latencies: dict[str, dict[str, float]],
    chunks_by_id: dict[str, DocumentChunk],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    summaries: list[dict[str, Any]] = []
    failures: dict[str, list[dict[str, Any]]] = {}
    for method_id in METHODS:
        observations = []
        for case in cases:
            reference = gold[case.case_id]
            chunks = [chunks_by_id[row] for row in rankings[method_id][case.case_id]]
            required = [row for claim in reference.claims for row in claim.evidence_refs]
            action = deterministic_boundary_action(case.question) or (
                "answer" if chunks else "abstain"
            )
            answerable = reference.expected_action == EvaluationAction.ANSWER
            exact_complete = bool(required) and all(
                _covered(row, chunks[:3]) for row in required
            )
            recall = (
                sum(_covered(row, chunks[:5]) for row in required) / len(required)
                if required
                else 1.0
            )
            course_violation = any(
                chunk.metadata.get("course_id") != case.course_id for chunk in chunks
            )
            required_sources = {
                (row.source_artifact_id, row.source_version, row.source_sha256)
                for row in required
            }
            version_violation = any(
                candidate is None
                or any(
                    candidate.source_artifact_id == source
                    and (
                        candidate.source_version != version
                        or candidate.source_sha256 != checksum
                    )
                    for source, version, checksum in required_sources
                )
                for candidate in (_hit_reference(chunk) for chunk in chunks)
            )
            observations.append(
                {
                    "case_id": case.case_id,
                    "slice": case.slice,
                    "course_id": case.course_id,
                    "source_family_id": case.source_family_id,
                    "answerable": answerable,
                    "evidence_at_3": exact_complete if answerable else True,
                    "recall_at_5": recall,
                    "boundary_correct": answerable
                    or action == reference.expected_action.value,
                    "severe": not answerable and action == "answer",
                    "course_violation": course_violation,
                    "version_violation": version_violation,
                    "latency_ms": latencies[method_id][case.case_id],
                }
            )
        answerable_rows = [row for row in observations if row["answerable"]]
        boundary_rows = [row for row in observations if not row["answerable"]]
        complete = sum(row["evidence_at_3"] for row in answerable_rows) / len(answerable_rows)
        recall = sum(row["recall_at_5"] for row in answerable_rows) / len(answerable_rows)
        boundary_accuracy = sum(row["boundary_correct"] for row in boundary_rows) / len(boundary_rows)
        severe = sum(row["severe"] for row in observations)
        course = sum(row["course_violation"] for row in observations)
        version = sum(row["version_violation"] for row in observations)
        latency = p95([row["latency_ms"] for row in observations])
        slices: dict[str, dict[str, float | int]] = {}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in observations:
            grouped[str(row["slice"])].append(row)
        for slice_name, rows in sorted(grouped.items()):
            answerable_slice = [row for row in rows if row["answerable"]]
            slices[slice_name] = {
                "case_count": len(rows),
                "complete_evidence_at_3": (
                    sum(row["evidence_at_3"] for row in answerable_slice)
                    / len(answerable_slice)
                    if answerable_slice
                    else 1.0
                ),
                "evidence_recall_at_5": (
                    sum(row["recall_at_5"] for row in answerable_slice)
                    / len(answerable_slice)
                    if answerable_slice
                    else 1.0
                ),
                "boundary_accuracy": (
                    sum(row["boundary_correct"] for row in rows if not row["answerable"])
                    / sum(not row["answerable"] for row in rows)
                    if any(not row["answerable"] for row in rows)
                    else 1.0
                ),
            }
        passed = (
            complete >= 0.90
            and recall >= 0.95
            and boundary_accuracy >= 0.98
            and severe == 0
            and course == 0
            and version == 0
            and latency <= 2_000
        )
        summaries.append(
            {
                "method_id": method_id,
                "implementation": METHODS[method_id],
                "case_count": len(observations),
                "complete_evidence_at_3": complete,
                "evidence_recall_at_5": recall,
                "boundary_accuracy": boundary_accuracy,
                "severe_release_count": severe,
                "course_violation_count": course,
                "source_version_violation_count": version,
                "latency_p95_ms": latency,
                "slice_metrics": slices,
                "passed": passed,
            }
        )
        failures[method_id] = [
            {
                "case_id": row["case_id"],
                "slice": row["slice"],
                "course_id": row["course_id"],
                "evidence_at_3": row["evidence_at_3"],
                "recall_at_5": row["recall_at_5"],
                "boundary_correct": row["boundary_correct"],
            }
            for row in observations
            if not row["evidence_at_3"]
            or row["recall_at_5"] < 1
            or not row["boundary_correct"]
        ]
    return summaries, failures


def _select(summaries: list[dict[str, Any]]) -> str | None:
    passing = [row for row in summaries if row["passed"]]
    if not passing:
        return None
    best = max(float(row["complete_evidence_at_3"]) for row in passing)
    eligible = [
        row for row in passing if best - float(row["complete_evidence_at_3"]) <= 0.02
    ]
    complexity = {method_id: index for index, method_id in enumerate(METHODS)}
    return str(
        min(
            eligible,
            key=lambda row: (
                complexity[str(row["method_id"])],
                -float(row["evidence_recall_at_5"]),
                float(row["latency_p95_ms"]),
            ),
        )["method_id"]
    )


def _open_hidden_gold_after_rankings(
    instrument: dict[str, Any],
    *,
    public_rankings_path: Path,
    expected_case_ids: set[str],
    source_sha256: str,
) -> dict[str, EvaluationGoldV1]:
    if not public_rankings_path.is_file():
        raise SourceAlignedRetrievalError(
            "hidden gold cannot open before public rankings are durable"
        )
    gold_payload = _verify_package(instrument["hidden_gold"], rows_key="gold")
    if gold_payload.get("source_plan_sha256") != source_sha256:
        raise SourceAlignedRetrievalError("hidden gold source binding drifted")
    gold = {
        row.case_id: row
        for row in (
            EvaluationGoldV1.model_validate(value) for value in gold_payload["gold"]
        )
    }
    if set(gold) != expected_case_ids:
        raise SourceAlignedRetrievalError("hidden gold case identity drifted")
    return gold


def _component_record(
    *,
    instrument: dict[str, Any],
    summaries: list[dict[str, Any]],
    selected: str | None,
    usage: dict[str, dict[str, Any]],
    public_path: Path,
) -> dict[str, Any]:
    thresholds = instrument["hard_gates"]
    candidates = []
    for summary in summaries:
        method_id = str(summary["method_id"])
        implementation_id = str(summary["implementation"])
        candidates.append(
            {
                "implementation": {
                    "implementation_id": implementation_id,
                    "version": method_id,
                    "configuration": {
                        "case_count": int(summary["case_count"]),
                        "provider_required": method_id != "M0",
                        "program_id": PROGRAM_ID,
                    },
                },
                "role": "control" if method_id == "M0" else "candidate",
                "metrics": [
                    {
                        "name": "complete-evidence-at-3",
                        "value": float(summary["complete_evidence_at_3"]),
                        "unit": "rate",
                        "direction": "higher-is-better",
                        "threshold": float(
                            thresholds["complete_evidence_at_3_minimum"]
                        ),
                        "passed": float(summary["complete_evidence_at_3"])
                        >= float(thresholds["complete_evidence_at_3_minimum"]),
                    },
                    {
                        "name": "evidence-recall-at-5",
                        "value": float(summary["evidence_recall_at_5"]),
                        "unit": "rate",
                        "direction": "higher-is-better",
                        "threshold": float(
                            thresholds["evidence_recall_at_5_minimum"]
                        ),
                        "passed": float(summary["evidence_recall_at_5"])
                        >= float(thresholds["evidence_recall_at_5_minimum"]),
                    },
                    {
                        "name": "boundary-accuracy",
                        "value": float(summary["boundary_accuracy"]),
                        "unit": "rate",
                        "direction": "higher-is-better",
                        "threshold": float(thresholds["boundary_accuracy_minimum"]),
                        "passed": float(summary["boundary_accuracy"])
                        >= float(thresholds["boundary_accuracy_minimum"]),
                    },
                    {
                        "name": "retrieval-latency-p95",
                        "value": float(summary["latency_p95_ms"]),
                        "unit": "milliseconds",
                        "direction": "lower-is-better",
                        "threshold": float(
                            thresholds["retrieval_p95_seconds_maximum"]
                        )
                        * 1_000,
                        "passed": float(summary["latency_p95_ms"])
                        <= float(thresholds["retrieval_p95_seconds_maximum"])
                        * 1_000,
                    },
                ],
                "hard_gates": [
                    {
                        "name": "zero-severe-unsupported-releases",
                        "passed": int(summary["severe_release_count"]) == 0,
                        "evidence": (
                            f"Observed {int(summary['severe_release_count'])} severe "
                            "unsupported boundary releases."
                        ),
                    },
                    {
                        "name": "source-course-version-isolation",
                        "passed": int(summary["course_violation_count"]) == 0
                        and int(summary["source_version_violation_count"]) == 0,
                        "evidence": (
                            f"Observed {int(summary['course_violation_count'])} course "
                            "and "
                            f"{int(summary['source_version_violation_count'])} source-"
                            "version violations."
                        ),
                    },
                    {
                        "name": "method-operationally-complete",
                        "passed": True,
                        "evidence": (
                            "All 500 rankings completed with durable public output "
                            "before hidden gold opened."
                        ),
                    },
                ],
                "failures_by_category": {
                    "incomplete-all-evidence-at-3": int(
                        round((1 - float(summary["complete_evidence_at_3"])) * 400)
                    ),
                    "boundary-action-error": int(
                        round((1 - float(summary["boundary_accuracy"])) * 100)
                    ),
                    "severe-unsupported-release": int(
                        summary["severe_release_count"]
                    ),
                    "course-violation": int(summary["course_violation_count"]),
                    "source-version-violation": int(
                        summary["source_version_violation_count"]
                    ),
                },
            }
        )
    selected_implementation = METHODS[selected] if selected else None
    record = {
        "schema_version": 1,
        "run_id": INSTRUMENT_ID,
        "component": "retriever",
        "dataset_id": "academic-factual-qa-source-aligned-wording-002",
        "corpus_id": "academic-factual-qa-source-aligned-public-100-clusters",
        "code_revision": _git_revision(),
        "candidates": candidates,
        "decision": {
            "outcome": "go-deeper" if selected else "refine",
            "selected_implementation_id": selected_implementation,
            "rationale": (
                "At least one source-aligned method passed every frozen retrieval "
                "gate and may advance once to the 500+100 actual-product checkpoint."
                if selected
                else "No source-aligned method passed every frozen retrieval gate; "
                "the factual scaling branch stops for a method-level decision."
            ),
            "limitations": [
                "This development comparison evaluates retrieval and boundary actions, not product answer quality.",
                "The benchmark uses public educational sources and no human participants.",
                "OpenAI embedding methods share one provider family; deterministic source truth remains authoritative.",
            ],
        },
    }
    validated = ComponentEvaluationRecord.model_validate(record).model_dump(mode="json")
    validated["operational_summary"] = {
        "provider_calls": sum(int(row["request_count"]) for row in usage.values()),
        "reported_cost_usd": sum(
            float(row["reported_cost_usd"]) for row in usage.values()
        ),
        "rankings_file_sha256": _file_sha256(public_path),
        "rankings_content_sha256": _load_object(public_path)["content_sha256"],
        "hidden_gold_loaded_only_after_rankings_persisted": True,
        "private_data_used": False,
        "human_participants": 0,
    }
    return validated


def execute(*, resume: bool = False) -> dict[str, Any]:
    check = preflight(resume=resume)
    if check["status"] != "ready":
        raise SourceAlignedRetrievalError(
            "source-aligned retrieval preflight is not ready: "
            + ", ".join(check["technical_blockers"])
        )
    instrument = _instrument()
    source, _, chunks, cases = _public_packages(instrument)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=resume)
    chunks_by_course: dict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        chunks_by_course[str(chunk.metadata["course_id"])].append(chunk)
    for values in chunks_by_course.values():
        values.sort(key=lambda row: row.id)
    bm25 = {
        course_id: BM25Retriever(values)
        for course_id, values in sorted(chunks_by_course.items())
    }
    store = StreamingRetrievalIndexMaterializerV2(OUTPUT_ROOT / "indexes")
    loaded: dict[str, dict[str, Any]] = {}
    usage: dict[str, dict[str, Any]] = {}
    for candidate in instrument["embedding_candidates"]:
        ledger = RetrievalUsageLedger(
            max_cost_usd=instrument["execution_limits"]["emergency_stop_usd"],
            price_per_million_input_tokens_usd=candidate["input_price_usd_per_million"],
        )
        embedder = OpenAITextEmbedder(
            os.environ["OPENAI_API_KEY"],
            ledger=ledger,
            model=candidate["model"],
            dimensions=candidate["dimensions"],
            batch_size=candidate["batch_size"],
            request_token_limit=candidate["request_token_limit"],
        )
        bindings: dict[str, ApiRetrievalIndexBindingV2] = {}
        manifests = {}
        for course_id, values in sorted(chunks_by_course.items()):
            binding = _embedding_binding(
                instrument, candidate, course_id=course_id, chunks=values
            )
            bindings[course_id] = binding
            ledger_path = store.work_root / f"{binding.binding_sha256}.sqlite3"
            manifests[course_id] = store.materialize(
                binding,
                values,
                embedder,
                resume=resume and ledger_path.exists(),
            )
        query_path = OUTPUT_ROOT / f"query-vectors-{candidate['model']}.sqlite3"
        query_vectors, query_usage = _query_vectors(
            path=query_path,
            cases=cases,
            embedder=embedder,
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
        loaded[candidate["model"]] = {
            course_id: store.load(
                manifests[course_id].artifact_id,
                expected_binding=bindings[course_id],
                embedder=cache,
            )
            for course_id in sorted(chunks_by_course)
        }
        usage[candidate["model"]] = {
            "request_count": sum(
                int(row.materialization["batch_count"]) for row in manifests.values()
            )
            + int(query_usage["batch_count"]),
            "input_tokens": sum(
                int(row.materialization["input_tokens"]) for row in manifests.values()
            )
            + int(query_usage["input_tokens"]),
            "reported_cost_usd": sum(
                float(row.materialization["cost_usd"]) for row in manifests.values()
            )
            + float(query_usage["cost_usd"]),
            "artifact_ids": {
                course_id: row.artifact_id
                for course_id, row in sorted(manifests.items())
            },
        }
    small = loaded[OPENAI_TEXT_EMBEDDING_SMALL_MODEL]
    large = loaded[OPENAI_TEXT_EMBEDDING_LARGE_MODEL]
    hierarchy = {
        course_id: StructuredHierarchicalRetriever(
            large[course_id].retriever, chunks_by_course[course_id]
        )
        for course_id in chunks_by_course
    }
    rankings, latencies = _rank(
        cases=cases,
        bm25=bm25,
        small=small,
        large=large,
        hierarchy=hierarchy,
    )
    public_payload = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "code_revision": _git_revision(),
        "case_ids": [row.case_id for row in cases],
        "methods": rankings,
        "latencies_ms": latencies,
        "gold_loaded": False,
    }
    public_path = OUTPUT_ROOT / "public-rankings.json"
    _atomic_json(public_path, public_payload)

    # Gold opens only after every method ranking has been persisted durably.
    gold = _open_hidden_gold_after_rankings(
        instrument,
        public_rankings_path=public_path,
        expected_case_ids={row.case_id for row in cases},
        source_sha256=source["content_sha256"],
    )
    chunks_by_id = {row.id: row for row in chunks}
    summaries, failures = _score(
        cases=cases,
        gold=gold,
        rankings=rankings,
        latencies=latencies,
        chunks_by_id=chunks_by_id,
    )
    selected = _select(summaries)
    provider_calls = sum(int(row["request_count"]) for row in usage.values())
    reported_cost = sum(float(row["reported_cost_usd"]) for row in usage.values())
    if (
        provider_calls > instrument["execution_limits"]["maximum_embedding_and_query_calls"]
        or reported_cost > instrument["execution_limits"]["emergency_stop_usd"]
    ):
        raise SourceAlignedRetrievalError("retrieval accounting exceeded its frozen limit")
    runtime_result = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "program_id": PROGRAM_ID,
        "decision": "completed-keep" if selected else "completed-refine",
        "selected_method": selected or "none",
        "code_revision": _git_revision(),
        "source_sha256": instrument["source_package"]["content_sha256"],
        "cases_sha256": instrument["public_cases"]["content_sha256"],
        "gold_sha256": instrument["hidden_gold"]["content_sha256"],
        "rankings_file_sha256": _file_sha256(public_path),
        "rankings_content_sha256": _load_object(public_path)["content_sha256"],
        "gold_loaded_only_after_rankings_persisted": True,
        "case_count": len(cases),
        "answerable_count": sum(
            row.expected_action == EvaluationAction.ANSWER for row in gold.values()
        ),
        "boundary_count": sum(
            row.expected_action != EvaluationAction.ANSWER for row in gold.values()
        ),
        "method_summaries": summaries,
        "failure_counts": {
            method_id: len(rows) for method_id, rows in sorted(failures.items())
        },
        "failure_examples": {
            method_id: rows[:12] for method_id, rows in sorted(failures.items())
        },
        "embedding_usage": usage,
        "provider_calls": provider_calls,
        "reported_cost_usd": reported_cost,
        "maximum_transport_retries": 0,
        "deterministic_truth_authoritative": True,
        "llm_or_agent_review_used": False,
        "private_data_used": False,
        "human_participants": 0,
        "final_split_opened": False,
        "automatic_next_stage": (
            "actual-product-500-plus-100" if selected else "stop-factual-scaling"
        ),
    }
    if RESULT_PATH.exists():
        raise SourceAlignedRetrievalError("exclusive sanitized result already exists")
    record = _component_record(
        instrument=instrument,
        summaries=summaries,
        selected=selected,
        usage=usage,
        public_path=public_path,
    )
    _atomic_json(RESULT_PATH, record, add_hash=False)
    _atomic_json(OUTPUT_ROOT / "runtime-summary.json", runtime_result)
    return runtime_result


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", choices=("pass", "quality-failure"))
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "method_evaluation_execution"
        )
        result = execute(resume=arguments.resume)
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.simulate:
        result = simulate(arguments.simulate)
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
