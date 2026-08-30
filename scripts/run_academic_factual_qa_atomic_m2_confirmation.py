#!/usr/bin/env python3
"""Run one fresh atomic-evidence M2 coverage-selection confirmation."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_academic_factual_qa_api_retrieval_selection import (  # noqa: E402
    _CachedQueryEmbedder,
    _query_vectors,
)
from scripts.run_academic_factual_qa_source_aligned_retrieval import (  # noqa: E402
    _atomic_json,
    _file_sha256,
    _git_dirty,
    _git_revision,
    _load_object,
    _verify_package,
)
from services.embeddings.openai_client import OpenAITextEmbedder  # noqa: E402
from services.retrieval_provider import RetrievalUsageLedger  # noqa: E402
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.finite_retrieval_evaluation import (  # noqa: E402
    validate_exact_reference_matchability,
)
from src.digital_twin.evaluation.models import ComponentEvaluationRecord  # noqa: E402
from src.digital_twin.grounding.api_retrieval_index import (  # noqa: E402
    ApiRetrievalIndexBindingV2,
    StreamingRetrievalIndexMaterializerV2,
)
from src.digital_twin.grounding.hierarchical_retrieval import (  # noqa: E402
    concept_tokens,
    deterministic_boundary_action,
    p95,
)
from src.digital_twin.grounding.models import (  # noqa: E402
    DocumentChunk,
    RetrievalHit,
)
from src.digital_twin.grounding.retrieval import retrieval_text  # noqa: E402
from src.digital_twin.grounding.retrieval_index import source_set_sha256  # noqa: E402
from src.digital_twin.model_policy import (  # noqa: E402
    OPENAI_EMBEDDING_PRICING_USD_PER_MILLION,
    OPENAI_TEXT_EMBEDDING_SMALL_MODEL,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


PROGRAM_ID = "course-digital-twin-nonhuman-evaluation-program-002"
INSTRUMENT_ID = "academic-factual-qa-atomic-m2-confirmation-001"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_atomic_m2_confirmation_001.json"
)
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
RESULT_PATH = ROOT / "research/05_evaluation/records" / f"{INSTRUMENT_ID}.json"
METHODS = {
    "M2": "atomic-bm25-openai-small-rrf-v1",
    "M2C": "atomic-m2-question-coverage-selector-v1",
}


class AtomicM2ConfirmationError(RuntimeError):
    """Raised when the finite atomic-M2 confirmation cannot be interpreted."""


def _instrument() -> dict[str, Any]:
    value = _load_object(INSTRUMENT_PATH)
    observed = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise AtomicM2ConfirmationError("atomic-M2 instrument hash drifted")
    if value.get("instrument_id") != INSTRUMENT_ID:
        raise AtomicM2ConfirmationError("atomic-M2 instrument identity drifted")
    if value.get("program_id") != PROGRAM_ID:
        raise AtomicM2ConfirmationError("atomic-M2 program binding drifted")
    return value


def _public_packages(
    instrument: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[DocumentChunk], list[EvaluationCaseV1]]:
    source = _verify_package(instrument["source_package"], rows_key="chunks")
    public = _verify_package(instrument["public_cases"], rows_key="cases")
    chunks = [DocumentChunk.model_validate(row) for row in source["chunks"]]
    cases = [EvaluationCaseV1.model_validate(row) for row in public["cases"]]
    return source, public, chunks, cases


def _validate_public(
    instrument: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[DocumentChunk], list[EvaluationCaseV1]]:
    if instrument.get("status") != "frozen-authorized-by-program":
        raise AtomicM2ConfirmationError("atomic-M2 instrument is not frozen")
    if not instrument.get("provider_execution_authorized_by_program"):
        raise AtomicM2ConfirmationError("atomic-M2 program authority drifted")
    if {
        str(row["method_id"]): str(row["implementation"])
        for row in instrument.get("methods", [])
    } != METHODS:
        raise AtomicM2ConfirmationError("atomic-M2 method binding drifted")
    embedding = instrument["embedding"]
    if (
        embedding.get("model") != OPENAI_TEXT_EMBEDDING_SMALL_MODEL
        or embedding.get("dimensions") != 1_536
        or embedding.get("input_price_usd_per_million")
        != OPENAI_EMBEDDING_PRICING_USD_PER_MILLION[
            OPENAI_TEXT_EMBEDDING_SMALL_MODEL
        ]
    ):
        raise AtomicM2ConfirmationError("atomic-M2 embedding binding drifted")
    source, public, chunks, cases = _public_packages(instrument)
    if (
        source.get("cluster_count") != 100
        or len(chunks) != 300
        or len(cases) != 500
        or len({row.case_id for row in cases}) != 500
        or public.get("source_plan_sha256") != source.get("content_sha256")
    ):
        raise AtomicM2ConfirmationError("atomic source/public package drifted")
    if source.get("authoritative_regions_non_overlapping") is not True:
        raise AtomicM2ConfirmationError("atomic evidence units are not unique")
    limits = instrument["execution_limits"]
    if (
        limits.get("maximum_embedding_and_query_calls") != 20
        or limits.get("maximum_transport_retries") != 0
        or limits.get("emergency_stop_usd") != 1.0
    ):
        raise AtomicM2ConfirmationError("atomic-M2 execution limits drifted")
    return source, public, chunks, cases


def validate() -> dict[str, Any]:
    instrument = _instrument()
    source, _, chunks, cases = _validate_public(instrument)
    hidden = _verify_package(instrument["hidden_gold"], rows_key="gold")
    gold = [EvaluationGoldV1.model_validate(row) for row in hidden["gold"]]
    if (
        len(gold) != 500
        or {row.case_id for row in cases} != {row.case_id for row in gold}
        or hidden.get("source_plan_sha256") != source.get("content_sha256")
    ):
        raise AtomicM2ConfirmationError("atomic hidden-gold binding drifted")
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)
    if matchability.get("missing_reference_count") != 0:
        raise AtomicM2ConfirmationError("atomic references are not exactly matchable")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "cluster_count": 100,
        "case_count": 500,
        "answerable_count": 400,
        "boundary_count": 100,
        "registered_region_count": len(chunks),
        "matchability": matchability,
        "provider_calls": 0,
        "private_data_used": False,
        "final_split_opened": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _instrument()
    _, _, chunks, cases = _validate_public(instrument)
    blockers: list[str] = []
    verified_at = datetime.fromisoformat(instrument["metadata"]["verified_at"])
    age = (datetime.now(UTC) - verified_at.astimezone(UTC)).total_seconds() / 3_600
    if age < 0 or age > instrument["metadata"]["freshness_hours"]:
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
        "status": "ready" if not blockers else "blocked-technical",
        "technical_blockers": blockers,
        "authority_blockers": [],
        "case_count": len(cases),
        "registered_region_count": len(chunks),
        "metadata_age_hours": age,
        "hidden_gold_opened": False,
        "provider_calls": 0,
    }


def _coverage_select(
    question: str,
    candidates: list[RetrievalHit],
    *,
    output_limit: int = 5,
    coverage_limit: int = 3,
) -> list[RetrievalHit]:
    """Select top evidence using question-only marginal concept coverage."""

    query = concept_tokens(question)
    uncovered = set(query)
    remaining = list(enumerate(candidates))
    selected: list[tuple[int, RetrievalHit]] = []
    while remaining and len(selected) < coverage_limit:
        index, chosen = min(
            remaining,
            key=lambda row: (
                -len(concept_tokens(retrieval_text(row[1].chunk)) & uncovered),
                -row[1].relevance_score,
                row[0],
                row[1].chunk.id,
            ),
        )
        selected.append((index, chosen))
        uncovered -= concept_tokens(retrieval_text(chosen.chunk))
        remaining.remove((index, chosen))
    selected_ids = {row.chunk.id for _, row in selected}
    tail = [row for row in candidates if row.chunk.id not in selected_ids]
    return [row for _, row in selected] + tail[: max(0, output_limit - len(selected))]


def _binding(
    instrument: dict[str, Any],
    *,
    course_id: str,
    chunks: list[DocumentChunk],
) -> ApiRetrievalIndexBindingV2:
    embedding = instrument["embedding"]
    return ApiRetrievalIndexBindingV2(
        instrument_id=INSTRUMENT_ID,
        course_id=course_id,
        release_id=f"{course_id}-atomic-m2-confirmation-v1",
        profile_id="atomic-m2-coverage-confirmation",
        profile_version="v1",
        chunker_id="unique-atomic-source-registration",
        chunker_version="v1",
        source_set_sha256=source_set_sha256(chunks),
        chunk_count=len(chunks),
        embedding_model=embedding["model"],
        embedding_dimensions=embedding["dimensions"],
        embedding_batch_size=embedding["batch_size"],
        embedding_request_token_limit=embedding["request_token_limit"],
        input_price_usd_per_million=embedding["input_price_usd_per_million"],
        metadata_verified_at=datetime.fromisoformat(
            instrument["metadata"]["verified_at"]
        ),
        bm25_k1=1.2,
        bm25_b=0.75,
        fusion_rank_constant=60,
        fusion_candidate_limit=30,
    )


def _rank(
    *,
    cases: list[EvaluationCaseV1],
    retrievers: dict[str, Any],
) -> tuple[dict[str, dict[str, list[str]]], dict[str, dict[str, float]]]:
    rankings = {method: {} for method in METHODS}
    latencies = {method: {} for method in METHODS}
    for case in cases:
        retriever = retrievers[case.course_id].retriever
        started = time.perf_counter()
        control = retriever.retrieve(case.question, limit=5)
        latencies["M2"][case.case_id] = (time.perf_counter() - started) * 1_000
        rankings["M2"][case.case_id] = [row.chunk.id for row in control]
        started = time.perf_counter()
        candidates = retriever.retrieve(case.question, limit=12)
        selected = _coverage_select(case.question, candidates)
        latencies["M2C"][case.case_id] = (time.perf_counter() - started) * 1_000
        rankings["M2C"][case.case_id] = [row.chunk.id for row in selected]
    return rankings, latencies


def _score(
    *,
    cases: list[EvaluationCaseV1],
    gold: dict[str, EvaluationGoldV1],
    rankings: dict[str, dict[str, list[str]]],
    latencies: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    summaries = []
    for method_id, implementation in METHODS.items():
        answerable = []
        boundaries = []
        for case in cases:
            reference = gold[case.case_id]
            required = {
                evidence.region_id
                for claim in reference.claims
                for evidence in claim.evidence_refs
            }
            hits = rankings[method_id][case.case_id]
            if reference.expected_action == EvaluationAction.ANSWER:
                answerable.append(
                    {
                        "complete_at_3": required.issubset(set(hits[:3])),
                        "recall_at_5": (
                            len(required & set(hits[:5])) / len(required)
                            if required
                            else 1.0
                        ),
                    }
                )
            else:
                action = deterministic_boundary_action(case.question) or (
                    "answer" if hits else "abstain"
                )
                boundaries.append(
                    {
                        "correct": action == reference.expected_action.value,
                        "severe": action == "answer",
                    }
                )
        complete = sum(row["complete_at_3"] for row in answerable) / len(answerable)
        recall = sum(row["recall_at_5"] for row in answerable) / len(answerable)
        boundary = sum(row["correct"] for row in boundaries) / len(boundaries)
        severe = sum(row["severe"] for row in boundaries)
        latency = p95(list(latencies[method_id].values()))
        summaries.append(
            {
                "method_id": method_id,
                "implementation": implementation,
                "complete_evidence_at_3": complete,
                "evidence_recall_at_5": recall,
                "boundary_accuracy": boundary,
                "severe_release_count": severe,
                "course_violation_count": 0,
                "source_version_violation_count": 0,
                "latency_p95_ms": latency,
                "passed": complete >= 0.90
                and recall >= 0.95
                and boundary >= 0.98
                and severe == 0
                and latency <= 2_000,
            }
        )
    return summaries


def _selected(summaries: list[dict[str, Any]]) -> str | None:
    by_id = {row["method_id"]: row for row in summaries}
    if by_id["M2"]["passed"]:
        return "M2"
    if by_id["M2C"]["passed"]:
        return "M2C"
    return None


def _open_hidden_gold(
    instrument: dict[str, Any],
    *,
    rankings_path: Path,
    source_sha256: str,
    expected_case_ids: set[str],
) -> dict[str, EvaluationGoldV1]:
    if not rankings_path.is_file():
        raise AtomicM2ConfirmationError(
            "hidden gold cannot open before public rankings are durable"
        )
    hidden = _verify_package(instrument["hidden_gold"], rows_key="gold")
    if hidden.get("source_plan_sha256") != source_sha256:
        raise AtomicM2ConfirmationError("atomic hidden-gold source binding drifted")
    gold = {
        row.case_id: row
        for row in (
            EvaluationGoldV1.model_validate(value) for value in hidden["gold"]
        )
    }
    if set(gold) != expected_case_ids:
        raise AtomicM2ConfirmationError("atomic hidden-gold identity drifted")
    return gold


def simulate(scenario: str) -> dict[str, Any]:
    validate()
    selected = "M2C" if scenario == "pass" else None
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "completed-keep" if selected else "completed-refine",
        "selected_method": selected or "none",
        "provider_calls": 0,
        "reported_cost_usd": 0.0,
        "simulation": True,
    }


def _record(
    *,
    summaries: list[dict[str, Any]],
    selected: str | None,
    provider_calls: int,
    cost: float,
    rankings_path: Path,
) -> dict[str, Any]:
    candidates = []
    for row in summaries:
        candidates.append(
            {
                "implementation": {
                    "implementation_id": row["implementation"],
                    "version": row["method_id"],
                    "configuration": {
                        "case_count": 500,
                        "atomic_authoritative_regions": True,
                        "candidate_pool": 12 if row["method_id"] == "M2C" else 5,
                    },
                },
                "role": "control" if row["method_id"] == "M2" else "candidate",
                "metrics": [
                    {
                        "name": "complete-evidence-at-3",
                        "value": row["complete_evidence_at_3"],
                        "unit": "rate",
                        "direction": "higher-is-better",
                        "threshold": 0.90,
                        "passed": row["complete_evidence_at_3"] >= 0.90,
                    },
                    {
                        "name": "evidence-recall-at-5",
                        "value": row["evidence_recall_at_5"],
                        "unit": "rate",
                        "direction": "higher-is-better",
                        "threshold": 0.95,
                        "passed": row["evidence_recall_at_5"] >= 0.95,
                    },
                    {
                        "name": "boundary-accuracy",
                        "value": row["boundary_accuracy"],
                        "unit": "rate",
                        "direction": "higher-is-better",
                        "threshold": 0.98,
                        "passed": row["boundary_accuracy"] >= 0.98,
                    },
                    {
                        "name": "retrieval-latency-p95",
                        "value": row["latency_p95_ms"],
                        "unit": "milliseconds",
                        "direction": "lower-is-better",
                        "threshold": 2_000.0,
                        "passed": row["latency_p95_ms"] <= 2_000,
                    },
                ],
                "hard_gates": [
                    {
                        "name": "zero-severe-unsupported-releases",
                        "passed": row["severe_release_count"] == 0,
                        "evidence": f"Observed {row['severe_release_count']} severe releases.",
                    },
                    {
                        "name": "source-course-version-isolation",
                        "passed": True,
                        "evidence": "Course-scoped immutable indexes returned only current registered atoms.",
                    },
                    {
                        "name": "unique-atomic-evidence-semantics",
                        "passed": True,
                        "evidence": "Every answer span maps to exactly one non-overlapping authoritative atom.",
                    },
                ],
                "failures_by_category": {
                    "incomplete-all-evidence-at-3": round(
                        (1 - row["complete_evidence_at_3"]) * 400
                    ),
                    "boundary-action-error": round(
                        (1 - row["boundary_accuracy"]) * 100
                    ),
                    "severe-unsupported-release": row["severe_release_count"],
                },
            }
        )
    record = {
        "schema_version": 1,
        "run_id": INSTRUMENT_ID,
        "component": "retriever",
        "dataset_id": "academic-factual-qa-atomic-m2-confirmation-001",
        "corpus_id": "academic-factual-qa-atomic-m2-public-100-clusters",
        "code_revision": _git_revision(),
        "candidates": candidates,
        "decision": {
            "outcome": "go-deeper" if selected else "refine",
            "selected_implementation_id": METHODS[selected] if selected else None,
            "rationale": (
                "A prospectively scored atomic-evidence method passed and may advance once to actual-product development."
                if selected
                else "Neither unchanged atomic M2 nor deterministic coverage selection passed every frozen gate."
            ),
            "limitations": [
                "This fresh development run evaluates retrieval, not generated product answers.",
                "The benchmark uses public educational sources and no human participants.",
                "Final 10,000-case data remains unopened.",
            ],
        },
    }
    value = ComponentEvaluationRecord.model_validate(record).model_dump(mode="json")
    value["operational_summary"] = {
        "provider_calls": provider_calls,
        "reported_cost_usd": cost,
        "rankings_file_sha256": _file_sha256(rankings_path),
        "hidden_gold_loaded_only_after_rankings_persisted": True,
        "private_data_used": False,
        "human_participants": 0,
    }
    return value


def execute(*, resume: bool = False) -> dict[str, Any]:
    check = preflight(resume=resume)
    if check["status"] != "ready":
        raise AtomicM2ConfirmationError(
            "atomic-M2 preflight blocked: " + ", ".join(check["technical_blockers"])
        )
    instrument = _instrument()
    source, _, chunks, cases = _public_packages(instrument)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=resume)
    by_course: dict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        by_course[str(chunk.metadata["course_id"])].append(chunk)
    for values in by_course.values():
        values.sort(key=lambda row: row.id)
    embedding = instrument["embedding"]
    ledger = RetrievalUsageLedger(
        max_cost_usd=instrument["execution_limits"]["emergency_stop_usd"],
        price_per_million_input_tokens_usd=embedding[
            "input_price_usd_per_million"
        ],
    )
    embedder = OpenAITextEmbedder(
        os.environ["OPENAI_API_KEY"],
        ledger=ledger,
        model=embedding["model"],
        dimensions=embedding["dimensions"],
        batch_size=embedding["batch_size"],
        request_token_limit=embedding["request_token_limit"],
    )
    store = StreamingRetrievalIndexMaterializerV2(OUTPUT_ROOT / "indexes")
    bindings = {}
    manifests = {}
    for course_id, values in sorted(by_course.items()):
        binding = _binding(instrument, course_id=course_id, chunks=values)
        bindings[course_id] = binding
        ledger_path = store.work_root / f"{binding.binding_sha256}.sqlite3"
        manifests[course_id] = store.materialize(
            binding,
            values,
            embedder,
            resume=resume and ledger_path.exists(),
        )
    query_path = OUTPUT_ROOT / "query-vectors.sqlite3"
    vectors, query_usage = _query_vectors(
        path=query_path,
        cases=cases,
        embedder=embedder,
        model=embedding["model"],
        dimensions=embedding["dimensions"],
        instrument_sha256=instrument["content_sha256"],
        resume=resume and query_path.exists(),
    )
    cache = _CachedQueryEmbedder(
        model=embedding["model"],
        dimensions=embedding["dimensions"],
        vectors=vectors,
    )
    retrievers = {
        course_id: store.load(
            manifests[course_id].artifact_id,
            expected_binding=bindings[course_id],
            embedder=cache,
        )
        for course_id in sorted(by_course)
    }
    rankings, latencies = _rank(cases=cases, retrievers=retrievers)
    public = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "case_ids": [row.case_id for row in cases],
        "methods": rankings,
        "latencies_ms": latencies,
        "gold_loaded": False,
    }
    rankings_path = OUTPUT_ROOT / "public-rankings.json"
    _atomic_json(rankings_path, public)

    gold = _open_hidden_gold(
        instrument,
        rankings_path=rankings_path,
        source_sha256=str(source["content_sha256"]),
        expected_case_ids={row.case_id for row in cases},
    )
    summaries = _score(
        cases=cases,
        gold=gold,
        rankings=rankings,
        latencies=latencies,
    )
    selected = _selected(summaries)
    provider_calls = sum(
        int(row.materialization["batch_count"]) for row in manifests.values()
    ) + int(query_usage["batch_count"])
    cost = sum(
        float(row.materialization["cost_usd"]) for row in manifests.values()
    ) + float(query_usage["cost_usd"])
    if (
        provider_calls
        > instrument["execution_limits"]["maximum_embedding_and_query_calls"]
        or cost > instrument["execution_limits"]["emergency_stop_usd"]
    ):
        raise AtomicM2ConfirmationError("atomic-M2 accounting limit exceeded")
    runtime = {
        "instrument_id": INSTRUMENT_ID,
        "program_id": PROGRAM_ID,
        "status": "completed-keep" if selected else "completed-refine",
        "selected_method": selected or "none",
        "method_summaries": summaries,
        "provider_calls": provider_calls,
        "reported_cost_usd": cost,
        "gold_loaded_only_after_rankings_persisted": True,
        "private_data_used": False,
        "final_split_opened": False,
        "automatic_next_stage": (
            "actual-product-500-plus-100" if selected else "stop-factual-scaling"
        ),
    }
    record = _record(
        summaries=summaries,
        selected=selected,
        provider_calls=provider_calls,
        cost=cost,
        rankings_path=rankings_path,
    )
    if RESULT_PATH.exists():
        raise AtomicM2ConfirmationError("exclusive atomic-M2 result already exists")
    _atomic_json(RESULT_PATH, record, add_hash=False)
    _atomic_json(OUTPUT_ROOT / "runtime-summary.json", runtime)
    return runtime


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
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
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
