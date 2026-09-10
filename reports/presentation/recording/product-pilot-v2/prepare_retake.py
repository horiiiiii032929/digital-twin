import sqlite3,json,httpx
from pathlib import Path
root=Path('output/playwright/product-pilot-v2');setup=json.load(open(root/'setup.json'))['courses'][0]
with sqlite3.connect(root/'runtime/recording.sqlite3') as db: profile=db.execute("select teaching_profile_id from releases where id='recording-0-v1'").fetchone()[0]
body="CPU A and CPU B cache x = 0. CPU A writes x = 1. Cache coherence invalidates or updates CPU B's stale copy. CPU B must read x = 1 next, not its old cached value of 0."
(root/'sources/cache-lab.md').write_text(body)
with httpx.Client(base_url='http://127.0.0.1:8026',trust_env=False,timeout=60) as c:
 h={'X-Account-ID':'professor-synthetic'}
 def call(method,path,**kw):
  r=c.request(method,path,headers={**h,**kw.pop('headers',{})},**kw);r.raise_for_status();return r.json()
 ing=call('PUT','/api/professor/courses/course-a-recording/sources/cache-lab',params={'title':'Two-CPU cache coherence lab','display_allowed':True},headers={'Content-Type':'text/markdown'},content=body.encode());print([x['text'] for x in ing['chunks']]);assert len(ing['chunks'])==1
 release=call('POST','/api/professor/courses/course-a-recording/releases',json={'session_id':setup['session_id'],'profile_id':'student-tutor','profile_version':'v1','teaching_profile_id':profile,'release_id':'recording-a-v3','chunks':ing['chunks']})
 assert call('POST','/api/professor/releases/recording-a-v3/preflight')['passed'];call('POST','/api/professor/releases/recording-a-v3/publish')
 chunk=ing['chunks'][0]
 payload={'release_id':'recording-a-v3','version':3,'objectives':[{'objective_id':'cache-review','statement':'Explain why CPU B must not read its stale cached value after CPU A writes.','concept_ids':['cache-example']}],'concepts':[{'concept_id':'cache-example','label':'Two-CPU cache coherence','description':chunk['text'],'canonical_ranges':[{'source_artifact_id':chunk['source_artifact_id'],'source_version':chunk['source_version'],'source_sha256':chunk.get('source_checksum') or chunk['content_hash'],'locator':chunk['locator'],'char_start':0,'char_end':len(chunk['text'])}]}]}
 call('POST','/api/professor/courses/course-a-recording/domain-model',json=payload)
 call('POST','/api/professor/courses/course-a-recording/students',json={'student_account_id':'student-b-synthetic'})
 for who,enabled in [('student-a-synthetic',False),('student-a2-recording',False),('student-b-synthetic',True)]:
  call('PUT','/api/student/courses/course-a-recording/outreach-preferences/in-app',headers={'X-Account-ID':who},json={'enabled':enabled,'timezone':'UTC','quiet_hours_start':'22:00','quiet_hours_end':'08:00','max_messages_per_7_days':3})
 (root/'release-v3.json').write_text(json.dumps(release,indent=2))
