"""Sanitized learner-side evidence collected from the real product.

This is the only learner-state surface the hidden-state evaluation reads. It
is built from public repository accessors, carries no message text, and is
attached to a response's diagnostic trace beside the independent evidence so
that the frozen 010 response payload and its hashes stay unchanged.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.student.autonomy_models import (
    AssessmentOutcome,
    LearnerBeliefStateV2,
    LearnerObservationV2,
)


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConceptBeliefEvidenceV1(_Contract):
    concept_id: str = Field(min_length=1, max_length=128)
    observation_count: int = Field(ge=0)
    assessed_evidence_count: int = Field(ge=0)
    correct_evidence_count: int = Field(ge=0)
    partial_evidence_count: int = Field(ge=0)
    incorrect_evidence_count: int = Field(ge=0)
    attribution_confidence: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)

    def laplace_estimate(self, prior: float = 0.5, weight: float = 2.0) -> float:
        """The count-derived mastery proxy; the product itself stores no probability."""

        successes = self.correct_evidence_count + 0.5 * self.partial_evidence_count
        return (successes + prior * weight) / (self.assessed_evidence_count + weight)


class HypothesisEvidenceV1(_Contract):
    concept_id: str = Field(min_length=1, max_length=128)
    kind: Literal["misconception", "knowledge-gap", "low-confidence", "inactive"]
    probability: float = Field(ge=0, le=1)
    status: Literal["tentative", "supported", "rejected"]


class ObservationEvidenceV1(_Contract):
    observed_at: str = Field(min_length=1, max_length=64)
    concept_ids: list[str] = Field(default_factory=list, max_length=16)
    assessment_outcome: Literal["correct", "partial", "incorrect", "not-assessed"]
    attempt_present: bool
    misconception_observed: bool


class ProactiveDeliveryEvidenceV1(_Contract):
    action_id: str = Field(min_length=1, max_length=128)
    action_kind: str = Field(min_length=1, max_length=64)
    concept_id: str | None = Field(default=None, max_length=128)
    status: str = Field(min_length=1, max_length=32)
    at: str = Field(min_length=1, max_length=64)


class LearnerEvidenceV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    revision: int = Field(ge=0)
    concepts: list[ConceptBeliefEvidenceV1] = Field(default_factory=list)
    hypotheses: list[HypothesisEvidenceV1] = Field(default_factory=list)
    observations: list[ObservationEvidenceV1] = Field(default_factory=list)
    deliveries: list[ProactiveDeliveryEvidenceV1] = Field(default_factory=list)


_OUTCOME_LABEL = {
    AssessmentOutcome.CORRECT: "correct",
    AssessmentOutcome.PARTIAL: "partial",
    AssessmentOutcome.INCORRECT: "incorrect",
    AssessmentOutcome.NOT_ASSESSED: "not-assessed",
}


def build_learner_evidence(
    belief: LearnerBeliefStateV2 | None,
    observations: list[LearnerObservationV2],
    deliveries: list[ProactiveDeliveryEvidenceV1],
) -> LearnerEvidenceV1:
    concepts = [
        ConceptBeliefEvidenceV1(
            concept_id=item.concept_id,
            observation_count=item.observation_count,
            assessed_evidence_count=item.assessed_evidence_count,
            correct_evidence_count=item.correct_evidence_count,
            partial_evidence_count=item.partial_evidence_count,
            incorrect_evidence_count=item.incorrect_evidence_count,
            attribution_confidence=item.attribution_confidence,
            uncertainty=item.uncertainty,
        )
        for item in (belief.concepts if belief is not None else [])
    ]
    hypotheses = [
        HypothesisEvidenceV1(
            concept_id=item.concept_id,
            kind=item.kind,
            probability=item.probability,
            status=item.status,
        )
        for item in (belief.hypotheses if belief is not None else [])
    ]
    observed = [
        ObservationEvidenceV1(
            observed_at=item.observed_at,
            concept_ids=list(item.concept_ids),
            assessment_outcome=_OUTCOME_LABEL[item.assessment_outcome],
            attempt_present=bool(item.perception.attempt_present),
            misconception_observed=bool(item.perception.misconception_observed),
        )
        for item in observations
    ]
    return LearnerEvidenceV1(
        revision=belief.revision if belief is not None else 0,
        concepts=concepts,
        hypotheses=hypotheses,
        observations=observed,
        deliveries=list(deliveries),
    )
