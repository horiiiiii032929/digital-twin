"""Withdrawal must bind both request admission and the final turn transaction."""
import asyncio

import pytest

from src.digital_twin.student import SQLiteStudentRepository, StudentWorkflowError
from src.digital_twin.student.models import StudentReleaseStatus
from src.digital_twin.student.teaching_profile import TeachingProfileService
from tests.api.test_publication_api import _teaching_profile_payload
from tests.api.test_student_api import _client, AtomicClaimGenerator, KeywordEmbedder


def bind_profile(repository, fixture):
    profiles = TeachingProfileService(repository)
    draft = profiles.create_draft(fixture.professor_id, fixture.course_a_id, _teaching_profile_payload())
    approved = profiles.approve(fixture.professor_id, fixture.course_a_id, draft.profile_id,
        preview_sha256=profiles.preview(fixture.professor_id, fixture.course_a_id, draft.profile_id).preview_sha256)
    release = repository.get_release(fixture.release_a_id).model_copy(update={
        'id': 'reaudit-profile-bound', 'status': StudentReleaseStatus.DRAFT,
        'teaching_profile_id': approved.profile_id, 'teaching_profile_sha256': approved.content_sha256})
    repository.save_release(release)
    repository.publish_release(release.id)
    return approved


@pytest.mark.asyncio
@pytest.mark.parametrize('timing', ['before_request', 'during_generation', 'superseded'])
async def test_turn_obeys_bound_profile_authority(tmp_path, timing):
    started, resume = asyncio.Event(), asyncio.Event()

    class PausedGenerator(AtomicClaimGenerator):
        calls = 0
        async def generate(self, question, hits, policy):
            self.calls += 1
            answer = await super().generate(question, hits, policy)
            started.set()
            await resume.wait()
            return answer

    generator = PausedGenerator(supported=True)
    client, repository, fixture = _client(tmp_path, embedder=KeywordEmbedder(), generator=generator)
    administrator = SQLiteStudentRepository(repository.path)
    task = None
    try:
        profile = bind_profile(repository, fixture)
        service = client.app.state.student_service
        conversation = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
        profiles = TeachingProfileService(administrator)
        if timing == 'before_request':
            profiles.withdraw(fixture.professor_id, fixture.course_a_id, profile.profile_id)
            resume.set()
            with pytest.raises(StudentWorkflowError) as caught:
                await service.submit_message(fixture.student_a_id, conversation.id,
                    content='Explain cache coherence.', client_request_id='withdrawn-before')
            assert caught.value.code == 'teaching_profile_unavailable'
            assert generator.calls == 0
            with pytest.raises(StudentWorkflowError):
                service.create_conversation(fixture.student_a_id, fixture.course_a_id)
        else:
            task = asyncio.create_task(service.submit_message(fixture.student_a_id, conversation.id,
                content='Explain cache coherence.', client_request_id='withdrawn-during'))
            await asyncio.wait_for(started.wait(), 5)
            if timing == 'during_generation':
                profiles.withdraw(fixture.professor_id, fixture.course_a_id, profile.profile_id)
            else:
                successor = profiles.create_draft(fixture.professor_id, fixture.course_a_id, _teaching_profile_payload())
                profiles.approve(fixture.professor_id, fixture.course_a_id, successor.profile_id,
                    preview_sha256=profiles.preview(fixture.professor_id, fixture.course_a_id, successor.profile_id).preview_sha256)
                assert repository.get_teaching_profile(profile.profile_id).status == 'superseded'
            resume.set()
            if timing == 'during_generation':
                with pytest.raises(StudentWorkflowError) as caught:
                    await task
                assert caught.value.code == 'turn_authority_changed'
            else:
                result = await task
                assert result.tutor_message.action == 'answer'
        assert len(repository.list_messages(conversation.id)) == (2 if timing == 'superseded' else 0)
    finally:
        resume.set()
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        administrator.close()
        client.close()
        repository.close()
