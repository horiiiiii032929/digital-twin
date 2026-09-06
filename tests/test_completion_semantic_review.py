import json

import httpx
import pytest

from scripts import run_completion_semantic_review as runner
from scripts.cross_course_quality_development import PACKET
from src.digital_twin.llm import LlmMessage


def review(**changes):
    return {'grounding':'adequate','relevance':'adequate','completeness':'adequate',
            'profile_adherence':'adequate','citation_validity':'adequate',
            'usefulness':'useful','overall':'acceptable','reason':'Supported.',
            'response_excerpts':[],**changes}


def test_calibration_hides_expected_labels_in_actual_payload():
    rows = runner.calibration_inputs(json.loads(PACKET.read_text()))
    assert len(rows) == 22
    assert {r['repetition'] for r in rows} == {0,1}
    assert all(not {'mutation','baseline','advisory','gold','expected'} & r['payload'].keys() for r in rows)
    assert len({r['id'] for r in rows}) == 22
    assert {r['mutation'] for r in rows if r['repetition']==0} == {r['mutation'] for r in rows if r['repetition']==1}


def test_calibration_requires_specific_defect_axis_and_not_just_rejection():
    assert not runner.calibration_match('unsupported-addition', review(overall='defective',relevance='defective'))
    assert runner.calibration_match('unsupported-addition', review(overall='defective',grounding='defective'))
    assert runner.calibration_match('clean',review())
    assert runner.calibration_match('generic-question',review()) is None
    assert runner.calibration_match('duplicate-text',review()) is None


@pytest.mark.parametrize('changes', [
    {'response_excerpts':['not actually said']},
    {'grounding':'defective'},
    {'grounding':'uncertain'},
])
def test_review_rejects_hallucinated_excerpt_or_inconsistent_verdict(changes):
    with pytest.raises(ValueError):
        runner.validate_review(json.dumps(review(**changes)), {'response':{'text':'Supported.'}})


def test_uncertainty_is_retained_not_coerced_to_pass():
    result=runner.validate_review(json.dumps(review(grounding='uncertain',overall='uncertain')), {'response':{'text':'Supported.'}})
    assert result['overall']=='uncertain'


@pytest.mark.asyncio
async def test_custom_schema_and_parser_share_actual_transport(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-contract-key')
    async def post(**kwargs):
        payload=kwargs['json']
        assert payload['store'] is False
        assert payload['text']['format']['name']==runner.TASK
        assert 'grounding' in payload['text']['format']['schema']['properties']
        assert payload['max_output_tokens']==1500
        return httpx.Response(200,json={'model':runner.MODEL,'status':'completed',
            'usage':{'input_tokens':10,'output_tokens':20},
            'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(review())}]}]})
    client=runner.AdvisoryClient(runner.MODEL,post=post,max_output_tokens=1500,reasoning_effort='low')
    messages=[LlmMessage(role='user',content='Synthetic review control')]
    ceiling=client.conservative_request_cost_usd(messages,runner.TASK)
    result=await client.chat(messages,runner.TASK)
    assert result.provider_model==runner.MODEL
    assert result.usage.approximate_cost_usd < ceiling
    assert json.loads(result.content)['grounding']=='adequate'


def test_all_inapplicable_axes_cannot_receive_acceptable_verdict():
    with pytest.raises(ValueError):
        runner.validate_review(json.dumps(review(**{k:'not_applicable' for k in
            ('grounding','relevance','completeness','profile_adherence','citation_validity')})),
            {'response':{'text':'Any response'}})


def test_missing_judgments_are_not_silently_counted_as_passes():
    rows=[{'id':'a','arm':'incumbent','case_id':'paired','course':'c','kind':'q','status':'not-executed'},
          {'id':'b','arm':'question-specific-profile-candidate','case_id':'paired','course':'c','kind':'q',
           'status':'completed','review':review()}]
    result=runner.summarize_judgments(rows)
    assert result['paired_overall_incumbent_then_candidate']=={'not-executed / acceptable':1}
    assert result['slices']['arm']['incumbent']['overall']=={'not-executed':1}
    with pytest.raises(ValueError,match='duplicate'):
        runner.summarize_judgments(rows+[rows[0]])


def test_v2_control_labels_never_enter_the_provider_payload():
    rows=runner.calibration_v2_inputs()
    assert len(rows)==64
    assert len({r['control_id'] for r in rows})==32
    assert all(set(r['payload'])=={'question','profile','history','sources','response'} for r in rows)
    assert all('expected' not in r['payload'] and 'gold' not in r['payload'] for r in rows)
    for r in rows:
        actual={'overall':r['expected']['overall'],**{axis: allowed[0] for axis,allowed in r['expected']['axes'].items()}}
        assert runner.matches_control(r,actual)
        assert not runner.matches_control(r,{**actual,'overall':'uncertain'})
