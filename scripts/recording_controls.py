"""Local-only virtual clock controls for the isolated recording factory.

No new planner, fabricated messages, or seeded opportunities. Existing services
observe saved product state and process due work after each virtual day.
"""
from __future__ import annotations

import hashlib
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from src.digital_twin.student import CanonicalSourceRangeV1, CourseConceptV1, CourseDomainModelV1, CourseObjectiveV1
from src.digital_twin.student.autonomy_models import AutonomousActionKind


class Advance(BaseModel):
    days: int = Field(ge=0, le=30)


def install_controls(app, clock, *, runtime_name="synthetic-deterministic-v1"):
    if runtime_name not in {"synthetic-deterministic-v1", "synthetic-model-backed-v4"}:
        raise ValueError("Unknown isolated recording runtime")
    app.state.recording_events = []
    app.state.recording_day = 1

    def guard(request):
        if request.client.host not in {'127.0.0.1', '::1', 'testclient'} or request.headers.get('X-Recording-Control') != 'local-synthetic-only':
            raise HTTPException(403, 'Recording controls are local scenario inputs only.')

    @app.post('/__recording/configure')
    def configure(request: Request):
        guard(request)
        repo = app.state.student_repository
        for i, (course, professor, topic, phrase) in enumerate([
            ('course-a-recording', 'professor-synthetic', 'Cache coherence', 'replicated processor data'),
            ('course-b-recording', 'professor-b-recording', 'Release policy', 'approval and withdrawal'),
        ]):
            release = repo.get_published_release(course)
            if release is None:
                raise HTTPException(409, 'Publish the course first.')
            chunk = next(c for c in release.chunks if phrase in c.text)
            objective = f'Explain {topic.lower()} using the approved course evidence.'
            repo.save_course_domain_model(CourseDomainModelV1(
                domain_model_id=f'recording-domain-{i}', course_id=course, release_id=release.id,
                release_sha256=hashlib.sha256(release.model_dump_json().encode()).hexdigest(), version=1,
                objectives=[CourseObjectiveV1(objective_id=f'objective-{i}', statement=objective, concept_ids=[f'concept-{i}'])],
                concepts=[CourseConceptV1(concept_id=f'concept-{i}', label=topic, description=chunk.text,
                    canonical_ranges=[CanonicalSourceRangeV1(source_artifact_id=chunk.source_artifact_id,
                        source_version=chunk.source_version, source_sha256=chunk.source_checksum or chunk.content_hash,
                        locator=chunk.locator, char_start=0, char_end=len(chunk.text))])], approved_by=professor))
            app.state.governed_autonomy_service.set_policy(professor, course,
                approved_course_objectives=[objective], allowed_actions=list(AutonomousActionKind), autonomy_enabled=True)
        return {'configured': True}

    @app.post('/__recording/advance')
    async def advance(payload: Advance, request: Request):
        guard(request)
        if app.state.recording_day + payload.days > 30:
            raise HTTPException(409, 'This recording is bounded to 30 virtual days.')
        service = app.state.governed_autonomy_service
        for step in range(max(1, payload.days)):
            if payload.days:
                clock.advance_by(86400)
                app.state.recording_day += 1
            sweep = service.observe_events(now=clock.now())
            results = await service.process_due(worker_id='recording-virtual-clock', now=clock.now())
            app.state.recording_events.append({'day': app.state.recording_day, 'time': clock.now().isoformat(),
                'observation': sweep.model_dump(mode='json'), 'results': [r.model_dump(mode='json') for r in results]})
        return state_data()

    def state_data():
        repo = app.state.student_repository
        courses = ['course-a-recording', 'course-b-recording']
        return {'recording_runtime': runtime_name,
                'day': app.state.recording_day, 'time': clock.now().isoformat(),
                'events': app.state.recording_events,
                'actions': [a.model_dump(mode='json') for c in courses for a in repo.list_autonomous_actions(c)],
                'inboxes': {student: [m.model_dump(mode='json') for m in repo.list_proactive_messages(student)]
                            for student in ['student-a-synthetic', 'student-a2-recording', 'student-b-synthetic', 'student-b2-recording']}}

    @app.get('/__recording/state')
    def state(request: Request):
        guard(request)
        return state_data()
