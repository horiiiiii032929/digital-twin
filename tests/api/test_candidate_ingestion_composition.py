"""Published upload/profile reach the actual opt-in tutoring composition."""
import hashlib
import json

from fastapi.testclient import TestClient

from services.api.app.config import AppSettings, AutonomyPlannerMode, EvidenceGateMode, StudentTutoringMode
from services.api.app.factory import create_app
from src.digital_twin.generation.question_specific import TASK
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse
from src.digital_twin.onboarding import InMemorySessionRepository, create_session
from src.digital_twin.student import SQLiteStudentRepository, approved_synthetic_policy, seed_synthetic_student_workflow
from tests.api.test_publication_api import _headers, _teaching_profile_payload


class UploadedEvidenceClient:
    def __init__(self):
        self.calls = []

    async def chat(self, messages, task):
        payload = json.loads(messages[-1].content)
        self.calls.append((task, payload))
        if task != TASK:
            raise LlmMalformedResponseError(usage=GenerationUsage(approximate_cost_usd=0))
        source = payload['evidence'][0]
        return LlmResponse(provider_model='gpt-5.6-luna',
            usage=GenerationUsage(approximate_cost_usd=0),
            content=json.dumps({'boundary': 'answerable', 'teaching_move': 'explain',
                'question_focus': '', 'hint_span': None,
                'aspects': [{'requirement': 'ready task order', 'supported': True,
                            'spans': [{'citation_id': source['citation_id'], 'text': source['text']}]}]}))


def test_uploaded_source_and_approved_profile_reach_candidate_then_withdraw(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / 'student.sqlite3')
    fixture = seed_synthetic_student_workflow(repository)
    sessions = InMemorySessionRepository()
    session = create_session('composition-onboarding')
    session.course_id = fixture.course_a_id
    session.current_step = 'professor_approval'
    session.policy = approved_synthetic_policy()
    sessions.save(session)
    provider = UploadedEvidenceClient()
    settings = AppSettings(data_root=tmp_path, database_path=tmp_path / 'student.sqlite3',
        autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE,
        evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3,
        student_tutoring_mode=StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
        learning_gap_hmac_secret=b'synthetic-composition-test-only-key-0001')
    app = create_app(repository=sessions, student_repository=repository, settings=settings,
        autonomy_planner_client=provider, teaching_profile_context_enabled=True,
        question_specific_generation_enabled=True)
    professor = _headers(fixture.professor_id)
    student = _headers(fixture.student_a_id)
    source = b'Aster scheduler chooses the ready task with the earliest deadline.'
    profile = _teaching_profile_payload()
    profile['help_ladder'] = ['Explain the supported answer first', 'Check understanding']
    try:
        with TestClient(app) as client:
            upload = client.put(f'/api/professor/courses/{fixture.course_a_id}/sources/composition-source',
                headers={**professor, 'Content-Type': 'text/plain'}, content=source,
                params={'title': 'Synthetic scheduling note', 'display_allowed': True,
                        'deidentified_reviewed': True})
            assert upload.status_code == 201, upload.text
            created = client.post(f'/api/professor/courses/{fixture.course_a_id}/teaching-profiles',
                headers=professor, json=profile)
            assert created.status_code == 201, created.text
            profile_id = created.json()['profile_id']
            profile_url = f'/api/professor/courses/{fixture.course_a_id}/teaching-profiles/{profile_id}'
            preview = client.get(profile_url + '/preview', headers=professor).json()
            approved = client.post(profile_url + '/approve', headers=professor,
                json={'preview_sha256': preview['preview_sha256']})
            assert approved.status_code == 200, approved.text
            release_id = 'composition-upload-profile-release'
            draft = client.post(f'/api/professor/courses/{fixture.course_a_id}/releases', headers=professor,
                json={'session_id': session.session_id, 'profile_id': 'student-tutor',
                      'profile_version': 'v1', 'release_id': release_id,
                      'teaching_profile_id': profile_id, 'chunks': upload.json()['chunks']})
            assert draft.status_code == 201, draft.text
            preflight = client.post(f'/api/professor/releases/{release_id}/preflight', headers=professor)
            assert preflight.status_code == 200 and preflight.json()['passed'], preflight.text
            assert client.post(f'/api/professor/releases/{release_id}/publish', headers=professor).status_code == 200
            chunk = upload.json()['chunks'][0]
            domain = client.post(f'/api/professor/courses/{fixture.course_a_id}/domain-model', headers=professor,
                json={'release_id': release_id, 'version': 1,
                      'objectives': [{'objective_id': 'explain-scheduling',
                                      'statement': 'Explain the ready task order.', 'concept_ids': ['aster']}],
                      'concepts': [{'concept_id': 'aster', 'label': 'Aster scheduling',
                                    'description': source.decode(), 'prerequisite_concept_ids': [],
                                    'canonical_ranges': [{'source_artifact_id': chunk['source_artifact_id'],
                                        'source_version': chunk['source_version'], 'source_sha256': hashlib.sha256(source).hexdigest(),
                                        'locator': chunk['locator'], 'char_start': 0, 'char_end': len(source.decode())}]}],
                      'misconceptions': []})
            assert domain.status_code == 201, domain.text
            conversation = client.post(f'/api/student/courses/{fixture.course_a_id}/conversations', headers=student)
            assert conversation.status_code == 201, conversation.text
            endpoint = f"/api/student/conversations/{conversation.json()['id']}/messages"
            response = client.post(endpoint, headers=student,
                json={'content': 'How does Aster choose the next ready task?', 'request_id': 'composition-turn'})
            assert response.status_code == 200, response.text
            turn = response.json()
            assert turn['tutor_message']['action'] == 'answer', turn
            assert source.decode() in turn['tutor_message']['content']
            assert turn['citations'] and all(c['source_checksum'] == hashlib.sha256(source).hexdigest()
                and c['release_id'] == release_id for c in turn['citations'])
            payload = next(payload for task, payload in provider.calls if task == TASK)
            assert payload['approved_teaching_profile']['preferences'] == profile
            assert payload['evidence'][0]['text'] == source.decode()
            assert app.state.student_service.evidence_gate.implementation_id == 'authorized-top5-async-answerability-admission-v1'
            calls_before_withdrawal = len(provider.calls)
            assert client.post(f'/api/professor/releases/{release_id}/withdraw', headers=professor).status_code == 200
            denied = client.post(endpoint, headers=student,
                json={'content': 'Explain the order again.', 'request_id': 'after-withdrawal'})
            assert denied.status_code == 409
            assert len(provider.calls) == calls_before_withdrawal
    finally:
        repository.close()
