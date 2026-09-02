from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from src.digital_twin.llm import FixtureLlmClient, LlmResponse
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
    CanonicalSourceRangeV1,
    CourseConceptV1,
    CourseDomainModelV1,
    CourseObjectiveV1,
    CourseTutoringRuntimeProfileV1,
    LearningGapPseudonymizer,
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
    AssessmentOutcome,
    AutonomousActionKind,
    AutonomousEventKind,
    ConceptAttributionV2,
    LearnerObservationV2,
    PedagogicalPolicyV2,
    TurnPerceptionV2,
)
from src.digital_twin.student.learner_belief import (
    DeterministicEvidenceCountBeliefEstimator,
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
from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
)
from src.digital_twin.student.autonomy_service import (
    GovernedAutonomyService,
    RepositoryGroundedWordingGenerator,
)
from src.digital_twin.student.tutoring_graph import (
    GovernedReactiveTutoringGraphV2,
    LiveReactiveSemanticPlanner,
    TutoringGraphInput,
    TutoringMode,
    initial_learner_state,
    resolve_policy_action,
)


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


class _UnavailableV2Generator:
    implementation_id = "unavailable-v2-generator"

    def __init__(self) -> None:
        self.calls = 0

    async def generate_for_intent(self, *args, **kwargs):
        del args, kwargs
        self.calls += 1
        raise RuntimeError("synthetic provider outage")


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
    chunk = release.chunks[0]
    repository.save_course_domain_model(
        CourseDomainModelV1(
            domain_model_id="domain-cache-coherence-v1",
            course_id=fixture.course_a_id,
            release_id=release.id,
            release_sha256="d" * 64,
            version=1,
            objectives=[
                CourseObjectiveV1(
                    objective_id="objective-cache-coherence",
                    statement=OBJECTIVE,
                    concept_ids=["cache-coherence"],
                )
            ],
            concepts=[
                CourseConceptV1(
                    concept_id="cache-coherence",
                    label="Cache coherence",
                    description=(
                        "Cache coherence keeps replicated processor data consistent; "
                        "invalidation prevents cached copies from diverging."
                    ),
                    canonical_ranges=[
                        CanonicalSourceRangeV1(
                            source_artifact_id=chunk.source_artifact_id,
                            source_version=chunk.source_version,
                            source_sha256=chunk.source_checksum or chunk.content_hash,
                            locator=chunk.locator,
                            char_start=0,
                            char_end=len(chunk.text),
                        )
                    ],
                )
            ],
            approved_by=fixture.professor_id,
        )
    )
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


