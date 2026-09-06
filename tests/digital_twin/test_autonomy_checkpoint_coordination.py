"""Mixed graph families share short SQLite writes, never model generation.

The four held-writer probes inject timeout=0 only in tests to make missing
coordination deterministic; they do not measure production busy timeouts.
"""
import asyncio
from types import SimpleNamespace

import aiosqlite
import pytest
from services.persistence.async_sqlite_coordination import coordinated_connection
from src.digital_twin.student.autonomy_runtime import GovernedAutonomousTutoringGraph, AutonomousJobInput
from tests.digital_twin.test_governed_autonomy import _autonomy_fixture, _goal_and_opportunity, NOW

@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['reserve', 'complete', 'fail', 'graph'])
async def test_autonomy_waits_for_coordinated_sqlite_writer(tmp_path, monkeypatch, operation):
    repo, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, opportunity = _goal_and_opportunity(service, fixture, release)
    graph = GovernedAutonomousTutoringGraph(checkpoint_database_path=str(repo.path))
    job = SimpleNamespace(opportunity=opportunity, now=NOW.isoformat())
    await graph._reserve_model_call(job, stage='seed', request_payload={})
    connect = aiosqlite.connect
    def immediate_connect(*args, **kwargs):
        # Deterministic probe, not a production timeout change: an uncoordinated
        # real SQLite write fails immediately while the held writer is live.
        kwargs['timeout'] = 0
        return connect(*args, **kwargs)
    monkeypatch.setattr(aiosqlite, 'connect', immediate_connect)
    if operation == 'graph':
        policy = repo.get_autonomy_policy(fixture.course_a_id)
        job = AutonomousJobInput(opportunity=opportunity, goal=goal, policy=policy,
            professor_id=fixture.professor_id, current_release_id=release.id,
            current_profile_id=policy.approved_profile_id,
            current_profile_sha256=policy.approved_profile_sha256,
            membership_active=True, consent_active=True, evidence_keys=[],
            evidence_complete=False, evidence_unique=False, evidence_current=False,
            evidence_authorized=False, now=NOW.isoformat())
        action = graph.run(job)
    elif operation == 'reserve':
        action = graph._reserve_model_call(job, stage='new', request_payload={})
    elif operation == 'complete':
        action = graph._complete_model_call(job, 'seed', '{}')
    else:
        action = graph._fail_model_call(job, 'seed', 'synthetic')
    task = None
    try:
        async with coordinated_connection(repo.path) as writer:
            await writer.execute('BEGIN IMMEDIATE')
            task = asyncio.create_task(action)
            try:
                await asyncio.wait_for(asyncio.shield(task), .1)
            except asyncio.TimeoutError:
                pass  # Correctly coordinated work waits until writer closes.
            assert not task.done(), 'writer operation bypassed the shared mutex'
            await writer.commit()
        result = await asyncio.wait_for(task, 3)
        if operation == 'graph':
            assert result.action.kind.value == 'no-action'
        else:
            stage = 'new' if operation == 'reserve' else 'seed'
            row = repo._connection.execute(
                'SELECT status, output_json, failure_code FROM autonomous_model_calls_v2 '
                'WHERE opportunity_id = ? AND stage = ?',
                (opportunity.opportunity_id, stage),
            ).fetchone()
            if operation == 'reserve':
                assert result == (None, True) and row['status'] == 'started'
            elif operation == 'complete':
                assert row['status'] == 'completed' and row['output_json'] == '{}'
            else:
                assert row['status'] == 'failed' and row['failure_code'] == 'synthetic'
    finally:
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        repo.close()

@pytest.mark.asyncio
async def test_mixed_graph_models_overlap_and_share_checkpoint_mutex(tmp_path, monkeypatch):
    from src.digital_twin.generation import DeterministicEvidenceSetGroundedGenerator
    from src.digital_twin.student.autonomy_runtime import DeterministicAutonomousWordingGenerator
    from src.digital_twin.student import tutoring_graph, autonomy_runtime
    from tests.digital_twin.test_governed_autonomy import (
        PROFILE, StudentTutoringService, StructuredLexicalCoverageEvidenceGate,
        AtomicClaimEvidenceValidator, ExactQuoteAtomicClaimVerifier,
        TutoringMode, LearningGapPseudonymizer,
    )
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, opportunity = _goal_and_opportunity(service, fixture, release)
    entered = set()
    both = asyncio.Event()
    calls = {'reactive': 0, 'autonomous': 0}
    async def barrier(family):
        calls[family] += 1
        entered.add(family)
        if len(entered) == 2:
            both.set()
        await asyncio.wait_for(both.wait(), 5)

    class ReactiveGenerator(DeterministicEvidenceSetGroundedGenerator):
        model_id = 'synthetic-barrier-reactive'
        async def generate_for_intent(self, *args, **kwargs):
            await barrier('reactive')
            return await super().generate_for_intent(*args, **kwargs)

    class AutonomousGenerator(DeterministicAutonomousWordingGenerator):
        model_id = 'synthetic-barrier-autonomous'
        async def generate(self, *args, **kwargs):
            await barrier('autonomous')
            return await super().generate(*args, **kwargs)

    collected = []
    saver_class = tutoring_graph.AsyncSqliteSaver
    def capture(*args, **kwargs):
        saver = saver_class(*args, **kwargs)
        collected.append(saver)
        return saver
    monkeypatch.setattr(tutoring_graph, 'AsyncSqliteSaver', capture)
    monkeypatch.setattr(autonomy_runtime, 'AsyncSqliteSaver', capture)
    tutoring = StudentTutoringService(repository, profile_path=PROFILE,
        generator=ReactiveGenerator(), evidence_gate=StructuredLexicalCoverageEvidenceGate(),
        claim_evidence_validator=AtomicClaimEvidenceValidator(ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0, maximum_contradiction=0.0),
        tutoring_mode=TutoringMode.T1_V2,
        learning_gap_pseudonymizer=LearningGapPseudonymizer(b'mixed-graph-synthetic-key-32-bytes'))
    conversation = tutoring.create_conversation(fixture.student_a_id, fixture.course_a_id)
    policy = repository.get_autonomy_policy(fixture.course_a_id)
    chunk = release.chunks[0]
    key = ':'.join((chunk.source_artifact_id, str(chunk.source_version), chunk.content_hash, chunk.locator))
    job = AutonomousJobInput(opportunity=opportunity, goal=goal, policy=policy,
        professor_id=fixture.professor_id, current_release_id=release.id,
        current_profile_id=policy.approved_profile_id,
        current_profile_sha256=policy.approved_profile_sha256,
        membership_active=True, consent_active=True, evidence_keys=[key], evidence_chunk_ids=[chunk.id],
        evidence_complete=True, evidence_unique=True, evidence_current=True,
        evidence_authorized=True, now=NOW.isoformat())
    graph = GovernedAutonomousTutoringGraph(generator=AutonomousGenerator(),
        checkpoint_database_path=str(repository.path))
    try:
        turn, outcome = await asyncio.gather(tutoring.submit_message(fixture.student_a_id,
            conversation.id, content='How does cache coherence keep processor copies consistent?',
            client_request_id='mixed-synthetic'), graph.run(job))
        assert both.is_set() and calls == {'reactive': 1, 'autonomous': 1}
        assert turn.tutor_message.content
        assert len(repository.list_messages(conversation.id)) == 2
        assert outcome.trace.generation_calls == 1
        assert len(collected) == 2 and collected[0].lock is collected[1].lock
    finally:
        repository.close()
