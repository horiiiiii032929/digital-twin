"""Add seven fictional roleplay accounts to the existing AWS demo without resetting it."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from scripts.seed_aws_pilot import ROOT, SeedRun, private_json, generate_demo_password
from src.digital_twin.evaluation.learner_simulator import PERSONAS, PERSONA_ROBUST_PERSONAS

PACK = ROOT / 'tests/fixtures/seed_data/seven-personas-v1/manifest.json'


def validate_pack():
    pack = json.loads(PACK.read_text())
    expected = {'typical-engaged', *(p.name for p in PERSONAS)}
    actual = [p['key'] for p in pack['personas']]
    if len(actual) != 7 or set(actual) != expected or not pack['synthetic']:
        raise ValueError('The seven-persona demo must use the explicit versioned selection')
    known = {p.name for p in (*PERSONAS, *PERSONA_ROBUST_PERSONAS)}
    if not set(actual) <= known or len({p['email'] for p in pack['personas']}) != 7:
        raise ValueError('Persona references or emails are invalid')
    if any(not p['email'].endswith('@example.test') or not p['opening'].strip() for p in pack['personas']):
        raise ValueError('Synthetic email and opening required')
    return pack


class PersonaSeed:
    def __init__(self, api: SeedRun, path: Path):
        self.api, self.path = api, path
        self.pack = validate_pack()
        digest = hashlib.sha256(PACK.read_bytes()).hexdigest()
        self.state = json.loads(path.read_text()) if path.exists() else {
            'seed_id':self.pack['seed_id'], 'manifest_sha256':digest, 'url':api.url, 'personas':{},
        }
        if self.state['manifest_sha256'] != digest or self.state['url'] != api.url:
            raise ValueError('Persona pack or destination changed; refuse overwrite')

    def save(self):
        private_json(self.path,self.state)

    def apply(self, admin, *, starters=True):
        owners = {}
        students = {}
        for cid, key in [('demo-pilot-v1-systems','demo-pilot-v1-professor-maya'),
                         ('demo-pilot-v1-security','demo-pilot-v1-professor-daniel')]:
            account=self.api.state['accounts'][key]
            c=self.api.client(); self.api.login(c,account['email'],account['password'])
            views=self.api.request(c,'GET','/api/professor/courses')
            course=next((v for v in views if v['course_id']==cid),None)
            expected_release=self.api.state['courses'][cid]['release_id']
            if course is None or not any(r['status']=='published' and r['id']==expected_release for r in course['releases']):
                raise RuntimeError('Expected published demo course missing')
            owners[cid]=c
        for persona in self.pack['personas']:
            key=persona['key']
            entry=self.state['personas'].setdefault(key,{'email':persona['email'],'password':generate_demo_password(),'memberships':[]})
            self.save()
            student=self.api.client()
            if 'account_id' not in entry:
                probe=student.post('/api/auth/login',json={'email':entry['email'],'password':entry['password']})
                if probe.status_code==200:
                    identity=probe.json()
                else:
                    identity=self.api.request(admin,'POST','/api/admin/accounts',json={
                        'email':entry['email'],'display_name':persona['display_name'],'role':'student','temporary_password':entry['password']})
                if identity['role']!='student': raise ValueError('Persona identity role mismatch')
                entry['account_id']=identity['account_id']; self.save()
            identity=self.api.login(student,entry['email'],entry['password'])
            students[key] = student
            if identity['account_id']!=entry['account_id'] or identity['role']!='student':
                raise ValueError('Persona login does not match the saved identity')
            for cid in self.pack['courses']:
                if cid not in entry['memberships']:
                    self.api.request(owners[cid],'POST','/api/professor/courses/'+cid+'/students',json={'student_account_id':entry['account_id']})
                    entry['memberships'].append(cid); self.save()
            visible=self.api.request(student,'GET','/api/student/courses')
            if {c['course_id'] for c in visible} != set(self.pack['courses']):
                raise RuntimeError('Persona course scope differs from expected demo courses')
            entry['access_verified']=True; self.save()
            if starters:
                if 'conversation_id' not in entry:
                    conv=self.api.request(student,'POST','/api/student/courses/'+self.pack['starter_course']+'/conversations')
                    entry['conversation_id']=conv['id']; self.save()
                base='/api/student/conversations/'+entry['conversation_id']
                if 'starter' not in entry:
                    began=time.monotonic()
                    # Stable request ID allows the API to recover a committed turn after an interrupted response.
                    turn=self.api.request(student,'POST',base+'/messages',json={'content':persona['opening'],'request_id':'seven-personas-v1-'+key})
                    entry['starter']={'elapsed_seconds':round(time.monotonic()-began,3),'turn':turn}; self.save()
                view=self.api.request(student,'GET',base)
                if not any(m.get('client_request_id')=='seven-personas-v1-'+key for m in view['messages']):
                    raise RuntimeError('Starter interaction did not persist')
                entry['message_count']=len(view['messages']); self.save()
            print(key+': login and courses verified'+('; starter saved' if starters else ''),flush=True)
        if starters:
            c=students[next(iter(self.state['personas']))]
            for entry in list(self.state['personas'].values())[1:]:
                result=c.get('/api/student/conversations/'+entry['conversation_id'])
                if result.status_code not in (403,404):
                    raise RuntimeError('Cross-persona conversation privacy failed')
            self.state['cross_persona_privacy']='passed'; self.save()

    def credential_sheet(self):
        lines=['# Seven persona demo accounts','',f'Application: {self.api.url}/student','',
               'These are fictional roleplay accounts. Use separate browser profiles or log out between roles.',
               'The existing office-hours schedule and temporary testing window still apply.','',
               '| Persona | Email | Password |','| --- | --- | --- |']
        for p in self.pack['personas']:
            a=self.state['personas'][p['key']]
            lines.append(f"| {p['label']} | {a['email']} | `{a['password']}` |")
        for p in self.pack['personas']:
            lines += ['', '## '+p['label'], '', p['purpose'], '', 'Continue with: '+p['suggested_followup']]
        destination=self.path.parent/'seven-persona-accounts.md'
        with os.fdopen(os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600),'w') as stream:
            stream.write('\n'.join(lines)+'\n')
        os.chmod(destination,0o600)
        return destination


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--apply',action='store_true')
    args=parser.parse_args(); pack=validate_pack()
    if not args.apply:
        print(json.dumps({'plan':pack['seed_id'],'accounts':len(pack['personas']),'memberships':14,'starter_turns':7})); return
    outputs=json.loads((ROOT/'infra/cdk/cdk-outputs.json').read_text())['DigitalTwinPilot']
    if outputs['AppUrlOutput']!='https://d3cccbyk2qjxd6.cloudfront.net': raise ValueError('Unexpected AWS pilot URL')
    directory=ROOT/'output/aws-pilot-seed'; directory.mkdir(parents=True,exist_ok=True,mode=0o700); os.chmod(directory,0o700)
    with (directory/'.persona-seed.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        api=SeedRun(directory/'state.json',outputs)
        seed=PersonaSeed(api,directory/'persona-state.json')
        try:
            raw=subprocess.run(['aws','secretsmanager','get-secret-value','--secret-id',outputs['RuntimeSecretArnOutput'],
                '--profile','digital-twin','--region','ap-southeast-1','--output','json'],capture_output=True,text=True,check=True)
            secret=json.loads(json.loads(raw.stdout)['SecretString']);admin=api.client()
            api.login(admin,secret['ADMIN_EMAIL'],secret['BOOTSTRAP_ADMIN_PASSWORD'])
            seed.apply(admin)
            print('Private persona logins: '+str(seed.credential_sheet()))
        finally: api.close()


if __name__=='__main__': main()
