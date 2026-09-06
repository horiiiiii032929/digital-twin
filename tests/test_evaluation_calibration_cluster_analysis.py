import json

import pytest

from scripts.cross_course_quality_development import PACKET
from scripts.evaluation_calibration_cluster_analysis import calibration, cluster_interval, paired_quality


def test_constant_cluster_is_exact_and_nested_size_does_not_reweight():
    assert cluster_interval({'a':[1]*100,'b':[1]})['percentile_95_interval']==[1,1]
    result=cluster_interval({'a':[0]*100,'b':[1]},repeats=1000)
    assert result['equal_cluster_mean']==.5
    assert result['percentile_95_interval']==[0,1]


@pytest.mark.parametrize('values',[{}, {'a':[]}, {'a':[float('nan')]}, {'a':[float('inf')]}])
def test_invalid_clusters_rejected(values):
    with pytest.raises(ValueError):cluster_interval(values)


def _row(arm, passed):
    return {'arm':arm,'case_id':'a','public_input':{'course_id':'one'},'score':{'mechanical_source_containment_pass':passed}}


def test_paired_discordance_and_seeded_interval():
    rows=[_row('incumbent',False),_row('question-specific-profile-candidate',True)]
    result=paired_quality(rows)
    assert result['discordance']=={'both_pass':0,'candidate_only':1,'incumbent_only':0,'both_fail':0}
    assert result['course_cluster_bootstrap']['percentile_95_interval']==[1,1]
    assert paired_quality(rows)==result


@pytest.mark.parametrize('rows',[
    [_row('incumbent',False)],
    [_row('incumbent',False),_row('incumbent',True)],
    [_row('unknown',False)],
])
def test_invalid_pairing_rejected(rows):
    with pytest.raises(ValueError):paired_quality(rows)


def test_adversarial_scorer_blindspots_are_visible_not_silently_promoted():
    results={r['mutation']:r for r in calibration(json.loads(PACKET.read_text()))}
    assert len(results)==11
    for name in ['clean','unsupported-addition','contradiction-addition','duplicate-text','generic-question','irrelevant-question','paraphrased-solution']:
        assert results[name]['baseline']['mechanical_pass']
    for name in ['missing-requirement','wrong-version','malformed-citation','empty-text']:
        assert not results[name]['baseline']['mechanical_pass']
    assert not results['clean']['advisory']['needs_review']
    assert results['unsupported-addition']['advisory']['needs_review']
    assert results['contradiction-addition']['advisory']['needs_review']
    assert results['generic-question']['advisory']['needs_review']
    # Repeated exact prose escapes residue detection; neither oracle proves quality.
    assert not results['duplicate-text']['advisory']['needs_review']
