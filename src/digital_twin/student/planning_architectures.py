"""Switchable autonomy planners for the A/B/C architecture comparison.

The candidates share one implementation: A disables semantic planning, B uses
one bounded proposal at depth zero, C adds an inspectable forward model, and
C+V adds a reject-only verifier as an ablation. Identity, policy, evidence,
delivery, and persistence remain deterministic authorities outside this module.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.llm import (
    LlmClient,
    LlmError,
    LlmIdentityDriftError,
    LlmMessage,
)
from src.digital_twin.student.autonomy_eligibility import (
    event_scoped_eligible_actions,
    preferred_event_action,
)
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
    AutonomousPlannerOutputV1,
)
from src.digital_twin.student.autonomy_runtime import AutonomousJobInput


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AutonomyArchitectureId(StrEnum):
    DETERMINISTIC_WORKFLOW_A = "deterministic-workflow-a"
    GOVERNED_SINGLE_PLANNER_B = "governed-single-planner-b"
    HIERARCHICAL_MODEL_BASED_C = "hierarchical-model-based-c"
    HIERARCHICAL_WITH_VERIFIER_CV = "hierarchical-model-based-c-plus-verifier"


class PlanningStateCardV1(_Contract):
    """Compact observable learner state supplied to every candidate equally."""

    schema_version: str = "1.0.0"
    concept_id: str | None = Field(default=None, max_length=128)
    mastery_probability: float = Field(default=0.5, ge=0, le=1)
    uncertainty: float = Field(default=1.0, ge=0, le=1)
    assessed_evidence_count: int = Field(default=0, ge=0)
    recent_incorrect_streak: int = Field(default=0, ge=0)
    days_since_last_observation: float | None = Field(default=None, ge=0)
    goal_progress: float = Field(default=0, ge=0, le=1)
    goal_attempts_remaining: int = Field(default=0, ge=0)


class EpisodeStepProposalV1(_Contract):
    action: AutonomousActionKind
    expected_observation: str = Field(min_length=1, max_length=300)
    stop_or_replan_predicate: str = Field(min_length=1, max_length=300)


class HierarchicalPlanningProposalV1(_Contract):
    """Only pedagogical fields a planner model may propose."""

    selected_action: AutonomousActionKind
    reason_code: str = Field(min_length=1, max_length=128)
    expected_learner_action: str | None = Field(default=None, max_length=500)
    outcome_observation: str | None = Field(default=None, max_length=500)
    stop_condition: str = Field(min_length=1, max_length=500)
    replan_condition: str | None = Field(default=None, max_length=500)
    episode_steps: list[EpisodeStepProposalV1] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def episode_is_bounded(self) -> "HierarchicalPlanningProposalV1":
        actions = [step.action for step in self.episode_steps]
        if len(actions) != len(set(actions)):
            raise ValueError("episode proposal actions must be unique")
        return self


class PlannerVerificationV1(_Contract):
    accept: bool
    reason_code: str = Field(min_length=1, max_length=128)


class ActionValuePredictionV1(_Contract):
    action: AutonomousActionKind
    immediate_learning_gain: float = Field(ge=0, le=1)
    observation_value: float = Field(ge=0, le=1)
    future_value: float = Field(ge=0, le=1)
    pedagogical_risk: float = Field(ge=0, le=1)
    interruption_cost: float = Field(ge=0, le=1)
    utility: float = Field(ge=-2, le=2)


class ArchitecturePlanTraceV1(_Contract):
    architecture_id: AutonomyArchitectureId
    planner_enabled: bool
    lookahead_depth: int = Field(ge=0, le=3)
    planner_model: str
    verifier_model: str | None = None
    provider_proposal_used: bool
    verifier_used: bool
    verifier_accepted: bool | None = None
    eligible_actions: list[AutonomousActionKind]
    candidate_values: list[ActionValuePredictionV1] = Field(default_factory=list)
    selected_action: AutonomousActionKind
    reason_code: str


class PlanningProposalProvider(Protocol):
    model_id: str

    async def propose(
        self,
        *,
        job: AutonomousJobInput,
        state_card: PlanningStateCardV1,
        eligible_actions: tuple[AutonomousActionKind, ...],
        maximum_episode_steps: int,
    ) -> HierarchicalPlanningProposalV1: ...


class PlanVerifier(Protocol):
    model_id: str

    async def verify(
        self,
        *,
        job: AutonomousJobInput,
        state_card: PlanningStateCardV1,
        proposal: AutonomousPlannerOutputV1,
        eligible_actions: tuple[AutonomousActionKind, ...],
    ) -> PlannerVerificationV1: ...


class PedagogicalForwardModel(Protocol):
    implementation_id: str

    def predict(
        self,
        *,
        state_card: PlanningStateCardV1,
        action: AutonomousActionKind,
        evidence_ready: bool,
        lookahead_depth: int,
    ) -> ActionValuePredictionV1: ...


class AnalyticPedagogicalForwardModel:
    """Inspectable first forward model; it never reads hidden learner state."""

    implementation_id = "analytic-pedagogical-forward-model-v1"

    _BASE_GAIN = {
        AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION: 0.05,
        AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE: 0.18,
        AutonomousActionKind.RECOMMEND_APPROVED_SOURCE: 0.12,
        AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE: 0.24,
        AutonomousActionKind.SCHEDULE_FOLLOW_UP: 0.02,
        AutonomousActionKind.SEND_IN_APP_CHECK_IN: 0.03,
        AutonomousActionKind.SUMMARIZE_PROGRESS: 0.04,
        AutonomousActionKind.CREATE_PROFESSOR_INSIGHT_DRAFT: 0.01,
        AutonomousActionKind.NO_ACTION: 0.0,
    }
    _OBSERVATION_VALUE = {
        AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION: 0.28,
        AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE: 0.12,
        AutonomousActionKind.RECOMMEND_APPROVED_SOURCE: 0.08,
        AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE: 0.24,
        AutonomousActionKind.SCHEDULE_FOLLOW_UP: 0.03,
        AutonomousActionKind.SEND_IN_APP_CHECK_IN: 0.05,
        AutonomousActionKind.SUMMARIZE_PROGRESS: 0.02,
        AutonomousActionKind.CREATE_PROFESSOR_INSIGHT_DRAFT: 0.0,
        AutonomousActionKind.NO_ACTION: 0.0,
    }
    _INTERRUPTION_COST = {
        AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION: 0.03,
        AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE: 0.04,
        AutonomousActionKind.RECOMMEND_APPROVED_SOURCE: 0.04,
        AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE: 0.05,
        AutonomousActionKind.SCHEDULE_FOLLOW_UP: 0.02,
        AutonomousActionKind.SEND_IN_APP_CHECK_IN: 0.08,
        AutonomousActionKind.SUMMARIZE_PROGRESS: 0.04,
        AutonomousActionKind.CREATE_PROFESSOR_INSIGHT_DRAFT: 0.01,
        AutonomousActionKind.NO_ACTION: 0.0,
    }

    def predict(
        self,
        *,
        state_card: PlanningStateCardV1,
        action: AutonomousActionKind,
        evidence_ready: bool,
        lookahead_depth: int,
    ) -> ActionValuePredictionV1:
        if lookahead_depth < 0 or lookahead_depth > 3:
            raise ValueError("lookahead depth must be between zero and three")
        if action == AutonomousActionKind.NO_ACTION:
            return ActionValuePredictionV1(
                action=action,
                immediate_learning_gain=0,
                observation_value=0,
                future_value=0,
                pedagogical_risk=0,
                interruption_cost=0,
                utility=0,
            )
        need = 1.0 - state_card.mastery_probability
        recency = state_card.days_since_last_observation
        spacing = 1.0 if recency is None else 1.0 - math.exp(-recency / 3.0)
        immediate = min(1.0, self._BASE_GAIN[action] * need * (0.5 + 0.5 * spacing))
        observation = min(
            1.0,
            self._OBSERVATION_VALUE[action] * (0.5 + 0.5 * state_card.uncertainty),
        )
        misconception_bonus = 0.0
        if state_card.recent_incorrect_streak >= 2:
            if action == AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE:
                misconception_bonus = 0.12
            elif action == AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION:
                misconception_bonus = 0.04
        future = min(
            1.0,
            lookahead_depth
            * 0.35
            * (immediate + observation)
            * (1.0 - state_card.goal_progress),
        )
        risk = 0.0 if evidence_ready else 1.0
        if action == AutonomousActionKind.SEND_IN_APP_CHECK_IN:
            risk += 0.05 * max(0, state_card.assessed_evidence_count - 2)
        risk = min(1.0, risk)
        interruption = self._INTERRUPTION_COST[action]
        utility = immediate + 0.45 * observation + future + misconception_bonus
        utility -= 0.9 * risk + interruption
        return ActionValuePredictionV1(
            action=action,
            immediate_learning_gain=immediate,
            observation_value=observation,
            future_value=future,
            pedagogical_risk=risk,
            interruption_cost=interruption,
            utility=max(-2.0, min(2.0, utility)),
        )


class LlmHierarchicalPlanningProvider:
    """One structured model proposal; deterministic code keeps authority."""

    def __init__(self, client: LlmClient, *, model_id: str) -> None:
        self.client = client
        self.model_id = model_id

    async def propose(
        self,
        *,
        job: AutonomousJobInput,
        state_card: PlanningStateCardV1,
        eligible_actions: tuple[AutonomousActionKind, ...],
        maximum_episode_steps: int,
    ) -> HierarchicalPlanningProposalV1:
        payload = {
            "instruction": (
                "Choose one pedagogically appropriate action inside eligible_actions. "
                "You may propose a bounded episode, but cannot change identity, course, "
                "release, policy, evidence, consent, delivery, or learner state. Use "
                "no-action when intervention is not justified. Return concise reasons, "
                "not chain-of-thought."
            ),
            "event_kind": job.opportunity.event_kind.value,
            "concept_id": job.opportunity.concept_id,
            "state_card": state_card.model_dump(mode="json"),
            "eligible_actions": [item.value for item in eligible_actions],
            "maximum_episode_steps": maximum_episode_steps,
            "evidence_ready": _evidence_ready(job),
            "goal": (
                {
                    "subgoal": job.goal.learner_subgoal,
                    "success_condition": job.goal.success_condition,
                    "attempts_remaining": max(
                        0, job.goal.attempt_limit - job.goal.attempt_count
                    ),
                }
                if job.goal is not None
                else None
            ),
        }
        response = await self.client.chat(
            [
                LlmMessage(
                    role="system",
                    content=(
                        "Return only the requested bounded tutoring-plan object. "
                        "Never include personal data or hidden reasoning."
                    ),
                ),
                LlmMessage(role="user", content=json.dumps(payload, sort_keys=True)),
            ],
            task="hierarchical_autonomy_plan",
        )
        return HierarchicalPlanningProposalV1.model_validate_json(response.content)


class LlmRejectOnlyPlanVerifier:
    """Optional C+V ablation: a model may reject but never amend a proposal."""

    def __init__(self, client: LlmClient, *, model_id: str) -> None:
        self.client = client
        self.model_id = model_id

    async def verify(
        self,
        *,
        job: AutonomousJobInput,
        state_card: PlanningStateCardV1,
        proposal: AutonomousPlannerOutputV1,
        eligible_actions: tuple[AutonomousActionKind, ...],
    ) -> PlannerVerificationV1:
        payload = {
            "instruction": (
                "Reject only if the move is pedagogically inappropriate for the "
                "observable state or leaves the supplied action envelope. Do not amend it."
            ),
            "event_kind": job.opportunity.event_kind.value,
            "state_card": state_card.model_dump(mode="json"),
            "eligible_actions": [item.value for item in eligible_actions],
            "proposal": proposal.model_dump(mode="json"),
        }
        response = await self.client.chat(
            [
                LlmMessage(
                    role="system",
                    content="Return only an accept/reject object with a short reason code.",
                ),
                LlmMessage(role="user", content=json.dumps(payload, sort_keys=True)),
            ],
            task="autonomy_plan_verifier",
        )
        return PlannerVerificationV1.model_validate_json(response.content)


class SwitchableAutonomyPlanner:
    """One implementation whose two switches recover A, B, C, and C+V."""

    def __init__(
        self,
        *,
        architecture_id: AutonomyArchitectureId,
        proposal_provider: PlanningProposalProvider | None = None,
        verifier: PlanVerifier | None = None,
        forward_model: PedagogicalForwardModel | None = None,
        state_card_resolver: Callable[[AutonomousJobInput], PlanningStateCardV1]
        | None = None,
        lookahead_depth: int | None = None,
        minimum_utility_margin: float = 0.04,
    ) -> None:
        if not math.isfinite(minimum_utility_margin) or minimum_utility_margin < 0:
            raise ValueError("minimum utility margin must be finite and non-negative")
        defaults = {
            AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A: 0,
            AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B: 0,
            AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C: 2,
            AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV: 2,
        }
        resolved_depth = (
            defaults[architecture_id] if lookahead_depth is None else lookahead_depth
        )
        if resolved_depth < 0 or resolved_depth > 3:
            raise ValueError("lookahead depth must be between zero and three")
        if architecture_id == AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A:
            if proposal_provider is not None or verifier is not None or resolved_depth != 0:
                raise ValueError("candidate A must disable planner, verifier, and lookahead")
        elif proposal_provider is None:
            raise ValueError("planner-enabled architectures require a proposal provider")
        if architecture_id == AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B and (
            resolved_depth != 0 or verifier is not None
        ):
            raise ValueError("candidate B is depth-zero planning without a verifier")
        if architecture_id == AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C and verifier:
            raise ValueError("candidate C cannot silently enable the verifier ablation")
        if (
            architecture_id == AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV
            and verifier is None
        ):
            raise ValueError("C+V requires a reject-only verifier")

        self.architecture_id = architecture_id
        self.proposal_provider = proposal_provider
        self.verifier = verifier
        self.forward_model = forward_model or AnalyticPedagogicalForwardModel()
        self.state_card_resolver = state_card_resolver or default_planning_state_card
        self.lookahead_depth = resolved_depth
        self.minimum_utility_margin = minimum_utility_margin
        self.model_id = (
            "deterministic/autonomy-architecture-a-v1"
            if proposal_provider is None
            else proposal_provider.model_id
        )

    async def plan(self, job: AutonomousJobInput) -> AutonomousPlannerOutputV1:
        proposal, _trace = await self.plan_with_trace(job)
        return proposal

    async def plan_with_trace(
        self, job: AutonomousJobInput
    ) -> tuple[AutonomousPlannerOutputV1, ArchitecturePlanTraceV1]:
        eligible = event_scoped_eligible_actions(
            job.opportunity.event_kind, job.policy.allowed_actions
        )
        state_card = self.state_card_resolver(job)
        if self.architecture_id == AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A:
            action = preferred_event_action(
                job.opportunity.event_kind, job.policy.allowed_actions
            )
            output = _bounded_output(job, action, "architecture-a-event-workflow")
            return output, ArchitecturePlanTraceV1(
                architecture_id=self.architecture_id,
                planner_enabled=False,
                lookahead_depth=0,
                planner_model=self.model_id,
                provider_proposal_used=False,
                verifier_used=False,
                eligible_actions=list(eligible),
                selected_action=action,
                reason_code=output.reason_code,
            )

        assert self.proposal_provider is not None
        try:
            provider = await self.proposal_provider.propose(
                job=job,
                state_card=state_card,
                eligible_actions=eligible,
                maximum_episode_steps=max(1, self.lookahead_depth + 1),
            )
            if provider.selected_action not in eligible:
                raise ValueError("planner proposed an action outside the envelope")
            if any(step.action not in eligible for step in provider.episode_steps):
                raise ValueError("planner episode leaves the action envelope")
        except LlmIdentityDriftError:
            raise
        except (LlmError, ValueError):
            return self._safe_failure(eligible, "planner-failure-no-action")

        candidate_values: list[ActionValuePredictionV1] = []
        if self.lookahead_depth == 0:
            selected = provider.selected_action
        else:
            candidate_values = [
                self.forward_model.predict(
                    state_card=state_card,
                    action=action,
                    evidence_ready=_evidence_ready(job),
                    lookahead_depth=self.lookahead_depth,
                )
                for action in eligible
            ]
            by_action = {item.action: item for item in candidate_values}
            ranked = sorted(
                candidate_values,
                key=lambda item: (
                    item.utility
                    + (0.01 if item.action == provider.selected_action else 0.0),
                    -list(eligible).index(item.action),
                ),
                reverse=True,
            )
            selected = ranked[0].action
            if (
                selected != AutonomousActionKind.NO_ACTION
                and by_action[selected].utility <= self.minimum_utility_margin
            ):
                selected = AutonomousActionKind.NO_ACTION

        output = _proposal_to_output(job, provider, selected)
        verifier_accepted: bool | None = None
        if self.verifier is not None and selected != AutonomousActionKind.NO_ACTION:
            try:
                decision = await self.verifier.verify(
                    job=job,
                    state_card=state_card,
                    proposal=output,
                    eligible_actions=eligible,
                )
                verifier_accepted = decision.accept
            except LlmIdentityDriftError:
                raise
            except (LlmError, ValueError):
                verifier_accepted = False
            if not verifier_accepted:
                output = _bounded_output(
                    job, AutonomousActionKind.NO_ACTION, "verifier-rejected"
                )

        trace = ArchitecturePlanTraceV1(
            architecture_id=self.architecture_id,
            planner_enabled=True,
            lookahead_depth=self.lookahead_depth,
            planner_model=self.proposal_provider.model_id,
            verifier_model=self.verifier.model_id if self.verifier is not None else None,
            provider_proposal_used=True,
            verifier_used=self.verifier is not None,
            verifier_accepted=verifier_accepted,
            eligible_actions=list(eligible),
            candidate_values=candidate_values,
            selected_action=output.action,
            reason_code=output.reason_code,
        )
        return output, trace

    def _safe_failure(
        self,
        eligible: tuple[AutonomousActionKind, ...],
        reason: str,
    ) -> tuple[AutonomousPlannerOutputV1, ArchitecturePlanTraceV1]:
        output = AutonomousPlannerOutputV1(
            action=AutonomousActionKind.NO_ACTION,
            reason_code=reason,
            stop_condition="Stop without delivery; wait for a new durable event.",
        )
        return output, ArchitecturePlanTraceV1(
            architecture_id=self.architecture_id,
            planner_enabled=True,
            lookahead_depth=self.lookahead_depth,
            planner_model=self.model_id,
            verifier_model=self.verifier.model_id if self.verifier else None,
            provider_proposal_used=False,
            verifier_used=self.verifier is not None,
            verifier_accepted=False if self.verifier else None,
            eligible_actions=list(eligible),
            selected_action=AutonomousActionKind.NO_ACTION,
            reason_code=reason,
        )


def default_planning_state_card(job: AutonomousJobInput) -> PlanningStateCardV1:
    """Derive a conservative observable state when no calibrated store is bound."""

    goal = job.goal
    assessed = len(job.opportunity.supporting_observation_ids)
    attempts = goal.attempt_count if goal is not None else 0
    attempt_limit = goal.attempt_limit if goal is not None else 0
    progress = attempts / attempt_limit if attempt_limit else 0.0
    event = job.opportunity.event_kind
    incorrect_streak = (
        2
        if event
        in {AutonomousEventKind.REPEATED_CONFUSION, AutonomousEventKind.MISCONCEPTION}
        else 1 if event == AutonomousEventKind.PRACTICE_INCOMPLETE else 0
    )
    return PlanningStateCardV1(
        concept_id=job.opportunity.concept_id,
        mastery_probability=min(0.95, (attempts + 1) / (attempts + 2)),
        uncertainty=1.0 / (assessed + 1),
        assessed_evidence_count=assessed,
        recent_incorrect_streak=incorrect_streak,
        goal_progress=progress,
        goal_attempts_remaining=max(0, attempt_limit - attempts),
    )


def _evidence_ready(job: AutonomousJobInput) -> bool:
    return all(
        (
            job.evidence_complete,
            job.evidence_unique,
            job.evidence_current,
            job.evidence_authorized,
            bool(job.evidence_keys),
        )
    )


def _bounded_output(
    job: AutonomousJobInput,
    action: AutonomousActionKind,
    reason_code: str,
) -> AutonomousPlannerOutputV1:
    if action == AutonomousActionKind.NO_ACTION:
        return AutonomousPlannerOutputV1(
            action=action,
            reason_code=reason_code,
            stop_condition="Stop without delivery; wait for a new durable event.",
        )
    return AutonomousPlannerOutputV1(
        action=action,
        reason_code=reason_code,
        expected_learner_action="Respond in the course workspace.",
        required_evidence_keys=list(job.evidence_keys),
        outcome_observation="Observe the next durable learner action.",
        stop_condition="Stop after one bounded action.",
        replan_condition="Replan only after a new durable event or scheduled wake-up.",
    )


def _proposal_to_output(
    job: AutonomousJobInput,
    provider: HierarchicalPlanningProposalV1,
    selected: AutonomousActionKind,
) -> AutonomousPlannerOutputV1:
    if selected == AutonomousActionKind.NO_ACTION:
        return _bounded_output(
            job, selected, f"architecture-no-action:{provider.reason_code}"
        )
    selected_step = next(
        (step for step in provider.episode_steps if step.action == selected), None
    )
    return AutonomousPlannerOutputV1(
        action=selected,
        reason_code=f"architecture-selected:{provider.reason_code}",
        expected_learner_action=provider.expected_learner_action
        or "Respond in the course workspace.",
        required_evidence_keys=list(job.evidence_keys),
        outcome_observation=(
            selected_step.expected_observation
            if selected_step is not None
            else provider.outcome_observation or "Observe the next durable learner action."
        ),
        stop_condition=provider.stop_condition,
        replan_condition=(
            selected_step.stop_or_replan_predicate
            if selected_step is not None
            else provider.replan_condition
        ),
    )


__all__ = [
    "ActionValuePredictionV1",
    "AnalyticPedagogicalForwardModel",
    "ArchitecturePlanTraceV1",
    "AutonomyArchitectureId",
    "EpisodeStepProposalV1",
    "HierarchicalPlanningProposalV1",
    "LlmHierarchicalPlanningProvider",
    "LlmRejectOnlyPlanVerifier",
    "PedagogicalForwardModel",
    "PlannerVerificationV1",
    "PlanningProposalProvider",
    "PlanningStateCardV1",
    "PlanVerifier",
    "SwitchableAutonomyPlanner",
    "default_planning_state_card",
]
