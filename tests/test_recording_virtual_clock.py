"""Integration checks for recording-only clock wiring, not model evaluation."""
from fastapi.testclient import TestClient

from scripts.prepare_recording_checkpoint import prepare
from scripts.recording_app import ACTORS, make_recording_app


CONTROL = {'X-Recording-Control': 'local-synthetic-only'}


def test_initial_support_does_not_require_a_student_question(tmp_path):
    with TestClient(make_recording_app(tmp_path)) as client:
        prepare(client)
        # Source provenance must not become the educational response itself.
        for course in ['course-a-recording', 'course-b-recording']:
            release = client.app.state.student_repository.get_published_release(course)
            assert release is not None
            assert all('RECORDING FIXTURE' not in chunk.text and 'Permission:' not in chunk.text
                       for chunk in release.chunks)
        assert client.post('/__recording/configure', headers=CONTROL).status_code == 200
        conversations = []
        for index, actor in enumerate(ACTORS[2:]):
            course = ['course-a-recording', 'course-b-recording'][index // 2]
            headers = {'X-Account-ID': actor[1]}
            created = client.post(f'/api/student/courses/{course}/conversations', headers=headers)
            assert created.status_code == 201
            conversations.append((created.json()['id'], headers))
            consent = client.put(f'/api/student/courses/{course}/outreach-preferences/in-app',
                headers=headers, json={'enabled': True, 'timezone': 'UTC',
                    'quiet_hours_start': '22:00', 'quiet_hours_end': '08:00', 'max_messages_per_7_days': 3})
            assert consent.status_code == 200
        first = client.post('/__recording/advance', headers=CONTROL, json={'days': 0}).json()
        assert first['events'][-1]['observation']['goals_created'] == 4
        second = client.post('/__recording/advance', headers=CONTROL, json={'days': 1}).json()
        assert second['events'][-1]['observation']['by_event'] == {'spaced-review-due': 4}
        assert all(len(inbox) == 1 for inbox in second['inboxes'].values())
        for conversation, headers in conversations:
            assert client.get(f'/api/student/conversations/{conversation}', headers=headers).json()['messages'] == []
        repeated = client.post('/__recording/advance', headers=CONTROL, json={'days': 0}).json()
        assert repeated['inboxes'] == second['inboxes']


def test_virtual_days_deliver_from_saved_state_and_respect_pause(tmp_path):
    with TestClient(make_recording_app(tmp_path)) as client:
        assert client.post('/__recording/advance', json={'days': 1}).status_code == 403
        prepare(client, include_turns=True)
        for index, actor in enumerate(ACTORS[2:]):
            course = ['course-a-recording', 'course-b-recording'][index // 2]
            response = client.put(f'/api/student/courses/{course}/outreach-preferences/in-app',
                headers={'X-Account-ID': actor[1]}, json={'enabled': True, 'timezone': 'UTC',
                    'quiet_hours_start': '22:00', 'quiet_hours_end': '08:00', 'max_messages_per_7_days': 3})
            assert response.status_code == 200
        first = client.post('/__recording/advance', headers=CONTROL, json={'days': 0}).json()
        assert first['events'][-1]['observation']['goals_created'] == 4
        assert all(not inbox for inbox in first['inboxes'].values())
        service = client.app.state.governed_autonomy_service
        policy = client.app.state.student_repository.get_autonomy_policy('course-b-recording')
        service.set_policy('professor-b-recording', 'course-b-recording',
            approved_course_objectives=policy.approved_course_objectives,
            allowed_actions=policy.allowed_actions, autonomy_enabled=True, paused=True)
        second = client.post('/__recording/advance', headers=CONTROL, json={'days': 1}).json()
        assert len(second['inboxes']['student-a-synthetic']) == 1
        assert len(second['inboxes']['student-a2-recording']) == 1
        assert not second['inboxes']['student-b-synthetic']
        assert not second['inboxes']['student-b2-recording']
        retry = client.post('/__recording/advance', headers=CONTROL, json={'days': 0}).json()
        assert retry['inboxes'] == second['inboxes']
        assert client.post('/__recording/advance', headers=CONTROL, json={'days': 30}).status_code == 409


def test_recording_guard_accepts_only_explicit_synthetic_runtime_names():
    import httpx
    import pytest
    from scripts.recording_safety import require_recording_runtime

    for name in ['synthetic-deterministic-v1', 'synthetic-model-backed-v4', 'production', None]:
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={'recording_runtime': name}))
        with httpx.Client(transport=transport, base_url='http://127.0.0.1') as client:
            if name in {'synthetic-deterministic-v1', 'synthetic-model-backed-v4'}:
                assert require_recording_runtime(client)['recording_runtime'] == name
            else:
                with pytest.raises(RuntimeError):
                    require_recording_runtime(client)
