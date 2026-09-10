"""Rebuild the deck so essential explanations are visible without narration."""
from pathlib import Path
import json
import copy

ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'reports/generated/slide-build'
source=json.loads((B/'pre-standalone-content.json').read_text())
s={x['number']:copy.deepcopy(x) for x in source['slides']}
review={}

def setslide(n, purpose, **fields):
    s[n].update(fields)
    s[n].pop('termNote',None)
    review[n]=purpose

def explain(n,title,intro,items,conclusion,limit='',**kw):
    setslide(n,title,kind='explanation',title=title,intro=intro,items=items,
             takeaway=conclusion,limit=limit,foot='',**kw)

def tbl(n,title,intro,rows,widths,conclusion,limit='',**kw):
    setslide(n,title,kind='readerTable',title=title,intro=intro,rows=rows,widths=widths,
             takeaway=conclusion,limit=limit,foot='',**kw)

setslide(1,'Identify the product and research scope.',title='A Course Digital Twin\nfor Continuing Student Support',
 subtitle='A professor-configured teaching prototype\nDesign comparisons, failures and remaining quality gaps')
s['brief']={'sources':s[29]['sources'],'kind':'explanation','title':'The requested course assistant','intro':'The professor supplies the course context. The software should continue supporting each student over time.',
 'items':[['Professor configuration','Use approved materials and learning objectives. Apply the professor’s teaching preferences, such as asking for an attempt before giving an explanation.'],['Continuing student support','Answer questions, retain earlier interactions and send permitted follow-ups. The professor and student must be able to stop that support.']],
 'takeaway':'The project must evaluate both the software’s operation and the quality of its teaching.',
 'limit':'“Digital twin” names this configurable assistant. Reproducing a real professor’s teaching remains an evaluation goal.','foot':''}
review['brief']='Establish the requested behavior and what the project must demonstrate.'
setslide(2,'Connect professor setup to student use before discussing architecture.',
 title='How a published course reaches the student',
 intro='A release is the reviewed version of a course. Answers and student records refer to that version.',
 takeaway='Publication gives students access to support using the approved course material.',
 foot='This workflow covers a student-initiated exchange. Scheduled follow-up is shown next.')
setslide(3,'Show exactly what makes the displayed behavior autonomous.',
 title='The system starts a follow-up after the student stops typing',
 intro='Actual demo frames: student B1 on virtual day 3. Advancing virtual time makes a scheduled job due.',
 captions=['Before: the student’s check-in inbox is empty.','After: the application has delivered a follow-up.'],
 takeaway='The scheduler initiates contact from saved work, without a new student question.',
 foot='Synthetic users and deterministic demo services. This event demonstrates delivery. Its educational usefulness is untested.')
setslide(4,'Tell the viewer which events matter and identify demo conditions.',
 title='Demo: course setup and a month of continuing support',
 videoGuide='2 professors, 2 courses, 4 synthetic students. Watch publication, the student inbox and the pause controls.',
 foot='4:06 recording of the actual application. Time advances virtually through 30 days. Model responses use deterministic demo services.')
tbl(7,'What the demonstration leaves to evaluate',
    'The evaluations test whether the working software meets these requirements.',
    [['Requirement','Question answered by the evaluation'],['Course answers','Does the response contain every required fact, supported by the course source?'],['Support decisions','Does the selected action obey the rules and help under the simulation’s assumptions?'],['Student state','Does completion use evidence for this goal? Does estimated knowledge reflect assessed answers?'],['Continuing operation','Do messages, permissions and saved state behave correctly over time and after failure?']],
    [310,850],
    'The studies provide local and synthetic evidence. Real-student learning and professor fidelity remain untested.',
    'Component comparisons use separate datasets. The integrated trial and learner simulation are not the demo recording.')
setslide(8,'Define complete and source-supported with an explicit example.',
 title='A retrieved source can still produce an incomplete answer',
 takeaway='Here, “grounded” requires both source support and every requested item. Two correct items are insufficient.',
 foot='Illustrative example. The next comparison tests how answer paths decide whether the available evidence is sufficient.')