def test_withdrawing_in_app_consent_cancels_pending_autonomy_scope(tmp_path):
    repository, fixture, service, release, _approved = _autonomy_fixture(tmp_path)
    goal, opportunity = _goal_and_opportunity(service, fixture, release)

    service.outreach.update_preference(
        fixture.student_a_id,
        fixture.course_a_id,
        channel=OutreachChannel.IN_APP,
        enabled=False,
        timezone="UTC",
        quiet_hours_start="23:00",
        quiet_hours_end="02:00",
        max_messages_per_7_days=3,
    )

    assert repository.get_autonomous_goal(goal.goal_id).status.value == "cancelled"
    assert repository.get_autonomous_opportunity(opportunity.opportunity_id).status.value == "cancelled"


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
async def test_live_planner_failure_fails_closed_without_delivery(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(service, fixture, release)
    planner = LiveAutonomousPlanner(
        FixtureLlmClient(response_content="not-json"),
        model_id="gpt-5.6-terra",
    )
    graph = GovernedAutonomousTutoringGraph(
        planner=planner,
        generator=DeterministicAutonomousWordingGenerator(),
        checkpoint_database_path=repository.path,
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

    assert result.plan.action == AutonomousActionKind.NO_ACTION
    assert result.action.kind == AutonomousActionKind.NO_ACTION
    assert result.outcome.kind.value == "no-action"
    assert result.plan.reason_code == "planner-failure-no-action"
    assert result.trace.planning_calls == 1
    assert result.trace.repair_calls == 0
    assert result.trace.graph_version == GRAPH_VERSION
    assert result.trace.generator_model == DETERMINISTIC_GENERATOR_MODEL


@pytest.mark.asyncio
async def test_live_planner_receives_event_envelope_and_cannot_escape_it(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(service, fixture, release)

    class CapturingOutOfEnvelopeClient:
        def __init__(self) -> None:
            self.payload = None

        async def chat(self, messages, task):
            assert task == "autonomous_tutoring_plan"
            self.payload = json.loads(messages[-1].content)
            return LlmResponse(
                content=json.dumps(
                    {
                        "action": "ask-diagnostic-question",
                        "reason_code": "provider-selected-wrong-action",
                        "expected_learner_action": "Reply.",
                        "required_evidence_keys": [],
                        "outcome_observation": "Observe a reply.",
                        "stop_condition": "Stop.",
                        "replan_condition": None,
                    }
                ),
                provider_model="fixture/v1",
            )

    client = CapturingOutOfEnvelopeClient()
    planner = LiveAutonomousPlanner(client, model_id="gpt-5.6-terra")
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

    proposal = await planner.plan(job)

    assert client.payload["action_eligibility_version"] == ACTION_ELIGIBILITY_VERSION
    assert client.payload["eligible_actions"] == [
        "issue-retrieval-practice",
        "no-action",
    ]
    assert "allowed_actions" not in client.payload
    assert proposal.action == AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE
    assert proposal.reason_code == "event-envelope-fallback-spaced-review-due"


@pytest.mark.asyncio
async def test_proactive_uncertain_generator_call_is_not_repeated(tmp_path):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(service, fixture, release)
    policy = repository.get_autonomy_policy(fixture.course_a_id)
    chunk = release.chunks[0]
    evidence_key = ":".join(
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
        evidence_keys=[evidence_key],
        evidence_chunk_ids=[chunk.id],
        evidence_complete=True,
        evidence_unique=True,
        evidence_current=True,
        evidence_authorized=True,
        now=NOW.isoformat(),
    )

    class SimulatedProcessExit(BaseException):
        pass

    class InterruptingGenerator:
        model_id = "synthetic-live-generator"

        def __init__(self):
            self.calls = 0

        async def generate(self, job, plan):
            self.calls += 1
            raise SimulatedProcessExit()

    generator = InterruptingGenerator()
    graph = GovernedAutonomousTutoringGraph(
        generator=generator,
        checkpoint_database_path=repository.path,
    )
    with pytest.raises(SimulatedProcessExit):
        await graph.run(job)

    resumed = await GovernedAutonomousTutoringGraph(
        generator=generator,
        checkpoint_database_path=repository.path,
    ).run(job)

    assert generator.calls == 1
    assert resumed.action.kind == AutonomousActionKind.NO_ACTION
    assert resumed.trace.restart_count == 1
    assert resumed.trace.decision_reason == "operational-provider-call-outcome-uncertain"


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
        ),
        checkpoint_database_path=repository.path,
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
        claim_evidence_validator=AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
        ),
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(b"v2-test-secret-32-bytes-minimum!!"),
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
    belief = repository.get_learner_belief_state_v2(conversation.id)
    goals = repository.list_autonomous_goals(
        fixture.student_a_id,
        fixture.course_a_id,
    )
    assert second.citations
    assert state is not None and state.mastery_by_concept == {}
    assert belief is not None and belief.revision == 2
    assert belief.concepts[0].correct_evidence_count == 2
    assert belief.concepts[0].attribution_confidence >= 0.5
    assert len(goals) == 1
    assert goals[0].status.value == "completed"
    assert repository.get_autonomous_opportunity(pending.opportunity_id).status.value == "cancelled"


def test_v2_evidence_contract_rejects_model_owned_mastery():
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        ConceptAttributionV2.model_validate(
            {
                "concept_id": "cache-coherence",
                "observed_mastery": 0.9,
                "attribution_confidence": 0.5,
                "uncertainty": 0.5,
            }
        )


def test_v2_action_lattice_is_fail_closed_and_total():
    assert resolve_policy_action("answer", "abstain") == "abstain"
    assert resolve_policy_action("answer", "clarify", "refuse") == "refuse"
    assert (
        resolve_policy_action("answer", "refuse", "operational-failure")
        == "operational-failure"
    )
    with pytest.raises(ValueError, match="unsupported policy actions"):
        resolve_policy_action("invented")


def test_v2_belief_revision_uses_assessed_evidence_counts_only():
    estimator = DeterministicEvidenceCountBeliefEstimator()
    learner_key = "a" * 64
    prior = estimator.initial_state(
        learner_key=learner_key,
        course_id="course-a",
        release_id="release-a",
    )
    observation = LearnerObservationV2(
        observation_id="observation-1",
        learner_key=learner_key,
        course_id="course-a",
        release_id="release-a",
        event_kind=AutonomousEventKind.STUDENT_MESSAGE,
        concept_ids=["cache-coherence"],
        perception=TurnPerceptionV2(
            event_kind=AutonomousEventKind.STUDENT_MESSAGE,
            request_type="attempt",
            attempt_present=True,
        ),
        assessment_outcome=AssessmentOutcome.CORRECT,
        assessment_confidence=0.8,
        evidence_keys=["source:1:hash:range"],
    )

    revised, delta = estimator.revise(prior, observation)

    attribution = revised.concepts[0]
    assert revised.revision == 1
    assert delta.previous_revision == 0 and delta.next_revision == 1
    assert attribution.observation_count == 1
    assert attribution.assessed_evidence_count == 1
    assert attribution.correct_evidence_count == 1
    assert 0 < attribution.attribution_confidence < 1
    assert "mastery" not in attribution.model_dump()


def test_release_domain_model_is_immutable(tmp_path):
    repository, _, _, release, _ = _autonomy_fixture(tmp_path)
    stored = repository.get_course_domain_model(release.id)
    assert stored is not None
    changed = stored.model_copy(
        update={
            "concepts": [
                stored.concepts[0].model_copy(update={"label": "Changed label"})
            ]
        },
        deep=True,
    )

    with pytest.raises(ValueError, match="immutable"):
        repository.save_course_domain_model(changed)


@pytest.mark.asyncio
async def test_t1_v2_persists_every_reactive_runtime_plane(tmp_path):
    repository, fixture, _, _, _ = _autonomy_fixture(tmp_path)
    tutoring = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
        ),
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(
            b"v2-runtime-plane-test-secret-32-bytes"
        ),
    )
    conversation = tutoring.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )

    turn = await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="How does cache coherence keep processor copies consistent?",
        client_request_id="runtime-plane-turn-1",
    )

    observations = repository.list_learner_observations_v2(conversation.id)
    deltas = repository.list_learner_state_deltas_v2(conversation.id)
    plans = repository.list_pedagogical_plans_v2(conversation.id)
    responses = repository.list_grounded_responses_v2(conversation.id)
    traces = repository.list_agent_traces_v2(
        fixture.course_a_id,
        conversation_id=conversation.id,
    )
    assert turn.citations
    assert len(observations) == len(deltas) == len(plans) == len(responses) == len(traces) == 1
    assert observations[0].observation_id == traces[0].event_id
    assert deltas[0].next_revision == traces[0].output_state_revision == 1
    assert plans[0].required_evidence_keys == responses[0].source_range_keys
    assert "atomic_commit_boundary" in traces[0].node_path
    assert len(traces[0].checkpoint_ids) >= 2
    assert traces[0].fast_path is True
    assert traces[0].planning_calls == 0


