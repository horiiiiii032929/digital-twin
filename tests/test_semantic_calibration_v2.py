import json

import pytest

from scripts.semantic_calibration_v2 import PACKET, public_payload, validate_packet


def packet():
    return json.loads(PACKET.read_text())


def test_explicit_turn_packet_has_four_balanced_courses():
    p=packet();validate_packet(p)
    assert sum(r['gold']['overall']=='acceptable' for r in p['cases'])==16


def test_public_payload_excludes_outer_gold_and_is_copy():
    row=packet()['cases'][0];row['hidden_answer']='secret'
    payload=public_payload(row)
    assert not {'gold','control_kind','id','hidden_answer'} & payload.keys()
    payload['profile']['mode']='mutated'
    assert row['payload']['profile']['mode']!='mutated'


@pytest.mark.parametrize('mutation',['duplicate','gold-leak','bad-positive-version','bad-span','missing-turn-policy'])
def test_invalid_calibration_is_rejected(mutation):
    p=packet();row=p['cases'][0]
    if mutation=='duplicate':p['cases'][1]['id']=row['id']
    if mutation=='gold-leak':row['payload']['gold']={}
    if mutation=='bad-positive-version':row['payload']['response']['citations'][0]['version']=2
    if mutation=='bad-span':row['gold']['support_spans'][0]['start']=1
    if mutation=='missing-turn-policy':row['payload']['profile']['current_turn_requirements']=[]
    with pytest.raises(ValueError):validate_packet(p)
