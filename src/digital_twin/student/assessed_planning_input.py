"""Experimental adapter from saved assessments to replaceable estimators.

Available through explicit post-report runtime selectors. Values are uncalibrated estimates,
not measured mastery. Delivery counts are intentionally absent from the input.
"""

from dataclasses import dataclass
from datetime import datetime

from src.digital_twin.student.autonomy_models import AssessmentOutcome, LearnerObservationV2
from src.digital_twin.student.learner_estimators import (
    AssessedObservation,
    ConceptEstimate,
    LearnerEstimator,
)


@dataclass(frozen=True)
class AssessedPlanningEvidence:
    implementation_id: str
    concept_id: str
    estimate: ConceptEstimate
    recent_incorrect_streak: int
    days_since_last_observation: float | None
    included_observation_ids: tuple[str, ...]
    excluded_observations: tuple[tuple[str, str], ...]


def build_assessed_planning_evidence(
    observations: list[LearnerObservationV2],
    *,
    learner_key: str,
    course_id: str,
    release_id: str,
    concept_id: str,
    now: datetime,
    estimator: LearnerEstimator,
) -> AssessedPlanningEvidence:
    """Convert explicitly scoped binary assessments without reading raw text."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("planning time must be timezone-aware")
    if not concept_id or not course_id or not release_id:
        raise ValueError("planning evidence requires an explicit scope")
    if len(learner_key) != 64 or any(char not in "0123456789abcdef" for char in learner_key):
        raise ValueError("planning evidence requires a pseudonymous learner key")
    unique: dict[str, LearnerObservationV2] = {}
    for observation in observations:
        if (observation.learner_key, observation.course_id, observation.release_id) != (
            learner_key, course_id, release_id
        ):
            raise ValueError("observation is outside the authorized planning scope")
        previous = unique.get(observation.observation_id)
        if previous is not None and previous != observation:
            raise ValueError("conflicting duplicate observation ID")
        unique[observation.observation_id] = observation

    ordered = []
    for observation in unique.values():
        observed_at = datetime.fromisoformat(observation.observed_at)
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("observation time must be timezone-aware")
        ordered.append((observed_at, observation.observation_id, observation))
    ordered.sort(key=lambda item: (item[0], item[1]))
    state = estimator.initial_state()
    included: list[str] = []
    excluded: list[tuple[str, str]] = []
    streak = 0
    last_observed_at = None
    seen_turns = {}
    admitted = []
    for observed_at, observation_id, observation in ordered:
        reason = None
        if observed_at > now:
            reason = "future-observation"
        elif observation.assessment_concept_ids is None:
            reason = "legacy-assessment-scope-unspecified"
        elif concept_id not in observation.assessment_concept_ids:
            reason = "concept-not-assessed"
        elif observation.assessment_outcome not in {AssessmentOutcome.CORRECT, AssessmentOutcome.INCORRECT}:
            reason = "not-a-binary-assessment"
        elif not observation.evidence_keys:
            reason = "assessment-evidence-missing"
        elif not observation.source_turn_key:
            reason = "assessment-turn-missing"
        elif observation.assessment_confidence < .5:
            reason = "assessment-confidence-insufficient"
        if reason is not None:
            excluded.append((observation_id, reason))
            continue
        signature = (observed_at, observation.assessment_outcome)
        if observation.source_turn_key in seen_turns:
            if seen_turns[observation.source_turn_key] != signature:
                raise ValueError("conflicting duplicate source-turn assessment")
            excluded.append((observation_id, "duplicate-source-turn"))
            continue
        seen_turns[observation.source_turn_key] = signature
        admitted.append((observed_at, observation_id, observation))
    outcomes_at = {}
    for observed_at, _, observation in admitted:
        outcomes_at.setdefault(observed_at, set()).add(observation.assessment_outcome)
    for observed_at, observation_id, observation in admitted:
        # Second-resolution timestamps cannot order contradictory turns. Do not
        # let an arbitrary hash order determine a BKT/PFA update or error streak.
        if len(outcomes_at[observed_at]) > 1:
            excluded.append((observation_id, "ambiguous-equal-time-assessments"))
            continue
        correct = observation.assessment_outcome == AssessmentOutcome.CORRECT
        state = estimator.update(state, AssessedObservation(concept_id, correct, observed_at))
        included.append(observation_id)
        streak = 0 if correct else streak + 1
        last_observed_at = observed_at
    return AssessedPlanningEvidence(
        implementation_id=estimator.implementation_id,
        concept_id=concept_id,
        estimate=estimator.estimate(state, concept_id, now),
        recent_incorrect_streak=streak,
        days_since_last_observation=(
            (now - last_observed_at).total_seconds() / 86400
            if last_observed_at is not None else None
        ),
        included_observation_ids=tuple(included),
        excluded_observations=tuple(excluded),
    )
