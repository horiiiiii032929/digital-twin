from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.student.autonomy_control import DeterministicAutonomousGoalManager
from src.digital_twin.student.autonomy_models import AutonomousGoalStatus
from src.digital_twin.student.learner_estimators import AssessedObservation
from src.digital_twin.student.post_report_learning import (
    AnalyticOnlyPlanner, AssessedPlanningStateResolver, DecayedEvidenceCountEstimator,
    RecoveryAwareGoalManager, ScopedObservationReader, learning_estimator,
)
from tests.digital_twin.test_assessed_planning_input import observation
from tests.digital_twin.test_goal_completion_scope import (
    ATTEMPT, belief_for, counts, setup_two_goals, tutoring_service,
)
from tests.digital_twin.test_planning_architectures import _job

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def test_decay_returns_toward_prior_and_increases_uncertainty():
    estimator = DecayedEvidenceCountEstimator(half_life_days=7)
    state = estimator.initial_state()
    state = estimator.update(state, AssessedObservation("cache", True, NOW))
    first = estimator.estimate(state, "cache", NOW)
    later = estimator.estimate(state, "cache", NOW + timedelta(days=7))
    assert .5 < later.probability < first.probability
    assert later.uncertainty > first.uncertainty
    assert later.evidence_count == first.evidence_count == 1
    with pytest.raises(ValueError, match="chronological"):
        estimator.update(state, AssessedObservation("cache", True, NOW - timedelta(days=1)))


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf")])
def test_decay_rejects_invalid_parameters(bad):
    with pytest.raises(ValueError):
        DecayedEvidenceCountEstimator(bad)


@pytest.mark.parametrize("mode", ["assessed-count", "assessed-decay", "assessed-bkt", "assessed-pfa"])
def test_planning_changes_only_with_assessment_not_delivery(mode):
    job = _job()
    op = job.opportunity
    rows = []
    reader = SimpleNamespace(read=lambda *_: rows, key=lambda *_: "a" * 64)
    resolver = AssessedPlanningStateResolver(reader, learning_estimator(mode))
    job = job.model_copy(update={"now": NOW.isoformat()})
    before = resolver(job)
    delivered = job.model_copy(update={"goal": job.goal.model_copy(update={"attempt_count": 1})})
    after = resolver(delivered)
    assert before.mastery_probability == after.mastery_probability
    assert before.assessed_evidence_count == after.assessed_evidence_count == 0
    assert after.goal_progress == before.goal_progress == 0
    rows.append(observation(course_id=op.course_id, release_id=op.release_id,
        concept_ids=[op.concept_id], assessment_concept_ids=[op.concept_id]))
    assessed = resolver(delivered)
    assert assessed.assessed_evidence_count == 1
    assert assessed.mastery_probability > after.mastery_probability


@pytest.fixture
def recovery(tmp_path):
    repository, fixture, goals = setup_two_goals(tmp_path)
    goal = goals[0].model_copy(update={"expires_at": (NOW + timedelta(days=7)).isoformat()})
    domain = repository.get_course_domain_model(goal.release_id)
    rows = []
    reader = SimpleNamespace(read=lambda *_: rows, key=lambda *_: "a" * 64)
    manager = RecoveryAwareGoalManager(reader, VirtualUtcClock(NOW))
    belief = belief_for(goal, [counts("cache-coherence", correct=2, incorrect=1)])
    def append(outcome="correct", concept="cache-coherence", **changes):
        index = len(rows)
        rows.append(observation(str(index), outcome, course_id=goal.course_id, release_id=goal.release_id,
            concept_ids=[concept], assessment_concept_ids=[concept], source_turn_key=f"turn-{index}",
            observed_at=(NOW - timedelta(minutes=10-index)).isoformat()).model_copy(update=changes))
    try:
        yield manager, goal, domain, belief, rows, append
    finally:
        repository.close()


def test_recovery_requires_two_distinct_correct_turns_after_contradiction(recovery):
    manager, goal, domain, belief, rows, append = recovery
    append("incorrect"); append()
    assert not manager.interpret(goal, belief, domain_model=domain).complete
    append()
    assert manager.interpret(goal, belief, domain_model=domain).complete
    assert not DeterministicAutonomousGoalManager().interpret(goal, belief, domain_model=domain).complete
    append("partial")
    assert not manager.interpret(goal, belief, domain_model=domain).complete


@pytest.mark.parametrize("changes", [
    {"source_turn_key": None}, {"evidence_keys": []}, {"assessment_concept_ids": None},
    {"observed_at": (NOW - timedelta(days=8)).isoformat()},
    {"observed_at": (NOW + timedelta(days=1)).isoformat()},
])
def test_unusable_second_turn_cannot_complete(recovery, changes):
    manager, goal, domain, belief, _, append = recovery
    append(); append(**changes)
    assert not manager.interpret(goal, belief, domain_model=domain).complete


