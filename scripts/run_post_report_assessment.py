"""Bounded source-assessment comparison; labels never enter provider requests."""
from __future__ import annotations
import argparse
import asyncio
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import resource
import sys
import tempfile
import time
from types import SimpleNamespace
import zipfile

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_final_profile_longitudinal import RecordedRunClient
from scripts.run_operational_dialogue_development import manifest as runtime_manifest
from services.llm import OpenAiResponsesClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student.model_assessment import SourceBoundModelAssessor
from src.digital_twin.student.source_assessment import assess_source_bound_attempt

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'research/05_evaluation/datasets/post-report-source-assessment-v1.json'
PLAN = ROOT / 'research/04_experiments/post-report-source-assessment-001.md'
PROGRAM = 'post-report-source-assessment-001'
LABELS = ('correct', 'incorrect', 'partial', 'not-assessed')


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def wilson(success, count):
    if not count:
        return None
    z = 1.959963984540054
    p = success / count
    midpoint = (p + z*z/(2*count))/(1+z*z/count)
    half = z*((p*(1-p)/count+z*z/(4*count*count))**.5)/(1+z*z/count)
    return [midpoint-half, midpoint+half]


def metrics(rows, arm):
    pairs = [(r['expected'], r[arm]['outcome']) for r in rows]
    confusion = {g: {p: sum(a == g and b == p for a,b in pairs) for p in LABELS} for g in LABELS}
    total = len(pairs); matches = sum(g == p for g,p in pairs)
    assessed = [(g,p) for g,p in pairs if p != 'not-assessed']
    positive = [(g,p) for g,p in pairs if p == 'correct']
    f1 = []
    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[g][label] for g in LABELS if g != label)
        fn = sum(confusion[label][p] for p in LABELS if p != label)
        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    return {'n':total, 'accuracy':matches/total if total else None,
        'accuracy_wilson_95':wilson(matches,total), 'macro_f1':sum(f1)/4,
        'confusion':confusion,'coverage':len(assessed)/total if total else None,
        'assessed_n':len(assessed),'assessed_accuracy':sum(g==p for g,p in assessed)/len(assessed) if assessed else None,
        'correct_predictions':len(positive),'correct_precision':sum(g=='correct' for g,p in positive)/len(positive) if positive else None,
        'correct_precision_wilson_95':wilson(sum(g=='correct' for g,p in positive),len(positive)),
        'false_correct':sum(g!='correct' and p=='correct' for g,p in pairs),
        'boundary_assessments':sum(r['boundary'] and r[arm]['outcome']!='not-assessed' for r in rows)}


def component_inputs(runtime, packet, case):
    domain = runtime.repository.get_course_domain_model(runtime.release_id).model_copy(deep=True)
    release = runtime.repository.get_release(runtime.release_id).model_copy(deep=True)
    targets = {s['concept_id']:s['target'] for s in packet['sources']}
    for c in domain.concepts:
        c.description = targets[c.concept_id]
    ids = [case['concept_id']]
    target = next(c for c in domain.concepts if c.concept_id == ids[0])
    source_id = target.canonical_ranges[0].source_artifact_id
    mutation = case['mutation']
    if mutation == 'foreign-release': release.id += '-foreign'
    elif mutation == 'foreign-course': release.course_id += '-foreign'
    elif mutation == 'ambiguous': ids.append(next(c.concept_id for c in domain.concepts if c.concept_id != ids[0]))
    elif mutation == 'permission':
        for c in release.chunks:
            if c.source_artifact_id == source_id: c.retrieval_allowed = False
    elif mutation == 'superseded':
        old = next(c for c in release.chunks if c.source_artifact_id == source_id)
        release.chunks.append(old.model_copy(update={'id':old.id+'-newer','source_version':old.source_version+1}))
    elif mutation == 'missing-range':
        for ref in target.canonical_ranges: ref.char_end = 1000000
    elif mutation == 'unsupported-target': target.description = 'Harbor guarantees every operation succeeds.'
    elif mutation != 'none': raise ValueError('unknown mutation')
    return ids, domain, release


