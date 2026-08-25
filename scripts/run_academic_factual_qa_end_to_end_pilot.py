#!/usr/bin/env python3
"""Validate and simulate the leakage-free academic factual-QA pilot."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import statistics
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field

from scripts.academic_factual_qa_pilot_data import (
    COURSES,
    DATASET_ID,
    build_development_dataset,
    canonical_sha256,
    validate_development_dataset,
)
from src.digital_twin.generation import DeterministicGroundedGenerator
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    DocumentChunk,
    EvidenceSufficiencyDecision,
    RetrievalHit,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student import (
    Account,
    AccountRole,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    MembershipRole,
    ReleaseEvaluationStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    approved_synthetic_policy,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-end-to-end-pilot-001"
DEFAULT_INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_end_to_end_pilot_001.json"
)
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
ALLOWED_SYSTEM_FIELDS = frozenset(
    {"case_id", "client_request_id", "course_id", "question"}
)
GOLD_FIELDS = frozenset(
    {"expected_action", "expected_claims", "required_source_ids", "rationale", "slice"}
)


class AcademicPilotError(RuntimeError):
    """Raised when the prospective pilot contract is invalid."""


class ProductCaseInput(BaseModel):
    """The complete case payload permitted to reach the product boundary."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    client_request_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    question: str = Field(min_length=1)


class _RecordingGate:
    def __init__(self, *, reject_all: bool) -> None:
        self.reject_all = reject_all
        self.implementation_id = (
            "always-reject-recording-control"
            if reject_all
            else AnyHitEvidenceGate.implementation_id
        )
        self._any_hit = AnyHitEvidenceGate()
        self.hits_by_question: dict[str, list[RetrievalHit]] = {}

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        self.hits_by_question[query] = list(hits)
        if self.reject_all:
            return EvidenceSufficiencyDecision(
                sufficient=False,
                score=0,
                reason="fail-closed development control rejects every retrieved set",
                features={"hit_count": len(hits)},
            )
        return self._any_hit.assess(query, hits)


class _RecordingDeterministicGenerator:
    implementation_id = "recording-deterministic-grounded-generator"
    version = "simulation-v1"

    def __init__(self) -> None:
        self._generator = DeterministicGroundedGenerator()
        self.calls: list[dict[str, Any]] = []

    async def generate(self, question, hits, policy):
        self.calls.append(
            {
                "question": question,
                "hit_ids": [hit.chunk.id for hit in hits],
                "input_fields": ["question", "hits", "policy"],
            }
        )
        return await self._generator.generate(question, hits, policy)


