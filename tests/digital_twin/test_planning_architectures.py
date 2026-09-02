from datetime import UTC, datetime, timedelta

import pytest

from src.digital_twin.llm import LlmIdentityDriftError
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
    AutonomousGoalV1,
    PedagogicalPolicyV2,
    ProactiveOpportunityV1,
)
from src.digital_twin.student.autonomy_runtime import (
    GRAPH_VERSION,
    AutonomousJobInput,
    GovernedAutonomousTutoringGraph,
)
from src.digital_twin.student.planning_architectures import (
    ActionValuePredictionV1,
    AutonomyArchitectureId,
    EpisodeStepProposalV1,
    GuardedPolicyValuePlanner,
    HierarchicalPlanningProposalV1,
    PlannerVerificationV1,
    PlanningStateCardV1,
    SwitchableAutonomyPlanner,
)


NOW = datetime(2026, 9, 2, 4, 0, tzinfo=UTC)
PROFILE_SHA = "a" * 64
ALLOWED = [
    AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
    AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
    AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE,
]


class _ProposalProvider:
    model_id = "gpt-5.6-luna"

    def __init__(
        self,
        action: AutonomousActionKind = AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        reason_code: str = "fixture-plan",
    ) -> None:
        self.action = action
        self.reason_code = reason_code
        self.calls = 0
        self.maximum_steps: list[int] = []

    async def propose(self, **kwargs):
        self.calls += 1
        self.maximum_steps.append(kwargs["maximum_episode_steps"])
        return HierarchicalPlanningProposalV1(
            selected_action=self.action,
            reason_code=self.reason_code,
            expected_learner_action="Explain one next step.",
            outcome_observation="Observe whether the next step is correct.",
            stop_condition="Stop after one move.",
            replan_condition="Replan after a new assessed attempt.",
            episode_steps=[
                EpisodeStepProposalV1(
                    action=self.action,
                    expected_observation="One assessed attempt.",
                    stop_or_replan_predicate="New assessed attempt received.",
                )
            ],
        )


class _RejectingVerifier:
    model_id = "gpt-5.6-luna"

    async def verify(self, **kwargs):
        del kwargs
        return PlannerVerificationV1(accept=False, reason_code="not-useful")


class _IdentityDriftProvider(_ProposalProvider):
    async def propose(self, **kwargs):
        del kwargs
        raise LlmIdentityDriftError(
            provider_model="unexpected-model", provider_revision=None
        )


class _FixedForwardModel:
    implementation_id = "fixed-forward-model-test"

    def predict(self, *, action, **_kwargs):
        utility = {
            AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION: 0.2,
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE: 0.5,
            AutonomousActionKind.NO_ACTION: 0.0,
        }.get(action, 0.1)
        return ActionValuePredictionV1(
            action=action,
            immediate_learning_gain=max(0.0, utility),
            observation_value=0.0,
            future_value=0.0,
            pedagogical_risk=0.0,
            interruption_cost=0.0,
            utility=utility,
        )


def _job(
    *,
    event: AutonomousEventKind = AutonomousEventKind.MISCONCEPTION,
    evidence_ready: bool = True,
) -> AutonomousJobInput:
    goal = AutonomousGoalV1(
        goal_id="goal-architecture-test",
        student_id="student-a",
        course_id="course-a",
        release_id="release-a",
        policy_version=1,
        profile_id="profile-a",
        profile_sha256=PROFILE_SHA,
        graph_version=GRAPH_VERSION,
        planner_model="gpt-5.6-luna",
        generator_model="gpt-5.4-mini-2026-03-17",
        approved_course_objective="Explain cache coherence.",
        learner_subgoal="Correct the invalidation misconception.",
        success_condition="Explain one correct step.",
        attempt_limit=3,
        attempt_count=1,
        expires_at=(NOW + timedelta(days=7)).isoformat(),
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
    )
    opportunity = ProactiveOpportunityV1(
        opportunity_id="opportunity-architecture-test",
        idempotency_key="architecture-test",
        event_kind=event,
        student_id="student-a",
        course_id="course-a",
        release_id="release-a",
        policy_version=1,
        profile_id="profile-a",
        profile_sha256=PROFILE_SHA,
        graph_version=GRAPH_VERSION,
        planner_model="gpt-5.6-luna",
        generator_model="gpt-5.4-mini-2026-03-17",
        goal_id=goal.goal_id,
        supporting_observation_ids=["observation-1", "observation-2"],
        concept_id="cache-coherence",
        source_chunk_id="chunk-a",
        source_chunk_ids=["chunk-a"],
        earliest_action_at=(NOW - timedelta(minutes=1)).isoformat(),
        latest_action_at=(NOW + timedelta(hours=1)).isoformat(),
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
    )
    policy = PedagogicalPolicyV2(
        course_id="course-a",
        version=1,
        approved_by="professor-a",
        approved_profile_id="profile-a",
        approved_profile_sha256=PROFILE_SHA,
        approved_course_objectives=["Explain cache coherence."],
        autonomy_enabled=True,
        allowed_actions=ALLOWED,
        updated_at=NOW.isoformat(),
    )
    return AutonomousJobInput(
        opportunity=opportunity,
        goal=goal,
        policy=policy,
        professor_id="professor-a",
        current_release_id="release-a",
        current_profile_id="profile-a",
        current_profile_sha256=PROFILE_SHA,
        membership_active=True,
        consent_active=True,
        evidence_keys=["source-range-a"] if evidence_ready else [],
        evidence_chunk_ids=["chunk-a"] if evidence_ready else [],
        evidence_complete=evidence_ready,
        evidence_unique=evidence_ready,
        evidence_current=evidence_ready,
        evidence_authorized=evidence_ready,
        now=NOW.isoformat(),
    )


