#!/usr/bin/env python3
"""Validate, simulate, preflight, or run the frozen v2 candidate comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from scripts.validate_evidence_sufficiency_v2_decision_freeze import validate_freeze
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    BM25Retriever,
    CalibratedOpenSetEvidenceGate,
    CrossEncoderNliCompletenessVerifier,
    CrossEncoderSupportVerifier,
    DocumentChunk,
    InspectableFeatureSupportVerifier,
    LocalCrossEncoderBackend,
    LocalNliCrossEncoderBackend,
    NliProbabilities,
    RetrievalHit,
)
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "evidence-sufficiency-v2-candidate-comparison-001"
DEFAULT_INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/"
    "evidence_sufficiency_v2_candidate_comparison_001.json"
)
DATASET_PATH = (
    ROOT
    / "research/05_evaluation/drafts/"
    "evidence_sufficiency_v2_decision_draft_002.json"
)


class CandidateComparisonError(RuntimeError):
    """Raised when the frozen comparison cannot proceed validly."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CandidateComparisonError("model verification time must include a timezone")
    return parsed


def validate_instrument(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise CandidateComparisonError("candidate-comparison ID drifted")
    if instrument.get("status") not in {
        "reviewed-not-authorized",
        "frozen-pending-execution",
        "authorization-revoked",
    }:
        raise CandidateComparisonError("candidate-comparison status is invalid")
    if instrument.get("model_leaderboard") is not False:
        raise CandidateComparisonError("comparison cannot become a model leaderboard")

    freeze = validate_freeze(ROOT / instrument["decision_freeze"]["path"])
    binding = instrument["decision_freeze"]
    if (
        binding.get("freeze_id") != freeze["freeze_id"]
        or binding.get("dataset_id") != freeze["dataset_id"]
        or binding.get("dataset_content_sha256") != freeze["content_sha256"]
        or binding.get("case_count") != 120
        or binding.get("opened") is not False
    ):
        raise CandidateComparisonError("decision-freeze binding drifted")

    retrieval = instrument["fixed_retrieval"]
    if (
        retrieval.get("implementation")
        != "bm25-course-scoped-active-approved-v1"
        or retrieval.get("top_k") != 5
        or retrieval.get("gold_evidence_injection") is not False
        or retrieval.get("course_scope_before_retrieval") is not True
        or retrieval.get("inactive_or_disallowed_sources_excluded") is not True
    ):
        raise CandidateComparisonError("fixed retrieval contract drifted")

    candidates = instrument["candidates"]
    expected_ids = [
        "any-hit-control",
        "inspectable-feature-classifier-v2",
        "cross-encoder-support-verifier-v2",
        "cross-encoder-nli-completeness-verifier-v2",
    ]
    if [candidate.get("id") for candidate in candidates] != expected_ids:
        raise CandidateComparisonError("candidate order or identity drifted")
    if candidates[0].get("selectable") is not False:
        raise CandidateComparisonError("AnyHit must remain unselectable")
    if any(candidate.get("selectable") is not True for candidate in candidates[1:]):
        raise CandidateComparisonError("a prospective candidate became unselectable")

    expected_models = {
        "cross-encoder-support-verifier-v2": (
            "Alibaba-NLP/gte-reranker-modernbert-base",
            "f7481e6055501a30fb19d090657df9ec1f79ab2c",
            149605633,
        ),
        "cross-encoder-nli-completeness-verifier-v2": (
            "cross-encoder/nli-deberta-v3-base",
            "6c749ce3425cd33b46d187e45b92bbf96ee12ec7",
            184424963,
        ),
    }
    for candidate in candidates[1:]:
        thresholds = candidate["thresholds"]
        for name in (
            "supporting_hit",
            "minimum_direct_support",
            "minimum_completeness",
            "maximum_contradiction",
            "maximum_ambiguity",
        ):
            value = thresholds.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise CandidateComparisonError(f"invalid threshold: {name}")
            if not math.isfinite(float(value)) or not 0 <= float(value) <= 1:
                raise CandidateComparisonError(f"invalid threshold: {name}")
        if thresholds.get("minimum_supporting_hits") != 1:
            raise CandidateComparisonError("supporting-hit minimum drifted")
        if candidate["id"] in expected_models:
            model = candidate["model"]
            expected_id, expected_revision, expected_parameters = expected_models[
                candidate["id"]
            ]
            if (
                model.get("model_id") != expected_id
                or model.get("revision") != expected_revision
                or model.get("parameter_count") != expected_parameters
                or model.get("license") != "apache-2.0"
            ):
                raise CandidateComparisonError("local model binding drifted")
            _parse_timestamp(model["verified_at"])

    gates = instrument["hard_gates"]
    if gates != {
        "false_answer_count_max": 0,
        "answerable_recall_min": 0.9,
        "balanced_accuracy_min": 0.95,
        "near_domain_accuracy_min": 1.0,
        "multi_evidence_recall_min": 0.9,
        "safety_violation_count_max": 0,
        "citation_lineage_failure_count_max": 0,
        "mutation_detection_rate_min": 1.0,
        "verifier_p95_ms_max": 500,
        "added_peak_memory_bytes_max": 2147483648,
    }:
        raise CandidateComparisonError("hard gates drifted")

    safety = instrument["execution_safety"]
    forbidden_true = {
        "provider_execution_authorized",
        "paid_execution_authorized",
        "private_source_execution_authorized",
        "heldout_execution_authorized",
        "automatic_selection",
        "automatic_release_promotion",
        "gemma_allowed",
        "claude_allowed",
    }
    if any(safety.get(name) is not False for name in forbidden_true):
        raise CandidateComparisonError("execution-safety boundary drifted")
    local_authorities = {
        safety.get("candidate_execution_authorized"),
        safety.get("local_model_execution_authorized"),
        safety.get("decision_split_execution_authorized"),
    }
    if len(local_authorities) != 1:
        raise CandidateComparisonError("local execution authorities disagree")
    authorized = local_authorities == {True}
    if authorized != (instrument["status"] == "frozen-pending-execution"):
        raise CandidateComparisonError("status and local authority disagree")
    if instrument["decision_rule"].get("authorize_release") is not False:
        raise CandidateComparisonError("comparison cannot authorize release")
    return instrument


def preflight(instrument: dict[str, Any]) -> dict[str, Any]:
    safety = instrument["execution_safety"]
    blockers: list[str] = []
    for name in (
        "candidate_execution_authorized",
        "local_model_execution_authorized",
        "decision_split_execution_authorized",
    ):
        if not safety[name]:
            blockers.append(name.replace("_", "-") + "-false")
    now = datetime.now(timezone.utc)
    max_age = instrument["freshness_policy"]["metadata_max_age_hours"]
    for candidate in instrument["candidates"]:
        model = candidate.get("model")
        if model is None:
            continue
        age_hours = (now - _parse_timestamp(model["verified_at"]).astimezone(timezone.utc)).total_seconds() / 3600
        if age_hours > max_age:
            blockers.append(f"stale-model-metadata:{candidate['id']}")
    return {
        "instrument_id": instrument["instrument_id"],
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "decision_split_opened": False,
        "model_loaded": False,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "private_data_read": False,
    }


class _StaticPairBackend:
    implementation_id = "network-free-static-pair-backend"
    version = "simulation-v1"

    def __init__(self, scores: list[float]) -> None:
        self.scores = scores

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        if len(pairs) != len(self.scores):
            raise CandidateComparisonError("simulation pair count drifted")
        return self.scores


class _StaticNliBackend:
    implementation_id = "network-free-static-nli-backend"
    version = "simulation-v1"

    def score_pairs(
        self,
        pairs: Sequence[tuple[str, str]],
    ) -> list[NliProbabilities]:
        return [
            NliProbabilities(contradiction=0.05, entailment=0.85, neutral=0.1)
            for _ in pairs
        ]


def _synthetic_hit(identifier: str, text: str) -> RetrievalHit:
    return RetrievalHit(
        chunk=DocumentChunk(
            id=identifier,
            document_id=f"document-{identifier}",
            text=text,
            ordinal=0,
            retrieval_allowed=True,
        ),
        relevance_score=1,
        raw_score=1,
    )


def simulate(instrument: dict[str, Any]) -> dict[str, Any]:
    hits = [
        _synthetic_hit("support", "A reset revokes every active session."),
        _synthetic_hit("noise", "A B-tree stores sorted keys."),
    ]
    thresholds = instrument["candidates"][2]["thresholds"]
    support = CrossEncoderSupportVerifier(
        _StaticPairBackend([0.95, 0.1]),
        supporting_hit_threshold=thresholds["supporting_hit"],
    )
    nli = CrossEncoderNliCompletenessVerifier(support, _StaticNliBackend())
    gate = _gate(nli, thresholds)
    accepted = gate.assess("What does a reset do to sessions?", hits)
    rejected = gate.assess("What does a reset do to sessions?", [])
    if not accepted.sufficient or rejected.sufficient:
        raise CandidateComparisonError("network-free simulation failed")
    return {
        "instrument_id": instrument["instrument_id"],
        "status": "passed-network-free-simulation",
        "accepted_supporting_hit_count": accepted.features["supporting_hit_count"],
        "empty_evidence_rejected": True,
        "decision_split_opened": False,
        "model_loaded": False,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "private_data_read": False,
    }


def _gate(verifier, thresholds: dict[str, Any]) -> CalibratedOpenSetEvidenceGate:
    return CalibratedOpenSetEvidenceGate(
        verifier,
        minimum_direct_support=thresholds["minimum_direct_support"],
        minimum_completeness=thresholds["minimum_completeness"],
        maximum_contradiction=thresholds["maximum_contradiction"],
        maximum_ambiguity=thresholds["maximum_ambiguity"],
        minimum_supporting_hits=thresholds["minimum_supporting_hits"],
        evidence_limit=5,
    )


def _source_chunks(dataset: dict[str, Any]) -> dict[str, list[DocumentChunk]]:
    by_course: dict[str, list[DocumentChunk]] = {}
    for source in dataset["sources"]:
        if not source["active"] or not source["tutoring_allowed"]:
            continue
        chunk = DocumentChunk(
            id=source["source_unit_id"],
            document_id=source["logical_source_id"],
            source_artifact_id=source["source_unit_id"],
            source_version=source["version"],
            text=source["content"],
            ordinal=0,
            locator="synthetic source unit",
            retrieval_allowed=True,
            display_allowed=True,
            metadata={
                "course_id": source["course_id"],
                "modality": source["modality"],
            },
        )
        by_course.setdefault(source["course_id"], []).append(chunk)
    return by_course


def _retrieved_hits(
    dataset: dict[str, Any],
) -> dict[str, list[RetrievalHit]]:
    by_course = _source_chunks(dataset)
    retrievers = {
        course_id: BM25Retriever(chunks)
        for course_id, chunks in by_course.items()
    }
    return {
        case["case_id"]: retrievers.get(case["course_id"], BM25Retriever([])).retrieve(
            case["question"],
            limit=5,
        )
        for case in dataset["cases"]
    }


def _peak_rss_bytes() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(usage if sys.platform == "darwin" else usage * 1024)


def _percentile_95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _passes(metrics: dict[str, Any], gates: dict[str, Any]) -> bool:
    return all(
        (
            metrics["false_answer_count"] <= gates["false_answer_count_max"],
            metrics["answerable_recall"] >= gates["answerable_recall_min"],
            metrics["balanced_accuracy"] >= gates["balanced_accuracy_min"],
            metrics["near_domain_accuracy"] >= gates["near_domain_accuracy_min"],
            metrics["multi_evidence_recall"]
            >= gates["multi_evidence_recall_min"],
            metrics["safety_violation_count"]
            <= gates["safety_violation_count_max"],
            metrics["citation_lineage_failure_count"]
            <= gates["citation_lineage_failure_count_max"],
            metrics["mutation_detection_rate"]
            >= gates["mutation_detection_rate_min"],
            metrics["verifier_p95_ms"] <= gates["verifier_p95_ms_max"],
            metrics["added_peak_memory_bytes"]
            <= gates["added_peak_memory_bytes_max"],
        )
    )


def _evaluate_candidate(
    candidate: dict[str, Any],
    gate,
    dataset: dict[str, Any],
    retrieved: dict[str, list[RetrievalHit]],
    hard_gates: dict[str, Any],
    baseline_rss: int,
) -> dict[str, Any]:
    case_results: list[dict[str, Any]] = []
    latencies: list[float] = []
    mutation_total = 0
    mutation_detected = 0
    for case in dataset["cases"]:
        hits = retrieved[case["case_id"]]
        started = time.perf_counter()
        decision = gate.assess(case["question"], hits)
        latencies.append((time.perf_counter() - started) * 1000)
        expected_answer = case["expected_action"] == "answer"
        required_sources = {item["source_unit_id"] for item in case["evidence"]}
        retrieved_sources = {hit.chunk.source_artifact_id for hit in hits}
        lineage_valid = not decision.sufficient or (
            expected_answer and required_sources.issubset(retrieved_sources)
        )
        mutation_detected_for_case: bool | None = None
        if decision.sufficient and expected_answer and required_sources:
            mutated_hits = [
                hit
                for hit in hits
                if hit.chunk.source_artifact_id not in required_sources
            ]
            mutation_total += 1
            mutation_detected_for_case = not gate.assess(
                case["question"],
                mutated_hits,
            ).sufficient
            mutation_detected += int(mutation_detected_for_case)
        case_results.append(
            {
                "case_id": case["case_id"],
                "slice": case["slice"],
                "expected_action": case["expected_action"],
                "predicted_action": "answer" if decision.sufficient else "abstain",
                "score": decision.score,
                "retrieved_source_ids": sorted(
                    source_id for source_id in retrieved_sources if source_id
                ),
                "lineage_valid": lineage_valid,
                "mutation_detected": mutation_detected_for_case,
                "features": decision.features,
            }
        )

    answerable = [item for item in case_results if item["expected_action"] == "answer"]
    abstain = [item for item in case_results if item["expected_action"] == "abstain"]
    answer_recall = sum(item["predicted_action"] == "answer" for item in answerable) / len(answerable)
    abstain_accuracy = sum(item["predicted_action"] == "abstain" for item in abstain) / len(abstain)
    slices: dict[str, list[dict[str, Any]]] = {}
    for item in case_results:
        slices.setdefault(item["slice"], []).append(item)
    slice_metrics = {
        name: {
            "case_count": len(items),
            "accuracy": sum(
                item["predicted_action"] == item["expected_action"] for item in items
            )
            / len(items),
        }
        for name, items in sorted(slices.items())
    }
    multi_items = slices["multi-evidence"]
    metrics = {
        "case_count": len(case_results),
        "answerable_recall": answer_recall,
        "abstain_accuracy": abstain_accuracy,
        "balanced_accuracy": (answer_recall + abstain_accuracy) / 2,
        "false_answer_count": sum(
            item["predicted_action"] == "answer" for item in abstain
        ),
        "false_abstention_count": sum(
            item["predicted_action"] == "abstain" for item in answerable
        ),
        "near_domain_accuracy": slice_metrics["near-domain"]["accuracy"],
        "multi_evidence_recall": sum(
            item["predicted_action"] == "answer" for item in multi_items
        )
        / len(multi_items),
        "safety_violation_count": sum(
            not hit.chunk.retrieval_allowed
            for hits in retrieved.values()
            for hit in hits
        ),
        "citation_lineage_failure_count": sum(
            not item["lineage_valid"] for item in case_results
        ),
        "mutation_detection_rate": (
            mutation_detected / mutation_total if mutation_total else 0.0
        ),
        "mutation_case_count": mutation_total,
        "verifier_mean_ms": statistics.fmean(latencies),
        "verifier_p95_ms": _percentile_95(latencies),
        "added_peak_memory_bytes": max(0, _peak_rss_bytes() - baseline_rss),
        "slice_metrics": slice_metrics,
    }
    return {
        "candidate_id": candidate["id"],
        "selectable": candidate["selectable"],
        "metrics": metrics,
        "hard_gates_passed": _passes(metrics, hard_gates),
        "cases": case_results,
    }


def _candidate_gates(instrument: dict[str, Any]):
    candidates = instrument["candidates"]
    yield candidates[0], AnyHitEvidenceGate()

    deterministic = candidates[1]
    yield deterministic, _gate(
        InspectableFeatureSupportVerifier(
            supporting_hit_threshold=deterministic["thresholds"]["supporting_hit"]
        ),
        deterministic["thresholds"],
    )

    support_candidate = candidates[2]
    support_model = support_candidate["model"]
    support_backend = LocalCrossEncoderBackend(
        model_id=support_model["model_id"],
        revision=support_model["revision"],
        max_length=support_model["execution_max_length"],
        batch_size=8,
    )
    support_verifier = CrossEncoderSupportVerifier(
        support_backend,
        supporting_hit_threshold=support_candidate["thresholds"]["supporting_hit"],
    )
    yield support_candidate, _gate(support_verifier, support_candidate["thresholds"])

    nli_candidate = candidates[3]
    nli_model = nli_candidate["model"]
    nli_backend = LocalNliCrossEncoderBackend(
        model_id=nli_model["model_id"],
        revision=nli_model["revision"],
        max_length=nli_model["execution_max_length"],
        batch_size=8,
    )
    nli_verifier = CrossEncoderNliCompletenessVerifier(
        support_verifier,
        nli_backend,
    )
    yield nli_candidate, _gate(nli_verifier, nli_candidate["thresholds"])


def execute(instrument: dict[str, Any], instrument_path: Path) -> dict[str, Any]:
    ready = preflight(instrument)
    if ready["status"] != "ready":
        raise CandidateComparisonError(
            "candidate comparison is not ready: " + ", ".join(ready["blockers"])
        )
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
    output = ROOT / instrument["execution"]["raw_output_path"]
    if output.exists():
        raise CandidateComparisonError("exclusive output path already exists")

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if dataset.get("content_sha256") != instrument["decision_freeze"]["dataset_content_sha256"]:
        raise CandidateComparisonError("opened decision dataset hash drifted")
    if len(dataset.get("cases", [])) != 120:
        raise CandidateComparisonError("opened decision dataset count drifted")
    retrieved = _retrieved_hits(dataset)
    baseline_rss = _peak_rss_bytes()
    results = [
        _evaluate_candidate(
            candidate,
            gate,
            dataset,
            retrieved,
            instrument["hard_gates"],
            baseline_rss,
        )
        for candidate, gate in _candidate_gates(instrument)
    ]
    passing = [
        result
        for result in results
        if result["selectable"] and result["hard_gates_passed"]
    ]
    selected = passing[0]["candidate_id"] if passing else None
    payload = {
        "schema_version": 1,
        "run_id": INSTRUMENT_ID,
        "instrument_sha256": _sha256(instrument_path),
        "dataset_id": dataset["dataset_id"],
        "dataset_content_sha256": dataset["content_sha256"],
        "dataset_opened_for_candidate_evaluation": True,
        "result_state": "completed-keep" if selected else "completed-refine",
        "selected_candidate": selected,
        "selection_requires_profile_update": selected is not None,
        "results": results,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "private_data_read": False,
        "automatic_release_promotion": False,
        "priority_audit_case_ids": _priority_case_ids(results, limit=12),
        "result_sha256": "",
    }
    payload["result_sha256"] = _canonical_sha256(
        {**payload, "result_sha256": ""}
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.open("x", encoding="utf-8").write(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    return payload


def _priority_case_ids(results: Sequence[dict[str, Any]], *, limit: int) -> list[str]:
    priorities: list[tuple[int, str]] = []
    for result in results:
        if not result["selectable"]:
            continue
        for case in result["cases"]:
            failed = case["predicted_action"] != case["expected_action"]
            lineage = not case["lineage_valid"]
            mutation = case["mutation_detected"] is False
            if failed or lineage or mutation:
                priorities.append((int(failed) + int(lineage) + int(mutation), case["case_id"]))
    return [
        case_id
        for _, case_id in sorted(set(priorities), key=lambda item: (-item[0], item[1]))[:limit]
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--simulate", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
    instrument = validate_instrument(arguments.instrument)
    if arguments.simulate:
        payload = simulate(instrument)
    elif arguments.preflight:
        payload = preflight(instrument)
    elif arguments.execute:
        payload = execute(instrument, arguments.instrument)
    else:
        payload = {
            "instrument_id": instrument["instrument_id"],
            "status": "validated-not-authorized",
            "candidate_count": len(instrument["candidates"]),
            "selectable_candidate_count": sum(
                candidate["selectable"] for candidate in instrument["candidates"]
            ),
            "decision_split_opened": False,
            "model_loaded": False,
            "provider_calls": 0,
            "paid_cost_usd": 0,
            "private_data_read": False,
        }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