def validate_instrument(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise AcademicPilotError("instrument ID drifted")
    if instrument.get("status") != "reviewed-build-only":
        raise AcademicPilotError("instrument status drifted")

    dataset = build_development_dataset()
    dataset_contract = instrument.get("dataset", {})
    if (
        dataset_contract.get("dataset_id") != DATASET_ID
        or dataset_contract.get("content_sha256") != dataset["content_sha256"]
        or dataset_contract.get("case_count") != 160
        or dataset_contract.get("source_count") != 32
        or dataset_contract.get("course_count") != 8
        or dataset_contract.get("cluster_count") != 80
        or dataset_contract.get("answerable_count") != 80
        or dataset_contract.get("boundary_count") != 80
        or dataset_contract.get("independent_gold") is not False
        or dataset_contract.get("final_evaluation_split") is not False
        or dataset_contract.get("private_data") is not False
    ):
        raise AcademicPilotError("development dataset binding drifted")

    input_contract = instrument.get("system_input_contract", {})
    if (
        set(input_contract.get("allowed_case_fields", [])) != ALLOWED_SYSTEM_FIELDS
        or set(input_contract.get("forbidden_case_fields", [])) != GOLD_FIELDS
        or input_contract.get("gold_available_only_after_persisted_response") is not True
        or input_contract.get("course_scope_before_retrieval") is not True
        or input_contract.get("normal_student_service_required") is not True
        or input_contract.get("normal_retriever_required") is not True
        or input_contract.get("normal_generator_contract_required") is not True
    ):
        raise AcademicPilotError("system input firewall drifted")

    conditions = instrument.get("development_conditions", [])
    if [condition.get("condition_id") for condition in conditions] != [
        "T0-FAIL-CLOSED-CONTROL",
        "T0-ANY-HIT-CONTROL",
    ] or any(condition.get("selectable") is not False for condition in conditions):
        raise AcademicPilotError("development control conditions drifted")
    future = instrument.get("required_future_condition", {})
    if (
        future.get("condition_id") != "T0-ATOMIC-CLAIM-CANDIDATE"
        or future.get("status") != "not-product-integrated-not-executable"
        or future.get("selection_requires_independent_gold") is not True
    ):
        raise AcademicPilotError("future candidate boundary drifted")

    safety = instrument.get("execution_safety", {})
    if safety.get("network_free_simulation_authorized") is not True:
        raise AcademicPilotError("network-free simulation is not authorized")
    forbidden_authorities = (
        "development_execution_authorized",
        "provider_execution_authorized",
        "paid_execution_authorized",
        "private_source_execution_authorized",
        "independent_gold_opening_authorized",
        "heldout_execution_authorized",
        "product_binding_authorized",
        "automatic_selection",
        "automatic_release_promotion",
    )
    if any(safety.get(name) is not False for name in forbidden_authorities):
        raise AcademicPilotError("execution safety boundary drifted")
    if instrument["decision_rule"].get("simulation_can_select_method") is not False:
        raise AcademicPilotError("simulation cannot select a method")
    return instrument


def preflight(instrument: dict[str, Any]) -> dict[str, Any]:
    safety = instrument["execution_safety"]
    blockers = [
        "development-execution-not-authorized",
        "atomic-claim-candidate-not-product-integrated",
        "independent-gold-not-available",
    ]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "blocked-not-authorized" if blockers else "ready",
        "blockers": blockers,
        "development_execution_authorized": safety["development_execution_authorized"],
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "private_data_read": False,
        "independent_gold_opened": False,
    }


def validate_build(instrument: dict[str, Any]) -> dict[str, Any]:
    dataset = build_development_dataset()
    dataset_without_hash = {key: value for key, value in dataset.items() if key != "content_sha256"}
    quality = validate_development_dataset(dataset_without_hash)
    if canonical_sha256(dataset_without_hash) != dataset["content_sha256"]:
        raise AcademicPilotError("development content hash is not canonical")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "validated-build-only",
        "dataset": quality,
        "content_sha256": dataset["content_sha256"],
        "system_input_allowed_fields": sorted(ALLOWED_SYSTEM_FIELDS),
        "system_input_forbidden_gold_fields": sorted(GOLD_FIELDS),
        "condition_count": len(instrument["development_conditions"]),
        "future_candidate_status": instrument["required_future_condition"]["status"],
        "provider_calls": 0,
        "private_data_read": False,
        "independent_gold_opened": False,
    }


async def simulate(instrument: dict[str, Any]) -> dict[str, Any]:
    dataset = build_development_dataset()
    condition_results = []
    all_case_rows: list[dict[str, Any]] = []
    for condition in instrument["development_conditions"]:
        result = await _run_condition(dataset, condition)
        condition_results.append(result["summary"])
        all_case_rows.extend(result["cases"])

    if len(all_case_rows) != 320:
        raise AcademicPilotError("simulation row count drifted")
    if any(row["gold_field_count_in_system_input"] for row in all_case_rows):
        raise AcademicPilotError("gold field crossed the system input boundary")
    if any(row["provider_calls"] for row in all_case_rows):
        raise AcademicPilotError("network-free simulation called a provider")
    if any(row["private_data_read"] for row in all_case_rows):
        raise AcademicPilotError("network-free simulation read private data")
    if any(summary["method_selected"] for summary in condition_results):
        raise AcademicPilotError("development control selected a method")

    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-network-free-harness-simulation",
        "dataset_id": DATASET_ID,
        "dataset_content_sha256": dataset["content_sha256"],
        "case_count": len(dataset["cases"]),
        "condition_count": len(condition_results),
        "condition_summaries": condition_results,
        "case_results": all_case_rows,
        "gold_field_count_in_system_input": 0,
        "provider_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "paid_cost_usd": 0,
        "private_data_read": False,
        "independent_gold_opened": False,
        "independent_gold_claimed": False,
        "method_selected": False,
        "next_state": instrument["decision_rule"]["next_state_after_build"],
    }