@pytest.mark.asyncio
async def test_t1_v2_clarification_is_policy_response_not_graph_failure(tmp_path):
    repository, fixture, _, _, _ = _autonomy_fixture(tmp_path)
    tutoring = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
        ),
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(
            b"v2-policy-clarification-secret-32-bytes"
        ),
    )
    conversation = tutoring.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )

    turn = await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="Explain that.",
        client_request_id="policy-clarification-turn",
    )

    trace = repository.list_agent_traces_v2(
        fixture.course_a_id,
        conversation_id=conversation.id,
    )[0]
    assert turn.tutor_message.action == "clarify-request"
    assert (
        turn.tutor_message.content
        == "Which concept or step would you like to work through?"
    )
    assert trace.decision_reason == "intent-clarify-request"
    assert trace.generation_calls == 0
    assert trace.validation_results["graph-validation"] is True


@pytest.mark.asyncio
async def test_t1_v2_uses_one_semantic_proposal_only_for_complex_turn(tmp_path):
    repository, fixture, _, _, _ = _autonomy_fixture(tmp_path)
    planner = LiveReactiveSemanticPlanner(
        FixtureLlmClient(
            response_content=(
                '{"proposed_intent":"correct_misconception",'
                '"concept_ids":["cache-coherence"],'
                '"hypothesis_kind":"misconception",'
                '"hypothesis_concept_id":"cache-coherence",'
                '"hypothesis_confidence":0.8,'
                '"reason_code":"misconception-repair"}'
            )
        ),
        model_id="gpt-5.6-terra",
    )
    tutoring = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
        ),
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(
            b"v2-semantic-proposal-secret-32-bytes"
        ),
        reactive_semantic_planner=planner,
    )
    conversation = tutoring.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )

    turn = await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content=(
            "I am confused because I think cache coherence duplicates stale values; "
            "my attempt says invalidation makes every copy stale."
        ),
        client_request_id="semantic-complex-turn",
    )

    belief = repository.get_learner_belief_state_v2(conversation.id)
    trace = repository.list_agent_traces_v2(
        fixture.course_a_id,
        conversation_id=conversation.id,
    )[0]
    assert turn.citations
    assert trace.fast_path is False
    assert trace.planning_calls == 1
    assert trace.planner_model == "gpt-5.6-terra"
    assert belief is not None and len(belief.hypotheses) == 1
    assert belief.hypotheses[0].kind == "misconception"
    assert belief.hypotheses[0].status == "tentative"


