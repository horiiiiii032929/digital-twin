"""Finite model-only review of frozen synthetic outputs; never human validation."""
from __future__ import annotations
import argparse
import asyncio
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import subprocess
import time
import zipfile
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv
from scripts.run_completion_semantic_review import AdvisoryClient, RATING, SYSTEM_V2, TASK, calibration_v2_inputs, matches_control, validate_review
from scripts.run_final_profile_longitudinal import RecordedRunClient
from src.digital_twin.llm import LlmMessage
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = 'post-report-blind-review-001'
PLAN = ROOT/'research/04_experiments/post-report-blind-review-001.md'
MODELS = {'nano':'gpt-5.4-nano-2026-03-17','mini':'gpt-5.4-mini-2026-03-17'}
RUNS = ['post-report-paired-quality-001-live-001','post-report-paired-quality-003-live-001'] + [f'post-report-audited-generation-{series}-case-{i:02d}-live-001' for series in ('004','005') for i in range(1,6)]
SYSTEM = SYSTEM_V2 + '\nProduct citations reference a complete supplied source chunk by identifier, version, checksum and locator; they do not require quote offsets. Calibration citations with offsets must match those offsets. Judge the response as delivered, including withheld responses. Do not treat abstention as a sufficient answer to a supported question.\n'

# Version 1 remains reproducible; version 2 changes evidence representation only.
SYSTEM_002 = SYSTEM + """
Evidence contract version 002: return evidence items with a JSON pointer into the
input payload and an exact excerpt of the string at that location. For example,
/response/text for tutor prose, /sources/0/text for approved evidence, or
/response/citations/0/source_id for a citation's identifier. Never put source
text or citation metadata under /response/text. Numeric or absent fields may be
explained in reason without an evidence item. Missing-content defects may use an
empty evidence list. Only cite supplied data; do not invent pointer values.
There are two supported citation representations. An offset citation is checked
against its supplied source text, version and offsets; do not demand a checksum
or locator if the input uses offsets. A whole-chunk citation is checked against
its supplied identifier, version, checksum and locator. Judge actual mismatches.
Ensure overall is defective when any core axis is defective; acceptable requires
adequate relevance, completeness and profile adherence, and no uncertain axes.
"""

class LocatedEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pointer: str = Field(min_length=1, max_length=240)
    excerpt: str = Field(min_length=1, max_length=1200)

class LocatedReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    grounding: RATING
    relevance: RATING
    completeness: RATING
    profile_adherence: RATING
    citation_validity: RATING
    usefulness: Literal['useful', 'weak', 'uncertain']
    overall: Literal['acceptable', 'defective', 'uncertain']
    reason: str = Field(min_length=1, max_length=1000)
    evidence: list[LocatedEvidence] = Field(max_length=5)

class LocatedAdvisoryClient(AdvisoryClient):
    @staticmethod
    def _output_type(task):
        if task != TASK:
            raise ValueError('evaluation-only task required')
        return LocatedReview


def validate_located_review(content, payload, *, allow_scalars=False):
    review = LocatedReview.model_validate_json(content).model_dump()
    for item in review['evidence']:
        pointer = item['pointer']
        if not pointer.startswith('/'):
            raise ValueError('absolute JSON pointer required')
        node = payload
        try:
            for part in pointer[1:].split('/'):
                part = part.replace('~1', '/').replace('~0', '~')
                if isinstance(node, list):
                    if not part.isdecimal() or str(int(part)) != part:
                        raise ValueError('canonical array index required')
                    node = node[int(part)]
                elif isinstance(node, dict):
                    node = node[part]
                else:
                    raise ValueError('pointer traverses scalar')
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError('evidence pointer absent') from error
        valid = isinstance(node, str) and item['excerpt'] in node
        if allow_scalars and (node is None or isinstance(node, (bool, int, float))):
            valid = item['excerpt'] == json.dumps(node, allow_nan=False)
        if not valid:
            raise ValueError('evidence excerpt absent from pointed string or exact scalar')
    # Reuse all original semantic consistency checks; do not silently repair labels.
    semantic = {k:v for k,v in review.items() if k != 'evidence'}
    validate_review(json.dumps({**semantic, 'response_excerpts': []}), payload)
    return review

