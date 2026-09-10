"""Apply the graduate CS review to the visual evidence revision."""
from pathlib import Path
import copy,json,re,subprocess,xml.etree.ElementTree as E
from scripts.build_standard_sdlc_diagrams import Diagram
p=Path('reports/generated/slide-build/deck-content.json');data=json.loads(p.read_text())
assert len(data['slides'])==42 and data['slides'][17]['kind']=='panels'
a={s['number']:copy.deepcopy(s) for s in data['slides']}
refs={
'C':'research/05_evaluation/records/successor-architecture-confirmation-005-001.json',
'E':'research/05_evaluation/successor-learner-timing-simulation-001-results.md',
'B':'research/05_evaluation/final-cross-method-factual-confirmation-001-results.md',
'H':'research/05_evaluation/goal-completion-scope-development-001-results.md',
'math':'research/06_reports/final/chapters/planner-math.tex'}
def panel(title,intro,items,takeaway,notes,sources,foot=''):
 return dict(kind='panels',title=title,intro=intro,items=items,takeaway=takeaway,notes=notes,sources=sources,foot=foot)
contribution=panel('The contribution is an evaluated system and its design lessons',
 'Research question: which component choices support correct, controlled continuing course support?',[
 ['Implemented system','Persistent course support with approved sources, explicit goals and instructor / student controls.'],
 ['Compared designs','Evidence selection, action planning and learner timing under each study’s stated controls.'],
 ['Empirical lessons','Required-fact contracts, useful fallbacks and exact-objective evidence affected the tested outcomes.']],
 'Contribution: inspectable implementation and bounded design evidence. Instructor fidelity and real learning remain open.',
 'There are two kinds of contribution here. The deliverable is an inspectable course-support prototype that retains state and schedules permitted work between questions. The research contribution is the evidence from explicit design comparisons, including unsuccessful candidates. The comparisons show why particular evidence contracts, fallback compositions and objective boundaries mattered in this implementation. I am not claiming to invent Bayesian Knowledge Tracing or retrieval. I am also not claiming that every complex design is inferior. The general lesson is a hypothesis informed by these bounded results: before adding another decision stage, check what evidence crosses the existing interfaces and what happens when a stage rejects it. The rest of the presentation follows those interfaces, then returns to the integrated system.',
 a[32]['sources'])
a[2]['notes']+='\n\nDuring the video, please watch the first follow-up after the student stops typing, and then what happens when the professor pauses support or a student withdraws consent. [Pause before playback.]'
# Replace the container view in the main talk with a focused standard UML component view.
container=copy.deepcopy(a[7]);container['title']='Deployment context: logical containers'
d=Diagram('15-experimental-boundaries','Experimental boundaries','Logical dependency view; not a deployment or sequence diagram')
service=d.node(40,180,1520,125,'«component»\nTutoring and autonomy services: authority checks, orchestration and durable state','shape=component;',30)
labels=[('Evidence selector','Required facts and evidence scope','Studies A / B'),('Planner-input adapter','Delivery / event proxy in runtime','Integration gap'),('Action planner','A / B / C / H decision strategies','Study C'),('Wording generator','Draft generation and revision','Study F')]
for i,(name,body,study) in enumerate(labels):
 x=40+i*390
 ident=d.node(x,470,350,190,'«component»\n'+name+'\n'+body,'shape=component;',28)
 d.line((x+175,305),(x+175,470),'uses','dashed=1;endArrow=open;',source=service,target=ident)
 d.text(x,680,350,45,study,25,True)
d.note(40,780,1520,105,'Study E tests learner estimators and timing outside the tutoring service. Its BKT candidate is not the default planner-input adapter.',28)
# Export a title-free slide image and retain editable standard notation.
for ident in ['n1','n2','n3']:
 c=d.r.find(f"mxCell[@id='{ident}']");d.r.remove(c)
