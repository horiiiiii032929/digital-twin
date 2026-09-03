"""Closed-loop driver: a hidden-state learner against the real product adapter.

`run_autonomy_case` replays a fixed event list. A learner whose next message
depends on the tutor's last action needs this driver instead. It uses only
the public adapter operations plus the two sanitized extensions
(`submit_event_observed`, `collect_learner_evidence`), so it stays independent
of graph nodes, tables, and prompts. The hidden truth it accumulates is kept
in a separate object that never reaches the adapter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from src.digital_twin.evaluation.autonomy_contract import (
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationEventV1,
    AutonomyEvaluationResponseV1,
    AutonomyObservedActionV1,
)
from src.digital_twin.evaluation.autonomy_product_adapter import (
    StudentProductAutonomyAdapterV1,
)
from src.digital_twin.evaluation.learner_evidence import LearnerEvidenceV1
from src.digital_twin.evaluation.simulated_learner_v1 import (
    LearnerUtterance,
    TextRealisingLearnerV1,
)

DAY_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class DriverScheduleV1:
    days: int = 30
    decision_hour_utc: int = 10
    reaction_offset_seconds: int = 30 * 60
    activity_offset_seconds: int = 4 * 60 * 60
    snapshot_offset_seconds: int = 8 * 60 * 60
    restart_day: int | None = 15
    question_every_days: int = 7
    misconception_day: int | None = 3


@dataclass
class HiddenUtteranceRecord:
    event_id: str
    day: int
    at_seconds: int
    observed_at: str
    kind: str
    concept_id: str
    hidden_correct: bool | None
    prompted: bool
    product_action: str | None
    realization_method: str = "deterministic-semantic-frame"
    realization_source: str = "canonical"
    realization_fallback_reason: str | None = None
    realization_key: str | None = None


@dataclass
class HiddenDeliveryRecord:
    action_id: str
    day: int
    concept_id: str | None
    action_kind: str
    hidden_mastery: float
    receptive: bool
    produced_attempt: bool


@dataclass
class HiddenDaySnapshot:
    day: int
    at_seconds: int
    hidden_mastery: dict[str, float]
    receptive: bool
    product_estimates: dict[str, float]


@dataclass
class HiddenStateTruthV1:
    case_id: str
    persona: str
    family: str
    seed: int
    concept_ids: list[str]
    response_realization_method: str = "deterministic-semantic-frame"
    utterances: list[HiddenUtteranceRecord] = field(default_factory=list)
    deliveries: list[HiddenDeliveryRecord] = field(default_factory=list)
    days: list[HiddenDaySnapshot] = field(default_factory=list)
    final_hidden_mastery: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HiddenStateRunResult:
    response: AutonomyEvaluationResponseV1
    learner_evidence: LearnerEvidenceV1
    truth: HiddenStateTruthV1
    independent_evidence: dict[str, Any] | None = None


async def run_hidden_state_learner_case(
    adapter: StudentProductAutonomyAdapterV1,
    case: AutonomyEvaluationCaseV1,
    learner: TextRealisingLearnerV1,
    *,
    schedule: DriverScheduleV1 = DriverScheduleV1(),
    clock_origin: datetime,
    collect_independent_evidence: bool = True,
) -> HiddenStateRunResult:
    if clock_origin.tzinfo is None:
        raise ValueError("driver clock origin must be timezone-aware")
    origin = clock_origin.astimezone(UTC)
    truth = HiddenStateTruthV1(
        case_id=case.case_id,
        persona=learner.persona.name,
        family=str(learner.family),
        seed=learner.seed,
        concept_ids=[card.concept_id for card in learner.cards],
        response_realization_method=str(
            getattr(learner, "realization_method", "deterministic-semantic-frame")
        ),
    )
    await adapter.reset(case)
    elapsed = 0
    reacted_delivery_ids: set[str] = set()
    event_counter = 0

    async def advance_to(target_seconds: int) -> None:
        nonlocal elapsed
        if target_seconds > elapsed:
            await adapter.advance_time(target_seconds - elapsed)
            elapsed = target_seconds

    async def submit(utterance: LearnerUtterance, day: int) -> None:
        nonlocal event_counter
        event_counter += 1
        event = AutonomyEvaluationEventV1(
            event_id=f"{case.case_id}:d{day:02d}:u{event_counter:03d}",
            kind="student-message",
            at_seconds=elapsed,
            payload={"message": utterance.text, "turn_kind": utterance.kind},
        )
        observed_at = (origin + timedelta(seconds=elapsed)).replace(microsecond=0).isoformat()
        action: AutonomyObservedActionV1 | None = await adapter.submit_event_observed(event)
        truth.utterances.append(
            HiddenUtteranceRecord(
                event_id=event.event_id,
                day=day,
                at_seconds=elapsed,
                observed_at=observed_at,
                kind=utterance.kind,
                concept_id=utterance.concept_id,
                hidden_correct=utterance.hidden_correct,
                prompted=utterance.prompted,
                product_action=action.action if action is not None else None,
                realization_method=utterance.realization_method,
                realization_source=utterance.realization_source,
                realization_fallback_reason=utterance.realization_fallback_reason,
                realization_key=utterance.realization_key,
            )
        )

    for day in range(1, schedule.days + 1):
        learner.advance_one_day()
        decision_seconds = day * DAY_SECONDS + schedule.decision_hour_utc * 3600
        if schedule.restart_day is not None and day == schedule.restart_day:
            await advance_to(decision_seconds - 3600)
            await adapter.restart()
        await advance_to(decision_seconds)

        # React to any newly delivered proactive message.
        evidence = await adapter.collect_learner_evidence()
        new_deliveries = [
            item
            for item in evidence.deliveries
            if item.status == "delivered" and item.action_id not in reacted_delivery_ids
        ]
        if new_deliveries:
            await advance_to(decision_seconds + schedule.reaction_offset_seconds)
        for delivery in new_deliveries:
            reacted_delivery_ids.add(delivery.action_id)
            target = delivery.concept_id if delivery.concept_id in truth.concept_ids else truth.concept_ids[0]
            hidden_before = learner.hidden_mastery(target)
            receptive = learner.is_receptive()
            utterance = learner.react_to_delivery(delivery.concept_id, delivery.action_kind)
            truth.deliveries.append(
                HiddenDeliveryRecord(
                    action_id=delivery.action_id,
                    day=day,
                    concept_id=delivery.concept_id,
                    action_kind=delivery.action_kind,
                    hidden_mastery=hidden_before,
                    receptive=receptive,
                    produced_attempt=utterance is not None,
                )
            )
            if utterance is not None:
                await submit(utterance, day)

        # Self-directed activity, plus scheduled question and misconception turns.
        await advance_to(decision_seconds + schedule.activity_offset_seconds)
        if schedule.misconception_day is not None and day == schedule.misconception_day:
            await submit(learner.misconception_statement(truth.concept_ids[0]), day)
        elif day % schedule.question_every_days == 1:
            await submit(learner.question(_weakest_concept(learner, truth.concept_ids)), day)
        activity = learner.self_directed_utterance()
        if activity is not None:
            await submit(activity, day)

        # End-of-day snapshot of hidden truth and the product's belief evidence.
        await advance_to(decision_seconds + schedule.snapshot_offset_seconds)
        evidence = await adapter.collect_learner_evidence()
        estimates = {item.concept_id: item.laplace_estimate() for item in evidence.concepts}
        truth.days.append(
            HiddenDaySnapshot(
                day=day,
                at_seconds=elapsed,
                hidden_mastery={c: learner.hidden_mastery(c) for c in truth.concept_ids},
                receptive=learner.is_receptive(),
                product_estimates=estimates,
            )
        )

    await advance_to(case.duration_seconds)
    actions = await adapter.collect_actions()
    final_state = await adapter.snapshot_state()
    metrics = await adapter.collect_operational_metrics()
    diagnostic = await adapter.collect_diagnostic_trace()
    learner_evidence = await adapter.collect_learner_evidence()
    independent = None
    if collect_independent_evidence:
        independent = (await adapter.collect_independent_evidence()).model_dump(mode="json")
    truth.final_hidden_mastery = {c: learner.hidden_mastery(c) for c in truth.concept_ids}
    response = AutonomyEvaluationResponseV1(
        case_id=case.case_id,
        actions=actions,
        final_state=final_state,
        operational_status="completed",
        latency_ms=0.0,
        operational_metrics=metrics,
        diagnostic_trace={
            "manifest": adapter.manifest.model_dump(mode="json"),
            **diagnostic,
            "learner_evidence_v1": learner_evidence.model_dump(mode="json"),
            **({"independent_evidence_v2": independent} if independent is not None else {}),
        },
    )
    return HiddenStateRunResult(
        response=response,
        learner_evidence=learner_evidence,
        truth=truth,
        independent_evidence=independent,
    )


def _weakest_concept(learner: TextRealisingLearnerV1, concept_ids: list[str]) -> str:
    return min(concept_ids, key=lambda c: learner.hidden_mastery(c))