async def _run_condition(
    dataset: dict[str, Any],
    condition: dict[str, Any],
) -> dict[str, Any]:
    reject_all = condition["condition_id"] == "T0-FAIL-CLOSED-CONTROL"
    with tempfile.TemporaryDirectory(prefix="academic-factual-qa-e2e-") as temp_root:
        repository = SQLiteStudentRepository(Path(temp_root) / "pilot.sqlite3")
        gate = _RecordingGate(reject_all=reject_all)
        generator = _RecordingDeterministicGenerator()
        professor_id = "afe2e-professor"
        student_id = "afe2e-student"
        repository.save_account(Account(id=professor_id, role=AccountRole.PROFESSOR))
        repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
        source_map = {source["source_id"]: source for source in dataset["sources"]}
        course_titles = {course["course_id"]: course["title"] for course in COURSES}
        conversations: dict[str, str] = {}
        for course_id, title in course_titles.items():
            repository.save_course(
                Course(id=course_id, title=title, owner_professor_id=professor_id)
            )
            repository.save_membership(
                CourseMembership(
                    account_id=professor_id,
                    course_id=course_id,
                    role=MembershipRole.PROFESSOR,
                )
            )
            repository.save_membership(
                CourseMembership(
                    account_id=student_id,
                    course_id=course_id,
                    role=MembershipRole.STUDENT,
                )
            )
            chunks = [
                _source_chunk(source)
                for source in dataset["sources"]
                if source["course_id"] == course_id
            ]
            release_id = f"{course_id}-release-v1"
            repository.save_release(
                DigitalTwinRelease(
                    id=release_id,
                    course_id=course_id,
                    profile_id="student-tutor",
                    profile_version="v1",
                    policy_version=1,
                    policy=approved_synthetic_policy(),
                    chunks=chunks,
                    status=StudentReleaseStatus.PUBLISHED,
                    evaluation_status=ReleaseEvaluationStatus.PASSED,
                )
            )

        service = StudentTutoringService(
            repository,
            profile_path=PROFILE_PATH,
            generator=generator,
            evidence_gate=gate,
            tutoring_mode="grounded-assistant",
        )
        for course_id in course_titles:
            conversations[course_id] = service.create_conversation(
                student_id, course_id
            ).id

        rows: list[dict[str, Any]] = []
        try:
            for case in dataset["cases"]:
                product_input = _product_input(case, condition["condition_id"])
                started = time.perf_counter()
                turn = await service.submit_message(
                    student_id,
                    conversations[product_input.course_id],
                    content=product_input.question,
                    client_request_id=product_input.client_request_id,
                )
                latency_ms = (time.perf_counter() - started) * 1000
                hits = gate.hits_by_question.get(product_input.question, [])
                persisted = service.get_conversation(
                    student_id,
                    conversations[product_input.course_id],
                )
                rows.append(
                    _score_case(
                        case,
                        turn,
                        hits,
                        persisted.messages[-1].action == turn.tutor_message.action,
                        latency_ms,
                        source_map,
                        condition["condition_id"],
                    )
                )
        finally:
            repository.close()

    if len(generator.calls) != len(dataset["cases"]):
        raise AcademicPilotError("generator call accounting drifted")
    if any(set(call["input_fields"]) & GOLD_FIELDS for call in generator.calls):
        raise AcademicPilotError("gold field reached the generator")
    return {"summary": _summarize(condition, rows), "cases": rows}


def _source_chunk(source: dict[str, Any]) -> DocumentChunk:
    checksum = canonical_sha256(
        {
            "source_id": source["source_id"],
            "version": source["version"],
            "text": source["text"],
        }
    )
    return DocumentChunk(
        id=f"chunk-{source['source_id']}",
        document_id=f"document-{source['source_id']}",
        text=source["text"],
        ordinal=0,
        source_artifact_id=source["source_id"],
        source_version=source["version"],
        source_checksum=checksum,
        source_label=SourceLabel.COURSE_APPROVED,
        locator="development source paragraph 1",
        retrieval_allowed=True,
        metadata={"title": source["title"], "course_id": source["course_id"]},
    )


