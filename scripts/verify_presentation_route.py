"""Verify the user-selected presentation route with synthetic two-turn conversations."""
from __future__ import annotations

import json
from pathlib import Path
import time

from scripts.seed_aws_pilot import ROOT, SeedRun, private_json


def main():
    outputs = json.loads((ROOT / 'infra/cdk/cdk-outputs.json').read_text())['DigitalTwinPilot']
    run = SeedRun(ROOT / 'output/aws-pilot-seed/state.json', outputs)
    stamp = time.strftime('%Y%m%dT%H%M%S', time.gmtime())
    destination = ROOT / 'reports/generated/aws-presentation-route' / (stamp + '.json')
    evidence = {'run': stamp, 'url': run.url, 'runtime': {}, 'histories': []}
    try:
        for professor, student, course, prompts in [
            ('maya', 'alex', 'systems', [
                'Why can two members have the same team_id?',
                'So team_id can repeat because several members belong to the same team. Can you explain the join result for Ari and Bo?',
            ]),
            ('daniel', 'dina', 'security', [
                'Why is cookie authentication alone not a complete CSRF defense?',
                'So the browser attaching cookies does not prove I intended the request. How does checking Origin help in the course example?',
            ]),
        ]:
            cid = 'demo-pilot-v1-' + course
            owner = run.state['accounts']['demo-pilot-v1-professor-' + professor]
            pc = run.client()
            run.login(pc, owner['email'], owner['password'])
            identity = run.request(pc, 'GET', '/api/professor/courses/' + cid + '/runtime-status')['api']
            evidence['runtime'][cid] = identity
            if identity['experimental_version'] != 'v19-luna-luna-medium':
                raise RuntimeError('Observed route differs from presentation configuration')
            if identity['generator_implementation'] != 'question-specific-profile-grounded-v19':
                raise RuntimeError('Observed generator differs from audited presentation implementation')
            account = run.state['accounts']['demo-pilot-v1-student-' + student]
            client = run.client()
            run.login(client, account['email'], account['password'])
            conversation = run.request(client, 'POST', '/api/student/courses/' + cid + '/conversations')
            history = {'course_id':cid, 'conversation_id':conversation['id'], 'turns':[]}
            evidence['histories'].append(history)
            for index, prompt in enumerate(prompts):
                started = time.monotonic()
                turn = run.request(client, 'POST', '/api/student/conversations/' + conversation['id'] + '/messages',
                                   json={'content':prompt, 'request_id':f'presentation-route-{stamp}-{course}-{index}'})
                history['turns'].append({'prompt':prompt, 'elapsed_seconds':round(time.monotonic()-started,3), 'result':turn})
                private_json(destination,evidence)
                print(json.dumps({'course':course,'turn':index+1,'action':turn['tutor_message']['action'],
                                  'citations':len(turn['citations']),'elapsed_seconds':history['turns'][-1]['elapsed_seconds']}),flush=True)
            view = run.request(client, 'GET', '/api/student/conversations/' + conversation['id'])
            if len(view['messages']) != 4:
                raise RuntimeError('Two-turn conversation did not persist four messages')
        evidence['http_and_persistence']='passed'
    finally:
        private_json(destination,evidence)
        run.close()
        print('Synthetic evidence: '+str(destination),flush=True)


if __name__=='__main__':
    main()
