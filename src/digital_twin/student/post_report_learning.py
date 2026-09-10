"""Explicit post-report learning candidates; historical defaults remain controls.

Estimates and completion rules are inspectable engineering heuristics, not
validated measures of mastery. Repository observations, not delivery counts,
form the input. Selection belongs to the versioned experimental composition.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from math import exp, isfinite, log

from src.digital_twin.student.assessed_planning_input import build_assessed_planning_evidence
from src.digital_twin.student.autonomy_control import (
    AutonomousGoalLifecycleDecisionV1, DeterministicAutonomousGoalManager,
)
from src.digital_twin.student.autonomy_models import (
    AssessmentOutcome, AutonomousActionKind, AutonomousGoalStatus,
    AutonomousGoalV1, CourseDomainModelV1, LearnerBeliefStateV2, LearnerObservationV2,
)
from src.digital_twin.student.autonomy_runtime import AutonomousJobInput
from src.digital_twin.student.learner_estimators import (
    AssessedObservation, BktEstimator, ConceptEstimate, ConceptRecord,
    EstimatorState, EvidenceCountEstimator, LearnerEstimator, PfaEstimator,
)
from src.digital_twin.student.learning_gap import LearningGapPseudonymizer
from src.digital_twin.student.planning_architectures import (
    AnalyticPedagogicalForwardModel, PlanningStateCardV1, _bounded_output,
    _evidence_ready,
)
from src.digital_twin.student.autonomy_eligibility import event_scoped_eligible_actions
from src.digital_twin.student.repository import StudentRepository


class DecayedEvidenceCountEstimator(EvidenceCountEstimator):
    """Laplace-smoothed counts whose effective evidence decays toward the prior."""

    implementation_id = "decayed-evidence-count-v1"

    def __init__(self, half_life_days: float = 7.0) -> None:
        super().__init__()
        if not isfinite(half_life_days) or half_life_days <= 0:
            raise ValueError("evidence half-life must be finite and positive")
        self.half_life_days = half_life_days

    def _factor(self, record: ConceptRecord, now: datetime) -> float:
        days = max(0, (now - record.last_observed_at).total_seconds() / 86400) if record.last_observed_at else 0
        return exp(-log(2) * days / self.half_life_days)

    def update(self, state: EstimatorState, observation: AssessedObservation) -> EstimatorState:
        record = state.concepts.get(observation.concept_id, ConceptRecord())
        if record.last_observed_at and observation.observed_at < record.last_observed_at:
            raise ValueError("estimator observations must be chronological")
        factor = self._factor(record, observation.observed_at)
        updated = replace(record, successes=record.successes * factor + int(observation.correct),
            failures=record.failures * factor + int(not observation.correct),
            evidence_count=record.evidence_count + 1, last_observed_at=observation.observed_at)
        return EstimatorState({**state.concepts, observation.concept_id: updated})

    def estimate(self, state: EstimatorState, concept_id: str, now: datetime) -> ConceptEstimate:
        record = state.concepts.get(concept_id, ConceptRecord())
        factor = self._factor(record, now)
        effective = (record.successes + record.failures) * factor
        return ConceptEstimate(probability=(record.successes * factor + 1) / (effective + 2),
            uncertainty=1 - min(.95, effective / (effective + 2)), evidence_count=record.evidence_count)


def learning_estimator(mode: str) -> LearnerEstimator:
    factories = {"assessed-count": EvidenceCountEstimator, "assessed-decay": DecayedEvidenceCountEstimator,
        "assessed-bkt": BktEstimator, "assessed-pfa": PfaEstimator}
    if mode not in factories:
        raise ValueError("unknown assessed planning mode")
    return factories[mode]()


class ScopedObservationReader:
    """Read only the learner's conversations in the exact published snapshot."""

    def __init__(self, repository: StudentRepository, pseudonymizer: LearningGapPseudonymizer):
        self.repository = repository
        self.pseudonymizer = pseudonymizer

    def key(self, student_id: str, course_id: str) -> str:
        return self.pseudonymizer.learner_key(course_id=course_id, account_id=student_id)

    def read(self, student_id: str, course_id: str, release_id: str) -> list[LearnerObservationV2]:
        expected = self.key(student_id, course_id)
        rows = []
        for conversation in self.repository.list_course_conversations(course_id):
            if conversation.student_id != student_id or conversation.release_id != release_id:
                continue
            for row in self.repository.list_learner_observations_v2(conversation.id):
                if (row.learner_key, row.course_id, row.release_id) != (expected, course_id, release_id):
                    raise ValueError("saved observation scope differs from its conversation")
                rows.append(row)
        return rows


class AssessedPlanningStateResolver:
    implementation_id = "scoped-assessed-planning-state-v1"

    def __init__(self, reader: ScopedObservationReader, estimator: LearnerEstimator):
        self.reader, self.estimator = reader, estimator

    def __call__(self, job: AutonomousJobInput) -> PlanningStateCardV1:
        goal, opportunity = job.goal, job.opportunity
        remaining = max(0, goal.attempt_limit - goal.attempt_count) if goal else 0
        if not opportunity.concept_id:
            return PlanningStateCardV1(goal_attempts_remaining=remaining)
        evidence = build_assessed_planning_evidence(
            self.reader.read(opportunity.student_id, opportunity.course_id, opportunity.release_id),
            learner_key=self.reader.key(opportunity.student_id, opportunity.course_id),
            course_id=opportunity.course_id, release_id=opportunity.release_id,
            concept_id=opportunity.concept_id, now=datetime.fromisoformat(job.now), estimator=self.estimator,
        )
        return PlanningStateCardV1(concept_id=opportunity.concept_id,
            mastery_probability=evidence.estimate.probability,
            uncertainty=evidence.estimate.uncertainty,
            assessed_evidence_count=evidence.estimate.evidence_count,
            recent_incorrect_streak=evidence.recent_incorrect_streak,
            days_since_last_observation=evidence.days_since_last_observation,
            goal_progress=0, goal_attempts_remaining=remaining)