d.bind();root=E.Element('mxfile',host='app.diagrams.net');root.append(d.d)
out=Path('reports/presentation/diagrams/slides');src=out/'15-experimental-boundaries.drawio'
E.ElementTree(root).write(src,encoding='utf-8',xml_declaration=True)
subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--format','png','--scale','1.5','--border','8','--embed-diagram','--output',str(src.with_suffix('.png')),str(src)],check=True,stdout=subprocess.DEVNULL)
a[7].update(title='Experiments change components inside shared runtime controls',image=str(src.with_suffix('.png')),foot='UML component dependencies. Each study has its own dataset and comparison scope. Logical container view is in backup.')
a[7]['notes']='This component view locates the experimental boundaries. The tutoring and autonomy services share authority checks and persistent state. Factual studies change evidence selection and the required-answer contract. Planner studies change the action-selection strategy. Wording studies change generation or revision. The planner-input adapter is a separate integration boundary: the current default supplies a delivery and event proxy. Study E evaluates learner estimators and timing outside the tutoring service, so it must not be read as evidence that BKT already operates inside this application. These studies do not form a single controlled ranking of complete systems. [Pause and point to the adapter before moving on.]'
a[7]['sources']+=['src/digital_twin/student/planning_architectures.py','src/digital_twin/student/learner_estimators.py','src/digital_twin/generation/generator.py']
# Clarify the factual instrument and its denominators without adding another main slide.
a[14]['intro']='Study B: fresh sources, 800 answerable cases and 200 boundary cases. Answerable metrics use n = 800.'
a[14]['side']=[['506 / 800 grounded','63.25%; source-family bootstrap 95% CI: 58.75%–67.63%.'],['192 / 200 boundaries','96% choose the required boundary action. Malformed questions also limit the instrument.']]
a[14]['foot']='Grounded = complete required claims supported by evidence. Mechanically generated questions and rigid target matching affect this benchmark.'
a[14]['notes']+='\n\nThe denominator is eight hundred for the answerable metrics and two hundred for boundary actions. The BM25 grounded score is five hundred and six out of eight hundred, with a source-family bootstrap interval from fifty-eight point seven five to sixty-seven point six three percent. Some mechanically generated questions are malformed. For example, the recorded analysis describes a question asking for the source point about two, whose expected answer is a raw table row. That limits the benchmark’s realism. We preserve the case and do not tune on these held-out results. The small difference between BM25 and hybrid is not a claim of general superiority.'
a[14]['sources']+=[refs['B'],'research/05_evaluation/records/final-cross-method-factual-confirmation-001-analysis-correction-001.json']
# Use four short rows rather than cramming another metric into narrow panels.
a[18].update(kind='results',title='Guarded replacement produced a small synthetic utility gain',
 intro='Study C: same 1,000 contexts. Evaluate selected actions with a separate registered synthetic instrument.',
 evidence=[
 ['Mean utility','A: 0.7954     H: 0.8002'],
 ['Paired difference','+0.004805     95% CI [0.003065, 0.006760]'],
 ['Action checks','Valid: 100% / 100%     Preferred: 74% / 73% (A / H)'],
 ['Recorded run cost','801 provider calls, 4 failed calls, USD 0.335790 total']],
 takeaway='Conditional progression. The effect does not establish learning benefit or the model proposal’s necessity.',
 foot='Runtime heuristic and evaluation utility are different quantities. Formulas and instrument scope are in backup.')
