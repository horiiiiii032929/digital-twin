"""Deterministic scoring and frozen gates for finite product stages."""

from __future__ import annotations

from collections import defaultdict
import math
import random
import statistics
from typing import Any

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
)
from src.digital_twin.evaluation.factual_qa_scoring import (
    FactualQaCaseScoreV1,
    score_case,
    summarize_scores,
)


class FiniteProductEvaluationError(ValueError):
    """Raised when response/gold packages cannot be compared safely."""


def score_product_responses(
    *,
    cases: list[EvaluationCaseV1],
    gold: list[EvaluationGoldV1],
    responses: list[EvaluationResponseV1],
) -> dict[str, Any]:
    case_by_id = {row.case_id: row for row in cases}
    gold_by_id = {row.case_id: row for row in gold}
    response_by_id = {row.case_id: row for row in responses}
    expected = set(case_by_id)
    if (
        len(expected) != len(cases)
        or set(gold_by_id) != expected
        or set(response_by_id) != expected
        or len(gold_by_id) != len(gold)
        or len(response_by_id) != len(responses)
    ):
        raise FiniteProductEvaluationError("case, gold, and response IDs drifted")
    scores = [
        score_case(case_by_id[case_id], gold_by_id[case_id], response_by_id[case_id])
        for case_id in sorted(expected)
    ]
    return {
        "summary": summarize_scores(scores),
        "case_scores": [row.model_dump(mode="json") for row in scores],
    }


def product_hard_gates(result: dict[str, Any], *, final: bool) -> dict[str, bool]:
    summary = result["summary"]
    metrics = summary["metrics"]
    malformed_rate = summary["operational_failure_count"] / summary["case_count"]
    gates = {
        "fully_grounded_factual_success": (
            metrics["fully_grounded_factual_success"] >= 0.95
        ),
        "action_accuracy_overall": metrics["action_accuracy_overall"] >= 0.95,
        "action_accuracy_answerable": (
            metrics["action_accuracy_answerable"] >= 0.95
        ),
        "boundary_action_accuracy": metrics["boundary_action_accuracy"] >= 0.98,
        "atomic_claim_precision": metrics["atomic_claim_precision"] >= 0.98,
        "atomic_claim_recall": metrics["atomic_claim_recall"] >= 0.95,
        "citation_precision": metrics["citation_precision"] >= 0.98,
        "citation_recall": metrics["citation_recall"] >= 0.95,
        "source_version_validity": metrics["source_version_validity"] == 1.0,
        "canonical_all_evidence_at_3": (
            metrics["canonical_all_evidence_at_3"] >= 0.90
        ),
        "evidence_recall_at_5": metrics["evidence_recall_at_5"] >= 0.95,
        "provider_completion": metrics["provider_completion"] >= 0.995,
        "malformed_output": malformed_rate <= 0.005,
        "zero_severe_unsupported_releases": (
            summary["severe_unsupported_release_count"] == 0
        ),
    }
    if final:
        gates["source_family_lower_95"] = (
            summary["fully_grounded_source_family_interval"]["lower_95"] >= 0.93
        )
    return gates


def paired_candidate_control(
    *,
    candidate: dict[str, Any],
    control: dict[str, Any],
) -> dict[str, Any]:
    candidate_rows = {
        row["case_id"]: FactualQaCaseScoreV1.model_validate(row)
        for row in candidate["case_scores"]
    }
    control_rows = {
        row["case_id"]: FactualQaCaseScoreV1.model_validate(row)
        for row in control["case_scores"]
    }
    if not control_rows or not set(control_rows) <= set(candidate_rows):
        raise FiniteProductEvaluationError("paired control is not a candidate subset")
    grouped: dict[str, list[float]] = defaultdict(list)
    boundary_pairs: list[tuple[FactualQaCaseScoreV1, FactualQaCaseScoreV1]] = []
    for case_id, control_row in sorted(control_rows.items()):
        candidate_row = candidate_rows[case_id]
        if (
            candidate_row.source_family_id != control_row.source_family_id
            or candidate_row.expected_action != control_row.expected_action
        ):
            raise FiniteProductEvaluationError("paired score metadata drifted")
        if candidate_row.answerable:
            grouped[candidate_row.source_family_id].append(
                float(candidate_row.fully_grounded_success)
                - float(control_row.fully_grounded_success)
            )
        else:
            boundary_pairs.append((candidate_row, control_row))
    family_deltas = [statistics.fmean(values) for _, values in sorted(grouped.items())]
    if not family_deltas or not boundary_pairs:
        raise FiniteProductEvaluationError("paired comparison lacks required strata")
    rng = random.Random(20260830)
    replicates = 10_000
    samples = sorted(
        statistics.fmean(rng.choice(family_deltas) for _ in family_deltas)
        for _ in range(replicates)
    )
    lower = samples[math.floor(0.025 * (replicates - 1))]
    upper = samples[math.ceil(0.975 * (replicates - 1))]
    candidate_boundary = sum(row.boundary_safe for row, _ in boundary_pairs) / len(
        boundary_pairs
    )
    control_boundary = sum(row.boundary_safe for _, row in boundary_pairs) / len(
        boundary_pairs
    )
    return {
        "paired_case_count": len(control_rows),
        "source_family_count": len(family_deltas),
        "supported_answer_retention_delta_lower_95": lower,
        "supported_answer_retention_delta_upper_95": upper,
        "supported_answer_retention_delta_estimate": statistics.fmean(
            family_deltas
        ),
        "bootstrap_replicates": replicates,
        "bootstrap_seed": 20260830,
        "boundary_safety_candidate": candidate_boundary,
        "boundary_safety_control": control_boundary,
        "retention_gate_passed": lower >= -0.03,
        "boundary_non_regression_passed": candidate_boundary >= control_boundary,
    }


def complete_product_decision(
    *,
    candidate: dict[str, Any],
    control: dict[str, Any],
    final: bool,
) -> tuple[bool, dict[str, bool], dict[str, Any]]:
    gates = product_hard_gates(candidate, final=final)
    paired = paired_candidate_control(candidate=candidate, control=control)
    passed = all(gates.values()) and bool(
        paired["retention_gate_passed"]
        and paired["boundary_non_regression_passed"]
    )
    return passed, gates, paired