# The main historical architecture diagram already names all three paths.
setslide(9,'Explain the failure mechanism before quantifying it.',
 title='The complex answer paths checked the wrong evidence target',
 foot='Both highlighted checks demanded evidence for the wording of the whole question. Framing words could fail the check even when the required answer facts were present.',
 diagramCaption='Lexical matches keywords. Hierarchy searches nested course sections. Plan–observe splits the query and combines retrieved evidence.')
setslide(10,'Separate supported-answer rate from willingness to answer.',
 title='The shared check rejected many answerable questions',
 intro='Same 495 development cases and 350 source chunks. “Fully grounded” means complete and supported by course evidence.',
 side=[['Answerable cases answered','Lexical: 100%\nHierarchy: 36.46%\nPlan–observe: 36.20%'],['Failure mechanism','The two complex paths rejected many cases before producing an answer.']],
 takeaway='This implementation failed at the shared evidence check. The study cannot isolate the value of either architecture.',
 foot='Development comparison with no external model calls. Boundary handling scored 100% in each arm.')
setslide(11,'Explain what the successful interface change specifies.',
 title='Explicit answer requirements recovered 102 grounded answers',
 intro='The revised interface states the required fact type and item count, such as “a set of three stages”. Same 397 answerable cases.',
 side=[['253 to 355 cases','The answer check now targets required facts rather than all question wording.'],['Ranking added no answers','Extra section ranking kept 355 cases and raised p95 latency: 1.36 to 2.79 ms.']],
 takeaway='Retain the explicit fact requirement. Additional ranking did not improve answer quality in this comparison.',
 foot='Development study A. p95 latency is the time within which 95% of measured requests finish.')
setslide(12,'Interpret every metric and its failure threshold directly.',
 title='Fresh questions still exposed incomplete answers',
 intro='Fresh-source study B: 800 answerable questions and 200 refusal/clarification cases. Both paths use the same answer check.',
 side=[['Answer threshold: 95%','BM25: 506/800 = 63.25%. Complete, source-supported answers remain far below the requirement.'],['Boundary threshold: 98%','BM25: 192/200 = 96%. Some cases still receive the wrong refusal or clarification.']],
 takeaway='BM25 remained the simpler fallback. Neither configuration met the two required quality thresholds.',
 foot='BM25: keyword ranking. Hybrid adds semantic retrieval. Evidence @3: required evidence appears in the first three results.\nBM25 answer-rate 95% confidence interval: 58.75–67.63%. Generated questions and rigid scoring limit generalization.')
s[12]['charts'][0]['categories']=['Evidence found @3','Grounded answer','Refuse / clarify']
setslide(13,'Explain why improved evidence retrieval did not repair final answers.',
 title='Visual retrieval found more evidence without fixing final answers',
 intro='Two separate studies compare visual models with their controls. The fresh control uses text and optical character recognition (OCR).',
 takeaway='Historical answer quality stayed flat. The fresh visual candidate produced fewer grounded answers and was dropped.',
 foot='Historical model: Jina embeddings v4. Fresh model: Jina embeddings v5 omni. Both historical arms retained citation failures.\nThe fresh control also had a citation defect. Image-region links and evidence layouts remained failure points.')
tbl(14,'The planner chooses an action before text is written',
    'The planner receives an event, learner information and allowed actions. The generator then writes the selected response.',
    [['Design','How it chooses','What can happen'],['A: fixed rules','Select an action from the event rule','Provides the baseline action'],['B: model proposal','Ask a model to propose an action','Proposal quality must justify replacing A'],['C: estimated consequences','Score the proposal’s expected consequences','A higher predicted score still needs evaluation'],['C + verifier','Accept or reject C’s action','Rejection ends with no replacement action']],
    [265,445,450],
    'The verifier can remove a usable action. The next design preserves the baseline when a replacement fails.',
    'These letters identify project candidates. Matching a preferred action label is a different test from obeying the action rules.')
setslide(15,'Make the retention rule and its conditions readable without narration.',
 title='The guarded planner keeps a fallback when a proposal fails',
 diagramCaption='A is the fixed-rule action. H is the combined design below. “Analytic best” means the highest predicted score among allowed actions.',
 foot='If evidence is disallowed, the system takes no action. With allowed evidence, a failed proposal keeps the baseline instead of ending the decision.')