@pytest.mark.asyncio
async def test_t1_v2_resumes_after_node_failure_without_duplicate_generation(tmp_path):
    repository, fixture, _, release, _ = _autonomy_fixture(tmp_path)
    validator = AtomicClaimEvidenceValidator(
        ExactQuoteAtomicClaimVerifier(),
        minimum_entailment=1.0,
        maximum_contradiction=0.0,
    )
    pseudonymizer = LearningGapPseudonymizer(
        b"v2-checkpoint-test-secret-32-bytes!!"
    )
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=validator,
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=pseudonymizer,
    )
    conversation = service.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )
    domain = repository.get_course_domain_model(release.id)
    learner_key = pseudonymizer.learner_key(
        course_id=fixture.course_a_id,
        account_id=fixture.student_a_id,
    )
    belief = DeterministicEvidenceCountBeliefEstimator().initial_state(
        learner_key=learner_key,
        course_id=fixture.course_a_id,
        release_id=release.id,
    )
    graph_input = TutoringGraphInput(
        account_id=fixture.student_a_id,
        conversation=conversation,
        release=release,
        student_message="Explain cache coherence and invalidation.",
        learner_state=initial_learner_state(conversation),
        event_id="checkpoint-resume-event",
        learner_key=learner_key,
        domain_model=domain,
        learner_belief=belief,
    )
    generation_calls = 0

    async def counted_generate(*args, **kwargs):
        nonlocal generation_calls
        generation_calls += 1
        return await service.tutoring_graph.generate(*args, **kwargs)

    class InterruptAfterValidationGraph(GovernedReactiveTutoringGraphV2):
        def __init__(self, *, interrupt_once: bool, **kwargs):
            self.interrupt_once = interrupt_once
            super().__init__(**kwargs)

        def _atomic_commit_boundary(self, state):
            if self.interrupt_once:
                self.interrupt_once = False
                raise RuntimeError("simulated process stop after validation")
            return super()._atomic_commit_boundary(state)

    kwargs = {
        "retrieve": service.tutoring_graph.retrieve,
        "generate": counted_generate,
        "fallback": service.tutoring_graph.fallback,
        "evidence_gate_configured": True,
        "claim_validator": validator,
        "checkpoint_database_path": repository.path,
    }
    first_process = InterruptAfterValidationGraph(interrupt_once=True, **kwargs)
    with pytest.raises(RuntimeError, match="simulated process stop"):
        await first_process.run(graph_input)
    assert generation_calls == 1

    restarted_process = InterruptAfterValidationGraph(interrupt_once=False, **kwargs)
    resumed = await restarted_process.run(graph_input)

    assert generation_calls == 1
    artifacts = resumed.reactive_v2_artifacts
    assert artifacts is not None
    assert artifacts.trace.restart_count == 1
    assert artifacts.trace.output_state_revision == 1
    assert artifacts.response.policy_action == "answer"


