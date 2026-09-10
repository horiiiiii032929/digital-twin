"""Goal completion must follow the approved objective, including real turn commits."""
from datetime import UTC, datetime, timedelta
import socket
from types import SimpleNamespace

import pytest

from tests.digital_twin import test_governed_autonomy as existing
from src.digital_twin.student.autonomy_control import DeterministicAutonomousGoalManager
from src.digital_twin.student.autonomy_models import ConceptAttributionV2, LearnerBeliefStateV2
from src.digital_twin.student.tutoring_graph import ConceptMastery, LearnerState, TurnSignals

OTHER_OBJECTIVE = "Explain how virtual memory maps process addresses."

@pytest.fixture(autouse=True)
def prohibit_network(monkeypatch):
    original = socket.socket.connect
    def connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("Network forbidden for synthetic goal regression")
        return original(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)

def setup_two_goals(tmp_path, *, source_supported_target=False):
    repository, fixture, autonomy, release, _ = existing._autonomy_fixture(tmp_path)
    domain = repository.get_course_domain_model(release.id)
    release = release.model_copy(update={
        "id": "release-two-goal-audit",
        "status": existing.StudentReleaseStatus.DRAFT,
    }, deep=True)
    repository.save_release(release)
    other_chunk = release.chunks[1]
    other = existing.CourseConceptV1(
        concept_id="virtual-memory",
        label="Virtual memory",
        description=OTHER_OBJECTIVE,
        canonical_ranges=[existing.CanonicalSourceRangeV1(
            source_artifact_id=other_chunk.source_artifact_id,
            source_version=other_chunk.source_version,
            source_sha256=other_chunk.source_checksum or other_chunk.content_hash,
            locator=other_chunk.locator,
            char_start=0,
            char_end=len(other_chunk.text),
        )],
    )
    updated = domain.model_dump(mode="python")
    if source_supported_target:
        domain.concepts[0].description = "Cache coherence keeps replicated processor data consistent."
    updated.update(
        domain_model_id="domain-two-goal-audit-v2",
        release_id=release.id,
        version=2,
        objectives=[*domain.objectives, existing.CourseObjectiveV1(
            objective_id="objective-virtual-memory",
            statement=OTHER_OBJECTIVE,
            concept_ids=["virtual-memory"],
        )],
        concepts=[*domain.concepts, other],
    )
    repository.save_course_domain_model(existing.CourseDomainModelV1.model_validate(updated))
    repository.publish_release(release.id)
    autonomy.set_policy(
        fixture.professor_id,
        fixture.course_a_id,
        approved_course_objectives=[existing.OBJECTIVE, OTHER_OBJECTIVE],
        allowed_actions=existing.ALLOWED_ACTIONS,
        autonomy_enabled=True,
    )
    goals = [
        autonomy.create_goal(
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            approved_course_objective=objective,
            learner_subgoal=objective,
            success_condition="Give two correct unassisted explanations of " + concept,
            expires_at=(datetime.now(UTC) + timedelta(days=7)).isoformat(),
        )
        for concept, objective in [
            ("cache-coherence", existing.OBJECTIVE),
            ("virtual-memory", OTHER_OBJECTIVE),
        ]
    ]
    return repository, fixture, goals

def counts(concept, *, correct=0, incorrect=0):
    n = correct + incorrect
    confidence = n / (n + 2)
    return ConceptAttributionV2(
        concept_id=concept,
        observation_count=n,
        assessed_evidence_count=n,
        correct_evidence_count=correct,
        incorrect_evidence_count=incorrect,
        attribution_confidence=confidence,
        uncertainty=1 - confidence,
    )


@pytest.fixture
def scope(tmp_path):
    repository, fixture, goals = setup_two_goals(tmp_path)
    try:
        yield repository, fixture, goals, repository.get_course_domain_model(goals[0].release_id)
    finally:
        repository.close()


def belief_for(goal, concepts):
    return LearnerBeliefStateV2(
        learner_key="a" * 64, course_id=goal.course_id,
        release_id=goal.release_id, revision=1, concepts=concepts,
    )


@pytest.mark.parametrize("target,correct,incorrect,expected", [
    (0, 2, 0, True), (1, 2, 0, False), (1, 2, 2, False), (0, 1, 0, False),
])
def test_only_the_target_evidence_can_complete(scope, target, correct, incorrect, expected):
    _, _, goals, domain = scope
    belief = belief_for(goals[0], [
        counts("cache-coherence", correct=correct),
        counts("virtual-memory", incorrect=incorrect),
    ])
    decision = DeterministicAutonomousGoalManager().interpret(goals[target], belief, domain_model=domain)
    assert decision.complete is expected


@pytest.mark.parametrize("scenario", ["no-state", "no-domain", "unknown-objective", "ambiguous-objective",
                                     "state-course", "state-release", "domain-course", "domain-release", "low-confidence"])
