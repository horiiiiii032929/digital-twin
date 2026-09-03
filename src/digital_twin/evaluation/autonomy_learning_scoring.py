"""New evaluation dimensions scored against hidden learner truth.

Sits beside the independent autonomy scorer and never changes its inputs or
outputs. Consumes: the hidden truth from the closed-loop driver, the public
response, and the sanitized learner evidence. Emits a separate score model.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.evaluation.autonomy_contract import AutonomyEvaluationResponseV1
from src.digital_twin.evaluation.autonomy_learner_driver import HiddenStateTruthV1
from src.digital_twin.evaluation.hidden_state_metrics import (
    auroc,
    brier_score,
    expected_calibration_error,
    paired_bootstrap_difference,
)
from src.digital_twin.evaluation.learner_evidence import LearnerEvidenceV1

MASTERY_THRESHOLD = 0.85


class HiddenStateCaseScoreV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    condition: str
    persona: str
    family: str
    seed: int
    response_realization_method: str = "deterministic-semantic-frame"
    realization_fallback_rate: float = Field(default=0.0, ge=0, le=1)
    # perception
    attempt_turns: int
    attribution_accuracy: float | None
    assessment_agreement: float | None
    attempts_recognised: float | None
    # calibration of the product's count-derived estimate
    mse_vs_hidden: float | None
    brier_next_outcome: float | None
    ece_next_outcome: float | None
    auroc_next_outcome: float | None
    # proactive
    messages_delivered: int
    wasted_rate: float | None
    follow_up_fraction: float | None
    quiet_hour_violations: int
    frequency_violations: int
    cooldown_violations: int
    # outcome proxy
    final_hidden_mastery: float
    concepts_mastered_final: int
    # operations
    provider_calls: int
    cost_usd: float
    restart_count: int


def score_hidden_state_case(
    *,
    condition: str,
    truth: HiddenStateTruthV1,
    response: AutonomyEvaluationResponseV1,
    evidence: LearnerEvidenceV1,
    quiet_hours_utc: tuple[int, int] = (23, 2),
    max_messages_per_7_days: int = 3,
    cooldown_hours: int = 24,
) -> HiddenStateCaseScoreV1:
    # ----- perception: match product observations to hidden utterances by event id
    observations_by_event = {
        item.event_id: item for item in evidence.observations if item.event_id is not None
    }
    attempts = [u for u in truth.utterances if u.kind == "attempt"]
    attribution_hits: list[bool] = []
    assessment_hits: list[bool] = []
    recognised: list[bool] = []
    predictions: list[tuple[float, bool]] = []
    estimate_by_day = {snapshot.day: snapshot.product_estimates for snapshot in truth.days}
    for utterance in attempts:
        observation = observations_by_event.get(utterance.event_id)
        recognised.append(observation is not None and observation.attempt_present)
        if observation is None:
            continue
        primary = observation.concept_ids[0] if observation.concept_ids else None
        attribution_hits.append(primary == utterance.concept_id)
        if utterance.hidden_correct is not None and observation.assessment_outcome != "not-assessed":
            product_correct = observation.assessment_outcome == "correct"
            assessment_hits.append(product_correct == utterance.hidden_correct)
        if utterance.hidden_correct is not None:
            previous = estimate_by_day.get(utterance.day - 1, {})
            predictions.append((previous.get(utterance.concept_id, 0.5), utterance.hidden_correct))

    # ----- calibration of the count-derived estimate against hidden mastery
    squared: list[float] = []
    for snapshot in truth.days:
        for concept_id, hidden in snapshot.hidden_mastery.items():
            estimate = snapshot.product_estimates.get(concept_id, 0.5)
            squared.append((estimate - hidden) ** 2)

    # ----- proactive quality from hidden truth and timestamps
    delivered = [d for d in truth.deliveries]
    wasted = [d.hidden_mastery >= MASTERY_THRESHOLD or not d.receptive for d in delivered]
    followed = [d.produced_attempt for d in delivered]
    delivered_actions = sorted(
        (
            (datetime.fromisoformat(item.at), item.concept_id)
            for item in evidence.deliveries
            if item.status == "delivered"
        ),
        key=lambda pair: pair[0],
    )
    quiet = frequency = cooldown = 0
    start, end = quiet_hours_utc
    for index, (at, concept_id) in enumerate(delivered_actions):
        hour = at.hour
        in_quiet = hour >= start or hour < end if start > end else start <= hour < end
        quiet += int(in_quiet)
        window = [a for a, _ in delivered_actions[:index] if at - a < timedelta(days=7)]
        frequency += int(len(window) >= max_messages_per_7_days)
        cooldown += int(
            any(
                c == concept_id and at - a < timedelta(hours=cooldown_hours)
                for a, c in delivered_actions[:index]
            )
        )

    finals = list(truth.final_hidden_mastery.values())
    return HiddenStateCaseScoreV1(
        case_id=truth.case_id,
        condition=condition,
        persona=truth.persona,
        family=truth.family,
        seed=truth.seed,
        response_realization_method=truth.response_realization_method,
        realization_fallback_rate=(
            sum(
                item.realization_source == "canonical-fallback"
                for item in truth.utterances
            )
            / len(truth.utterances)
            if truth.utterances
            else 0.0
        ),
        attempt_turns=len(attempts),
        attribution_accuracy=_mean_bool(attribution_hits),
        assessment_agreement=_mean_bool(assessment_hits),
        attempts_recognised=_mean_bool(recognised),
        mse_vs_hidden=statistics.fmean(squared) if squared else None,
        brier_next_outcome=brier_score(predictions),
        ece_next_outcome=expected_calibration_error(predictions),
        auroc_next_outcome=auroc(predictions),
        messages_delivered=len(delivered),
        wasted_rate=_mean_bool(wasted),
        follow_up_fraction=_mean_bool(followed),
        quiet_hour_violations=quiet,
        frequency_violations=frequency,
        cooldown_violations=cooldown,
        final_hidden_mastery=statistics.fmean(finals) if finals else 0.0,
        concepts_mastered_final=sum(1 for value in finals if value >= MASTERY_THRESHOLD),
        provider_calls=response.provider_calls,
        cost_usd=response.cost_usd,
        restart_count=response.final_state.restart_count,
    )


def _mean_bool(values: list[bool]) -> float | None:
    return statistics.fmean(float(v) for v in values) if values else None


SUMMARY_METRICS: tuple[str, ...] = (
    "attribution_accuracy",
    "assessment_agreement",
    "attempts_recognised",
    "mse_vs_hidden",
    "brier_next_outcome",
    "ece_next_outcome",
    "auroc_next_outcome",
    "messages_delivered",
    "wasted_rate",
    "follow_up_fraction",
    "quiet_hour_violations",
    "frequency_violations",
    "cooldown_violations",
    "final_hidden_mastery",
    "concepts_mastered_final",
    "provider_calls",
    "cost_usd",
    "realization_fallback_rate",
)

CONTRAST_METRICS: tuple[str, ...] = (
    "mse_vs_hidden",
    "attribution_accuracy",
    "wasted_rate",
    "follow_up_fraction",
    "final_hidden_mastery",
    "messages_delivered",
)


def summarize_hidden_state_scores(
    scores: list[HiddenStateCaseScoreV1],
    *,
    contrasts: list[tuple[str, str]],
    resamples: int = 1000,
) -> dict[str, Any]:
    by_condition: dict[str, list[HiddenStateCaseScoreV1]] = {}
    for score in scores:
        by_condition.setdefault(score.condition, []).append(score)
    aggregate: dict[str, dict[str, Any]] = {}
    for condition, items in sorted(by_condition.items()):
        row: dict[str, Any] = {"n_cases": len(items)}
        for metric in SUMMARY_METRICS:
            values = [getattr(item, metric) for item in items]
            present = [float(v) for v in values if v is not None]
            row[metric] = statistics.fmean(present) if present else None
        for family in sorted({item.family for item in items}):
            subset = [item for item in items if item.family == family]
            row[f"mse_vs_hidden[{family}]"] = _mean_or_none([i.mse_vs_hidden for i in subset])
            row[f"wasted_rate[{family}]"] = _mean_or_none([i.wasted_rate for i in subset])
        row["worst_persona_final_mastery"] = min(
            statistics.fmean(i.final_hidden_mastery for i in items if i.persona == persona)
            for persona in {i.persona for i in items}
        )
        row["realization_slices"] = {
            method: {
                "n_cases": len(subset),
                "attribution_accuracy": _mean_or_none(
                    [item.attribution_accuracy for item in subset]
                ),
                "assessment_agreement": _mean_or_none(
                    [item.assessment_agreement for item in subset]
                ),
                "final_hidden_mastery": statistics.fmean(
                    item.final_hidden_mastery for item in subset
                ),
                "realization_fallback_rate": statistics.fmean(
                    item.realization_fallback_rate for item in subset
                ),
            }
            for method in sorted({item.response_realization_method for item in items})
            for subset in [[i for i in items if i.response_realization_method == method]]
        }
        row["hard_gates"] = {
            "zero_quiet_hour_violations": all(i.quiet_hour_violations == 0 for i in items),
            "zero_frequency_violations": all(i.frequency_violations == 0 for i in items),
            "zero_cooldown_violations": all(i.cooldown_violations == 0 for i in items),
        }
        aggregate[condition] = row
    paired: dict[str, dict[str, Any]] = {}
    for candidate, control in contrasts:
        if candidate not in by_condition or control not in by_condition:
            continue
        paired[f"{candidate} vs {control}"] = {
            metric: paired_bootstrap_difference(
                by_condition[candidate],
                by_condition[control],
                value=lambda item, m=metric: getattr(item, m),
                key=lambda item: (
                    item.family,
                    item.persona,
                    item.seed,
                    item.response_realization_method,
                ),
                resamples=resamples,
                seed=f"hidden-state:{metric}:{candidate}:{control}",
            )
            for metric in CONTRAST_METRICS
        }
    return {"aggregate": aggregate, "paired_contrasts": paired}


def _mean_or_none(values: list[float | None]) -> float | None:
    present = [float(v) for v in values if v is not None]
    return statistics.fmean(present) if present else None