async def run(output, *, model='luna', live=False, transport=None, assessment_version='v1'):
    if model not in {'luna','sol'}: raise ValueError('declared model required')
    if assessment_version not in {'v1','v2'}: raise ValueError('declared assessor version required')
    if live: require_bounded_pilot_operation_allowed(PROGRAM, 'external_model_evaluation')
    packet = json.loads(DATASET.read_text())
    if len(packet['cases']) != 32 or len({c['id'] for c in packet['cases']}) != 32:
        raise ValueError('frozen complete packet required')
    output = Path(output); output.mkdir(parents=True,exist_ok=False)
    identity = {key: value for key, value in runtime_manifest(days=2).items()
        if key in {"code_revision", "dirty", "harness_sha256"}}
    identity["instrument_id"] = PROGRAM
    identity["python_version"] = sys.version
    hashes = identity['harness_sha256']
    for p in (Path(__file__), DATASET, PLAN, ROOT/'tests/test_post_report_assessment_runner.py'):
        hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    with zipfile.ZipFile(output/'source-snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,digest in hashes.items():
            raw=(ROOT/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=digest: raise RuntimeError('source changed before archive')
            archive.writestr(name,raw)
    model_id = f'gpt-5.6-{model}'; effort='low' if model=='luna' else 'medium'
    config={'model':model_id,'reasoning_effort':effort,'output_cap':3000,'maximum_calls':32,'maximum_reservation_usd':6,'per_call_reservation_usd':.16,
        'assessor':'source-bound-model-assessment-'+assessment_version,'literal':'source-bound-literal-v1','seed':None,'repetitions':1}
    manifest={**identity,'run_configuration':config,'dataset_id':packet['dataset_id'],'network_mode':'live' if live else 'injected-contract',
        'invocation_argv':sys.argv,'dataset_sha256':hashlib.sha256(DATASET.read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        'source_archive_sha256':hashlib.sha256((output/'source-snapshot.zip').read_bytes()).hexdigest()}
    dump(output/'manifest.json',manifest); dump(output/'packet.json',packet)
    if transport is None:
        if not live: raise ValueError('explicit injected transport required')
        transport=OpenAiResponsesClient(model_id,max_output_tokens=3000,reasoning_effort=effort,timeout_seconds=30,experimental_sol_enabled=model=='sol')
    client=RecordedRunClient(transport,output/'provider.jsonl',maximum_calls=32,maximum_cost_usd=6,
        reservation_usd=.16,expected_model=model_id,max_output_tokens=3000,reasoning_effort=effort,experimental_sol_enabled=model=='sol',network_mode=manifest['network_mode'])
    assessor=SourceBoundModelAssessor(client,model_id=model_id,version=assessment_version); rows=[]; started=time.perf_counter(); error=None
    with tempfile.TemporaryDirectory(prefix='assessment-component-') as directory:
        cards=tuple(ConceptCardV1(concept_id=s['concept_id'],label=s['label'],description=s['text'],objective='Explain '+s['label']) for s in packet['sources'])
        factory=build_final_profile_runtime_factory(Path(directory),'t1-v2-reactive',concept_cards=cards,fixture_id=packet['dataset_id'])
        runtime=factory(SimpleNamespace(case_id='component'),VirtualUtcClock(datetime(2026,9,22,tzinfo=UTC)))
        try:
            for case in packet['cases']:
                began=time.perf_counter(); ids,domain,release=component_inputs(runtime,packet,case)
                literal=assess_source_bound_attempt(case['attempt'],ids,domain,release)
                result=await assessor.assess(case['attempt'],ids,domain,release)
                row={'id':case['id'],'kind':case['kind'],'boundary':case['id'].startswith('boundary-'),'expected':case['expected'],
                    'literal':asdict(literal),'model':asdict(result.assessment),'provider_called':result.provider_called,
                    'usage':result.usage.model_dump(mode='json'),'elapsed_ms':(time.perf_counter()-began)*1000}
                rows.append(row)
                with (output/'cases.jsonl').open('a') as stream: stream.write(json.dumps(row,sort_keys=True)+'\n')
                if result.usage.approximate_cost_usd is None or client.stopped:
                    error='unknown-cost-or-ledger-stop';break
        except Exception as caught:
            error=type(caught).__name__
            raise
        finally:
            runtime.close_runtime(runtime)
            aggregate={arm:metrics(rows,arm) for arm in ('literal','model')}
            slices={kind:{arm:metrics([r for r in rows if r['kind']==kind],arm) for arm in ('literal','model')} for kind in sorted({r['kind'] for r in rows})}
            usage=[r['usage'] for r in rows]; unknown=sum(u['approximate_cost_usd'] is None for u in usage)
            summary={'run_configuration':config,'completed_cases':len(rows),'planned_cases':32,'error':error,'metrics':aggregate,'slices':slices,
                'provider_calls':client.attempts,'unknown_cost_calls':unknown,'reported_cost_usd':sum(u['approximate_cost_usd'] or 0 for u in usage),
                'input_tokens':sum(u['input_tokens'] for u in usage),'output_tokens':sum(u['output_tokens'] for u in usage),
                'elapsed_seconds':time.perf_counter()-started,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
                'source_files_unchanged':all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in hashes.items()),
                'decision':'refine-no-promotion' if error or len(rows)!=32 or aggregate['model']['false_correct'] or aggregate['model']['boundary_assessments'] else 'go-deeper-no-promotion',
                'limitations':['Assistant-authored gold, no independent human validation.','Small synthetic component probe, no real learner benefit or mastery claim.','Latency includes component fixture processing, not an HTTP load benchmark.']}
            dump(output/'summary.json',summary)
    return summary


def main():
    require_bounded_pilot_operation_allowed(PROGRAM, 'external_model_evaluation')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=('luna','sol'),required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--assessment-version',choices=('v1','v2'),default='v1')
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=False)
    result=asyncio.run(run(args.output_dir,model=args.model,live=args.live,assessment_version=args.assessment_version))
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
