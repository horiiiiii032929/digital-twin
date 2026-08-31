"""Deterministic control-plane components for governed tutoring autonomy.

These components decide evidence eligibility, goal lifecycle, and event
materialization without granting a model authority over course or learner state.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Literal, Sequence
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.grounding.evidence_sufficiency import (
    QuestionTargetedAtomicEvidenceGate,
)
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.student.autonomy_models import (
    AutonomousEventKind,
    AutonomousGoalStatus,
    AutonomousGoalV1,
    PedagogicalPolicyV2,
    ProactiveOpportunityV1,
)
from src.digital_twin.student.models import DigitalTwinRelease
from src.digital_twin.student.tutoring_graph import LearnerState


_TOKEN = re.compile(r"[A-Za-z0-9_+#.-]+")


class AutonomousEvidenceDecisionV1(BaseModel):
    """Inspectable source-range decision used before autonomous generation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    sufficient: bool
    complete: bool
    unique: bool
    current: bool
    authorized: bool
    reason: str = Field(min_length=1, max_length=256)
    selected_chunk_ids: list[str] = Field(default_factory=list, max_length=5)
    source_range_keys: list[str] = Field(default_factory=list, max_length=5)


class AutonomousGoalLifecycleDecisionV1(BaseModel):
    """Deterministic interpretation of the latest learner-state revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    complete: bool
    progress: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=128)
    next_event: AutonomousEventKind | None = None


class AutonomousEvidenceAssessor:
    """Require structurally unique, current, authorized, query-complete evidence."""

    implementation_id = "autonomous-structured-evidence-assessor-v1"

    def __init__(
        self,
        gate: QuestionTargetedAtomicEvidenceGate | None = None,
    ) -> None:
        self.gate = gate or QuestionTargetedAtomicEvidenceGate()

    def assess(
        self,
        release: DigitalTwinRelease | None,
        opportunity: ProactiveOpportunityV1,
        *,
        query: str,
    ) -> AutonomousEvidenceDecisionV1:
        requested_ids = list(opportunity.source_chunk_ids)
        if opportunity.source_chunk_id and opportunity.source_chunk_id not in requested_ids:
            requested_ids.insert(0, opportunity.source_chunk_id)
        if release is None or release.id != opportunity.release_id:
            return self._rejected("current release is unavailable")
        if not requested_ids:
            return self._rejected("opportunity has no evidence lineage")
        if len(requested_ids) != len(set(requested_ids)):
            return self._rejected("opportunity evidence IDs are duplicated", unique=False)

        matches: list[DocumentChunk] = []
        for identifier in requested_ids:
            rows = [chunk for chunk in release.chunks if chunk.id == identifier]
            if len(rows) != 1:
                return self._rejected(
                    "opportunity evidence does not resolve uniquely", unique=False
                )
            matches.append(rows[0])

        keys = [_source_range_key(chunk) for chunk in matches]
        unique = len(keys) == len(set(keys))
        if not unique:
            return self._rejected("canonical source ranges are duplicated", unique=False)

        active_versions: dict[str, int] = {}
        for chunk in release.chunks:
            source_id = chunk.source_artifact_id or chunk.document_id
            active_versions[source_id] = max(
                active_versions.get(source_id, 0), chunk.source_version
            )
        current = all(
            chunk.source_version
            == active_versions[chunk.source_artifact_id or chunk.document_id]
            for chunk in matches
        )
        authorized = all(
            chunk.retrieval_allowed
            and bool(chunk.source_checksum)
            and bool(chunk.content_hash)
            and bool(chunk.locator.strip())
            and bool(chunk.text.strip())
            for chunk in matches
        )
        if not current:
            return self._rejected("evidence is not from the current source version", current=False)
        if not authorized:
            return self._rejected("evidence is not source-authorized", authorized=False)

        hits = [
            RetrievalHit(
                chunk=chunk,
                relevance_score=max(0.0, 1.0 - (index * 0.05)),
                raw_score=max(0.0, 1.0 - (index * 0.05)),
            )
            for index, chunk in enumerate(matches)
        ]
        decision = self.gate.assess(query.strip(), hits)
        if not decision.sufficient:
            return AutonomousEvidenceDecisionV1(
                sufficient=False,
                complete=False,
                unique=True,
                current=True,
                authorized=True,
                reason=decision.reason[:256],
            )
        selected = set(decision.selected_hit_ids)
        selected_chunks = [chunk for chunk in matches if chunk.id in selected]
        if not selected_chunks:
            return self._rejected("evidence gate selected no canonical range")
        return AutonomousEvidenceDecisionV1(
            sufficient=True,
            complete=True,
            unique=True,
            current=True,
            authorized=True,
            reason=decision.reason[:256],
            selected_chunk_ids=[chunk.id for chunk in selected_chunks],
            source_range_keys=[_source_range_key(chunk) for chunk in selected_chunks],
        )

    @staticmethod
    def _rejected(
        reason: str,
        *,
        unique: bool = True,
        current: bool = True,
        authorized: bool = True,
    ) -> AutonomousEvidenceDecisionV1:
        return AutonomousEvidenceDecisionV1(
            sufficient=False,
            complete=False,
            unique=unique,
            current=current,
            authorized=authorized,
            reason=reason,
        )


class DeterministicAutonomousGoalManager:
    """Select, prioritize, and terminate goals from approved objectives."""

    implementation_id = "deterministic-autonomous-goal-manager-v1"

    def select_objective(
        self,
        policy: PedagogicalPolicyV2,
        evidence: Sequence[DocumentChunk],
    ) -> str:
        evidence_terms = set().union(*(_terms(chunk.text) for chunk in evidence))
        return max(
            policy.approved_course_objectives,
            key=lambda objective: (
                len(_terms(objective) & evidence_terms),
                -policy.approved_course_objectives.index(objective),
            ),
        )

    def build_goal(
        self,
        *,
        student_id: str,
        release: DigitalTwinRelease,
        policy: PedagogicalPolicyV2,
        objective: str,
        learner_state: LearnerState | None,
        observed_at: str,
        planner_model: str,
        generator_model: str,
    ) -> AutonomousGoalV1:
        instant = _instant(observed_at)
        signals = learner_state.latest_signals if learner_state else None
        priority = 5 if signals and signals.misconception_observed else 4 if signals and signals.confusion >= 0.7 else 3
        return AutonomousGoalV1(
            goal_id=f"autonomous-goal-{uuid4()}",
            student_id=student_id,
            course_id=release.course_id,
            release_id=release.id,
            policy_version=policy.version,
            profile_id=policy.approved_profile_id,
            profile_sha256=policy.approved_profile_sha256,
            graph_version="governed-autonomous-tutoring-graph-v2.1",
            planner_model=planner_model,
            generator_model=generator_model,
            approved_course_objective=objective,
            learner_subgoal=f"Demonstrate the approved objective: {objective}",
            success_condition=(
                "Complete at least two source-grounded attempts with mastery at or above "
                "0.80, confidence at or above 0.60, and no current confusion or misconception."
            ),
            priority=priority,
            attempt_limit=3,
            expires_at=(instant + timedelta(days=7)).isoformat(),
            created_at=observed_at,
            updated_at=observed_at,
        )

    def interpret(
        self,
        goal: AutonomousGoalV1,
        learner_state: LearnerState | None,
    ) -> AutonomousGoalLifecycleDecisionV1:
        if goal.status != AutonomousGoalStatus.ACTIVE:
            return AutonomousGoalLifecycleDecisionV1(
                complete=goal.status == AutonomousGoalStatus.COMPLETED,
                progress=1.0 if goal.status == AutonomousGoalStatus.COMPLETED else 0.0,
                reason=f"goal-{goal.status.value}",
            )
        if learner_state is None or not learner_state.mastery_by_concept:
            return AutonomousGoalLifecycleDecisionV1(
                complete=False,
                progress=0.0,
                reason=(
                    "attempt-limit-reached"
                    if goal.attempt_count >= goal.attempt_limit
                    else "insufficient-learner-observations"
                ),
                next_event=(
                    None
                    if goal.attempt_count >= goal.attempt_limit
                    else AutonomousEventKind.INCOMPLETE_OBJECTIVE
                ),
            )
        strongest = max(
            learner_state.mastery_by_concept.values(),
            key=lambda item: (item.estimate, item.confidence, item.observation_count),
        )
        signals = learner_state.latest_signals
        complete = bool(
            strongest.estimate >= 0.80
            and strongest.confidence >= 0.60
            and strongest.observation_count >= 2
            and signals is not None
            and signals.attempt_present
            and signals.confusion < 0.40
            and not signals.misconception_observed
        )
        progress = min(
            1.0,
            0.5 * strongest.estimate
            + 0.3 * strongest.confidence
            + 0.2 * min(1.0, strongest.observation_count / 2),
        )
        return AutonomousGoalLifecycleDecisionV1(
            complete=complete,
            progress=1.0 if complete else progress,
            reason=(
                "success-condition-met"
                if complete
                else "attempt-limit-reached"
                if goal.attempt_count >= goal.attempt_limit
                else "goal-needs-more-evidence"
            ),
            next_event=(
                None
                if complete or goal.attempt_count >= goal.attempt_limit
                else AutonomousEventKind.INCOMPLETE_OBJECTIVE
            ),
        )


def select_relevant_chunks(
    objective: str,
    chunks: Sequence[DocumentChunk],
    *,
    limit: int = 5,
) -> list[DocumentChunk]:
    """Deterministically rank source-authorized chunks for a course objective."""

    objective_terms = _terms(objective)
    ranked = sorted(
        (
            chunk
            for chunk in chunks
            if chunk.retrieval_allowed
        ),
        key=lambda chunk: (
            -len(objective_terms & _terms(chunk.text)),
            -(chunk.source_version),
            chunk.id,
        ),
    )
    return [chunk for chunk in ranked if objective_terms & _terms(chunk.text)][:limit]


def _source_range_key(chunk: DocumentChunk) -> str:
    return ":".join(
        (
            chunk.source_artifact_id or chunk.document_id,
            str(chunk.source_version),
            chunk.content_hash,
            chunk.locator,
        )
    )


def _terms(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(value) if len(token) > 1}


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("autonomy timestamps must be timezone-aware")
    return parsed.astimezone(UTC)