@pytest.mark.asyncio
async def test_t1_v2_uncertain_provider_call_fails_closed_without_retry(tmp_path):
    repository, fixture, _, release, _ = _autonomy_fixture(tmp_path)
    validator = AtomicClaimEvidenceValidator(
        ExactQuoteAtomicClaimVerifier(),
        minimum_entailment=1.0,
        maximum_contradiction=0.0,
    )
    pseudonymizer = LearningGapPseudonymizer(
        b"v2-uncertain-call-secret-32-bytes!!"
    )
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=validator,
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=pseudonymizer,
    )
    conversation = service.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )
    learner_key = pseudonymizer.learner_key(
        course_id=fixture.course_a_id,
        account_id=fixture.student_a_id,
    )
    graph_input = TutoringGraphInput(
        account_id=fixture.student_a_id,
        conversation=conversation,
        release=release,
        student_message="Explain cache coherence and invalidation.",
        learner_state=initial_learner_state(conversation),
        event_id="uncertain-provider-call-event",
        learner_key=learner_key,
        domain_model=repository.get_course_domain_model(release.id),
        learner_belief=DeterministicEvidenceCountBeliefEstimator().initial_state(
            learner_key=learner_key,
            course_id=fixture.course_a_id,
            release_id=release.id,
        ),
    )
    generation_calls = 0

    class SimulatedProcessExit(BaseException):
        pass

    async def interrupted_generate(*args, **kwargs):
        nonlocal generation_calls
        generation_calls += 1
        raise SimulatedProcessExit()

    kwargs = {
        "retrieve": service.tutoring_graph.retrieve,
        "generate": interrupted_generate,
        "fallback": service.tutoring_graph.fallback,
        "evidence_gate_configured": True,
        "claim_validator": validator,
        "checkpoint_database_path": repository.path,
    }
    with pytest.raises(SimulatedProcessExit):
        await GovernedReactiveTutoringGraphV2(**kwargs).run(graph_input)

    resumed = await GovernedReactiveTutoringGraphV2(**kwargs).run(graph_input)

    assert generation_calls == 1
    artifacts = resumed.reactive_v2_artifacts
    assert artifacts is not None and not artifacts.state_committed
    assert artifacts.trace.restart_count == 1
    assert artifacts.trace.decision_reason == "operational-provider-call-outcome-uncertain"
    assert artifacts.response.policy_action != "answer"


