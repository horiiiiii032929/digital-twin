from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.digital_twin.llm import FixtureLlmClient
from src.digital_twin.generation import authoritative_citation_for_chunk
from src.digital_twin.grounding import (
    AtomicClaimEvidenceValidator,
    ExactQuoteAtomicClaimVerifier,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.grounding.models import (
    AtomicAnswerClaim,
    GenerationTrace,
    TutorAnswer,
)
from src.digital_twin.student import (
    Conversation,
    Message,
    OutreachChannel,
    ProactiveOutreachService,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    TeachingProfileDepth,
    TeachingProfileService,
    seed_synthetic_student_workflow,
)
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
    PedagogicalPolicyV2,
)
from src.digital_twin.student.autonomy_control import AutonomousEvidenceAssessor
from src.digital_twin.student.autonomy_runtime import (
    DETERMINISTIC_GENERATOR_MODEL,
    GRAPH_VERSION,
    AutonomousJobInput,
    DeterministicAutonomousWordingGenerator,
    GovernedAutonomousTutoringGraph,
    LiveAutonomousPlanner,
)
from src.digital_twin.student.autonomy_service import (
    GovernedAutonomyService,
    RepositoryGroundedWordingGenerator,
)
from src.digital_twin.student.tutoring_graph import TutoringMode


NOW = datetime(2026, 8, 31, 4, 0, tzinfo=UTC)
OBJECTIVE = "Explain how cache coherence protects replicated processor data."
ALLOWED_ACTIONS = [
    AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
    AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
    AutonomousActionKind.RECOMMEND_APPROVED_SOURCE,
    AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE,
    AutonomousActionKind.SEND_IN_APP_CHECK_IN,
]
PROFILE = (
    Path(__file__).resolve().parents[2]
    / "research/05_evaluation/profiles/student-tutor-v1.json"
)


class _UnsupportedClaimGenerator:
    async def generate_for_intent(self, question, hits, policy, **kwargs):
        del question, policy, kwargs
        chunk = hits[0].chunk
        return TutorAnswer(
            content="The Moon is made of cheese.",
            citations=[authoritative_citation_for_chunk(chunk)],
            atomic_claims=[
                AtomicAnswerClaim(
                    claim_id="claim-unsupported",
                    text="The Moon is made of cheese.",
                    evidence_hit_ids=[chunk.id],
                )
            ],
            trace=GenerationTrace(
                generator_id="unsupported-test-generator",
                provider_model="synthetic-provider",
                prompt_version="test-v1",
                policy_action="answer",
                latency_ms=0,
            ),
        )