a[18]['notes']='The means are close, so the paired effect is more informative than the means alone. Guarded replacement improves registered evaluation utility by zero point zero zero four eight zero five. The ninety-five-percent paired interval runs from about zero point zero zero three one to zero point zero zero six eight. It excludes zero for these synthetic contexts, but the gain is small. Both methods obeyed the tested action rules. Preferred-action agreement moved from seventy-four to seventy-three percent and its paired interval includes zero. Evaluation utility is the synthetic instrument’s value for the selected action, not the runtime heuristic used to rank proposals. The run recorded eight hundred and one provider calls, four failed calls and about thirty-four US cents in reported cost. Those are historical totals rather than a controlled latency or current-price claim. The result justified progression to the next engine comparison. It did not establish student learning or isolate the language model’s contribution against direct analytic selection. That ablation remains necessary.'
a[18]['sources']+=[refs['C'],refs['math']]
# Main-method slide keeps metric definitions and exposes the main validity limits.
a[20]['intro']='Fit on development seeds; test 240 learners per condition for 30 days. Authored families: BKT-like and logistic-like.'
a[20]['takeaway']='Test seeds share our simulator assumptions. Count has no fitted parameters or decay, unlike the fitted alternatives.'
a[20]['foot']='6 personas × 2 families × 20 test seeds. Same consent / timing constraints. 1,000 paired learner bootstrap resamples.'
a[20]['notes']+='\n\nOne simulator family is BKT-like and the other logistic-like. Both are assumptions chosen by the researcher. A held-out seed changes the random trajectory, not the family of learner behaviour. The count baseline has no fitted parameters or forgetting. The alternatives have fitted parameters and time-dependent behaviour, which limits the fairness of the baseline comparison.'
a[21]['foot']='BKT remains outside the default runtime. Next controls: count with decay and a third simulator family. Limitations are expanded in backup.'
a[21]['notes']='Here timing is held constant for count and BKT on the same learners. Hidden-state error falls from zero point zero eight four to zero point zero three five. The paired interval excludes zero. The estimate made before the next answer tells a different story: both rounded Brier means are zero point two five nine, and the paired interval includes zero. A closer fit to the simulated hidden state therefore does not establish better prediction of observed answers. The source also reports lower hidden-state error in both simulator families, which reduces but does not remove concern that BKT benefits from simulator alignment. We need a decayed-count control and a third family before strengthening the claim. BKT remains an experimental candidate outside the default planner-input adapter. [Pause on the two different evaluation targets.]'
a[22]['notes']+=' The scope is still the simulator. Lower message volume is not automatically a better teaching outcome. The next test should challenge the assumptions as well as reproduce the paired comparison.'
# Put contract-vs-mastery limitation in ordinary-size body text.
a[26]['side']=[['12 to 0 unsupported','Contract: exact target, ≥2 correct, 0 incorrect, confidence ≥0.5.'],['Correctness scope','Tests objective-evidence matching. Assessment accuracy and mastery validity remain open.']]
a[26]['takeaway']='Keep the scope fix. In the autonomous slice: 56 extra messages, mastery change −0.0024, no established learning gain.'
a[26]['foot']='Study H: 72 histories/arm; autonomous slice 36/arm. Dependent synthetic histories do not establish a population error-rate guarantee.'
a[26]['notes']+='\n\nThe independent audit checks the same explicit completion contract using committed evidence snapshots. It is an independent check of contract compliance, not independent educational validation. The assessment itself could still be wrong. Two correct records, no incorrect records and confidence at least one half do not prove mastery. An earlier incorrect record also matters under this prototype rule. Zero observed unsupported completions applies to these dependent synthetic histories, not all future users.'
a[26]['sources']+=[refs['H']]
a[27]['notes']+='\n\nThe invariant is that a generated proposal cannot commit under stale or revoked authority. Generation runs outside the write transaction, followed by current authority and expected-revision checks. This is a local functional contract; it is not a scaling result.'
a[28]['notes']+='\n\nThe invariant is that retrying the same saved delivery key returns the existing in-app message. A crash after the message save but before the job commit is the concrete failure window. External provider effects remain outside this local guarantee. [Point to the crash window and then the repeated key.]'
a[32]['sections']=[['System delivered','Inspectable course support with persistent goals, approved content and execution controls.'],['Knowledge gained','In these comparisons, explicit required facts improved answers; reject-only verification lost actions; exact-objective evidence removed invalid completions.'],['Claim boundary','Synthetic and local evidence. Factual acceptance, instructor fidelity and useful real-course intervention remain unresolved.']]
a[32]['notes']='The deliverable is the inspectable persistent-support system. The knowledge contribution is the bounded comparison evidence: explicit required facts improved answering in development; reject-only verification could discard a usable move; exact-objective evidence removed unsupported completions in the tested histories. These are different experimental scopes, not one universal claim about architecture. The planner’s small synthetic gain and the learner-estimator results identify promising next comparisons. They do not establish professor fidelity or real learning. The immediate integration experiment changes the planner-input adapter while holding the other components fixed, alongside continued work on factual and assessment quality.'
utility=panel('Runtime prediction and evaluation utility are different quantities',
 'Study C evaluates an action chosen by the planner. It does not report the planner’s own predicted score.',[
 ['Runtime heuristic U(a)','G + 0.45O + F + B − 0.9R − I\nG: immediate gain; O: observation value; F: future value; B: misconception bonus; R: evidence risk; I: interruption cost.'],
 ['Evaluation mean utility','Mean of registered vᵢ(selected action) over contexts. Values use the state card and a seeded hidden learner outcome.\nRegret compares with the best permitted action.']],
 'Both use authored assumptions. Direct analytic selection remains an untested ablation for the model proposal’s added value.',
 'The executable runtime heuristic uses authored constants. It rewards estimated immediate gain, observation and future value, adds a misconception bonus and subtracts evidence risk and interruption. These weights were not fitted to measured educational outcomes. The confirmation runner instead looks up a registered synthetic value for the selected action and averages it over contexts. The instrument uses state information and a seeded hidden outcome. It is separate from the runtime heuristic, but that separation does not make it a real-student outcome measure. The missing direct-analytic ablation is still required to isolate why the guarded composition helps.',
 [refs['math'],'src/digital_twin/student/planning_architectures.py','scripts/run_successor_architecture_confirmation_005.py'],
 'U weights are implementation constants. Full action constants and worked calculation: submitted report, Planner Calculation appendix.')
