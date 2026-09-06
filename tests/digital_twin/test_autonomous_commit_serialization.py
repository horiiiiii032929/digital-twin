"""Separate workers cannot cancel a job between its state read and final writes."""
import sqlite3

import pytest

from src.digital_twin.student import SQLiteStudentRepository
from tests.digital_twin.test_governed_autonomy import _autonomy_fixture, _goal_and_opportunity, NOW


@pytest.mark.asyncio
async def test_autonomous_commit_serializes_administrative_cancellation(tmp_path, monkeypatch):
    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(service, fixture, release)
    commit = repository.commit_autonomous_job
    captured = []

    def capture(result):
        captured.append(result)
        raise RuntimeError('pause before durable job commit')

    monkeypatch.setattr(repository, 'commit_autonomous_job', capture)
    with pytest.raises(RuntimeError, match='pause before durable'):
        await service.process_due(worker_id='serialization-test', now=NOW)
    monkeypatch.setattr(repository, 'commit_autonomous_job', commit)
    administrator = SQLiteStudentRepository(repository.path)
    administrator._connection.execute('PRAGMA busy_timeout=0')
    attempted = []

    def race(statement):
        if 'INSERT INTO autonomous_plans' not in statement or attempted:
            return
        try:
            administrator.cancel_autonomy_scope(student_id=fixture.student_a_id,
                course_id=fixture.course_a_id, changed_at=NOW.isoformat())
        except sqlite3.OperationalError as error:
            attempted.append('blocked' if 'locked' in str(error) else str(error))
        else:
            attempted.append('cancelled-before-commit')

    try:
        repository._connection.set_trace_callback(race)
        commit(captured[0])
        assert attempted == ['blocked']
        assert repository.get_autonomous_opportunity(opportunity.opportunity_id).status.value == 'completed'
        assert len(repository.list_autonomous_actions(fixture.course_a_id)) == 1
        repository._connection.set_trace_callback(None)
        # A later administrative operation can still cancel the active goal.
        administrator.cancel_autonomy_scope(student_id=fixture.student_a_id,
            course_id=fixture.course_a_id, changed_at=NOW.isoformat())
        assert repository.list_autonomous_goals(fixture.student_a_id, fixture.course_a_id, active_only=True) == []
    finally:
        repository._connection.set_trace_callback(None)
        administrator.close()
        repository.close()


def test_wakeup_materialization_serializes_cancellation(tmp_path):
    from src.digital_twin.student.autonomy_models import AutonomousWakeUpV1

    repository, fixture, service, release, _ = _autonomy_fixture(tmp_path)
    goal, original = _goal_and_opportunity(service, fixture, release)
    wake = AutonomousWakeUpV1(wake_up_id='serialized-wake', goal_id=goal.goal_id,
        student_id=fixture.student_a_id, course_id=fixture.course_a_id, release_id=release.id,
        due_at=NOW.isoformat(), event_kind=original.event_kind)
    with repository._connection:
        repository._insert_autonomous_wakeup(wake)
    next_opportunity = original.model_copy(update={
        'opportunity_id': 'from-serialized-wake', 'idempotency_key': 'serialized-wake-key'})
    administrator = SQLiteStudentRepository(repository.path)
    administrator._connection.execute('PRAGMA busy_timeout=0')
    attempted = []

    def race(statement):
        if 'INSERT INTO autonomous_opportunities' not in statement or attempted:
            return
        try:
            administrator.cancel_autonomy_scope(student_id=fixture.student_a_id,
                course_id=fixture.course_a_id, changed_at=NOW.isoformat())
        except sqlite3.OperationalError as error:
            attempted.append('blocked' if 'locked' in str(error) else str(error))
        else:
            attempted.append('cancelled-before-insert')

    try:
        repository._connection.set_trace_callback(race)
        assert repository.materialize_autonomous_wakeup(wake.wake_up_id,
            next_opportunity, fired_at=NOW.isoformat())
        assert attempted == ['blocked']
        repository._connection.set_trace_callback(None)
        administrator.cancel_autonomy_scope(student_id=fixture.student_a_id,
            course_id=fixture.course_a_id, changed_at=NOW.isoformat())
        assert repository.get_autonomous_opportunity(next_opportunity.opportunity_id).status.value == 'cancelled'
    finally:
        repository._connection.set_trace_callback(None)
        administrator.close()
        repository.close()
