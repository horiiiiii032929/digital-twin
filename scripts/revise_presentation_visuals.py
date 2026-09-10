"""Turn the 42-slide reader revision into an evidence-led presentation."""
from pathlib import Path
import copy,json,re,subprocess,xml.etree.ElementTree as E
p=Path('reports/generated/slide-build/deck-content.json');data=json.loads(p.read_text())
assert len(data['slides'])==42, 'Run the three content preparation scripts first.'
a={s['number']:copy.deepcopy(s) for s in data['slides']}
for s in a.values():
 s.pop('gloss',None)
 s['notes']=s['notes'].split('\n\nTerminology')[0]

def panels(n,title,items,takeaway,intro=''):
 s=a[n];s.update(kind='panels',title=title,items=items,takeaway=takeaway,intro=intro)
def chart(n,title,charts,takeaway,intro):
 s=a[n];s.update(kind='charts',title=title,charts=charts,takeaway=takeaway,intro=intro)
def spec(title,cats,series,max_,fmt='0',detail=''):
 return dict(title=title,categories=cats,series=series,max=max_,format=fmt,detail=detail)
def series(name,values,color='#285E8E'):return dict(name=name,values=values,fill=color)

panels(2,'The twin continues course support between questions',[
 ['Professor','Publishes approved materials and teaching preferences.\nControls whether support can run.'],
 ['Student','Asks questions and submits attempts.\nCan permit or withdraw proactive contact.'],
 ['Software','Keeps observations and goals.\nStarts permitted follow-ups when work becomes due.']],
 'Research question: which designs make continuing support correct, controlled and useful?',
 'Demo: 2 professors, 2 courses, 4 synthetic students, 30 virtual days in 4:06.')
a[2]['notes']+='\n\n'+a[4]['notes']
a[2]['sources']+=a[4]['sources']
a[2]['foot']='“Digital twin” means a configured course assistant. Instructor fidelity remains unvalidated.'
a[5]['title']='After the student stops typing, scheduled support continues'
a[5]['foot']='Actual UI. Synthetic users and virtual time. Deterministic services. Edited 4:06 demo, separate from the evaluations.'
a[6]['title']='Publication binds approved content to a course release'
a[9]['title']='Persistent goals connect observations to scheduled work'
a[12]['title']='The complex factual paths shared an acceptance stage'
chart(13,'Both complex factual paths lost answer coverage',[
 spec('Fully grounded answers (%)',['Lexical control','Hierarchy','Plan–observe'],[series('Grounded answers',[52.66,24.81,24.81])],60,'0.00')],
 'Shared defect: the coverage check demanded question-framing words in the evidence.',
 'Round 1: 495 development cases, 350 chunks, no external model calls.')
a[13]['side']=[['100% / 36.46% / 36.20%','Answers when possible, in the same candidate order.'],['Design implication','Fix the shared answer requirement before adding more retrieval stages.']]
a[14].update(kind='example',title='A retrieved passage can still produce an incomplete answer',
 prompt='Question: “List all three stages.”',source='Source: “The stages are draft, review and publish.”',
 bad='“Draft and review.”',good='“Draft, review and publish.”',
 takeaway='The answer contract requires a set of three items. Finding the source alone cannot enforce completeness.')
chart(15,'Explicit required facts helped. Extra ranking added no gain.',[
 spec('Grounded answerable cases, out of 397',['Before targets','Typed targets','Targets + ranking'],[series('Cases',[253,355,355])],400)],
 'Retain explicit target type and required count. The extra ranking stage did not earn its cost.',
 'Study A: same development fold and answerable cases. Only the answer contract / ranking stage changes.')