explain(16,'Guarded replacement produced a small simulated gain',
    'Study C compares rules A and guarded H on the same 1,000 contexts. Both obeyed every tested action rule.',
    [['What improved','Rules A: 0.7954 mean utility\nGuarded H: 0.8002 mean utility\nPaired gain: 0.004805\n95% confidence interval: 0.003065–0.006760.'],
     ['What that score means','Utility is an authored evaluator’s value for the chosen action, using simulated learner outcomes. It is separate from the planner’s predicted score.']],
    'The gain justified further comparison. It does not establish improved learning for real students.',
    '801 provider calls, 4 failures, $0.335790 historical cost. Missing control: choose the analytic best action without a model proposal.')
tbl(17,'Learner models estimate knowledge from assessed answers',
    'An assessment records whether an attempt is correct for a concept. The methods turn that history into a probability estimate.',
    [['Estimator','How this implementation uses the history'],['Count baseline','(Correct attempts + 1) / (all assessed attempts + 2). Earlier evidence never fades.'],['Bayesian Knowledge Tracing (BKT)','Updates belief that the concept is known. Allows guessing, mistakes despite knowledge, learning and forgetting.'],['Performance Factors Analysis (PFA)','Predicts success from earlier correct and incorrect attempts. Older evidence receives less weight here.']],
    [365,795],
    'These models run in a separate learner simulation. The product’s current planner input uses a different method.',
    'BKT and PFA parameters were chosen on development seeds. Count has no fitted parameters or forgetting, which weakens it as a control.')
s['timing']={'sources':s[17]['sources']}
tbl('timing','Contact timing decides when to send support',
    'The same knowledge estimate can lead to different contact schedules. All methods first apply the shared delivery limits.',
    [['Timing policy','Send decision'],['Constant','Send at every eligible check.'],['Conditional','Send when progress stalls, or estimated knowledge is low and uncertain.'],['Value-based','Send only when the estimated benefit exceeds the configured margin.']],
    [330,830],
    'The experiment crosses three estimators with three timing policies to separate estimation from contact frequency.',
    'Shared limits: consent required, quiet hours 22:00–08:00, at most 3 messages per 7 days and 24 hours between messages on the same concept.')
setslide(18,'Teach the two measurement targets with calculations.',
 title='The simulation measures knowledge error and answer prediction',
 intro='240 simulated learners per condition, over 30 days. The simulator supplies hidden knowledge and generates correct/incorrect answers.',
 items=[['Knowledge error: MSE','Mean squared error between the estimate and hidden simulator knowledge.'],['Next-answer error: Brier score','Mean squared error between a predicted probability and the observed answer: correct = 1, incorrect = 0.']],
 takeaway='Lower is better for both measures. Matching hidden knowledge and predicting an answer are separate tests.',
 foot='Calculations are illustrative. Tests use held-out random seeds but the same two authored simulator families. This is not a classroom experiment.')
setslide(19,'Distinguish a hidden-state advantage from an inconclusive prediction result.',
 title='BKT fitted hidden knowledge better without clearer prediction',
 intro='Hold constant timing fixed. Count and BKT each send 14 messages per learner, so contact frequency is equal.',
 takeaway='BKT improved fit to the simulator’s hidden state. Its next-answer difference remains inconclusive.',
 foot='MSE: mean squared error. Brier: probability prediction error. CI: confidence interval. Study E, 240 learners per condition.\nBoth simulator families are authored assumptions. A count baseline with forgetting remains an important missing comparison.')
setslide(20,'Show the contact-versus-knowledge tradeoff and define mastery.',
 title='Fewer messages came with lower simulated knowledge',
 intro='Keep the count estimator fixed. “Mastery” below is the simulator’s mean hidden knowledge at day 30.',
 takeaway='Conditional timing saves 7 messages per learner but lowers mastery by 0.012 [95% CI −0.018, −0.005].',
 foot='Constant sends at eligible checks. Conditional waits for a need signal. Value requires predicted benefit above a margin.\nWaste rates: 50.6%, 38.8%, 34.1%. Waste means contact when mastery is at least 0.85 or the learner is unreceptive.')
