"""Fresh-seed, network-free comparison; simulated gains are not learning evidence."""
from __future__ import annotations
import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
import zipfile
import numpy as np

from scripts.run_operational_dialogue_development import manifest as runtime_manifest
from src.digital_twin.evaluation.learner_simulator import LearnerSimulator, PERSONAS, PERSONA_ROBUST_PERSONAS, SimulatorFamily
from src.digital_twin.evaluation.successor_simulation import run_learner, _instant
from src.digital_twin.student.intervention_policies import build_policy
from src.digital_twin.student.learner_estimators import AssessedObservation, BktEstimator
from src.digital_twin.student.post_report_learning import learning_estimator
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

ROOT=Path(__file__).resolve().parents[1]
PROGRAM='post-report-learner-policy-001'
PLAN=ROOT/'research/04_experiments/post-report-learner-policy-001.md'
ESTIMATORS=('count','decay','bkt','pfa')
POLICIES=('constant','conditional','value','never')
SEEDS=tuple(range(7100,7120))
ALL_PERSONAS=(*PERSONAS,*PERSONA_ROBUST_PERSONAS)
CONDITIONS=tuple((e,p) for e in ESTIMATORS for p in POLICIES)+(('count','oracle'),)


def dump(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def make_estimator(name):return learning_estimator('assessed-'+name)
def append(path,row):
    with Path(path).open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n')


def open_loop(persona,family,seed, *, days=30):
    simulator=LearnerSimulator(persona=persona,family=family,seed=seed)
    estimators={name:make_estimator(name) for name in ESTIMATORS}
    states={name:e.initial_state() for name,e in estimators.items()}
    values={name:[] for name in estimators}; trace=[]
    for day in range(1,days+1):
        simulator.advance_one_day(); outcome=simulator.self_directed_activity()
        if outcome is None:continue
        now=_instant(day)+timedelta(hours=4); predictions={}
        for name,e in estimators.items():
            p=e.estimate(states[name],outcome.concept_id,now).probability
            # Convert latent mastery to observable-success space only for BKT.
            if isinstance(e,BktEstimator):p=e.p_guess+(1-e.p_guess-e.p_slip)*p
            predictions[name]=p;values[name].append((p-float(outcome.correct))**2)
            states[name]=e.update(states[name],AssessedObservation(outcome.concept_id,outcome.correct,now))
        trace.append({'day':day,'concept':outcome.concept_id,'correct':outcome.correct,'predictions':predictions})
    return {name:float(np.mean(v)) if v else None for name,v in values.items()},trace


def paired_interval(deltas):
    a=np.asarray(deltas,dtype=float)
    if not len(a):return None
    rng=np.random.default_rng(20260908)
    means=a[rng.integers(0,len(a),size=(1000,len(a)))].mean(axis=1)
    return {'mean_delta':float(a.mean()),'ci95':[float(x) for x in np.quantile(means,[.025,.975])], 'paired_histories':len(a)}


def summarize(rows):
    fields=('mse_vs_hidden','brier_next_outcome','log_loss_next_outcome','ece_next_outcome','messages_sent',
        'wasted_interventions','wasted_rate','prompted_attempts','follow_up_fraction','eligibility_violations','no_action_days','final_hidden_mastery','concepts_mastered_final')
    grouped=defaultdict(list)
    for r in rows:grouped[r['condition']].append(r)
    result={}
    for condition,group in grouped.items():
        result[condition]={'histories':len(group),**{f'mean_{k}':float(np.mean([r[k] for r in group if r[k] is not None]))
            if any(r[k] is not None for r in group) else None for k in fields},
            'eligibility_violations_total':sum(r['eligibility_violations'] for r in group)}
    return result


def run(output, *, seeds=SEEDS, personas=ALL_PERSONAS, days=30, engineering_test=False):
    if not engineering_test:
        require_bounded_pilot_operation_allowed(PROGRAM,'method_evaluation_execution')
        if tuple(seeds)!=SEEDS or tuple(personas)!=ALL_PERSONAS or days!=30:raise ValueError('full fixed grid required')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    base=runtime_manifest(days=max(2,days));hashes=base['harness_sha256']
    for p in (Path(__file__),PLAN,ROOT/'tests/test_post_report_learner_policy.py'):
        hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    with zipfile.ZipFile(output/'source-snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,digest in hashes.items():
            raw=(ROOT/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=digest:raise RuntimeError('source changed before archive')
            archive.writestr(name,raw)
    manifest={'instrument_id':PROGRAM,'code_revision':base['code_revision'],'dirty':base['dirty'],'python_version':sys.version,
        'numpy_version':np.__version__,'source_hashes_start':hashes,'source_archive_sha256':hashlib.sha256((output/'source-snapshot.zip').read_bytes()).hexdigest(),
        'days':days,'seeds':list(seeds),'personas':[asdict(p) for p in personas],'families':[f.value for f in SimulatorFamily],
        'conditions':CONDITIONS,'estimator_configuration':{name:vars(make_estimator(name)) for name in ESTIMATORS},
        'policy_configuration':{name:vars(build_policy(name)) for name in (*POLICIES,'oracle')},'external_calls':0,'external_cost_usd':0,
        'bootstrap_seed':20260908,'bootstrap_resamples':1000,'invocation_argv':sys.argv,'engineering_test':engineering_test}
    # TimingPolicy contains a dataclass config; serialize it as explicit values.
    for policy in manifest['policy_configuration'].values():
        for key,value in list(policy.items()):
            if hasattr(value,'__dataclass_fields__'):policy[key]=asdict(value)
            elif key == 'gate':policy[key]={'implementation':'EligibilityGate','configuration':asdict(value.config)}
    dump(output/'manifest.json',manifest)
    rows=[];forecast=[];started=time.perf_counter()
    for family in SimulatorFamily:
        for persona in personas:
            for seed in seeds:
                identity={'family':family.value,'persona':persona.name,'seed':seed}
                brier,trace=open_loop(persona,family,seed,days=days)
                forecast.append({**identity,'brier':brier,'observations':len(trace)})
                append(output/'open-loop-histories.jsonl',forecast[-1])
                for r in trace:append(output/'open-loop-observations.jsonl',{**identity,**r})
                for estimator,policy in CONDITIONS:
                    r=asdict(run_learner(persona=persona,family=family,seed=seed,estimator=make_estimator(estimator),
                        policy=build_policy(policy),estimator_id=estimator,days=days))
                    rows.append(r);append(output/'histories.jsonl',r)
            print('completed',family.value,persona.name,flush=True)
    key=lambda r:(r['family'],r['persona'],r['seed'])
    control={key(r):r for r in rows if r['condition']=='count+conditional'}
    policy_deltas={}
    for condition in sorted({r['condition'] for r in rows}):
        group=[r for r in rows if r['condition']==condition]
        policy_deltas[condition]={metric:paired_interval([r[metric]-control[key(r)][metric] for r in group])
            for metric in ('final_hidden_mastery','wasted_interventions','messages_sent')}
    forecast_deltas={name:paired_interval([r['brier'][name]-r['brier']['count'] for r in forecast
        if r['brier'][name] is not None and r['brier']['count'] is not None]) for name in ESTIMATORS}
    slices={}
    for column in ('family','persona'):
        slices[column]={v:summarize([r for r in rows if r[column]==v]) for v in sorted({r[column] for r in rows})}
    summary={'history_count':len(rows),'histories_per_condition':len(forecast),'conditions':summarize(rows),'slices':slices,
        'paired_policy_deltas_vs_count_conditional':policy_deltas,'open_loop_observation_brier':{name:float(np.mean([r['brier'][name] for r in forecast if r['brier'][name] is not None]))
            if any(r['brier'][name] is not None for r in forecast) else None for name in ESTIMATORS},
        'open_loop_aggregation':'Equal-weight history means; histories without observations remain recorded with undefined loss excluded from mean.',
        'open_loop_paired_brier_deltas_vs_count':forecast_deltas,'open_loop_observation_count':sum(r['observations'] for r in forecast),
        'external_calls':0,'external_cost_usd':0,'elapsed_seconds':time.perf_counter()-started,
        'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
        'source_files_unchanged':all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in hashes.items()),
        'eligibility_violations':sum(r['eligibility_violations'] for r in rows),
        'decision':'go-deeper-no-promotion','limitations':['Synthetic hidden state is not observed real mastery.','Component timing policies differ from the application planner.','No human learning outcome measured.','Raw closed-loop BKT score is not an observation-space probability; primary estimator comparison is separate open-loop Brier.']}
    dump(output/'summary.json',summary)
    return summary


def main():
    require_bounded_pilot_operation_allowed(PROGRAM, 'method_evaluation_execution')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args()
    result=run(args.output_dir);print(json.dumps({k:result[k] for k in ('history_count','elapsed_seconds','eligibility_violations','open_loop_observation_brier')},sort_keys=True))
if __name__=='__main__':main()