a[15]['side']=[['253 to 355','102 additional grounded cases after typed targets.'],['1.36 to 2.79 ms','p95 latency with added ranking, with the same 355 grounded cases.']]
chart(16,'Fresh factual answers still missed the acceptance gates',[
 spec('Correct result (%)',['All evidence @3','Fully grounded','Boundary action'],[
 series('BM25 + dominance',[98,63.25,96]),series('Qwen3 hybrid + same gate',[92.88,62,95],'#91A4B7')],100,'0.00')],
 'Grounded-answer gate: 95%. Boundary-action gate: 98%. Neither candidate passed both.',
 'Study B: 1,000 fresh cases from disjoint sources. Metrics use their respective eligible case sets.')
a[16]['side']=[['98% evidence retrieval','All required evidence appears in the top three results for BM25.'],['63.25% grounded answers','The final answer must also be complete and contain only supported claims.']]
a[16]['foot']='Study B. Evidence retrieval and grounded answering are different checks, not successive counts in a funnel.'
chart(17,'Better visual retrieval did not improve grounded answers',[
 spec('Historical study: successes / 30',['Relevant visual','Grounded answer'],[series('Control',[18,20]),series('Visual candidate',[28,20],'#91A4B7')],30),
 spec('Fresh study: grounded answers / 30',['Control','Omni candidate'],[series('Grounded answers',[26,16])],30)],
 'Retain the controls. Retrieval gains did not establish an end-to-end answer improvement.',
 'Two separate 30-case datasets. Compare candidates within each study, not across the panels.')
a[18]['title']='A rejecting verifier could remove a usable action'
a[18]['rows'][1:]=[['A','Deterministic event rule','Keep as control'],['B','Model proposal','No justified replacement of A'],['C','Proposal + analytic lookahead','Mixed utility / label agreement'],['C + V','C + accepting/rejecting verifier','Rejected move has no fallback']]
a[18]['points']=['Failure mechanism: rejecting an action did not supply another useful action.']
a[18]['intro']='A / B / C / C + V are the local candidate labels. All share the same execution authority checks.'
a[19]['title']='Guarded replacement falls back to the deterministic action'
a[19]['foot']='H replaces A only for a valid, permitted proposal matching the analytic best action, with value gain ≥ 0.04.'
planner=copy.deepcopy(a[19]);planner.update(kind='panels',title='Guarded replacement gave a small simulated utility gain',
 intro='Study C: A and H evaluated on the same 1,000 contexts.',items=[
 ['Utility: 0.7954 / 0.8002','A / H means. The utility instrument scores simulated action value.'],
 ['Valid actions: 100% / 100%','Both obeyed the tested transition and permission rules.'],
 ['Preferred label: 74% / 73%','Agreement fell slightly despite the utility increase.']],
 takeaway='Conditional progression. An analytic-only ablation is still needed to isolate the model proposal’s contribution.',
 foot='Study C. Utility is a study-specific instrument, not a measured student learning effect.')
# Put the measured result narration next to its result, leaving the decision path on the preceding slide.
parts=a[19]['notes'].split('\n\n');a[19]['notes']='\n\n'.join(parts[:1]);planner['notes']='\n\n'.join(parts[1:])
panels(20,'Estimation and timing are separate experimental choices',[
 ['Learner estimator','Count: smoothed correct-attempt rate.\nBKT: Bayesian Knowledge Tracing, with learning, forgetting, guesses and slips.\nPFA: Performance Factors Analysis, using weighted successes and failures.'],
 ['Contact policy','Constant: send at eligible checks.\nConditional: require a stalled or low-and-uncertain state.\nValue: require sufficient estimated gain.']],
 'Cross 3 estimators with 3 timing policies. Add oracle and never-send bounds.',
 'All estimators consume assessed correctness and time. The contact policy decides whether to intervene.')
panels(22,'The learner study tests two different prediction targets',[
 ['Hidden-state error (MSE)','Compare the daily estimate with hidden simulator mastery.\nMean squared difference over concept-days. Lower is better.'],
 ['Next-answer error (Brier)','Compare the pre-attempt estimate with the observed correct / incorrect outcome.\nMean squared probability error. Lower is better.']],
 'Fit on separate development seeds. Test 240 learners per condition over 30 days and 8 concepts.',
 'Same learners and constraints across methods: 6 personas × 2 simulator families × 20 held-out seeds.')