tbl(21,'The product’s “mastery” input rises when a message is sent',
    'The input adapter uses delivery count n to set the planner’s probability: (n + 1) / (n + 2), capped at 0.95.',
    [['Event','New assessed answer?','Planner input'],['Before any delivery: n = 0','No','1 / 2 = 0.50'],['After one delivery: n = 1','No','2 / 3 = 0.67']],
    [510,350,300],
    'The number rises without new evidence of understanding. A planner decision can therefore react to its own activity.',
    'This is current adapter behavior. Experimental BKT/PFA results do not validate this input. Goal completion uses assessed evidence separately.')
setslide(22,'Expose the critical meaning change and explain why both candidates failed.',
 title='A wording revision changed a requirement into a guarantee',
 intro='Two candidates revised paired adequate and defective answers. Each repaired 47 of 56 defects, but retained a critical meaning error.',
 takeaway='A necessary condition does not guarantee acceptance. Both candidates failed the zero-critical-error requirement.',
 foot='Study F, 56 pairs per candidate, with AI-assisted review. The example paraphrases a recorded defect in synthetic course material.')
tbl(23,'Evidence for one topic incorrectly completed another goal',
    'Recorded case: the student answers two cache-coherence questions correctly. The student has no assessed answer about virtual memory.',
    [['Learning goal','Relevant evidence','Old decision','Corrected decision'],['Cache coherence','Two correct attempts','Completed','Completed'],['Virtual memory','No assessed attempts','Completed','Keep active']],
    [310,335,250,265],
    'The correction requires evidence for each goal’s own target concepts. Unrelated answers cannot complete it.',
    'Per target: at least 2 correct, 0 incorrect and evidence confidence ≥0.5. These are software thresholds whose mastery validity remains untested.')
setslide(24,'Explain supported completion and isolate what the correction establishes.',
 title='The scope correction removed 12 unsupported completions',
 intro='Same 72 synthetic histories per version. “Supported” means the saved evidence meets the completion rule for that goal’s concepts.',
 side=[['Control: 26 completed','14 had relevant evidence.\n12 incorrectly used evidence outside the goal’s scope.'],['Corrected: 15 completed','All 15 met the target-evidence rule. Assessment accuracy still needs validation.']],
 takeaway='Retain the correction for state correctness. The additional follow-ups did not establish a learning benefit.',
 foot='Study H used deterministic planning and wording. In the 36-history autonomous slice: 56 more messages and −0.0024 simulated mastery.')
setslide(25,'Name the race condition and what the second check protects.',
 title='A permission change must invalidate an unfinished answer',
 intro='Failure scenario: the professor withdraws the course release while the generator prepares an answer.',
 takeaway='The final check must reject stale work before saving the answer, citations or learner update.',
 foot='UML sequence. Generation runs outside the write transaction. The commit rechecks current permission and the state revision.')
setslide(26,'Explain the crash point, recovery key and limit of the guarantee.',
 title='A restart must reuse the message that was already saved',
 intro='Crash scenario: the message is saved, but the worker stops before recording job completion. The unfinished job runs again.',
 takeaway='The same delivery key finds the existing in-app message, preventing a duplicate during this retry.',
 foot='UML sequence of local recovery. Permission checks still apply. This mechanism does not guarantee exactly-once delivery to external systems.')
tbl(27,'The month-long trial exposed weak continuing support',
    'Historical integrated trial: 24 synthetic histories, 30 virtual days and actual external model calls through the application services.',
    [['Observed behavior','Result','What it establishes'],['Tutor exchanges','484 turns, 654 model calls','The integrated path ran with model failures'],['Proactive support','16 messages, 10 replies','The saved check-ins remained generic'],['Consent off on days 10–19','No proactive messages','The application respected the off-window'],['After that window','No resumed proactive delivery','Useful sustained support remains unresolved']],
    [345,330,485],
    'A working delivery mechanism was demonstrated. The trial did not establish useful personalized teaching.',
    'Study G is separate from the demo. 24 restarts, 11 output-limit calls and 13 tutor turns ending in safe graph failure.')
tbl(28,'Evaluation defects reduced the claims the project can make',
    'An evaluation audit found problems in earlier runs. Their raw scores cannot all be used as independent evidence.',
    [['Problem found','Consequence'],['Author saw the reference answer','The 10,000-case analysis cannot establish independent answer quality'],['Reported totals contradicted each other','Exclude the unresolved grounded-answer percentage'],['More candidates tested than registered','Round 3 cannot justify its reported selection'],['Preferred label treated as a valid action','Reassess preference separately from obeying action rules']],
    [485,675],
    'The other comparisons retain their separate scopes. Invalid results stay documented with their corrections.',
    'These corrections affect the strength of the evidence, not just its presentation. Real-course and real-student validation is still missing.')
