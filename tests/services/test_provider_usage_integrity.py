import json

import httpx
import pytest

from services.llm import BudgetedLlmClient, OpenAiResponsesClient
from src.digital_twin.llm import LlmBudgetExceededError, LlmMalformedResponseError, LlmMessage

MODEL='gpt-5.6-luna'
MESSAGES=[LlmMessage(role='user',content='Synthetic accounting boundary')]


def payload(usage):
    body={'model':MODEL,'status':'completed',
          'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'answer':'A fact.','citation_ids':['S1']})}]}]}
    if usage != 'absent':
        body['usage'] = usage
    return body


@pytest.mark.asyncio
@pytest.mark.parametrize('usage',['absent',None,{}, {'input_tokens':10},{'output_tokens':20},
                                  {'input_tokens':True,'output_tokens':3},{'input_tokens':-1,'output_tokens':3}])
async def test_missing_or_invalid_usage_never_becomes_known_free_usage(monkeypatch,usage):
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-contract-key')
    async def post(**_):return httpx.Response(200,json=payload(usage))
    client=OpenAiResponsesClient(MODEL,post=post)
    with pytest.raises(LlmMalformedResponseError) as error:
        await client.chat(MESSAGES,'grounded_tutor_answer')
    assert error.value.stage=='usage-validation'
    assert error.value.usage is None


@pytest.mark.asyncio
@pytest.mark.parametrize('usage',[{'input_tokens':0,'output_tokens':0},{'input_tokens':10,'output_tokens':20}])
async def test_explicit_zero_and_normal_usage_remain_valid(monkeypatch,usage):
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-contract-key')
    async def post(**_):return httpx.Response(200,json=payload(usage))
    client=OpenAiResponsesClient(MODEL,post=post)
    response=await client.chat(MESSAGES,'grounded_tutor_answer')
    assert response.usage.total_tokens==sum(usage.values())
    assert response.usage.approximate_cost_usd is not None


@pytest.mark.asyncio
@pytest.mark.parametrize('concurrency',[1,5])
async def test_real_transport_unknown_usage_stops_subsequent_budget_admissions(monkeypatch,concurrency):
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-contract-key')
    calls=0
    async def post(**_):
        nonlocal calls
        calls+=1
        return httpx.Response(200,json=payload('absent'))
    transport=OpenAiResponsesClient(MODEL,post=post)
    budget=BudgetedLlmClient(transport,max_calls=10,max_cost_usd=1,max_concurrency=concurrency)
    with pytest.raises(LlmMalformedResponseError):
        await budget.chat(MESSAGES,'grounded_tutor_answer')
    with pytest.raises(LlmBudgetExceededError):
        await budget.chat(MESSAGES,'grounded_tutor_answer')
    snapshot=budget.snapshot()
    assert calls==1
    assert snapshot['cost_reporting_failed'] is True
    assert snapshot['unknown_cost_calls']==1
    if concurrency>1:
        assert snapshot['uncertain_reserved_usd']>0
