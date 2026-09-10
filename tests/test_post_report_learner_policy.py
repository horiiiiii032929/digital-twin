import json
import pytest
from scripts.run_post_report_learner_policy import run, open_loop, paired_interval, PERSONAS, SimulatorFamily


def test_open_loop_shares_one_observation_sequence_and_reproduces():
    a=open_loop(PERSONAS[0],SimulatorFamily.BKT_LIKE,7100)
    b=open_loop(PERSONAS[0],SimulatorFamily.BKT_LIKE,7100)
    assert a==b and a[1]
    assert all(set(row['predictions'])=={'count','decay','bkt','pfa'} for row in a[1])
    assert all(0<=p<=1 for row in a[1] for p in row['predictions'].values())


def test_small_contract_grid_retains_controls_and_accounts_for_every_history(tmp_path):
    s=run(tmp_path/'run',seeds=(7100,),personas=(PERSONAS[0],),days=3,engineering_test=True)
    assert s['history_count']==34 and s['histories_per_condition']==2
    assert s['eligibility_violations']==0 and s['external_calls']==0
    assert s['source_files_unchanged']
    rows=[json.loads(x) for x in (tmp_path/'run/histories.jsonl').read_text().splitlines()]
    never=[r for r in rows if r['policy']=='never']
    assert len(never)==8 and all(r['messages_sent']==0 for r in never)
    for family in SimulatorFamily:
        assert len({r['final_hidden_mastery'] for r in never if r['family']==family.value})==1
    assert paired_interval([0,0])['ci95']==[0,0]


def test_named_run_cannot_reduce_the_frozen_grid(tmp_path):
    with pytest.raises(ValueError):run(tmp_path/'run',seeds=(7100,))
