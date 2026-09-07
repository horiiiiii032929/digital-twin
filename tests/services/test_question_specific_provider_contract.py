import json

import pytest

from services.llm.openai_responses_client import OpenAiResponsesClient
from src.digital_twin.llm import LlmMalformedResponseError, LlmMessage
from tests.services.test_openai_responses_client import _response


@pytest.mark.asyncio
@pytest.mark.parametrize('valid', [True, False])
async def test_question_specific_task_validates_the_same_shape_it_requests(monkeypatch, valid):
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-test-key')
    proposal = {'boundary':'answerable','aspects':[{'requirement':'selection order',
        'supported':True,'spans':[{'citation_id':'S1','text':'Order by deadline.'}]}],
        'teaching_move':'explain','question_focus':'order','hint_span':None}
    async def post(**kwargs):
        props = kwargs['json']['text']['format']['schema']['properties']
        assert set(props) == set(proposal)
        return _response(model='gpt-5.6-luna',text=json.dumps(proposal if valid else
            {'answer':'Old unrelated response schema.','citation_ids':['S1']}))
    client = OpenAiResponsesClient('gpt-5.6-luna',post=post)
    if valid:
        result=await client.chat([LlmMessage(role='user',content='What order?')],
                                'question_specific_profile_tutoring')
        assert json.loads(result.content) == proposal
        assert result.usage.input_tokens == 12
    else:
        with pytest.raises(LlmMalformedResponseError) as error:
            await client.chat([LlmMessage(role='user',content='What order?')],
                              'question_specific_profile_tutoring')
        assert error.value.stage == 'schema-validation'
        assert error.value.diagnostics['schema_errors']
        assert 'Old unrelated response schema.' not in str(error.value.diagnostics)


@pytest.mark.asyncio
@pytest.mark.parametrize('boundary,aspects,accepted', [
    ('clarify', [], True),
    ('insufficient', [], True),
    ('answerable', [], False),
    ('answerable', [{'requirement': 'order', 'supported': True,
                    'spans': [{'citation_id': 'S1', 'text': 'Order by deadline.'}]}], True),
])
async def test_conditional_proposal_contract_at_provider_boundary(monkeypatch, boundary, aspects, accepted):
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-test-key')
    proposal = {'boundary': boundary, 'aspects': aspects,
                'teaching_move': 'explain', 'question_focus': '', 'hint_span': None}
    async def post(**kwargs):
        return _response(model='gpt-5.6-luna', text=json.dumps(proposal))
    client = OpenAiResponsesClient('gpt-5.6-luna', post=post)
    if accepted:
        result = await client.chat([LlmMessage(role='user', content='What order?')],
                                   'question_specific_profile_tutoring')
        assert json.loads(result.content) == proposal
    else:
        with pytest.raises(LlmMalformedResponseError):
            await client.chat([LlmMessage(role='user', content='What order?')],
                              'question_specific_profile_tutoring')