def test_missing_ambiguous_or_wrong_scope_cannot_complete(scope, scenario):
    _, _, goals, domain = scope
    goal = goals[0]
    belief = belief_for(goal, [counts("cache-coherence", correct=2)])
    if scenario == "no-state":
        belief = None
    elif scenario == "no-domain":
        domain = None
    elif scenario == "unknown-objective":
        goal = goal.model_copy(update={"approved_course_objective": "Not mapped"})
    elif scenario == "ambiguous-objective":
        duplicate = domain.objectives[0].model_copy(update={"objective_id": "duplicate"})
        domain = domain.model_copy(update={"objectives": [*domain.objectives, duplicate]})
    elif scenario.startswith("state-"):
        belief = belief.model_copy(update={scenario.removeprefix("state-") + "_id": "other"})
    elif scenario.startswith("domain-"):
        domain = domain.model_copy(update={scenario.removeprefix("domain-") + "_id": "other"})
    else:
        belief.concepts[0] = belief.concepts[0].model_copy(update={"attribution_confidence": 0.49, "uncertainty": 0.51})
    result = DeterministicAutonomousGoalManager().interpret(goal, belief, domain_model=domain)
    assert not result.complete


@pytest.mark.parametrize("second_correct,expected", [(0, False), (1, False), (2, True)])
def test_multi_concept_objective_requires_every_concept(scope, second_correct, expected):
    _, _, goals, domain = scope
    objective = domain.objectives[0].model_copy(update={"concept_ids": ["cache-coherence", "virtual-memory"]})
    domain = domain.model_copy(update={"objectives": [objective, domain.objectives[1]]})
    concepts = [counts("cache-coherence", correct=2)]
    if second_correct:
        concepts.append(counts("virtual-memory", correct=second_correct))
    result = DeterministicAutonomousGoalManager().interpret(goals[0], belief_for(goals[0], concepts), domain_model=domain)
    assert result.complete is expected
    if not second_correct:
        assert result.progress == 0


def test_legacy_mastery_is_also_scoped(scope):
    _, _, goals, domain = scope
    state = LearnerState(
        conversation_id="legacy", course_id=goals[0].course_id, release_id=goals[0].release_id,
        mastery_by_concept={"cache-coherence": ConceptMastery(estimate=0.9, confidence=0.8, observation_count=2)},
        latest_signals=TurnSignals(request_type="attempt", attempt_present=True),
    )
    manager = DeterministicAutonomousGoalManager()
    assert manager.interpret(goals[0], state, domain_model=domain).complete
    assert not manager.interpret(goals[1], state, domain_model=domain).complete


def tutoring_service(repository):
    return existing.StudentTutoringService(
        repository, profile_path=existing.PROFILE,
        evidence_gate=existing.StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=existing.AtomicClaimEvidenceValidator(
            existing.ExactQuoteAtomicClaimVerifier(), minimum_entailment=1.0, maximum_contradiction=0.0,
        ), tutoring_mode=existing.TutoringMode.T1_V2,
        learning_gap_pseudonymizer=existing.LearningGapPseudonymizer(b"synthetic-goal-scope-secret-32bytes"),
    )


ATTEMPT = ("I think cache coherence keeps replicated processor data consistent "
           "because invalidation prevents cached copies from diverging.")


@pytest.mark.asyncio
async def test_real_turns_complete_only_target_and_persist_on_reopen(tmp_path):
    repository, fixture, goals = setup_two_goals(tmp_path)
    path = repository.path
    try:
        service = tutoring_service(repository)
        conversation = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
        for index, expected in [(1, ["active", "active"]), (2, ["completed", "active"]), (3, ["completed", "active"])]:
            result = await service.submit_message(fixture.student_a_id, conversation.id, content=ATTEMPT, client_request_id=f"goal-scope-{index}")
            assert result.citations
            assert [repository.get_autonomous_goal(g.goal_id).status.value for g in goals] == expected
        assert len(repository.list_autonomous_goals(fixture.student_a_id, fixture.course_a_id)) == 2
    finally:
        repository.close()
    reopened = existing.SQLiteStudentRepository(path)
    try:
        assert [reopened.get_autonomous_goal(g.goal_id).status.value for g in goals] == ["completed", "active"]
    finally:
        reopened.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("committed", [False, True])
async def test_completion_and_other_follow_up_respect_commit_boundary(scope, monkeypatch, committed):
    repository, fixture, goals, _ = scope
    service = tutoring_service(repository)
    conversation = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
    captured = {}
    original = service._autonomous_follow_up

    def capture(**kwargs):
        captured.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(service, "_autonomous_follow_up", capture)
    await service.submit_message(fixture.student_a_id, conversation.id, content=ATTEMPT, client_request_id="capture")
    artifacts = captured["reactive_v2_artifacts"]
    captured["reactive_v2_artifacts"] = SimpleNamespace(
        belief_state=belief_for(goals[0], [counts("cache-coherence", correct=2)]),
        state_committed=committed, observation=artifacts.observation,
    )
    # Deterministically select the other approved objective to isolate the lifecycle
    # branch from retrieval ranking. Turn inputs and citations are from the real service.
    monkeypatch.setattr(service.autonomy_goal_manager, "select_objective", lambda *_: OTHER_OBJECTIVE)
    opportunity, completed = original(**captured)
    assert completed == ([goals[0].goal_id] if committed else [])
    assert opportunity is not None and opportunity.goal_id == goals[1].goal_id
