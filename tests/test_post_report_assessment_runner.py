import json
import pytest
from scripts.run_post_report_assessment import run, metrics, wilson
from src.digital_twin.llm import LlmResponse
from src.digital_twin.grounding.models import GenerationUsage


@pytest.mark.asyncio
async def test_complete_packet_keeps_gold_out_of_requests_and_accounts_for_boundaries(tmp_path):
    class Client:
        async def chat(self,messages,task):
            assert task=='source_bound_attempt_assessment_v1'
            payload=json.loads(messages[-1].content)
            assert set(payload)=={'attempt','target','evidence'}
            assert all(set(s)=={'source_id','text'} for s in payload['evidence'])
            return LlmResponse(content=json.dumps({'outcome':'not-assessed','confidence':0,
                'reason':'insufficient-evidence','quotations':[]}),provider_model='gpt-5.6-luna',
                usage=GenerationUsage(input_tokens=10,output_tokens=10,total_tokens=20,approximate_cost_usd=.0001))
    result=await run(tmp_path/'run',transport=Client())
    assert result['completed_cases']==32
    assert result['provider_calls']<=26
    assert result['unknown_cost_calls']==0
    assert result['metrics']['model']['accuracy']==.5
    assert result['metrics']['model']['coverage']==0
    assert result['metrics']['model']['correct_precision'] is None
    assert result['source_files_unchanged']
    rows=[json.loads(s) for s in (tmp_path/'run/cases.jsonl').read_text().splitlines()]
    assert all(not r['provider_called'] for r in rows if r['kind'] in {
        'foreign-release','foreign-course','ambiguous-concepts','permission-denied','superseded-source','missing-range'})


def test_false_correct_and_abstention_cannot_hide_in_accuracy():
    rows=[{'expected':'incorrect','model':{'outcome':'correct'},'boundary':False},
        {'expected':'not-assessed','model':{'outcome':'partial'},'boundary':True}]
    result=metrics(rows,'model')
    assert result['accuracy']==0 and result['false_correct']==1
    assert result['boundary_assessments']==1
    assert result['correct_precision']==0
    assert wilson(0,0) is None
    assert wilson(0,10)[1]>0