tbl(29,'Implemented behavior and remaining acceptance gaps',
    'The project has an inspectable prototype. These gaps determine which requirements can be considered complete.',
    [['Requirement','Available behavior','Still to establish'],['Course configuration','Review and publish course materials','Quality beyond local workflow tests'],['Course answers','Responses with source citations','Required factual-quality thresholds'],['Professor’s teaching','Preferences enter generation','Fidelity to actual teaching practice'],['Continuing support','Stored goals and scheduled contact','Useful, sustained student intervention']],
    [330,425,405],
    'Configuration and operation alone do not satisfy the factual and instructional quality requirements.',
    'Review, pause and consent controls are implemented. Selected components still need evaluation together in a representative course.')
explain(30,'The next comparison should repair the planner’s input',
    'Test whether relevant assessment evidence changes support decisions more usefully than delivery counts.',
    [['Control: current adapter','Keep the current delivery-based probability. Hold the evidence selector, planner, wording and permission controls fixed.'],['Candidate: assessment adapter','Use committed answers for the goal’s own concepts. Keep missing or contradictory evidence explicit rather than treating delivery as understanding.']],
    'Compare identical snapshots first, then full histories. Measure useful actions, missed support and inappropriate contact.',
    'Proposed work, not a completed run. Also check permissions, latency and cost. Product claims depend on independent assessment-quality validation.')
setslide(31,'Close with delivered system, defensible findings and unresolved questions.',
 title='The prototype yielded specific lessons from failed designs',
 sections=[['Delivered','A configurable course assistant with stored student context and scheduled follow-up.'],['Engineering findings','Specify required answer facts. Preserve an allowed fallback. Complete each goal only from its own evidence.'],['Remaining gap','Reliable answers and useful instruction are still acceptance requirements. Synthetic results do not establish real-student benefit.']])
# Backups are self-contained answers rather than hidden prerequisites.
explain(6,'A saved response follows the requested first teaching step',
    'Professor preference: ask the student to explain before giving an answer. This saved case tests only whether that step appears.',
    [['Requested behavior','Elicit the student’s current explanation before supplying the solution.'],['Saved response excerpt','“what is your current explanation, and which step are you unsure about?”']],
    'The response asks for an explanation first. One response cannot establish faithful reproduction of the professor’s teaching.',
    'Saved case F21. The question concerned a synthetic course concept. A controlled comparison would keep the question and evidence fixed while changing the teaching profile.')
setslide(5,'Locate software responsibilities after the audience knows their purpose.',
 title='Component responsibilities behind tutoring and follow-up',
 intro='The shared services control permissions and persistence. The components below supply evidence, state, actions and text.',
 takeaway='A retrieval change cannot by itself fix the planner’s input or the wording of its selected action.',
 foot='Simplified UML component view. The experimental learner estimators are separate from the product’s current input adapter.')
setslide(33,'Explain publication terminology and the rejection loop.',
 title='Publication checks protect access to the reviewed course',
 foot='Preflight means checking whether the draft is ready to publish. A blocker returns it for revision. A release identifies the approved course version used by student conversations.')
setslide(34,'Explain every parameter in the illustrative BKT update.',
 title='Bayesian Knowledge Tracing: a worked update',
 intro='Illustrative assumptions: guess 20%, slip 10%, learning 30%, daily forgetting 5%. A slip is an incorrect answer despite knowing the concept.',
 foot='The belief column is the estimated probability the concept is known. The calculation is illustrative, not an observed student trajectory.')
setslide(35,'Make external provider responsibility and scope explicit.',
 title='System context and the external model provider',
 foot='The professor configures the course and the student uses support. The external provider returns proposed text/actions. Local application services retain permission and persistence controls.')
setslide(36,'Explain the storage hierarchy and unfamiliar entities.',
 title='The data model ties student records to a course release',
 foot='A release is a reviewed course version. A goal is a learning objective for one student. An opportunity is candidate scheduled work. Citations link an answer to its source version.')