a[22]['foot']='Study E. 1,000 paired learner bootstrap resamples. Consent, quiet hours, frequency cap and cooldown held fixed.'
chart(23,'BKT improved state estimates. Answer prediction was inconclusive.',[
 spec('Hidden-state MSE ↓',['Count','BKT'],[series('MSE',[.084,.035])],.1,'0.000','Paired change −0.050; 95% CI [−0.053, −0.047].'),
 spec('Next-answer Brier score ↓',['Count','BKT'],[series('Brier',[.259,.259])],.3,'0.000','Paired change ≈ 0; 95% CI [−0.006, 0.006].')],
 'A closer estimate of hidden simulator state did not establish better prediction of observed answers.',
 'Study E: hold constant timing fixed. Same 240 simulated learners. Both conditions send 14 messages per learner.')
a[23]['foot']='Values are rounded. Confidence intervals use paired learner differences. BKT remains experimental, outside the default planner adapter.'
oldnotes=a[23]['notes'];a[23]['notes']='The two panels hold timing fixed and compare count with BKT on the same simulated learners. '+oldnotes
# Keep timing separate so the estimator effect is not confounded with a policy change.
timing=copy.deepcopy(a[23]);timing.update(title='Conditional timing halved contact, with a mastery tradeoff',charts=[
 spec('Messages per learner',['Constant','Conditional','Value'],[series('Messages',[14,7,10.2])],16,'0.0'),
 spec('Hidden mastery on day 30',['Constant','Conditional','Value'],[series('Mastery',[.314,.302,.317])],.4,'0.000')],
 intro='Study E: hold the count estimator fixed and change only the contact policy.',
 takeaway='Less contact has a tradeoff: conditional timing reduced mastery by 0.012 (95% CI −0.018 to −0.005).',
 foot='Waste: 50.6% / 38.8% / 34.1%. Waste means contact at mastery ≥ 0.85 or while unreceptive. Simulator outcomes only.',
 notes='With the count estimator fixed, conditional timing cuts the mean number of messages from fourteen to seven. However, the mean final hidden mastery falls from zero point three one four to zero point three zero two. The paired interval excludes zero in this simulator. Value timing retains more contact and has lower waste. That result warns against treating fewer messages as an unqualified success. The complete crossed experiment and the BKT-plus-value result remain in backup. These policies have not established a real-course educational benefit.')
chart(27,'Exact-objective evidence removed unsupported completions',[
 spec('Completed goals, out of 72 histories per arm',['Control','Corrected'],[
 series('Supported',[14,15]),series('Unsupported',[12,0],'#B66B52')],30)],
 'Keep the completion correctness fix. The experiment did not establish improved learning.',
 'Study H: same 30-day history design. Completion now requires committed evidence for the exact target concept.')
a[27]['side']=[['12 to 0','Unsupported completions after correcting evidence scope.'],['56 additional messages','In the 36-history autonomous slice. Final simulated mastery changed by −0.0024.']]
a[27]['charts'][0]['stacked']=True
panels(30,'The integrated trial ran, but every check-in stayed generic',[
 ['484 turns, 654 model calls','643 calls completed. 11 reached the output cap.\n13 tutor turns ended in safe graph failure.'],
 ['16 proactive messages','10 synthetic replies. Every check-in used a source card with a generic wrapper.'],
 ['24 restarts, 48 consent changes','No messages during the consent-off window. The run did not demonstrate later resumption.']],
 'Operational execution is demonstrated. Useful personalized teaching remains unestablished.',
 'Historical Study G: 24 histories over 30 virtual days with external model calls. Separate from the new demo.')