def _autonomy_fixture(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "autonomy.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    profiles = TeachingProfileService(repository)
    draft = profiles.create_draft(
        fixture.professor_id,
        fixture.course_a_id,
        {
            "tone": "Patient, precise, and encouraging",
            "depth": TeachingProfileDepth.BALANCED,
            "explanation_structure": ["diagnose", "hint", "check"],
            "example_preferences": ["systems examples"],
            "misconception_handling": "Identify the misconception and ask for one corrected step.",
            "integrity_limits": "Require an attempt before help on assessed work.",
            "help_ladder": ["diagnostic question", "hint", "worked analogy"],
            "outreach_policy": "Use private in-app follow-ups within the approved limits.",
        },
    )
    preview = profiles.preview(
        fixture.professor_id, fixture.course_a_id, draft.profile_id
    )
    approved = profiles.approve(
        fixture.professor_id,
        fixture.course_a_id,
        draft.profile_id,
        preview_sha256=preview.preview_sha256,
    )
    old_release = repository.get_published_release(fixture.course_a_id)
    release = old_release.model_copy(
        update={
            "id": "release-a-autonomy-v2",
            "status": StudentReleaseStatus.DRAFT,
            "teaching_profile_id": approved.profile_id,
            "teaching_profile_sha256": approved.content_sha256,
            "created_at": "2026-08-31T00:00:00+00:00",
        },
        deep=True,
    )
    repository.save_release(release)
    repository.publish_release(release.id)
    outreach = ProactiveOutreachService(repository)
    outreach.update_preference(
        fixture.student_a_id,
        fixture.course_a_id,
        channel=OutreachChannel.IN_APP,
        enabled=True,
        timezone="UTC",
        quiet_hours_start="23:00",
        quiet_hours_end="02:00",
        max_messages_per_7_days=3,
    )
    service = GovernedAutonomyService(repository, outreach)
    service.set_policy(
        fixture.professor_id,
        fixture.course_a_id,
        approved_course_objectives=[OBJECTIVE],
        allowed_actions=ALLOWED_ACTIONS,
        autonomy_enabled=True,
    )
    return repository, fixture, service, release, approved


def _goal_and_opportunity(service, fixture, release):
    goal = service.create_goal(
        student_id=fixture.student_a_id,
        course_id=fixture.course_a_id,
        approved_course_objective=OBJECTIVE,
        learner_subgoal="Recall why replicated cache data needs coherence.",
        success_condition="Explain the consistency purpose without a hint.",
        expires_at=(NOW + timedelta(days=7)).isoformat(),
    )
    opportunity = service.create_opportunity(
        student_id=fixture.student_a_id,
        course_id=fixture.course_a_id,
        goal_id=goal.goal_id,
        event_kind=AutonomousEventKind.SPACED_REVIEW_DUE,
        concept_id="cache-coherence",
        source_chunk_id=release.chunks[0].id,
        earliest_action_at=(NOW - timedelta(minutes=1)).isoformat(),
        latest_action_at=(NOW + timedelta(hours=1)).isoformat(),
        idempotency_key="autonomy-test-spaced-review",
    )
    return goal, opportunity


@pytest.mark.asyncio
async def test_due_opportunity_delivers_once_and_survives_restart(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, opportunity = _goal_and_opportunity(service, fixture, release)

    first = await service.process_due(worker_id="worker-a", now=NOW)
    second = await service.process_due(worker_id="worker-b", now=NOW)

    assert len(first) == 1
    assert first[0].opportunity_id == opportunity.opportunity_id
    assert first[0].outcome == "delivered"
    assert first[0].action_kind == AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE
    assert second == []
    assert len(service.outreach.list_inbox(fixture.student_a_id)) == 1
    assert len(repository.list_autonomous_actions(fixture.course_a_id)) == 1
    repository.close()

    reopened = SQLiteStudentRepository(tmp_path / "autonomy.sqlite3")
    stored_goal = reopened.get_autonomous_goal(goal.goal_id)
    assert stored_goal is not None
    assert stored_goal.attempt_count == 1
    assert stored_goal.status == goal.status
    assert len(reopened.list_autonomous_actions(fixture.course_a_id)) == 1
    assert reopened.list_due_autonomous_opportunities(NOW.isoformat()) == []
    reopened.close()


@pytest.mark.asyncio
async def test_scheduled_wakeup_preserves_concept_and_evidence_lineage(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, _ = _goal_and_opportunity(service, fixture, release)

    first = await service.process_due(worker_id="worker-day-0", now=NOW)
    second = await service.process_due(
        worker_id="worker-day-1", now=NOW + timedelta(days=1)
    )

    assert first[0].outcome == "delivered"
    assert second[0].outcome == "delivered"
    opportunities = repository.list_autonomous_actions(fixture.course_a_id)
    assert len(opportunities) == 2
    repeated = repository.get_autonomous_opportunity(
        opportunities[-1].opportunity_id
    )
    assert repeated.concept_id == "cache-coherence"
    assert repeated.source_chunk_id == release.chunks[0].id
    assert len(service.outreach.list_inbox(fixture.student_a_id)) == 2


@pytest.mark.asyncio
async def test_student_response_links_back_to_autonomous_goal(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, _ = _goal_and_opportunity(service, fixture, release)
    await service.process_due(worker_id="worker", now=NOW)
    action = repository.list_autonomous_actions(fixture.course_a_id)[0]
    outreach_message = service.outreach.list_inbox(fixture.student_a_id)[0].message
    conversation = repository.save_conversation(
        Conversation(
            id="conversation-autonomy-response",
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            release_id=release.id,
            created_at=NOW.isoformat(),
            updated_at=(NOW + timedelta(minutes=2)).isoformat(),
        )
    )
    student_message = Message(
        id="message-autonomy-response",
        conversation_id=conversation.id,
        role="student",
        content="The invalidation keeps cached copies from silently diverging.",
        action="question",
        client_request_id="request-autonomy-response",
        created_at=(NOW + timedelta(minutes=2)).isoformat(),
    )
    tutor_message = Message(
        id="message-autonomy-response-tutor",
        conversation_id=conversation.id,
        role="tutor",
        content="Thanks. I recorded your response safely.",
        action="safe-failure",
        response_to_message_id=student_message.id,
        created_at=(NOW + timedelta(minutes=2)).isoformat(),
    )

    repository.save_turn(
        conversation,
        student_message,
        tutor_message,
        [],
        [],
        responding_to_outreach_message_id=outreach_message.id,
    )

    outcome = repository.get_autonomous_outcome(action.action_id)
    assert outcome.kind.value == "answered"
    assert outcome.goal_id == goal.goal_id
    assert outcome.learner_observation_id == student_message.id


@pytest.mark.asyncio
async def test_student_dismissal_updates_outcome_and_cancels_replan(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, _ = _goal_and_opportunity(service, fixture, release)
    await service.process_due(worker_id="worker", now=NOW)
    action = repository.list_autonomous_actions(fixture.course_a_id)[0]
    message = service.outreach.list_inbox(fixture.student_a_id)[0].message

    dismissed = service.outreach.dismiss(fixture.student_a_id, message.id)
    later = await service.process_due(
        worker_id="worker-later",
        now=NOW + timedelta(days=1),
    )

    outcome = repository.get_autonomous_outcome(action.action_id)
    assert dismissed.message.status.value == "dismissed"
    assert outcome is not None and outcome.kind.value == "dismissed"
    assert outcome.next_wake_at is None
    assert repository.get_autonomous_goal(goal.goal_id).status.value == "active"
    assert later == []


@pytest.mark.asyncio
async def test_expired_goal_cancels_future_work(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, opportunity = _goal_and_opportunity(service, fixture, release)

    results = await service.process_due(
        worker_id="worker", now=NOW + timedelta(days=8)
    )

    assert results == []
    assert repository.get_autonomous_goal(goal.goal_id).status.value == "expired"
    assert (
        repository.get_autonomous_opportunity(opportunity.opportunity_id).status.value
        == "expired"
    )


@pytest.mark.asyncio
async def test_kill_switch_cancels_goal_and_pending_work(tmp_path):
    repository, fixture, service, release, approved = _autonomy_fixture(tmp_path)
    goal, opportunity = _goal_and_opportunity(service, fixture, release)

    stopped = service.set_policy(
        fixture.professor_id,
        fixture.course_a_id,
        approved_course_objectives=[OBJECTIVE],
        allowed_actions=ALLOWED_ACTIONS,
        autonomy_enabled=True,
        kill_switch=True,
    )

    assert stopped.kill_switch is True
    assert repository.get_autonomous_goal(goal.goal_id).status.value == "cancelled"
    assert (
        repository.get_autonomous_opportunity(opportunity.opportunity_id).status.value
        == "cancelled"
    )
    assert await service.process_due(worker_id="worker", now=NOW) == []
    assert repository.get_teaching_profile(approved.profile_id).status.value == "approved"


@pytest.mark.asyncio
async def test_pause_preserves_goal_and_due_work_until_resume(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, opportunity = _goal_and_opportunity(service, fixture, release)

    service.set_policy(
        fixture.professor_id,
        fixture.course_a_id,
        approved_course_objectives=[OBJECTIVE],
        allowed_actions=ALLOWED_ACTIONS,
        autonomy_enabled=True,
        paused=True,
    )

    assert await service.process_due(worker_id="paused-worker", now=NOW) == []
    assert repository.get_autonomous_goal(goal.goal_id).status.value == "active"
    assert (
        repository.get_autonomous_opportunity(opportunity.opportunity_id).status.value
        == "pending"
    )

    service.set_policy(
        fixture.professor_id,
        fixture.course_a_id,
        approved_course_objectives=[OBJECTIVE],
        allowed_actions=ALLOWED_ACTIONS,
        autonomy_enabled=True,
    )
    resumed = await service.process_due(worker_id="resumed-worker", now=NOW)

    assert len(resumed) == 1
    assert resumed[0].outcome == "delivered"


@pytest.mark.asyncio
async def test_unapproved_or_incomplete_scope_resolves_to_no_action(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(service, fixture, release)
    claimed = repository.claim_autonomous_opportunity(
        opportunity.opportunity_id,
        lease_owner="worker",
        acquired_at=NOW.isoformat(),
        lease_expires_at=(NOW + timedelta(minutes=5)).isoformat(),
    )
    policy = repository.get_autonomy_policy(fixture.course_a_id)
    job = AutonomousJobInput(
        opportunity=claimed,
        goal=repository.get_autonomous_goal(claimed.goal_id),
        policy=policy,
        professor_id=fixture.professor_id,
        current_release_id=release.id,
        current_profile_id=policy.approved_profile_id,
        current_profile_sha256=policy.approved_profile_sha256,
        membership_active=True,
        consent_active=True,
        evidence_keys=[],
        evidence_complete=False,
        evidence_unique=False,
        evidence_current=False,
        evidence_authorized=False,
        now=NOW.isoformat(),
    )

    result = await GovernedAutonomousTutoringGraph().run(job)

    assert result.action.kind == AutonomousActionKind.NO_ACTION
    assert result.outcome.kind.value == "no-action"
    assert result.trace.validation_results["evidence-complete"] is False


@pytest.mark.asyncio
async def test_live_planner_failure_uses_finite_deterministic_fallback(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(service, fixture, release)
    planner = LiveAutonomousPlanner(
        FixtureLlmClient(response_content="not-json"),
        model_id="gpt-5.6-terra",
    )
    graph = GovernedAutonomousTutoringGraph(
        planner=planner,
        generator=DeterministicAutonomousWordingGenerator(),
    )
    policy = repository.get_autonomy_policy(fixture.course_a_id)
    chunk = release.chunks[0]
    key = ":".join(
        (
            chunk.source_artifact_id,
            str(chunk.source_version),
            chunk.content_hash,
            chunk.locator,
        )
    )
    job = AutonomousJobInput(
        opportunity=opportunity,
        goal=repository.get_autonomous_goal(opportunity.goal_id),
        policy=policy,
        professor_id=fixture.professor_id,
        current_release_id=release.id,
        current_profile_id=policy.approved_profile_id,
        current_profile_sha256=policy.approved_profile_sha256,
        membership_active=True,
        consent_active=True,
        evidence_keys=[key],
        evidence_chunk_ids=[chunk.id],
        evidence_complete=True,
        evidence_unique=True,
        evidence_current=True,
        evidence_authorized=True,
        now=NOW.isoformat(),
    )

    result = await graph.run(job)

    assert result.plan.action == AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE
    assert result.trace.planning_calls == 1
    assert result.trace.repair_calls == 0
    assert result.trace.graph_version == GRAPH_VERSION
    assert result.trace.generator_model == DETERMINISTIC_GENERATOR_MODEL


def test_policy_contract_enforces_governance_limits():
    with pytest.raises(ValueError, match="less than or equal to 3"):
        PedagogicalPolicyV2(
            course_id="course",
            version=1,
            approved_by="professor",
            approved_profile_id="profile",
            approved_profile_sha256="0" * 64,
            approved_course_objectives=[OBJECTIVE],
            autonomy_enabled=True,
            allowed_actions=ALLOWED_ACTIONS,
            max_messages_per_7_days=4,
        )


def test_autonomous_evidence_uses_tutoring_permission_not_crop_display(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(service, fixture, release)

    decision = AutonomousEvidenceAssessor().assess(
        release,
        opportunity,
        query=OBJECTIVE,
    )

    assert release.chunks[0].display_allowed is False
    assert decision.sufficient is True
    assert decision.authorized is True
    assert decision.selected_chunk_ids == [release.chunks[0].id]

    blocked_release = release.model_copy(
        update={
            "chunks": [
                release.chunks[0].model_copy(update={"retrieval_allowed": False}),
                *release.chunks[1:],
            ]
        },
        deep=True,
    )
    blocked = AutonomousEvidenceAssessor().assess(
        blocked_release,
        opportunity,
        query=OBJECTIVE,
    )
    assert blocked.sufficient is False
    assert blocked.authorized is False


def test_autonomous_evidence_rejects_stale_or_incomplete_ranges(tmp_path):
    _, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(service, fixture, release)
    current = release.chunks[0].model_copy(
        update={
            "id": "chunk-cache-current",
            "source_version": 2,
            "source_checksum": "b" * 64,
        }
    )
    mixed_release = release.model_copy(
        update={"chunks": [release.chunks[0], current, *release.chunks[1:]]},
        deep=True,
    )

    stale = AutonomousEvidenceAssessor().assess(
        mixed_release,
        opportunity,
        query=OBJECTIVE,
    )
    incomplete = AutonomousEvidenceAssessor().assess(
        release,
        opportunity,
        query="Explain quantum entanglement and Bell inequalities.",
    )

    assert stale.current is False
    assert stale.sufficient is False
    assert incomplete.complete is False
    assert incomplete.sufficient is False


def test_observer_materializes_new_release_event_once(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    repository.save_conversation(
        Conversation(
            id="conversation-prior-release",
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            release_id=fixture.release_a_id,
            created_at=(NOW - timedelta(days=2)).isoformat(),
            updated_at=(NOW - timedelta(days=2)).isoformat(),
        )
    )

    first = service.observe_events(now=NOW)
    second = service.observe_events(now=NOW)
    due = repository.list_due_autonomous_opportunities(NOW.isoformat())

    assert first.goals_created == 1
    assert first.by_event == {AutonomousEventKind.NEW_COURSE_RELEASE.value: 1}
    assert second.opportunities_created == 0
    assert len(due) == 1
    assert due[0].release_id == release.id
    assert due[0].event_kind == AutonomousEventKind.NEW_COURSE_RELEASE
    assert due[0].source_chunk_ids == [release.chunks[0].id]


@pytest.mark.asyncio
async def test_goal_attempt_limit_stops_additional_delivery(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal = service.create_goal(
        student_id=fixture.student_a_id,
        course_id=fixture.course_a_id,
        approved_course_objective=OBJECTIVE,
        learner_subgoal="Explain one coherence invariant.",
        success_condition="Give one grounded explanation.",
        expires_at=(NOW + timedelta(days=7)).isoformat(),
        attempt_limit=1,
    )
    for suffix in ("first", "second"):
        service.create_opportunity(
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            goal_id=goal.goal_id,
            event_kind=AutonomousEventKind.SPACED_REVIEW_DUE,
            concept_id="cache-coherence",
            source_chunk_id=release.chunks[0].id,
            earliest_action_at=(NOW - timedelta(minutes=1)).isoformat(),
            latest_action_at=(NOW + timedelta(hours=1)).isoformat(),
            idempotency_key=f"attempt-limit-{suffix}",
        )
        result = await service.process_due(worker_id=f"worker-{suffix}", now=NOW)
        assert len(result) == 1
        if suffix == "first":
            assert result[0].outcome == "delivered"
        else:
            assert result[0].outcome == "no-action"
            assert result[0].reason == "goal-attempt-limit-reached"

    stored = repository.get_autonomous_goal(goal.goal_id)
    assert stored is not None
    assert stored.attempt_count == 1
    assert len(service.outreach.list_inbox(fixture.student_a_id)) == 1


@pytest.mark.asyncio
async def test_unsupported_live_atomic_claim_fails_closed_before_delivery(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, _ = _goal_and_opportunity(service, fixture, release)
    validator = AtomicClaimEvidenceValidator(
        ExactQuoteAtomicClaimVerifier(),
        minimum_entailment=1.0,
        maximum_contradiction=0.0,
    )
    graph = GovernedAutonomousTutoringGraph(
        generator=RepositoryGroundedWordingGenerator(
            repository,
            _UnsupportedClaimGenerator(),
            model_id="synthetic-provider",
            claim_validator=validator,
        )
    )
    governed = GovernedAutonomyService(
        repository,
        service.outreach,
        graph=graph,
    )

    result = await governed.process_due(worker_id="claim-validator", now=NOW)

    assert len(result) == 1
    assert result[0].outcome == "no-action"
    assert result[0].reason == "claim-lineage-complete"
    assert governed.outreach.list_inbox(fixture.student_a_id) == []


def test_policy_boundary_change_cancels_existing_autonomy_scope(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, opportunity = _goal_and_opportunity(service, fixture, release)

    updated = service.set_policy(
        fixture.professor_id,
        fixture.course_a_id,
        approved_course_objectives=[
            OBJECTIVE,
            "Explain how virtual memory maps process addresses.",
        ],
        allowed_actions=ALLOWED_ACTIONS,
        autonomy_enabled=True,
    )

    assert updated.version == 2
    assert repository.get_autonomous_goal(goal.goal_id).status.value == "cancelled"
    assert (
        repository.get_autonomous_opportunity(opportunity.opportunity_id).status.value
        == "cancelled"
    )


@pytest.mark.asyncio
async def test_two_grounded_attempts_complete_goal_and_cancel_follow_up(tmp_path):
    repository, fixture, _, _, _ = _autonomy_fixture(tmp_path)
    tutoring = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        tutoring_mode=TutoringMode.T1_V2,
    )
    conversation = tutoring.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )
    attempt = (
        "I think cache coherence keeps replicated processor data consistent "
        "because invalidation prevents cached copies from diverging."
    )

    first = await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content=attempt,
        client_request_id="goal-attempt-1",
    )
    active = repository.list_autonomous_goals(
        fixture.student_a_id,
        fixture.course_a_id,
        active_only=True,
    )
    assert first.citations
    assert len(active) == 1
    pending = repository.get_autonomous_opportunity_by_key(
        f"turn-follow-up:{first.tutor_message.id}:incomplete-objective"
    )
    assert pending is not None

    second = await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content=attempt,
        client_request_id="goal-attempt-2",
    )

    state = repository.get_learner_state(conversation.id)
    goals = repository.list_autonomous_goals(
        fixture.student_a_id,
        fixture.course_a_id,
    )
    assert second.citations
    assert state is not None and state.objective_complete is True
    assert len(goals) == 1
    assert goals[0].status.value == "completed"
    assert repository.get_autonomous_opportunity(pending.opportunity_id).status.value == "cancelled"