setslide(37,'Explain publication transaction and what remains outside it.',
 title='Publication replaces a release and cancels its pending work',
 foot='Preflight checks readiness. The repository transaction publishes the new release, withdraws the previous one and cancels its work. Index preparation happens outside that transaction.')
setslide(38,'Describe the verifier failure using labels whose meaning is visible.',
 title='Rejecting the planner’s choice can leave no action',
 foot='C adds estimated consequences to a model proposal. The verifier accepts or rejects that action. The rejected branch supplies no baseline replacement, so useful work can be lost.')
setslide(39,'Keep full results with units and definitions near the data.',
 title='Full learner-estimator and timing results',
 intro='240 simulated learners per condition. MSE: mean squared knowledge error. Mastery: hidden knowledge at day 30.',
 foot='Messages: per learner. Waste: contact at mastery ≥0.85 or while unreceptive. Lower MSE and waste are better.\nBKT: Bayesian Knowledge Tracing. PFA: Performance Factors Analysis. Oracle sees hidden state. Never: no contact.')
setslide(40,'Explain model aliases and distinguish completion from semantic validity.',
 title='Model comparisons and output-completion limits',
 intro='Luna = GPT-5.6 Luna, Terra = GPT-5.6 Terra, Mini = GPT-5.4 Mini. Compare alternatives within each study row.',
 foot='Utility is an authored simulated score. Valid final output includes fallback recovery. Completion measures whether generator calls finish. Study D retained Luna for both roles.')
setslide(41,'Give descriptive study scopes and bounded decisions.',
 title='Evidence index: the decision supported by each study',
 foot='Study labels refer to separate datasets and configurations. They are not stages of a single improvement curve. Exact result records are cited in the notes.')
setslide(42,'Separate historical invalid analyses from newer demonstration footage.',
 title='Evidence index: corrected analyses and the newer demo',
 foot='Corrections remain linked to the original records. The newer deterministic demo shows application behavior and cannot validate the older external-model configuration.')
setslide(43,'Explain lifecycle states and completion guard.',
 title='Goal states and the conditions for ending work',
 foot='Completed means the software’s evidence rule passes. Expired means time ran out. Cancelled means the scope became invalid. An attempt limit blocks more work but leaves the goal active.')
explain(44,'The planner and evaluator calculate different scores',
    'The planner predicts the value of candidate actions. The evaluator scores the action the planner actually selected.',
    [['Planner: choose an action','U(a) = G + 0.45O + F + B − 0.9R − I\nG: gain, O: observation, F: future value, B: misconception bonus, R: evidence risk, I: interruption.'],['Evaluator: compare policies','Use the registered action value and a seeded hidden learner outcome. Average this evaluation utility over the test contexts.']],
    'Both scores depend on authored assumptions. Neither directly measures student learning in a course.',
    'A direct analytic-selection control is still missing. The full runtime constants and calculation are in the submitted report appendix.')
explain(45,'The learner-model result needs stronger comparisons',
    'BKT reduced hidden-state error in the tested simulator. That advantage could partly reflect the chosen simulator and weak baseline.',
    [['Simulator limitation','Test seeds differ, but the two families remain BKT-like and logistic-like. Add a third family with different learning and forgetting assumptions.'],['Baseline limitation','Count has no fitting or forgetting. Compare BKT against a count model that discounts older evidence before attributing the improvement to BKT’s structure.']],
    'For next-answer prediction, PFA improved Brier by 0.010. The BKT difference was inconclusive.',
    'Study E, constant timing. PFA paired difference −0.010, 95% confidence interval [−0.013, −0.008]. Educational effectiveness remains untested.')
setslide(46,'Explain why attempt confidence cannot stand in for correctness.',
 title='Evidence confidence grows with attempts regardless of correctness',
 intro='For n assessed attempts, confidence = min(0.95, n / (n + 2)). The completion rule checks correctness separately.',
 foot='Each row is an illustrative two-attempt history. These thresholds implement a completion rule. Their pedagogical meaning and the assessments themselves still need validation.')
setslide(47,'Explain workers, stores and whether the topology was compared.',
 title='Logical deployment of the local prototype',
 foot='The web app calls the API. Workers process due support and source ingestion. SQLite stores runtime records, while files store sources. This topology has not won a scaling or database comparison.')