@pytest.mark.asyncio
async def test_autonomy_observer_uses_v2_belief_observation_lineage(tmp_path):
    repository, fixture, autonomy, _, _ = _autonomy_fixture(tmp_path)
    tutoring = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
        ),
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(
            b"v2-observer-test-secret-32-bytes!!!"
        ),
    )
    conversation = tutoring.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )
    await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content=(
            "I thought cache coherence must always duplicate stale values, "
            "and I am confused because invalidation seems opposite."
        ),
        client_request_id="v2-observer-misconception",
    )
    observation = repository.list_learner_observations_v2(conversation.id)[0]

    sweep = autonomy.observe_events(now=datetime.now(UTC) + timedelta(minutes=1))
    observed = [
        item
        for item in repository.list_due_autonomous_opportunities(
            (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        )
        if item.idempotency_key.startswith("observer:misconception:")
    ]

    assert sweep.by_event[AutonomousEventKind.MISCONCEPTION.value] == 1
    assert len(observed) == 1
    assert observed[0].concept_id == "cache-coherence"
    assert observed[0].supporting_observation_ids == [observation.observation_id]
    goal = repository.get_autonomous_goal(observed[0].goal_id)
    assert goal is not None
    assert "mastery" not in goal.success_condition.casefold()


@pytest.mark.asyncio
async def test_v2_provider_failure_falls_back_without_state_advance_or_retry(tmp_path):
    repository, fixture, _, _, _ = _autonomy_fixture(tmp_path)
    generator = _UnavailableV2Generator()
    tutoring = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        generator=generator,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
        ),
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(
            b"v2-provider-failure-secret-32-bytes"
        ),
    )
    conversation = tutoring.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )

    turn = await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="Explain cache coherence and invalidation.",
        client_request_id="v2-provider-failure",
    )

    traces = repository.list_agent_traces_v2(
        fixture.course_a_id,
        conversation_id=conversation.id,
    )
    assert turn.tutor_message.action == "safe-graph-failure"
    assert generator.calls == 1
    assert repository.get_learner_state(conversation.id) is None
    assert repository.get_learner_belief_state_v2(conversation.id) is None
    assert repository.list_learner_state_deltas_v2(conversation.id) == []
    assert len(repository.list_learner_observations_v2(conversation.id)) == 1
    assert len(repository.list_pedagogical_plans_v2(conversation.id)) == 1
    assert len(repository.list_grounded_responses_v2(conversation.id)) == 1
    assert len(traces) == 1
    assert traces[0].repair_calls == 0
    assert traces[0].input_state_revision == traces[0].output_state_revision == 0
    assert traces[0].validation_results["graph-validation"] is False


@pytest.mark.asyncio
async def test_course_runtime_profile_selects_v2_and_one_setting_rolls_back_to_t0(
    tmp_path,
):
    repository, fixture, _, _, _ = _autonomy_fixture(tmp_path)
    tutoring = StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
        ),
        tutoring_mode=TutoringMode.T0,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(
            b"course-runtime-profile-test-secret!!"
        ),
    )
    repository.save_course_tutoring_runtime_profile(
        CourseTutoringRuntimeProfileV1(
            course_id=fixture.course_a_id,
            mode=TutoringMode.T1_V2,
            version=1,
            changed_by=fixture.professor_id,
            reason="Select governed V2 for this course.",
        )
    )
    conversation = tutoring.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )

    v2_turn = await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="How does cache coherence keep processor copies consistent?",
        client_request_id="runtime-v2-turn",
    )
    repository.save_course_tutoring_runtime_profile(
        CourseTutoringRuntimeProfileV1(
            course_id=fixture.course_a_id,
            mode=TutoringMode.T0,
            version=2,
            changed_by=fixture.professor_id,
            reason="Immediate professor safety rollback.",
        )
    )
    t0_turn = await tutoring.submit_message(
        fixture.student_a_id,
        conversation.id,
        content="What does invalidation prevent?",
        client_request_id="runtime-t0-turn",
    )

    assert v2_turn.tutoring_mode == TutoringMode.T1_V2
    assert t0_turn.tutoring_mode == TutoringMode.T0
    assert len(repository.list_agent_traces_v2(fixture.course_a_id)) == 1
