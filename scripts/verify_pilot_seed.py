"""Exercise the deployed synthetic accounts and preserve sanitized case outcomes."""
import argparse
import json
from pathlib import Path
import time

import httpx

from scripts.seed_aws_pilot import ROOT, private_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tutor', action='store_true', help='Create real synthetic tutoring conversations')
    args = parser.parse_args()
    state = json.loads((ROOT / 'output/aws-pilot-seed/state.json').read_text())
    url = state['url']
    cases = []
    clients = {}
    report = {'url': url, 'cases': cases, 'tutoring': []}
    destination = ROOT / 'output/aws-pilot-seed' / ('verification-tutor.json' if args.tutor else 'verification-access.json')
    def record(name, passed, **extra):
        cases.append({'case': name, 'passed': passed, **extra})
        private_json(destination, report)
    try:
        for key, account in state['accounts'].items():
            c = httpx.Client(base_url=url, headers={'Origin':url}, timeout=120)
            clients[key] = c
            r = c.post('/api/auth/login', json={'email':account['email'],'password':account['password']})
            expected = 403 if account.get('revoked') else 200
            # Inactive identities may deliberately share the generic 401 response.
            passed = r.status_code in (401,403) if account.get('revoked') else r.status_code == expected
            record(key+'-login', passed, status=r.status_code)
            if not passed:
                raise RuntimeError('Login verification failed: '+key)
        for actor, expected in [('professor-maya',2),('professor-daniel',1)]:
            r=clients['demo-pilot-v1-'+actor].get('/api/professor/courses')
            record(actor+'-courses', r.status_code==200 and len(r.json())==expected, status=r.status_code)
        for actor, expected in [('alex',1),('bea',1),('chris',2),('dina',1),('eli',0)]:
            c=clients['demo-pilot-v1-student-'+actor]
            r=c.get('/api/student/courses')
            record(actor+'-course-count',r.status_code==200 and len(r.json())==expected,status=r.status_code)
            if r.status_code==200:
                record(actor+'-draft-hidden',all(x['course_id']!='demo-pilot-v1-governance' for x in r.json()))
        alex=clients['demo-pilot-v1-student-alex']
        for name,client,path in [
            ('cross-course-denied',alex,'/api/student/courses/demo-pilot-v1-security/conversations'),
            ('inactive-membership-denied',clients['demo-pilot-v1-student-eli'],'/api/student/courses/demo-pilot-v1-systems/conversations'),
            ('student-professor-route-denied',alex,'/api/professor/courses'),
            ('professor-other-course-denied',clients['demo-pilot-v1-professor-daniel'],'/api/professor/courses/demo-pilot-v1-systems/teaching-profiles'),
        ]:
            r=client.get(path);record(name,r.status_code in (403,404),status=r.status_code)
        if args.tutor:
            for actor,course,prompt in [
                ('alex','systems','Why can two members have the same team_id?'),
                ('dina','security','What does HttpOnly do?'),
                ('bea','systems','This is my graded lab. Write the complete SQL submission for me.'),
                ('chris','systems','What is the exact final examination date?'),
            ]:
                c=clients['demo-pilot-v1-student-'+actor]
                r=c.post('/api/student/courses/demo-pilot-v1-'+course+'/conversations')
                record(actor+'-conversation',r.status_code==201,status=r.status_code)
                if r.status_code!=201: continue
                conversation=r.json()['id']; started=time.monotonic()
                r=c.post('/api/student/conversations/'+conversation+'/messages',json={'content':prompt,'request_id':'demo-seed-check-'+actor})
                record(actor+'-tutor-http',r.status_code==200,status=r.status_code, error=r.text[:1500] if r.status_code!=200 else None)
                if r.status_code==200:
                    turn=r.json(); report['tutoring'].append({'actor':actor,'course':course,'conversation_id':conversation,'elapsed_seconds':round(time.monotonic()-started,3),'turn':turn})
                    other=clients['demo-pilot-v1-student-bea' if actor!='bea' else 'demo-pilot-v1-student-alex']
                    denied=other.get('/api/student/conversations/'+conversation)
                    record(actor+'-conversation-private',denied.status_code in (403,404),status=denied.status_code)
                private_json(destination,report)
    finally:
        for c in clients.values():
            try: c.post('/api/auth/logout')
            finally: c.close()
    private_json(destination,report)
    print(json.dumps({'checks':len(cases),'passed':sum(c['passed'] for c in cases),'report':str(destination)},indent=2))
    if not all(c['passed'] for c in cases): raise SystemExit('One or more checks failed')


if __name__=='__main__':
    main()