def _product_input(case: dict[str, Any], condition_id: str) -> ProductCaseInput:
    payload = {
        "case_id": case["case_id"],
        "client_request_id": f"{condition_id.lower()}-{case['case_id']}",
        "course_id": case["course_id"],
        "question": case["question"],
    }
    if set(payload) != ALLOWED_SYSTEM_FIELDS or set(payload) & GOLD_FIELDS:
        raise AcademicPilotError("product input firewall rejected a case")
    return ProductCaseInput.model_validate(payload)


def _score_case(
    case: dict[str, Any],
    turn,
    hits: list[RetrievalHit],
    persisted_consistently: bool,
    latency_ms: float,
    source_map: dict[str, dict[str, Any]],
    condition_id: str,
) -> dict[str, Any]:
    del source_map
    expected_action = case["expected_action"]
    actual_action = turn.tutor_message.action
    required_sources = set(case["required_source_ids"])
    retrieved_sources = {
        hit.chunk.source_artifact_id or hit.chunk.document_id for hit in hits
    }
    cited_sources = {citation.source_artifact_id for citation in turn.citations}
    matched_citations = cited_sources & required_sources
    answerable = expected_action == "answer"
    normalized_answer = " ".join(turn.tutor_message.content.casefold().split())
    matched_claims = [
        claim
        for claim in case["expected_claims"]
        if " ".join(claim.casefold().split()) in normalized_answer
    ]
    retrieval_recall = (
        len(retrieved_sources & required_sources) / len(required_sources)
        if required_sources
        else None
    )
    citation_precision = (
        len(matched_citations) / len(cited_sources) if cited_sources else (0.0 if answerable else 1.0)
    )
    citation_recall = (
        len(matched_citations) / len(required_sources) if required_sources else None
    )
    claim_recall = (
        len(matched_claims) / len(case["expected_claims"])
        if case["expected_claims"]
        else None
    )
    usage = turn.tutor_message.trace.usage if turn.tutor_message.trace is not None else None
    provider_called = bool(
        turn.tutor_message.trace is not None
        and turn.tutor_message.trace.provider_model
        not in {"not-called", "deterministic/v1"}
    )
    return {
        "condition_id": condition_id,
        "case_id": case["case_id"],
        "course_id": case["course_id"],
        "slice": case["slice"],
        "cluster_id": case["cluster_id"],
        "expected_action": expected_action,
        "actual_action": actual_action,
        "action_correct": actual_action == expected_action,
        "unsupported_release": actual_action == "answer" and not answerable,
        "supported_answer_retained": actual_action == "answer" if answerable else None,
        "retrieval_recall": retrieval_recall,
        "complete_retrieval_evidence": retrieval_recall == 1.0 if answerable else None,
        "expected_claim_recall": claim_recall,
        "expected_claim_complete": claim_recall == 1.0 if answerable else None,
        "claim_precision": None,
        "semantic_factual_f1": None,
        "citation_precision": citation_precision if answerable else None,
        "citation_recall": citation_recall,
        "citation_complete": citation_recall == 1.0 if answerable else None,
        "retrieved_source_ids": sorted(retrieved_sources),
        "cited_source_ids": sorted(cited_sources),
        "latency_ms": latency_ms,
        "persistence_consistent": persisted_consistently,
        "gold_field_count_in_system_input": 0,
        "provider_calls": int(provider_called),
        "input_tokens": usage.input_tokens if usage is not None else 0,
        "output_tokens": usage.output_tokens if usage is not None else 0,
        "cost_usd": usage.approximate_cost_usd if usage is not None else None,
        "private_data_read": False,
        "independently_validated": False,
    }