def dump(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def product_inputs(run_ids=None, expected_count=152):
    rows=[]; paths=set()
    for run_id in (RUNS if run_ids is None else run_ids):
        root=ROOT/'reports/generated'/run_id
        packet_path=root/'packet.json'; paths.add(packet_path)
        packet=json.loads(packet_path.read_text())
        contexts={c['id']:c for c in packet['contexts']}
        history_file=root/'histories.jsonl'; paths.add(history_file)
        for history in map(json.loads,history_file.read_text().splitlines()):
            context=contexts[history['case_id']]
            folder=root/history['id']; turns_file=folder/'turns.jsonl'; paths.add(turns_file)
            databases=list((folder/'runtime').rglob('runtime.sqlite3'))
            if len(databases)!=1: raise ValueError('Expected one frozen runtime database')
            database=databases[0]; paths.add(database)
            with sqlite3.connect(f'file:{database.resolve()}?mode=ro',uri=True) as conn:
                releases=conn.execute("SELECT id,teaching_profile_id FROM releases WHERE course_id='course-a-synthetic' AND status='published'").fetchall()
                if len(releases)!=1: raise ValueError('Ambiguous release')
                release_id,profile_id=releases[0]
                profile=json.loads(conn.execute('SELECT profile_json FROM teaching_profiles WHERE profile_id=?',(profile_id,)).fetchone()[0])
                chunks=[json.loads(r[0]) for r in conn.execute('SELECT chunk_json FROM release_chunks WHERE release_id=? ORDER BY chunk_id',(release_id,))]
            public_profile=context['public']['profile_values']
            if any(profile.get(k)!=v for k,v in public_profile.items()): raise ValueError('Frozen profile mismatch')
            sources=[]; mapping={}
            for index,c in enumerate(chunks):
                artifact=c['source_artifact_id']; label=f'S{index+1}'
                mapping[artifact]=label
                sources.append({'source_id':label,'version':c['source_version'],'checksum':c.get('source_checksum') or c['content_hash'],'locator':c['locator'],'title':c['document_id'],'text':c['text']})
            previous=[]
            turns=list(map(json.loads,turns_file.read_text().splitlines()))
            if len(turns)!=history['planned_turns']: raise ValueError('Missing delivered turn; do not silently omit')
            for t in turns:
                tutor=t['turn']['tutor_message']
                citations=[{'source_id':mapping.get(c['source_artifact_id'],'UNKNOWN-SOURCE'), 'version':c.get('source_version'), 'checksum':c.get('source_checksum'), 'locator':c.get('locator')} for c in t['turn']['citations']]
                payload={'question':t['student'],'profile':public_profile,'history':list(previous),'sources':sources,
                    'response':{'text':tutor['content'],'action':tutor['action'],'citations':citations}}
                rows.append({'id':f'output-{len(rows):03d}','run_id':run_id,'case_id':history['case_id'],'arm':history['version'],'stage':t['stage'],'payload':payload})
                previous.extend([{'role':'user','content':t['student']},{'role':'assistant','content':tutor['content']}])
    if len(rows)!=expected_count: raise ValueError(f'Expected complete {expected_count} outputs, received {len(rows)}')
    return rows,paths

def calibration_gate(rows):
    return len(rows)==64 and all(r.get('status')=='completed' and r.get('calibration_match') is True for r in rows)

def summarize(rows):
    controls=[r for r in rows if r['phase']=='calibration']; products=[r for r in rows if r['phase']=='product']
    slices={}
    for r in products:
        key=r['run_id']+'/'+r['arm']
        slices.setdefault(key,Counter())[r.get('review',{}).get('overall',r['status'])]+=1
    repeated={}
    for r in products: repeated.setdefault(r['id'],[]).append(r.get('review',{}).get('overall',r['status']))
    return {'calibration_passed':calibration_gate(controls),'calibration_matched':sum(r.get('calibration_match') is True for r in controls),
        'calibration_cases':len(controls),'product_ratings':len(products),'by_run_and_arm':{k:dict(v) for k,v in slices.items()},
        'product_repeat_agreement':{'agree':sum(len(v)==2 and v[0]==v[1] and v[0] in ('acceptable','defective','uncertain') for v in repeated.values()),'outputs':len(repeated)},
        'quality_qualified':False,'human_review':False,'decision':'Keep model diagnostic only' if calibration_gate(controls) else 'Refine judge; product ratings diagnostic only, no quality gate or promotion'}

async def run(output,model,*,live=False,transport=None,version=1,calibration_only=False,product_run_ids=None,expected_count=152):
    require_bounded_pilot_operation_allowed(PROGRAM,'external_model_evaluation' if live else 'method_evaluation_execution')
    if version not in (1, 2, 3): raise ValueError('unsupported review version')
    products,paths=([],set()) if calibration_only else product_inputs(product_run_ids,expected_count)
    controls=calibration_v2_inputs()
    system=SYSTEM if version==1 else SYSTEM_002
    if version==3:
        system += '\nEvidence contract 003: numeric, boolean and null fields may also be cited using their exact JSON spelling as excerpt (for example 999). Never cite arrays/objects. Return at most FIVE evidence items; select the most relevant ones.\n' 
    validator=validate_review if version==1 else lambda content,payload: validate_located_review(content,payload,allow_scalars=version==3)
    serializer_type=AdvisoryClient if version==1 else LocatedAdvisoryClient
    maximum_calls=64+2*len(products)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    model_id=MODELS[model]; reservation=.015 if model=='nano' else .03; maximum=maximum_calls*reservation
    serializer=serializer_type(model_id,max_output_tokens=1800,reasoning_effort='low',timeout_seconds=60)
    if transport is None and not live: raise ValueError('Explicit injected transport required')
    client=RecordedRunClient(transport or serializer,output/'provider.jsonl',maximum_calls=maximum_calls,maximum_cost_usd=maximum,
        reservation_usd=reservation,expected_model=model_id,max_output_tokens=1800,reasoning_effort='low',
        serializer_client=serializer,network_mode='live' if live else 'injected-contract')
    paths.update({Path(__file__).resolve(),PLAN,ROOT/'scripts/run_completion_semantic_review.py',ROOT/'scripts/semantic_calibration_v2.py',ROOT/'scripts/run_final_profile_longitudinal.py',ROOT/'services/llm/openai_responses_client.py',ROOT/'src/digital_twin/model_policy.py',ROOT/'research/05_evaluation/datasets/completion-semantic-calibration-v2.json'})
    if version>=2: paths.add(ROOT/'research/04_experiments/post-report-final-selection-002.md')
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
    with zipfile.ZipFile(output/'source-snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,digest in hashes.items():
            raw=(ROOT/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=digest: raise RuntimeError('source drift')
            archive.writestr(name,raw)
    manifest={'program_id':PROGRAM,'model':model_id,'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)),'source_hashes':hashes,'source_archive_sha256':sha(output/'source-snapshot.zip'),
        'instrument_version':version,'calibration_only':calibration_only,'maximum_calls':maximum_calls,'maximum_reservation_usd':maximum,'reasoning':'low','output_cap':1800,'concurrency':4,'retries':0,
        'system_prompt':system,'started_at':datetime.now(UTC).isoformat(),'network':'live' if live else 'injected-contract'}
    dump(output/'manifest.json',manifest);dump(output/'frozen-inputs.json',{'controls':controls,'products':products})
    results=[]; semaphore=asyncio.Semaphore(4);started=time.perf_counter()
    async def one(row,phase,repetition):
        async with semaphore:
            record={k:v for k,v in row.items() if k!='payload'};record.update(phase=phase,repetition=repetition)
            if client.stopped: record.update(status='not-executed')
            else:
                try:
                    answer=await client.chat([LlmMessage(role='system',content=system),LlmMessage(role='user',content=json.dumps(row['payload'],sort_keys=True))],TASK)
                    record.update(status='completed',review=validator(answer.content,row['payload']))
                except Exception as error: record.update(status='failed',error_type=type(error).__name__,error=str(error)[:250])
            if phase=='calibration': record['calibration_match']=matches_control(row,record.get('review',{}))
            results.append(record)
            with (output/'judgments.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
    try:
        await asyncio.gather(*(one(r,'calibration',r['repetition']) for r in controls))
        # An unsuccessful calibration does not become a pass by voting. Product
        # ratings remain explicitly diagnostic, but both arms still get equal review.
        for repetition,seed in enumerate((202609081,202609082)):
            ordered=list(products);random.Random(seed).shuffle(ordered)
            await asyncio.gather(*(one(r,'product',repetition) for r in ordered))
    finally:
        summary=summarize(results);summary.update(manifest=manifest,provider_calls=client.attempts,
            reported_cost_usd=sum((r.get('usage') or {}).get('approximate_cost_usd') or 0 for r in client.records),
            unknown_cost_calls=sum((r.get('usage') or {}).get('approximate_cost_usd') is None for r in client.records),
            stopped=client.stopped,elapsed_seconds=time.perf_counter()-started,
            source_unchanged=all(sha(ROOT/n)==d for n,d in hashes.items()))
        if client.stopped or not summary['source_unchanged']:summary['decision']='Incomplete or source drift; no promotion'
        dump(output/'summary.json',summary)
    return summary

def main():
    require_bounded_pilot_operation_allowed(PROGRAM, 'external_model_evaluation')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');parser.add_argument('--model',choices=MODELS,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--version',type=int,choices=(1,2,3),default=1)
    parser.add_argument('--calibration-only',action='store_true')
    parser.add_argument('--product-run-ids',nargs='+')
    parser.add_argument('--expected-count',type=int,default=152)
    args=parser.parse_args()
    if not args.execute:parser.error('--execute required')
    load_dotenv(ROOT/'.env',override=False)
    result=asyncio.run(run(args.output_dir,args.model,live=True,version=args.version,calibration_only=args.calibration_only,product_run_ids=args.product_run_ids,expected_count=args.expected_count))
    print(json.dumps({k:v for k,v in result.items() if k!='manifest'},indent=2))
if __name__=='__main__':main()