@pytest.mark.asyncio
async def test_a_is_deterministic_and_uses_no_planner_call(tmp_path):
    planner = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A
    )
    output, trace = await planner.plan_with_trace(_job())

    assert output.action == AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
    assert trace.planner_enabled is False
    assert trace.lookahead_depth == 0

    graph = GovernedAutonomousTutoringGraph(
        planner=planner,
        checkpoint_database_path=str(tmp_path / "candidate-a.sqlite3"),
    )
    result = await graph.run(_job())
    assert result.trace.planning_calls == 0


@pytest.mark.asyncio
async def test_c_at_depth_zero_recovers_b_exactly():
    provider_b = _ProposalProvider(AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE)
    provider_c = _ProposalProvider(AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE)
    b = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B,
        proposal_provider=provider_b,
    )
    c_depth_zero = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C,
        proposal_provider=provider_c,
        lookahead_depth=0,
    )

    b_output, b_trace = await b.plan_with_trace(_job())
    c_output, c_trace = await c_depth_zero.plan_with_trace(_job())

    assert b_output == c_output
    assert b_trace.selected_action == c_trace.selected_action
    assert provider_b.maximum_steps == provider_c.maximum_steps == [1]


@pytest.mark.asyncio
async def test_c_adds_forward_lookahead_without_widening_action_envelope():
    provider = _ProposalProvider(AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION)
    planner = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C,
        proposal_provider=provider,
        state_card_resolver=lambda _job: PlanningStateCardV1(
            concept_id="cache-coherence",
            mastery_probability=0.2,
            uncertainty=0.8,
            assessed_evidence_count=2,
            recent_incorrect_streak=2,
            days_since_last_observation=3,
            goal_progress=0.2,
            goal_attempts_remaining=2,
        ),
    )

    output, trace = await planner.plan_with_trace(_job())

    assert output.action == AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
    assert trace.lookahead_depth == 2
    assert {row.action for row in trace.candidate_values} == set(
        trace.eligible_actions
    )
    assert output.action in trace.eligible_actions


@pytest.mark.asyncio
async def test_c_prefers_no_action_when_authoritative_evidence_is_incomplete():
    planner = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C,
        proposal_provider=_ProposalProvider(),
    )

    output, trace = await planner.plan_with_trace(_job(evidence_ready=False))

    assert output.action == AutonomousActionKind.NO_ACTION
    assert max(
        row.pedagogical_risk
        for row in trace.candidate_values
        if row.action != AutonomousActionKind.NO_ACTION
    ) == 1.0


@pytest.mark.asyncio
async def test_out_of_envelope_model_action_fails_closed():
    planner = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B,
        proposal_provider=_ProposalProvider(
            AutonomousActionKind.CREATE_PROFESSOR_INSIGHT_DRAFT
        ),
    )

    output, trace = await planner.plan_with_trace(_job())

    assert output.action == AutonomousActionKind.NO_ACTION
    assert trace.provider_proposal_used is False
    assert trace.reason_code == "planner-failure-no-action"


