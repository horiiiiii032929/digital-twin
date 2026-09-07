import asyncio

import httpx
import pytest

from scripts.tutoring_capacity_probe import StudentProbeSession, measure_tutoring_requests


@pytest.mark.asyncio
async def test_probe_measures_concurrent_posts_but_keeps_student_turns_sequential():
    active = set()
    seen = []

    async def handler(request):
        conversation = request.url.path.split('/')[-2]
        assert request.method == 'POST' and request.url.path.endswith('/messages')
        assert conversation not in active
        active.add(conversation)
        await asyncio.sleep(0.005)
        seen.append(conversation)
        active.remove(conversation)
        return httpx.Response(200, json={'tutor_message': {
            'conversation_id': conversation, 'content': 'A bounded question?', 'action': 'question'},
            'citations': []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url='http://test') as client:
        sessions = [StudentProbeSession(client, f'c{i}', 'course', 'release') for i in range(3)]
        result = await measure_tutoring_requests(sessions, ['first', 'second'])
    assert result['request_count'] == len(seen) == 6
    assert result['maximum_client_requests_in_flight'] == 3
    assert result['failure_count'] == 0
    assert result['quality_pass'] is None and not result['deployment_qualified']


@pytest.mark.asyncio
async def test_probe_counts_wrong_release_and_http_failure_without_leaking_text():
    async def handler(request):
        if '/bad/' in request.url.path:
            return httpx.Response(503, text='sensitive-provider-error')
        return httpx.Response(200, json={'tutor_message': {
            'conversation_id': 'wrong', 'content': 'sensitive-response', 'action': 'answer'},
            'citations': [{'course_id': 'course', 'release_id': 'another-release'}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url='http://test') as client:
        result = await measure_tutoring_requests([
            StudentProbeSession(client, c, 'course', 'release') for c in ['bad', 'wrong']], ['question'])
    assert result['failure_count'] == 2
    assert result['successful_response_p95_ms'] is None
    assert 'sensitive' not in str(result)