def test_other_concepts_duplicate_turn_and_equal_time_contradiction_do_not_complete(recovery):
    manager, goal, domain, belief, rows, append = recovery
    append(); append(concept="virtual-memory")
    assert not manager.interpret(goal, belief, domain_model=domain).complete
    rows[1] = rows[0].model_copy(update={"observation_id": "duplicate-new-id"})
    assert not manager.interpret(goal, belief, domain_model=domain).complete
    rows.clear(); append(); append()
    append("incorrect", observed_at=rows[-1].observed_at)
    assert not manager.interpret(goal, belief, domain_model=domain).complete


def test_goal_scope_expiry_and_terminal_status_are_retained(recovery):
    manager, goal, domain, belief, _, append = recovery
    append(); append()
    foreign = belief.model_copy(update={"learner_key": "b" * 64})
    assert not manager.interpret(goal, foreign, domain_model=domain).complete
    expired = goal.model_copy(update={"expires_at": NOW.isoformat()})
    assert not manager.interpret(expired, belief, domain_model=domain).complete
    cancelled = goal.model_copy(update={"status": AutonomousGoalStatus.CANCELLED})
    assert not manager.interpret(cancelled, belief, domain_model=domain).complete


@pytest.mark.asyncio
async def test_actual_turns_commit_recovery_and_preserve_other_goal(tmp_path):
    repository, fixture, goals = setup_two_goals(tmp_path, source_supported_target=True)
    try:
        service = tutoring_service(repository)
        reader = ScopedObservationReader(repository, service.learning_gap_pseudonymizer)
        service.autonomy_goal_manager = RecoveryAwareGoalManager(reader, service.clock)
        service.tutoring_graph.source_bound_assessment_enabled = True
        # The historical fixture's description adds an invalidation claim absent
        # from its approved source. Use an explicitly source-supported target for
        # this positive integration case; unsupported targets must abstain.
        conversation = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
        for index in range(2):
            await service.submit_message(fixture.student_a_id, conversation.id,
                content="I think cache coherence keeps replicated processor data consistent.",
                client_request_id=f"recovery-real-{index}")
            statuses = [repository.get_autonomous_goal(g.goal_id).status.value for g in goals]
            assert statuses == (["active", "active"] if index == 0 else ["completed", "active"])
        assert len(reader.read(fixture.student_a_id, goals[0].course_id, goals[0].release_id)) == 2
    finally:
        repository.close()


@pytest.mark.asyncio
async def test_analytic_only_needs_evidence_and_never_selects_forbidden_action():
    from src.digital_twin.student.planning_architectures import default_planning_state_card
    planner = AnalyticOnlyPlanner(default_planning_state_card)
    assert (await planner.plan(_job(evidence_ready=False))).action.value == "no-action"
    job = _job()
    output = await planner.plan(job)
    assert output.action in job.policy.allowed_actions or output.action.value == "no-action"
    assert planner.model_id.startswith("deterministic/")


@pytest.mark.asyncio
async def test_failed_turn_cannot_commit_completion_and_retry_is_idempotent(tmp_path, monkeypatch):
    repository, fixture, goals = setup_two_goals(tmp_path, source_supported_target=True)
    try:
        service = tutoring_service(repository)
        reader = ScopedObservationReader(repository, service.learning_gap_pseudonymizer)
        service.autonomy_goal_manager = RecoveryAwareGoalManager(reader, service.clock)
        service.tutoring_graph.source_bound_assessment_enabled = True
        first = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
        second = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
        message = "I think cache coherence keeps replicated processor data consistent."
        await service.submit_message(fixture.student_a_id, first.id, content=message,
            client_request_id="first-correct")
        original = repository.save_turn
        def fail(*args, **kwargs):
            raise RuntimeError("synthetic persistence failure")
        monkeypatch.setattr(repository, "save_turn", fail)
        with pytest.raises(RuntimeError, match="synthetic persistence failure"):
            await service.submit_message(fixture.student_a_id, second.id, content=message,
                client_request_id="second-correct")
        assert repository.get_autonomous_goal(goals[0].goal_id).status.value == "active"
        assert len(reader.read(fixture.student_a_id, goals[0].course_id, goals[0].release_id)) == 1
        monkeypatch.setattr(repository, "save_turn", original)
        for _ in range(2):
            await service.submit_message(fixture.student_a_id, second.id, content=message,
                client_request_id="second-correct")
        assert repository.get_autonomous_goal(goals[0].goal_id).status.value == "completed"
        assert repository.get_autonomous_goal(goals[1].goal_id).status.value == "active"
        assert len(reader.read(fixture.student_a_id, goals[0].course_id, goals[0].release_id)) == 2
    finally:
        repository.close()