setslide(48,'Keep definitions understandable independently of the main section.',
 title='Glossary: learner estimates and their evaluation',
 foot='A knowledge estimate, a prediction of the next answer and a measured learning benefit are different quantities. The simulation evaluates the first two.')
setslide(49,'Define the local candidate labels and avoid ambiguous model references.',
 title='Glossary: retrieval and action-selection terms',
 foot='Candidate letters are local to the project. Utility scores depend on the registered synthetic evaluator. Model names identify implementations rather than evaluation metrics.')
s[49]['rows'][-1][2]='Qwen3 is a model family. Luna, Terra and Mini abbreviate the GPT models named in the model-allocation backup.'
# Keep the diagram names consistent with the result chart.
import xml.etree.ElementTree as ET
import subprocess
out=ROOT/'reports/presentation/diagrams/standalone'
out.mkdir(exist_ok=True)
tree=ET.parse((ROOT/s[9]['image']).with_suffix('.drawio'))
for cell in tree.findall('.//mxCell'):
    if cell.get('value')=='Evidence-first':cell.set('value','Hierarchy')
    if cell.get('value')=='Retrieve lexical matches':cell.set('value','Retrieve keyword matches')
dest=out/'factual-paths.drawio'
tree.write(dest,encoding='utf-8',xml_declaration=True)
subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--format','png','--scale','1.5','--border','8','--embed-diagram','--output',str(dest.with_suffix('.png')),str(dest)],check=True,stdout=subprocess.DEVNULL)
s[9]['image']=str(dest.with_suffix('.png').relative_to(ROOT))
s[41]['rows'][1]=['A','Explicit answer facts on development cases','Keep the interface change and refine quality']
s[41]['rows'][2]=['B','Fresh-source answer comparison','Keep fallback, quality thresholds still unmet']
s[41]['rows'][4]=['E','Knowledge estimates and contact timing','Further study, estimators not integrated']
s[41]['rows'][5]=['F','Revision of adequate and defective answers','Neither candidate passes the critical-error gate']
s[41]['rows'][7]=['H','Completion from each goal’s own evidence','Keep the correction to goal scope']

# Every old source page is retained once. Additional setup replaces narration-only context.
order=[1,'brief',2,3,4,7,8,9,10,11,12,13,14,15,16,17,'timing',18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,6,5]+list(range(33,50))
mapping={str(old):i for i,old in enumerate(order,1)}
s[32]['sections']=[['System detail',f'Teaching example {mapping["6"]}, components {mapping["5"]}, publication {mapping["33"]}, deployment {mapping["47"]}'],['Methods',f'BKT calculation {mapping["34"]}, full learner results {mapping["39"]}, planner scoring {mapping["44"]}'],['Evidence limits',f'Model comparison {mapping["40"]}, corrected runs {mapping["42"]}, stronger controls {mapping["45"]}']]
review[32]='Provide accurate navigation for questions.'
for i,old in enumerate(order,1):
    s[old]['number']=i;s[old]['backup']=i>32;s[old]['audited_number']=old
    s[old]['notes']='' # This revision carries explanations on the slides. Preserve citations only.
    s[old].pop('termNote',None)
    for unused in ['gloss','old_number']:s[old].pop(unused,None)
source['slides']=[s[k] for k in order];source['main_slide_count']=31
source.pop('main_word_count',None)
(B/'deck-content.json').write_text(json.dumps(source,indent=2))
(B/'standalone-slide-map.json').write_text(json.dumps(mapping,indent=2))
lines=['# Structure for a presentation that stands without narration','',
 'This revision places essential explanations on the slide. The main talk has 31 slides, followed by Questions and 19 backups. The previous read-aloud script is not the basis for this revision.',
 '', '| New slide | Previous slide | Reader’s task |','| --- | --- | --- |']
for i,old in enumerate(order,1):lines.append(f'| {i} | {old} | {review[old]} |')
(ROOT/'reports/presentation/structure-revision-13-standalone.md').write_text('\n'.join(lines)+'\n')
print('Rebuilt',len(order),'slides. All 49 earlier pages retained, with teaching/component detail moved to backup.')
