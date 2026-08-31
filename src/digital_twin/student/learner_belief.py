"""Deterministic learner-evidence accounting for governed tutoring V2.1.

This module deliberately does not estimate or persist a mastery probability.
It records what was observed, which observations were actually assessed, and
how much uncertainty remains. More sophisticated estimators such as BKT/PFA
can later be compared behind the same contract without changing product APIs.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from src.digital_twin.student.autonomy_models import (
    AssessmentOutcome,
    ConceptAttributionV2,
    LearnerBeliefStateV2,
    LearnerHypothesisV2,
    LearnerObservationV2,
    LearnerStateDeltaV2,
)
from src.digital_twin.tutor_policy import timestamp_now


class DeterministicEvidenceCountBeliefEstimator:
    """Revise evidence summaries using only validated observation fields."""

    implementation_id = "deterministic-assessed-evidence-count-v1"

    def initial_state(
        self,
        *,
        learner_key: str,
        course_id: str,
        release_id: str,
        active_goal_ids: list[str] | None = None,
    ) -> LearnerBeliefStateV2:
        return LearnerBeliefStateV2(
            learner_key=learner_key,
            course_id=course_id,
            release_id=release_id,
            active_goal_ids=list(active_goal_ids or [])[:3],
        )

    def revise(
        self,
        prior: LearnerBeliefStateV2,
        observation: LearnerObservationV2,
        *,
        active_goal_ids: list[str] | None = None,
        updated_at: str | None = None,
    ) -> tuple[LearnerBeliefStateV2, LearnerStateDeltaV2]:
        if (
            prior.learner_key != observation.learner_key
            or prior.course_id != observation.course_id
            or prior.release_id != observation.release_id
        ):
            raise ValueError("belief revision scope differs from its observation")

        by_concept = {item.concept_id: item for item in prior.concepts}
        changed: list[str] = []
        for concept_id in observation.concept_ids:
            current = by_concept.get(
                concept_id,
                ConceptAttributionV2(
                    concept_id=concept_id,
                    attribution_confidence=0,
                    uncertainty=1,
                ),
            )
            observation_ids = [*current.observation_ids, observation.observation_id]
            if len(observation_ids) > 64:
                observation_ids = observation_ids[-64:]
            evidence_keys = list(
                dict.fromkeys([*current.evidence_keys, *observation.evidence_keys])
            )[-16:]
            assessed = observation.assessment_outcome != AssessmentOutcome.NOT_ASSESSED
            correct = observation.assessment_outcome == AssessmentOutcome.CORRECT
            partial = observation.assessment_outcome == AssessmentOutcome.PARTIAL
            incorrect = observation.assessment_outcome == AssessmentOutcome.INCORRECT
            assessed_count = current.assessed_evidence_count + int(assessed)
            observation_count = current.observation_count + 1
            # Evidence count, not a knowledge-state probability. Two assessed
            # observations are needed before confidence reaches one half.
            confidence = min(0.95, assessed_count / (assessed_count + 2))
            by_concept[concept_id] = ConceptAttributionV2(
                concept_id=concept_id,
                observation_count=observation_count,
                assessed_evidence_count=assessed_count,
                correct_evidence_count=current.correct_evidence_count + int(correct),
                partial_evidence_count=current.partial_evidence_count + int(partial),
                incorrect_evidence_count=current.incorrect_evidence_count + int(incorrect),
                attribution_confidence=confidence,
                uncertainty=1 - confidence,
                observation_ids=observation_ids,
                evidence_keys=evidence_keys,
            )
            changed.append(concept_id)

        hypotheses = self._hypotheses(
            observation,
            by_concept,
            observed_at=updated_at or observation.observed_at,
        )
        next_goals = list(active_goal_ids if active_goal_ids is not None else prior.active_goal_ids)
        next_state = LearnerBeliefStateV2(
            learner_key=prior.learner_key,
            course_id=prior.course_id,
            release_id=prior.release_id,
            revision=prior.revision + 1,
            concepts=sorted(by_concept.values(), key=lambda item: item.concept_id),
            hypotheses=hypotheses,
            active_goal_ids=next_goals[:3],
            updated_at=updated_at or timestamp_now(),
        )
        delta = LearnerStateDeltaV2(
            previous_revision=prior.revision,
            next_revision=next_state.revision,
            completed_goal_ids=[
                goal_id for goal_id in prior.active_goal_ids if goal_id not in next_goals
            ],
            activated_goal_ids=[
                goal_id for goal_id in next_goals if goal_id not in prior.active_goal_ids
            ],
            changed_concept_ids=changed,
            reason_code="validated-learner-observation",
        )
        return next_state, delta

    @staticmethod
    def _hypotheses(
        observation: LearnerObservationV2,
        attributions: dict[str, ConceptAttributionV2],
        *,
        observed_at: str,
    ) -> list[LearnerHypothesisV2]:
        parsed = datetime.fromisoformat(observed_at)
        if parsed.tzinfo is None:
            raise ValueError("learner observations require timezone-aware timestamps")
        expires_at = (parsed.astimezone(UTC) + timedelta(days=7)).isoformat()
        hypotheses: list[LearnerHypothesisV2] = []
        for concept_id in observation.concept_ids:
            attribution = attributions[concept_id]
            if observation.perception.misconception_observed:
                kind = "misconception"
                probability = 0.75
            elif attribution.incorrect_evidence_count >= 2:
                kind = "knowledge-gap"
                probability = 0.70
            elif observation.perception.confidence is not None and observation.perception.confidence < 0.4:
                kind = "low-confidence"
                probability = 0.65
            else:
                continue
            digest = hashlib.sha256(
                f"{observation.learner_key}:{concept_id}:{kind}".encode("utf-8")
            ).hexdigest()[:24]
            hypotheses.append(
                LearnerHypothesisV2(
                    hypothesis_id=f"hypothesis-{digest}",
                    concept_id=concept_id,
                    kind=kind,
                    probability=probability,
                    observation_ids=[observation.observation_id],
                    status="tentative",
                    expires_at=expires_at,
                )
            )
        return hypotheses