panels(32,'The next comparison should change the planner’s input evidence',[
 ['Control','Delivery / event-count proxy.\nSending an action can raise the field called mastery.'],
 ['Candidate','Committed assessments for the goal’s target concepts.\nMissing and unrelated evidence remain explicit.']],
 'Hold planner, actions, retrieval and wording fixed. Compare identical snapshots, then complete histories.',
 'Proposed experiment: useful and missed support, authority violations, latency and cost.')
a[32]['foot']='Proposed design only. Predefine gates before the run. No candidate result is claimed.'
# Remove redundant roadmaps, move the worked BKT arithmetic into backup.
order=[1,2,3,5,6,7,8,9,10,12,13,14,15,16,17,18,19,'planner',20,22,23,'timing',24,25,26,27,28,29,30,31,32,33,34,21,35,36,37,38,39,40,41,42]
extra={'planner':planner,'timing':timing};slides=[extra[k] if isinstance(k,str) else a[k] for k in order]
# Re-export native draw.io pages without the duplicated document title, scope and footer.
# The notation and diagram content are unchanged. Scope is retained in slide notes.
out=Path('reports/presentation/diagrams/slides');out.mkdir(exist_ok=True)
for src in [Path('reports/presentation/diagrams/standard/sdlc-standard-diagrams.drawio'),Path('reports/presentation/diagrams/failures/failed-designs.drawio')]:
 tree=E.parse(src)
 for page in tree.getroot().findall('diagram'):
  root=page.find('mxGraphModel/root');removed=[]
  for cell in list(root):
   g=cell.find('mxGeometry')
   if g is not None and cell.get('vertex')=='1' and (cell.get('id') in ['n1','n2','n3'] or float(g.get('y','0'))>=942):
    if cell.get('value'):removed.append(cell.get('value'))
    root.remove(cell)
  stem=page.get('name')
  if stem=='11-guarded-replacement':
   root.find("mxCell[@id='n8']").set('value','Guards\npass?')
   root.find("mxCell[@id='n5']").set('value','Evidence\nallowed?')
  for cell in root.findall("mxCell[@edge='1']"):
   if cell.get('value','').startswith('scopeInvalidated'):
    cell.find("mxGeometry/mxPoint[@as='offset']").set('x','-110')
  doc=E.Element('mxfile',host='app.diagrams.net');doc.append(page)
  target=out/(stem+'.drawio');E.ElementTree(doc).write(target,encoding='utf-8',xml_declaration=True)
  subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--format','png','--scale','1.5','--border','8','--embed-diagram','--output',str(out/(stem+'.png')),str(target)],check=True,stdout=subprocess.DEVNULL)
  for s in slides:
   if s.get('kind')=='figure' and Path(s['image']).stem==stem:
    s['image']=str(out/(stem+'.png'));s['notes']+='\n\nDiagram scope and key: '+' '.join(removed)
    if 'inside the figure' in s.get('foot',''):s['foot']='Native draw.io source and full notation key are included in the presentation package.'
for s in slides:
 if s['kind']=='charts':
  s['notes']=s['notes'].replace('The table reports','The chart reports').replace('The table separates','The comparison separates')
 s['notes']=s['notes'].replace('The next table shows','The next chart shows')
q=next(i for i,s in enumerate(slides) if s['kind']=='questions')
for i,s in enumerate(slides,1):s['number']=i;s['backup']=i>q+1
words=sum(len(re.findall(r"\b[\w’'-]+\b",s['notes'].split('\n\nDiagram scope')[0])) for s in slides[:q])
data.update(slides=slides,main_slides=q,main_word_count=words);p.write_text(json.dumps(data,indent=2))
lines=['# Visual evidence presentation script','',f'{q} main slides, Questions, {len(slides)-q-1} backup slides. {words} narration words plus 4:06 video.','']
for s in slides:lines += [f"## {s['number']}. {s['title'].replace(chr(10),' ')}",'',s['notes'],'','Sources: '+', '.join(s['sources']),'']
Path('reports/presentation/speaker-script-visual.md').write_text('\n'.join(lines))
print(len(slides),'slides;',q,'main;',words,'narration words')
