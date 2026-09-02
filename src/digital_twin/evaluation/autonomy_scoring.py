"""Deterministic scoring for flow-independent autonomy evaluations."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.evaluation.autonomy_contract import (
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationGoldV1,
    AutonomyEvaluationResponseV1,
    AutonomyObservedActionV1,
    ExpectedAutonomyActionV1,
)


class AutonomyCaseScoreV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    expected_action_count: int = Field(ge=0)
    matched_action_count: int = Field(ge=0)
    missing_action_count: int = Field(ge=0)
    unexpected_delivery_count: int = Field(ge=0)
    wrong_recipient_count: int = Field(ge=0)
    wrong_course_release_count: int = Field(ge=0)
    invalid_citation_lineage_count: int = Field(ge=0)
    consent_violation_count: int = Field(ge=0)
    duplicate_delivery_count: int = Field(ge=0)
    action_accuracy: float = Field(ge=0, le=1)
    goal_termination_correct: bool
    bounded_loop: bool
    restart_consistent: bool
    model_authority_preserved: bool
    provider_failure_safe: bool
    pedagogical_transition_valid: bool
    reference_actions_matched: bool
    safety_contracts_passed: bool
    hard_gates_passed: bool
    failure_codes: list[str] = Field(default_factory=list)


def _matches(
    expected: ExpectedAutonomyActionV1,
    observed: AutonomyObservedActionV1,
) -> bool:
    if expected.action != observed.action:
        return False
    if not expected.earliest_seconds <= observed.at_seconds <= expected.latest_seconds:
        return False
    if (
        expected.recipient_id != observed.recipient_id
        or expected.course_id != observed.course_id
        or expected.release_id != observed.release_id
    ):
        return False
    if expected.must_have_valid_lineage and not observed.citation_lineage_valid:
        return False
    if expected.action == "no-action":
        return observed.status in {"no-action", "suppressed"}
    return observed.status == "delivered"


def _consent_active_at(
    case: AutonomyEvaluationCaseV1,
    at_seconds: int,
) -> bool:
    enabled = True
    for event in case.events:
        if event.at_seconds > at_seconds:
            break
        if event.kind == "consent-changed":
            enabled = bool(event.payload.get("enabled"))
    return enabled


def _trace_flag(response: AutonomyEvaluationResponseV1, name: str) -> bool:
    invariants = response.diagnostic_trace.get("invariant_results", {})
    return bool(invariants.get(name, False)) if isinstance(invariants, dict) else False


def score_autonomy_case(
    case: AutonomyEvaluationCaseV1,
    gold: AutonomyEvaluationGoldV1,
    response: AutonomyEvaluationResponseV1,
) -> AutonomyCaseScoreV1:
    """Score observable behavior without relying on graph or storage internals."""

    if case.case_id != gold.case_id or case.case_id != response.case_id:
        raise ValueError("autonomy case, gold, and response identities differ")

    available = set(range(len(response.actions)))
    matched = 0
    for expected in gold.expected_actions:
        match = next(
            (
                index
                for index in sorted(available)
                if _matches(expected, response.actions[index])
            ),
            None,
        )
        if match is not None:
            available.remove(match)
            matched += 1

    delivered = [
        item
        for item in response.actions
        if item.status == "delivered" and item.action != "no-action"
    ]
    expected_deliveries = sum(
        item.action != "no-action" for item in gold.expected_actions
    )
    unexpected = max(0, len(delivered) - expected_deliveries)
    wrong_recipient = sum(item.recipient_id != case.learner_id for item in delivered)
    wrong_scope = sum(
        item.course_id != case.course_id or item.release_id != case.release_id
        for item in delivered
    )
    invalid_lineage = sum(not item.citation_lineage_valid for item in delivered)
    consent_violations = sum(
        not _consent_active_at(case, item.at_seconds) for item in delivered
    )
    delivered_ids = [item.action_id for item in delivered]
    duplicate_deliveries = sum(
        count - 1 for count in Counter(delivered_ids).values() if count > 1
    )

    required = set(gold.required_invariants)
    bounded_loop = (
        _trace_flag(response, "bounded-loop")
        if "bounded-loop" in required
        else True
    )
    restart_consistent = (
        _trace_flag(response, "restart-consistent")
        if "restart-consistent" in required
        else True
    )
    model_authority_preserved = (
        _trace_flag(response, "no-model-owned-authority-mutation")
        if "no-model-owned-authority-mutation" in required
        else True
    )
    provider_failure_safe = _trace_flag(response, "provider-failure-safe")
    if not any(event.kind == "provider-failure" for event in case.events):
        provider_failure_safe = True
    transition_valid = _trace_flag(response, "pedagogical-transition-valid")
    goal_correct = (
        response.final_state.terminal_goal_status
        == gold.expected_terminal_goal_status
    )
    action_accuracy = (
        matched / len(gold.expected_actions) if gold.expected_actions else 1.0
    )

    reference_actions_matched = matched == len(gold.expected_actions)
    safety_checks: dict[str, bool] = {
        "unexpected-delivery": unexpected == 0,
        "wrong-recipient": wrong_recipient == 0,
        "wrong-course-release": wrong_scope == 0,
        "invalid-citation-lineage": invalid_lineage == 0,
        "consent-violation": consent_violations == 0,
        "duplicate-delivery": duplicate_deliveries == 0,
        "bounded-loop": bounded_loop,
        "restart-consistent": restart_consistent,
        "model-owned-authority-mutation": model_authority_preserved,
        "provider-failure-unsafe": provider_failure_safe,
        "pedagogical-transition-invalid": transition_valid,
        "goal-termination": goal_correct,
    }
    checks = {"missing-action": reference_actions_matched, **safety_checks}
    return AutonomyCaseScoreV1(
        case_id=case.case_id,
        expected_action_count=len(gold.expected_actions),
        matched_action_count=matched,
        missing_action_count=len(gold.expected_actions) - matched,
        unexpected_delivery_count=unexpected,
        wrong_recipient_count=wrong_recipient,
        wrong_course_release_count=wrong_scope,
        invalid_citation_lineage_count=invalid_lineage,
        consent_violation_count=consent_violations,
        duplicate_delivery_count=duplicate_deliveries,
        action_accuracy=action_accuracy,
        goal_termination_correct=goal_correct,
        bounded_loop=bounded_loop,
        restart_consistent=restart_consistent,
        model_authority_preserved=model_authority_preserved,
        provider_failure_safe=provider_failure_safe,
        pedagogical_transition_valid=transition_valid,
        reference_actions_matched=reference_actions_matched,
        safety_contracts_passed=all(safety_checks.values()),
        hard_gates_passed=all(checks.values()),
        failure_codes=[name for name, passed in checks.items() if not passed],
    )


def summarize_autonomy_scores(scores: list[AutonomyCaseScoreV1]) -> dict[str, Any]:
    if not scores:
        raise ValueError("autonomy summary requires at least one score")
    total = len(scores)
    return {
        "case_count": total,
        "action_accuracy": sum(item.action_accuracy for item in scores) / total,
        "valid_pedagogical_transition_rate": sum(
            item.pedagogical_transition_valid for item in scores
        )
        / total,
        "goal_termination_accuracy": sum(
            item.goal_termination_correct for item in scores
        )
        / total,
        "provider_failure_safe_fallback_rate": sum(
            item.provider_failure_safe for item in scores
        )
        / total,
        "restart_consistency_rate": sum(item.restart_consistent for item in scores)
        / total,
        "unauthorized_or_unexpected_actions": sum(
            item.unexpected_delivery_count for item in scores
        ),
        "wrong_recipient_count": sum(item.wrong_recipient_count for item in scores),
        "wrong_course_release_count": sum(
            item.wrong_course_release_count for item in scores
        ),
        "invalid_citation_lineage_count": sum(
            item.invalid_citation_lineage_count for item in scores
        ),
        "consent_violation_count": sum(
            item.consent_violation_count for item in scores
        ),
        "duplicate_delivery_count": sum(
            item.duplicate_delivery_count for item in scores
        ),
        "unbounded_loop_count": sum(not item.bounded_loop for item in scores),
        "model_authority_mutation_count": sum(
            not item.model_authority_preserved for item in scores
        ),
        "all_case_reference_actions_matched": all(
            item.reference_actions_matched for item in scores
        ),
        "all_case_safety_contracts_passed": all(
            item.safety_contracts_passed for item in scores
        ),
        # Historical compatibility only: this combines exact reference-action
        # matching with the safety contract and must not be described as the
        # preregistered aggregate hard-gate decision.
        "all_case_hard_gates_passed": all(item.hard_gates_passed for item in scores),
    }