class RecoveryAwareGoalManager(DeterministicAutonomousGoalManager):
    """Two recent, distinct correct turns after the last contradiction per concept."""

    implementation_id = "objective-scoped-recovery-v1"
    requires_observation_history = True

    def __init__(self, reader: ScopedObservationReader, clock, *, evidence_window_days: int = 7):
        if evidence_window_days < 1:
            raise ValueError("goal evidence window must be positive")
        self.reader, self.clock = reader, clock
        self.evidence_window_days = evidence_window_days

    def interpret(self, goal: AutonomousGoalV1, learner_state, *,
        domain_model: CourseDomainModelV1 | None = None,
        additional_observation: LearnerObservationV2 | None = None,
        now: datetime | None = None,
    ) -> AutonomousGoalLifecycleDecisionV1:
        baseline = super().interpret(goal, learner_state, domain_model=domain_model)
        if goal.status != AutonomousGoalStatus.ACTIVE:
            return baseline
        valid_domain = domain_model is not None and (domain_model.course_id, domain_model.release_id) == (goal.course_id, goal.release_id)
        objectives = [o for o in domain_model.objectives if o.statement == goal.approved_course_objective] if valid_domain else []
        expected = self.reader.key(goal.student_id, goal.course_id)
        if len(objectives) != 1 or not objectives[0].concept_ids or not isinstance(learner_state, LearnerBeliefStateV2):
            return AutonomousGoalLifecycleDecisionV1(complete=False, progress=0, reason="recovery-needs-scoped-objective-and-state")
        if (learner_state.learner_key, learner_state.course_id, learner_state.release_id) != (expected, goal.course_id, goal.release_id):
            return AutonomousGoalLifecycleDecisionV1(complete=False, progress=0, reason="recovery-learner-scope-mismatch")
        instant = now or self.clock.now()
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("goal evaluation time must be timezone-aware")
        if instant >= datetime.fromisoformat(goal.expires_at):
            return AutonomousGoalLifecycleDecisionV1(complete=False, progress=0, reason="goal-expired")
        rows = self.reader.read(goal.student_id, goal.course_id, goal.release_id)
        if additional_observation is not None:
            rows.append(additional_observation)
        seen = {}
        for row in rows:
            if (row.learner_key, row.course_id, row.release_id) != (expected, goal.course_id, goal.release_id):
                raise ValueError("goal observation outside authorized scope")
            old = seen.get(row.observation_id)
            if old is not None and old != row:
                raise ValueError("conflicting duplicate goal observation")
            seen[row.observation_id] = row
        counts = []
        for concept in objectives[0].concept_ids:
            buckets = {}
            turn_keys = {}
            for row in seen.values():
                at = datetime.fromisoformat(row.observed_at)
                if at.tzinfo is None or at.utcoffset() is None:
                    raise ValueError("goal observation time must be timezone-aware")
                if not (instant - timedelta(days=self.evidence_window_days) <= at <= instant):
                    continue
                if (concept not in (row.assessment_concept_ids or []) or not row.evidence_keys
                    or not row.source_turn_key or row.assessment_confidence < .5
                    or row.assessment_outcome == AssessmentOutcome.NOT_ASSESSED):
                    continue
                signature = (at, row.assessment_outcome)
                if row.source_turn_key in turn_keys:
                    if turn_keys[row.source_turn_key] != signature:
                        return AutonomousGoalLifecycleDecisionV1(complete=False, progress=0, reason="conflicting-source-turn-assessment")
                    continue
                turn_keys[row.source_turn_key] = signature
                buckets.setdefault(at, []).append(row.assessment_outcome)
            streak = 0
            for at in sorted(buckets):
                outcomes = buckets[at]
                # Equal timestamps cannot establish contradiction-before-correction.
                if any(outcome != AssessmentOutcome.CORRECT for outcome in outcomes):
                    streak = 0
                else:
                    streak += len(outcomes)
            counts.append(streak)
        progress = min(min(1, count / 2) for count in counts)
        complete = all(count >= 2 for count in counts)
        return AutonomousGoalLifecycleDecisionV1(complete=complete, progress=progress,
            reason="recent-target-evidence-satisfied" if complete else "needs-two-recent-correct-turns-per-target")


class AnalyticOnlyPlanner:
    """No provider call: choose the best permitted action under the shared heuristic."""

    implementation_id = "analytic-only-planner-v1"
    model_id = "deterministic/analytic-only-v1"

    def __init__(self, state_card_resolver):
        self.state_card_resolver = state_card_resolver
        self.forward_model = AnalyticPedagogicalForwardModel()

    async def plan(self, job: AutonomousJobInput):
        if not _evidence_ready(job):
            return _bounded_output(job, AutonomousActionKind.NO_ACTION, "analytic-evidence-incomplete")
        state = self.state_card_resolver(job)
        eligible = event_scoped_eligible_actions(job.opportunity.event_kind, job.policy.allowed_actions)
        values = [self.forward_model.predict(state_card=state, action=action,
            evidence_ready=True, lookahead_depth=2) for action in eligible]
        # max retains event order when utilities tie, matching guarded planning.
        action = max(values, key=lambda value: value.utility).action
        return _bounded_output(job, action, "analytic-best-permitted-action")