def _summarize(condition: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if row["expected_action"] == "answer"]
    boundary = [row for row in rows if row["expected_action"] != "answer"]
    latencies = [row["latency_ms"] for row in rows]
    slice_metrics: dict[str, dict[str, Any]] = {}
    for slice_name in sorted({row["slice"] for row in rows}):
        subset = [row for row in rows if row["slice"] == slice_name]
        slice_metrics[slice_name] = {
            "case_count": len(subset),
            "action_accuracy": _mean_bool(subset, "action_correct"),
            "unsupported_release_rate": _mean_bool(subset, "unsupported_release"),
        }
    return {
        "condition_id": condition["condition_id"],
        "selectable": False,
        "method_selected": False,
        "case_count": len(rows),
        "answerable_count": len(answerable),
        "boundary_count": len(boundary),
        "action_accuracy": _metric_with_cluster_interval(rows, "action_correct"),
        "unsupported_release_rate": _metric_with_cluster_interval(
            boundary, "unsupported_release"
        ),
        "supported_answer_retention": _metric_with_cluster_interval(
            answerable, "supported_answer_retained"
        ),
        "expected_claim_complete_rate": _metric_with_cluster_interval(
            answerable, "expected_claim_complete"
        ),
        "citation_precision": _mean_numeric(answerable, "citation_precision"),
        "citation_recall": _mean_numeric(answerable, "citation_recall"),
        "complete_retrieval_evidence_rate": _mean_bool(
            answerable, "complete_retrieval_evidence"
        ),
        "persistence_consistency_rate": _mean_bool(rows, "persistence_consistent"),
        "latency_p50_ms": _percentile(latencies, 0.50),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "provider_calls": sum(row["provider_calls"] for row in rows),
        "input_tokens": sum(row["input_tokens"] for row in rows),
        "output_tokens": sum(row["output_tokens"] for row in rows),
        "cost_usd": sum(row["cost_usd"] or 0 for row in rows),
        "claim_precision": None,
        "semantic_factual_f1": None,
        "slice_metrics": slice_metrics,
        "failure_counts": {
            "wrong_action": sum(not row["action_correct"] for row in rows),
            "unsupported_release": sum(row["unsupported_release"] for row in rows),
            "incomplete_expected_claims": sum(
                row["expected_claim_complete"] is False for row in answerable
            ),
            "incomplete_citations": sum(
                row["citation_complete"] is False for row in answerable
            ),
            "incomplete_retrieval": sum(
                row["complete_retrieval_evidence"] is False for row in answerable
            ),
            "persistence_mismatch": sum(
                not row["persistence_consistent"] for row in rows
            ),
        },
    }


def _metric_with_cluster_interval(
    rows: list[dict[str, Any]], key: str
) -> dict[str, float | int]:
    usable = [row for row in rows if row[key] is not None]
    estimate = _mean_bool(usable, key)
    by_cluster: dict[str, list[float]] = defaultdict(list)
    for row in usable:
        by_cluster[row["cluster_id"]].append(float(bool(row[key])))
    cluster_ids = sorted(by_cluster)
    if not cluster_ids:
        return {
            "estimate": estimate,
            "lower_95": estimate,
            "upper_95": estimate,
            "cluster_count": 0,
        }
    randomizer = random.Random(127)
    replicates = []
    for _ in range(2000):
        sampled = [randomizer.choice(cluster_ids) for _ in cluster_ids]
        values = [value for cluster_id in sampled for value in by_cluster[cluster_id]]
        replicates.append(sum(values) / len(values))
    return {
        "estimate": estimate,
        "lower_95": _percentile(replicates, 0.025),
        "upper_95": _percentile(replicates, 0.975),
        "cluster_count": len(cluster_ids),
    }


def _mean_bool(rows: list[dict[str, Any]], key: str) -> float:
    values = [bool(row[key]) for row in rows if row[key] is not None]
    return sum(values) / len(values) if values else 1.0


def _mean_numeric(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows if row[key] is not None]
    return statistics.fmean(values) if values else 1.0


def _percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    if not 0 <= quantile <= 1 or not all(math.isfinite(value) for value in values):
        raise AcademicPilotError("invalid percentile input")
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--execute-development", action="store_true")
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    instrument = validate_instrument(arguments.instrument)
    if arguments.execute_development:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
        if not instrument["execution_safety"]["development_execution_authorized"]:
            raise AcademicPilotError("development execution is not authorized")
        raise AcademicPilotError("candidate product integration is not complete")
    if arguments.preflight:
        result = preflight(instrument)
    elif arguments.simulate:
        result = asyncio.run(simulate(instrument))
    else:
        result = validate_build(instrument)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if arguments.output is None:
        if "case_results" in result:
            result = {key: value for key, value in result.items() if key != "case_results"}
            rendered = json.dumps(result, indent=2, sort_keys=True)
        print(rendered)
    else:
        if arguments.output.exists():
            raise AcademicPilotError("exclusive output path already exists")
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