validity=panel('The learner result needs stronger controls before integration',
 'Study E supports further work within the tested simulator. It does not validate educational effectiveness.',[
 ['Simulator alignment','One BKT-like and one logistic-like family. The source reports lower hidden-state error for BKT in both. Author-defined transitions and receptivity still constrain validity.'],
 ['Comparison fairness','Count has no fitted parameters or decay. BKT/PFA parameters were fitted on development seeds. Next controls: decayed count and a third family.']],
 'PFA also matters: under constant timing its Brier change versus count is −0.010 [−0.013, −0.008].',
 'The full comparison should not imply BKT wins every target. PFA improves next-answer Brier under constant timing, while BKT does not establish that improvement. The hidden-state ranking favours BKT in both tested families, but it remains conditional on the simulator and control choice. The next design should separately test calibration, targeting and the integration of committed assessments. Neither BKT nor PFA was selected for product release.',
 [refs['E']],
 '95% paired bootstrap interval. Hidden-state prediction, observed-answer prediction and educational benefit are distinct targets.')
contract=panel('Completion correctness leaves mastery validity unresolved',
 'Study H audits committed attribution at completion time for the exact approved objective.',[
 ['Required evidence','Every target concept has at least two correct assessments, no incorrect assessment and confidence ≥0.5. Reject missing, ambiguous, unrelated or uncommitted evidence.'],
 ['What remains open','Confidence = min(0.95, n/(n+2)); n counts assessed attempts, regardless of correctness. Open: assessment accuracy, mastery threshold and treatment of earlier mistakes.']],
 'The correction prevents unrelated evidence from completing a goal. It does not validate the learner assessment model.',
 'The test compares the selected objective with committed concept-level evidence. This catches an implementation error that earlier persistence and assessment checks missed. However, the contract is authored, and checking it independently does not validate the educational meaning of its threshold. The experiment separately verified timestamp and service-boundary behaviour with regression tests. The current rule’s treatment of earlier mistakes is a limitation to discuss rather than silently call mastery.',
 [refs['H'],'tests/digital_twin/test_goal_completion_scope.py','tests/test_goal_completion_scope_evaluation.py'])
# Add the contribution without lengthening the main talk: move the detailed lifecycle to backup.
slides=[a[1],a[2],contribution]+[a[i] for i in range(3,8)]+[a[i] for i in range(9,43)]+[a[8],utility,validity,contract,container]
q=next(i for i,s in enumerate(slides) if s['kind']=='questions')
oldmap={}
for i,s in enumerate(slides,1):
 if 'number' in s and s is not container:oldmap[s['number']]=i
 s['number']=i;s['backup']=i>q+1
words=sum(len(re.findall(r"\b[\w’'-]+\b",s['notes'].split('\n\nDiagram scope')[0])) for s in slides[:q])
data.update(slides=slides,main_slides=q,main_word_count=words,revision='graduate-cs');p.write_text(json.dumps(data,indent=2))
lines=['# Graduate CS presentation script','',f'{q} main slides, Questions, {len(slides)-q-1} backup slides. Approximately {words} narration words plus 4:06 video. Stage directions in brackets are not spoken.','']
for s in slides:lines += [f"## {s['number']}. {s['title'].replace(chr(10),' ')}",'',s['notes'],'','Sources: '+', '.join(s['sources']),'']
Path('reports/presentation/speaker-script-graduate.md').write_text('\n'.join(lines))
qa=Path('reports/presentation/defence-notes-graduate.md').read_text()
qa=re.sub(r'## Slide ([0-9 /]+):',lambda m:'## Slide '+' / '.join(f'{oldmap[int(n)]:02d}' for n in re.findall(r'\d+',m[1]))+':',qa)
qa=qa.replace('digital-twin-presentation-improved.pptx (32 main slides, Questions, nine backup slides)','digital-twin-presentation-graduate-final.pptx (32 main slides, Questions, fourteen backup slides)')
qa=qa.replace('## Slide 02 / 32: What is the research contribution?','## Slide 03 / 32: What is the research contribution?')
Path('reports/presentation/defence-notes-graduate-final.md').write_text(qa)
print(len(slides),'slides;',q,'main;',words,'narration words; video slide',next(s['number'] for s in slides if s['kind']=='video'))