@pytest.mark.asyncio
async def test_c_plus_verifier_can_reject_but_not_amend():
    planner = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV,
        proposal_provider=_ProposalProvider(),
        verifier=_RejectingVerifier(),
    )

    output, trace = await planner.plan_with_trace(_job())

    assert output.action == AutonomousActionKind.NO_ACTION
    assert trace.verifier_used is True
    assert trace.verifier_accepted is False


@pytest.mark.asyncio
async def test_identity_drift_is_never_converted_to_a_quality_decision():
    planner = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B,
        proposal_provider=_IdentityDriftProvider(),
    )

    with pytest.raises(LlmIdentityDriftError):
        await planner.plan_with_trace(_job())


@pytest.mark.asyncio
async def test_runtime_prefix_keeps_maximum_length_provider_reason_valid():
    provider_reason = "r" * 128
    planner = SwitchableAutonomyPlanner(
        architecture_id=AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B,
        proposal_provider=_ProposalProvider(reason_code=provider_reason),
    )

    output, trace = await planner.plan_with_trace(_job())

    assert output.action == AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
    assert len(output.reason_code) == 128
    assert output.reason_code.startswith("architecture-selected:")
    assert ":sha256-" in output.reason_code
    assert trace.reason_code == output.reason_code


def test_provider_reason_is_normalized_before_local_contract_validation():
    proposal = HierarchicalPlanningProposalV1.model_validate(
        {
            "selected_action": "ask-diagnostic-question",
            "reason_code": "reason-" * 40,
            "expected_learner_action": None,
            "outcome_observation": None,
            "stop_condition": "Stop after one move.",
            "replan_condition": None,
            "episode_steps": [],
        }
    )
    verification = PlannerVerificationV1.model_validate(
        {"accept": True, "reason_code": "verify-" * 40}
    )

    assert len(proposal.reason_code) <= 128
    assert len(verification.reason_code) <= 128
    assert ":sha256-" in proposal.reason_code
    assert ":sha256-" in verification.reason_code


@pytest.mark.asyncio
async def test_policy_value_planner_promotes_only_with_model_value_agreement():
    planner = GuardedPolicyValuePlanner(
        proposal_provider=_ProposalProvider(
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
        ),
        forward_model=_FixedForwardModel(),
    )

    output, trace = await planner.plan_with_trace(
        _job(event=AutonomousEventKind.STUDENT_MESSAGE)
    )

    assert output.action == AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
    assert trace.provider_proposal_used is True
    assert trace.verifier_used is False


@pytest.mark.asyncio
async def test_policy_value_planner_retains_baseline_on_disagreement_or_failure():
    disagreement = GuardedPolicyValuePlanner(
        proposal_provider=_ProposalProvider(
            AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
        ),
        forward_model=_FixedForwardModel(),
    )
    drift = GuardedPolicyValuePlanner(
        proposal_provider=_IdentityDriftProvider(),
        forward_model=_FixedForwardModel(),
    )

    output, _trace = await disagreement.plan_with_trace(
        _job(event=AutonomousEventKind.STUDENT_MESSAGE)
    )
    assert output.action == AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
    with pytest.raises(LlmIdentityDriftError):
        await drift.plan(_job(event=AutonomousEventKind.STUDENT_MESSAGE))


def test_invalid_switch_combinations_fail_at_construction():
    with pytest.raises(ValueError, match="candidate B"):
        SwitchableAutonomyPlanner(
            architecture_id=AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B,
            proposal_provider=_ProposalProvider(),
            lookahead_depth=1,
        )
    with pytest.raises(ValueError, match=r"C\+V"):
        SwitchableAutonomyPlanner(
            architecture_id=AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV,
            proposal_provider=_ProposalProvider(),
        )


def test_bounded_episode_can_repeat_an_action_without_widening_authority():
    proposal = HierarchicalPlanningProposalV1(
        selected_action=AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        reason_code="repeat-diagnostic-after-observation",
        stop_condition="Stop after the bounded episode.",
        episode_steps=[
            EpisodeStepProposalV1(
                action=AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
                expected_observation="Observe the first explanation.",
                stop_or_replan_predicate="Continue only if uncertainty remains.",
            ),
            EpisodeStepProposalV1(
                action=AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
                expected_observation="Observe the refined explanation.",
                stop_or_replan_predicate="Stop after the second observation.",
            ),
        ],
    )

    assert len(proposal.episode_steps) == 2
    assert {step.action for step in proposal.episode_steps} == {
        AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
    }
