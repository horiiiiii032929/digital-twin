"""Apply a page-by-page clarity audit to the natural-script deck."""
from pathlib import Path
import copy
import json
import subprocess
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/generated/slide-build'
OUT = ROOT / 'reports/presentation/diagrams/clarity'
data = json.loads((BUILD / 'pre-clarity-content.json').read_text())
s = {x['number']: x for x in data['slides']}
audit = {}


def change(n, question, problem, **fields):
    audit[n] = [question, problem]
    s[n].update(fields)


class Diagram:
    def __init__(self, name):
        self.name = name
        self.doc = E.Element('mxfile', host='app.diagrams.net')
        page = E.SubElement(self.doc, 'diagram', name=name, id=name)
        model = E.SubElement(page, 'mxGraphModel', pageWidth='1160', pageHeight='440')
        self.root = E.SubElement(model, 'root')
        E.SubElement(self.root, 'mxCell', id='0')
        E.SubElement(self.root, 'mxCell', id='1', parent='0')
        self.i = 1
    def node(self, x, y, w, h, text, extra='', size=25):
        self.i += 1
        c = E.SubElement(self.root, 'mxCell', id=str(self.i), value=text, parent='1', vertex='1',
            style=f'whiteSpace=wrap;html=0;fontFamily=Arial;fontSize={size};fontColor=#172B45;strokeColor=#172B45;fillColor=#FFFFFF;spacing=8;{extra}')
        E.SubElement(c, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), attrib={'as':'geometry'})
    def line(self, x1, y1, x2, y2, label='', points=(), reply=False):
        self.i += 1
        c = E.SubElement(self.root, 'mxCell', id=str(self.i), value=label, parent='1', edge='1',
            style=f'endArrow={"open" if reply else "block"};endFill={0 if reply else 1};strokeColor=#172B45;fontColor=#172B45;fontFamily=Arial;fontSize=21;labelBackgroundColor=#FFFFFF;dashed={1 if reply else 0};')
        g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
        E.SubElement(g,'mxPoint',x=str(x1),y=str(y1),attrib={'as':'sourcePoint'})
        E.SubElement(g,'mxPoint',x=str(x2),y=str(y2),attrib={'as':'targetPoint'})
        if points:
            a=E.SubElement(g,'Array',attrib={'as':'points'})
            for x,y in points:E.SubElement(a,'mxPoint',x=str(x),y=str(y))
    def save(self):
        path=OUT/(self.name+'.drawio')
        E.ElementTree(self.doc).write(path,encoding='utf-8',xml_declaration=True)
        subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--format','png','--scale','1.5','--border','8','--embed-diagram','--output',str(path.with_suffix('.png')),str(path)],check=True,stdout=subprocess.DEVNULL)
        return str(path.with_suffix('.png').relative_to(ROOT))


OUT.mkdir(parents=True,exist_ok=True)
d=Diagram('course-workflow')
for x,label in [(0,'Professor'),(390,'Application'),(780,'Student')]:
    d.node(x,0,380,425,'','fillColor=none;')
    d.node(x+10,10,360,40,label,'strokeColor=none;fontStyle=1;')
d.node(175,65,20,20,'','ellipse;fillColor=#172B45;')
for x,y,w,h,t in [(45,110,290,85,'Provide and approve\ncourse materials'),(420,110,320,85,'Publish the reviewed\ncourse assistant'),(815,110,310,85,'Ask a course question'),(420,285,320,85,'Answer using\ncourse material'),(815,285,310,85,'Read the answer\nor submit an attempt')]:d.node(x,y,w,h,t,'rounded=1;arcSize=14;')
d.line(185,85,185,110);d.line(335,153,420,153);d.line(740,153,815,153)
d.line(970,195,580,285,points=[(970,235),(580,235)])
d.line(740,327,815,327);d.node(1090,390,25,25,'','shape=endState;');d.line(1102,370,1102,390)
workflow=d.save()

d=Diagram('component-responsibilities')
d.node(100,0,960,110,'«component»\nTutoring and scheduled-support services\nCheck permissions and save the result','shape=component;',27)
labels=[('Evidence selector','Find the required course facts'),('Input adapter','Prepare the learner information'),('Action planner','Choose the next support action'),('Wording generator','Write the student-facing text')]
for i,(name,meaning) in enumerate(labels):
    x=10+i*290
    d.node(x,235,270,165,'«component»\n'+name+'\n'+meaning,'shape=component;',25)
    d.line(x+135,110,x+135,235,'uses',reply=True)
components=d.save()

def sequence(name, roles, messages):
    d=Diagram(name)
    for x,label in zip([140,580,1020],roles):
        d.node(x-135,0,270,65,label,'',25)
        d.line(x,65,x,430,reply=True)
        # Lifelines are dashed lines, without arrowheads.
        d.root[-1].set('style',d.root[-1].get('style').replace('endArrow=open','endArrow=none'))
    for start,end,y,label,reply in messages:d.line(start,y,end,y,label,reply=reply)
    return d.save()
authority=sequence('authority-before-save',['tutor:Service','state:Repository','text:Generator'],[
    (140,580,110,'Check permission and read state',False),(580,140,160,'Allowed snapshot',True),
    (140,1020,225,'Prepare candidate answer',False),(1020,140,275,'Candidate answer',True),
    (140,580,340,'Recheck permission + state revision',False),(580,140,400,'Commit, or reject if checks fail',True)])
retry=sequence('saved-message-retry',['worker:Service','delivery:Service','state:Repository'],[
    (140,580,110,'Deliver using stable key K',False),(580,1020,160,'Save the in-app message',False),
    (1020,580,210,'Message saved',True),(140,580,315,'After restart: retry key K',False),
    (580,1020,365,'Find the saved message for K',False),(1020,140,420,'Reuse message; finish job record',True)])

change(1,'What did this project build?','Title gave a research category before a plain product description.',
       subtitle='A professor-configured course assistant that answers questions\nand can follow up later.',details='Hikaru\nGraduate research presentation\n8 September 2026')
change(2,'How do a professor and student use it?','Role columns concealed the interaction and mixed demo counts with research goals.',
       kind='focusFigure',title='A course assistant configured by the professor',image=workflow,
       intro='The professor approves the course. Students use that published course for support.',
       takeaway='The same course context connects the professor’s setup to the student’s answer.',
       foot='Simplified UML activity. Detailed publication checks are in backup slide 33.')
change(3,'What happens without another student question?','Abstract contribution claims arrived before any concrete software behavior.',
       kind='screenPair',title='A follow-up arrives without another question',
       intro='Same student B1, same course, virtual day 3. The student stops typing.',
       images=['reports/generated/slide-build/clarity-assets/inbox-before.png','reports/generated/slide-build/clarity-assets/inbox-after.png'],
       labels=['Before scheduled delivery','After scheduled delivery'],
       captions=['The inbox has no check-ins yet.','A system-initiated follow-up appears.'],
       takeaway='Saved state and scheduled work let the system start the next contact.',
       foot='Cropped actual frames from the synthetic recording. This shows delivery, not useful personalization.',
       sources=s[5]['sources'])
change(4,'Which requested outcomes still need work?','Acceptance table arrived before the system and its evidence were understandable.',
       title='What is delivered, and what remains unresolved?',intro='Current status after the workflow tests and design comparisons.',
       rows=[['Requested outcome','Implemented behavior','Remaining evidence gap'],['Course setup','Reviewed materials and publication','Only local workflow tests'],['Course answers','Source-based responses with citations','Fresh answer-quality thresholds unmet'],['Teaching preferences','Settings enter response generation','Professor’s teaching fidelity untested'],['Continuing support','Stored goals and scheduled messages','Useful student intervention unproven'],['Human oversight','Review, pause and consent controls','Evaluate selected components together']],
       points=['A working prototype is available. Teaching quality and real-student benefit remain open.'],foot='This status table separates implemented behavior from evidence of quality.')
change(5,'What should I watch in the recording?','Busy poster and dense title gave no simple viewing instruction.',
       title='Demo: setup, student interaction and follow-up',
       foot='Watch the inbox after the last question, and the pause controls. Actual UI; synthetic users; virtual time; 4:06.')
change(6,'How does a reviewed draft become available to students?','Detailed onboarding duplicated the video in the main talk.',
       title='Publication workflow: review before student access',foot='Read across the UML partitions. A published release is the approved course version used by students.',backup=True)
change(7,'Did the requested teaching style appear in the response?','Settings table and quote did not identify the requested sequence next to the observed response.',
       kind='teachingExample',title='The tutor asks for an attempt, but stays generic',
       intro='Saved Socratic-profile example: a course question about “slot seal”.',
       labels=['Requested teaching sequence','Saved tutor response'],
       left='Ask a diagnostic question.\nLet the student attempt an explanation.\nThen offer one hint.',
       takeaway='The tutor requests an explanation, but does not identify the specific misunderstanding.',
       foot='Saved example F21, not a controlled profile comparison. “Slot seal” is a concept in the synthetic course.')
change(8,'Which software decisions were compared?','Early architecture used research labels and an unexplained BKT integration caveat.',
       kind='focusFigure',title='The components behind answers and follow-ups',image=components,
       intro='Each experiment changes a specific part of this shared application.',
       takeaway='We compare how evidence is found, support is chosen, and the response is written.',
       foot='Simplified UML component view. Learner-estimator experiments are separate from the current input adapter.')
s[8].pop('termNote',None)
change(9,'Which studies run the application, and which simulate learners?','A single Study G diagram could not explain all three different evidence sources.',
       kind='table',title='Three kinds of evidence, with different claims',intro='The demo, operational trial and learner experiment are separate configurations.',
       rows=[['Evidence','What actually runs','What it can tell us'],['Demo video','Product services; scripted users; virtual time','How the visible workflow executes'],['Operational trial (G)','Product services + external models; synthetic users','Delivery, failures, consent and recovery'],['Learner experiment (E)','Simulated knowledge and contact decisions','Prediction errors and simulated outcomes']],
       widths=[270,445,445],points=['None of these is a real-student classroom trial.'],foot='Study E does not run the text retrieval/generation pipeline. Configurations and sources are in the notes.')
change(10,'Where did the complex factual designs reject usable evidence?','Failure location appeared only in the later narration, not in the paths.',
       title='Two answer paths shared the same faulty evidence check',
       foot='Failure: the highlighted checks required evidence for question-framing words, even when the answer was present.')
change(11,'How much did the shared check reduce answering?','A slash-separated secondary metric required readers to remember candidate order.',
       title='The shared check rejected many answerable questions',
       intro='Same 495 development cases. Grounded = all required answer claims supported by course evidence.',
       side=[['Answers given','Lexical: 100%\nHierarchy: 36.46%\nPlan–observe: 36.20%'],['Why it regressed','Both complex paths required evidence for the wording of the entire question.']],
       takeaway='Fix which facts are required before adding more retrieval stages.')
change(12,'Why is finding a passage insufficient?','A useful example was placed after the mechanism and used unnecessary contract jargon.',
       title='Finding the source does not guarantee a complete answer',
       takeaway='The question requires three items. The answer must include all three.',
       foot='Illustrative example, not a measured evaluation case. Grounded answers must be complete and source-supported.')
change(13,'What changed, and did extra ranking help?','Typed targets and cardinality were not decoded next to the result.',
       title='Stating the required facts improved answers',
       intro='Study A: tell the answer path what type of fact is needed and how many items to return.',
       takeaway='Keep the explicit answer requirement. Extra section ranking added no correct answers.',
       side=[['253 to 355 / 397','102 more complete, supported answers on the same development fold.'],['Extra ranking cost','Extra ranking: p95 rose from 1.36 to 2.79 ms. Both variants scored 355 / 397.']])
s[13]['charts'][0]['categories']=['Original rule','Explicit facts','Facts + ranking']
change(14,'Did complete retrieval become a correct final answer?','Three scores, gates and a long uncertainty sidebar competed for attention.',
       title='Evidence was usually found; complete answers still failed',
       intro='Study B: fresh sources; 800 answerable questions and 200 boundary cases.',
       side=[['506 / 800 answers','BM25: 63.25% grounded.\n95% CI: 58.75–67.63%.\nRequired threshold: 95%.'],['192 / 200 correct','BM25: 96% correct refusal or clarification. Required threshold: 98%.']],
       takeaway='Neither configuration passed both quality thresholds.',
       termNote='BM25: keyword ranking. Hybrid: keyword + semantic retrieval. CI: confidence interval.\nGenerated questions and rigid answer matching limit the test. @3 checks the top three retrieved results.')
s[14]['charts'][0]['categories']=['Evidence found @3','Complete answer','Correct boundary']
s[14]['charts'][0]['series'][0]['name']='BM25 + answer gate';s[14]['charts'][0]['series'][1]['name']='Hybrid + same gate'
change(15,'Did richer visual input improve the final answer?','The fresh candidate had an unexplained Omni label.',
       title='Visual retrieval improved, but final answers did not',
       takeaway='The visual candidates did not justify replacing their controls.',
       foot='Two separate 30-case studies. Grounded means complete and source-supported. Both controls still had citation limits.')
s[15]['charts'][1]['categories']=['Control','Image-capable']
change(16,'What do the planner alternatives do, and what failed?','Local letters carried the explanation and findings were too abstract.',
       title='A verifier could reject an action without replacing it',
       intro='Planner = the component that chooses the next allowed support action.',
       rows=[['Candidate','Selection method','Result / failure'],['A: rules','Choose by a fixed event rule','Retained baseline'],['B: proposal','Ask a model for an action','Did not justify replacing A'],['C: lookahead','Add estimated action consequences','Mixed results across metrics'],['C + V: verifier','Accept or reject C’s selection','Rejection returns no action']],
       widths=[250,465,445],points=['The rejected branch had no fallback. A usable action could be lost.'],
       termNote='V = verifier. These are project labels. Preferred-label agreement, action validity and utility are different measures.')
change(17,'What happens when a replacement is rejected?','Keep-baseline branch did not stand out from the rest of the diagram.',
       title='A rejected proposal now keeps the baseline action',
       termNote='A: rule baseline. H: guarded replacement. A proposal replaces A only after the shown conditions pass.')
change(18,'How large was the benefit and what does it mean?','Precise totals and local labels obscured the small paired effect.',
       title='Guarded replacement gave a small simulated score gain',
       intro='Study C: the same 1,000 contexts. Utility scores the selected action using a separate synthetic evaluator.',
       evidence=[['Average utility','Rules A: 0.7954     Guarded H: 0.8002'],['Paired gain','+0.004805; 95% CI [0.003065, 0.006760]'],['Rules satisfied','100% for both. Preferred-action agreement: 74% / 73%.'],['Extra operation','801 provider calls; 4 failed; historical total cost $0.335790.']],
       takeaway='The gain supports further testing. The model’s added value is still unisolated.',
       termNote='Missing control: select the analytic best action directly, without the model proposal. Utility is not measured learning.')
change(19,'How are learner estimation and timing different?','The header incorrectly implied that the count baseline uses elapsed time.',
       title='Estimate the learner’s knowledge, then decide when to send',
       intro='All estimators use assessed answers. BKT and this PFA implementation also account for elapsed time.',
       takeaway='An estimator predicts knowledge. A timing policy decides whether support is due.')
change(20,'What is the prediction being compared with?','Definitions gave no concrete numerical example of the two targets.',
       kind='metricExample',title='Knowledge estimates and next-answer predictions are different',
       intro='Study E: 240 simulated learners per condition, tested for 30 days on held-out random seeds.',
       items=[['Mean squared error (MSE)','Compare estimated knowledge with the hidden simulator state.'],['Next-answer error (Brier)','Compare the prediction before an attempt with its correct / incorrect outcome.']],
       examples=['Illustration: estimate 0.70; hidden state 0.80.\nSquared error = (0.70 − 0.80)² = 0.01.','Illustration: predicted success 0.70; answer correct (1).\nSquared error = (0.70 − 1)² = 0.09.'],
       takeaway='Lower is better for both, but each metric answers a different question.',
       termNote='Illustrative calculations, not measured cases. Test seeds share two authored simulator families.\nCount has no fitted parameters or forgetting; the alternatives do. Stronger controls are needed.')
change(21,'Did BKT predict actual answers better?','Long takeaway and abbreviations crowded the interpretation.',
       title='BKT improved estimates of hidden simulator knowledge',
       takeaway='Better fit to simulated knowledge did not establish better next-answer prediction.',
       termNote='BKT: Bayesian Knowledge Tracing. MSE: mean squared error. CI: confidence interval. Lower is better.\nThese are simulator outcomes. BKT is not connected to the default product adapter.')
s[21]['charts'][0]['title']='Hidden knowledge: MSE (lower is better)';s[21]['charts'][1]['title']='Next answer: Brier (lower is better)'
change(22,'What did fewer messages cost?','Policy names and hidden mastery needed to remain explicit with the result.',
       title='Halving messages also reduced simulated knowledge',
       intro='Study E: keep the count estimator fixed; compare when support is sent.',
       takeaway='Conditional timing: 7 fewer messages, but mastery fell by 0.012 [95% CI −0.018, −0.005].',
       termNote='Constant: every eligible check. Conditional: stalled or low/uncertain state. Value: estimated benefit passes a margin.\nMastery is hidden simulator state. Wasted-contact rates: 50.6%, 38.8%, 34.1%, respectively.')
change(23,'What information does the product planner actually receive?','Proxy title was too abstract for a visible and concrete integration defect.',
       title='Sending a message raises the planner’s “mastery” input',
       termNote='This is a delivery-count proxy, not a measured knowledge gain. Concept assessments inform completion separately.')
change(24,'How did the revised text change the source meaning?','Aggregate table came before the semantic example.',
       kind='semanticExample',title='The revision turned a requirement into a guarantee',
       intro='Study F: both revision candidates left the same class of critical semantic error.',
       takeaway='Two seals are necessary. The source does not say they guarantee acceptance.',
       foot='Paraphrase of the recorded defect, not a verbatim output. 56 adequate/defective pairs per candidate; AI-assisted review.')
s[24]['rows'][-1][0]='Critical errors (allowed: 0)'
change(25,'Why was a topic completed without evidence?','Abstract before/after flows hid the concrete two-topic bug.',
       kind='table',title='Evidence for Topic A incorrectly completed Topic B',
       intro='Recorded reproduction: two correct attempts on cache coherence (A); no assessment for virtual memory (B).',
       rows=[['Goal','Committed assessment evidence','Old status','Corrected status'],['Topic A','Two correct attempts on A','Completed','Completed'],['Topic B','No attempts on B','Completed','Still active']],widths=[190,450,250,270],
       points=['Correction: check each goal against evidence for its own target concepts.','Missing, unrelated or ambiguous evidence must not complete the goal.'],
       foot='Software completion rule: ≥2 correct, 0 incorrect and confidence ≥0.5 for every target. This does not validate mastery.')
change(26,'What changed after the scope correction?','Supported status and learning benefit were too easy to conflate.',
       title='The correction removed all 12 unsupported completions',
       intro='Study H: 72 synthetic histories per version, with deterministic planning and wording.',
       side=[['12 unsupported → 0','A completion is supported only by committed evidence for its own target concepts.'],['What changed','The tested scope rule is enforced. Assessment accuracy and mastery validity remain open.']],
       takeaway='Keep the correction. More follow-ups did not establish a learning benefit.',
       foot='Autonomous slice: 36 histories/version; +56 messages; simulated mastery change −0.0024. Dependent synthetic cases.')
change(27,'What if permission changes while an answer is generated?','Detailed call labels obscured the single consistency requirement.',
       kind='focusFigure',title='Permission can change while an answer is being written',image=authority,
       intro='Failure scenario: a release is withdrawn after the first permission check.',
       takeaway='Recheck current permission and state revision before saving any effects.',
       foot='Simplified UML sequence. Generation is outside the write transaction. Commit includes response, citations and learner update.')
change(28,'What if a worker stops after saving the message?','Recovery mechanism was clear only after reading dense method names.',
       kind='focusFigure',title='A retry must find the message that was already saved',image=retry,
       intro='Crash window: message saved, but job completion not yet recorded.',
       takeaway='The same delivery key reuses the saved message instead of creating a duplicate.',
       foot='Simplified UML sequence of local in-app recovery. Permission checks still apply. External effects are outside this guarantee.')
change(29,'What did the month-long operational trial actually demonstrate?','Dense metric columns hid the missing resumption and generic content.',
       kind='table',title='The system ran, but its follow-ups remained generic',
       intro='Historical Study G: 24 synthetic histories, 30 virtual days, actual external model calls.',
       rows=[['Observed behavior','Result','Interpretation'],['Tutor interactions','484 turns; 654 model calls','Execution included model failures'],['Proactive follow-ups','16 messages; 10 replies','Every check-in stayed generic'],['Consent disabled: days 10–19','No proactive messages','The off-window was respected'],['Later in the run','No resumed proactive delivery','Sustained support was not demonstrated']],widths=[350,370,440],
       points=['Local operation worked, but useful, sustained teaching remains unresolved.'],
       foot='24 restarts; 11 model calls reached the output cap; 13 tutor turns stopped in safe graph failure. Separate from the demo.')
change(30,'Which historical numbers should we stop using?','Internal terms made the invalidity decisions difficult to interpret.',
       title='Some earlier quality claims had to be withdrawn',
       rows=[['Evaluation problem','Consequence for the claim'],['Author saw the reference answer','10,000-case analysis is not independent quality evidence'],['Aggregate totals contradict each other','Exclude the unsupported grounded-answer percentage'],['More candidates tested than registered','Round 3 explains failures but cannot justify its selection'],['Preferred label treated as valid action','Report preference, rule validity and utility separately']],
       points=['The separately scoped factual, planner and completion results retain their stated claims.'])
change(31,'Which comparison addresses the integration gap?','Proposed input change lacked a simple operational question.',
       title='Next test: plan from student answers instead of delivery counts',
       intro='Proposed comparison: does relevant assessment evidence improve support decisions?',
       items=[['Current input','Counts delivered actions and events.\nA sent message can raise the “mastery” field.'],['Proposed input','Uses assessed answers for this goal’s concepts.\nKeeps missing and conflicting evidence explicit.']],
       takeaway='Hold the other components fixed. Test identical snapshots, then full histories.',
       foot='Measure useful, missed and inappropriate support, permissions, latency and cost. Independently check assessment quality.')
change(32,'What was delivered and learned?','Conclusion compressed several abstract claims into one long paragraph.',
       title='A working prototype and specific lessons from failed designs',
       sections=[['Delivered','Course configuration, question answering and scheduled follow-up with saved state.'],['Learned','Specify all required facts. Keep a fallback action. Complete only the goal supported by its own evidence.'],['Still open','Reliable factual answers, fidelity to the professor, and useful support for real students.']])
change(33,'Where can we find detail during questions?','Question page offered no useful navigation.',
       sections=[['System detail','Publication 33 / 37 · Data model 36 · Deployment 47'],['Methods','BKT example 34 · Full learner results 39 · Planner scores 44'],['Evidence limits','Models 40 · Corrections 42 · Validity 45 / 46']])
change(34,'How does BKT update a probability?','Dense inline equation hid the step result.',
       title='BKT worked example: from one answer to an updated belief',
       rows=[['Step','Calculation','Belief'],['Initial estimate','Assume 30% probability the concept is known','0.300'],['Correct answer','(0.30 × 0.90) / [(0.30 × 0.90) + (0.70 × 0.20)]','0.659'],['Learning during the attempt','0.659 + (1 − 0.659) × 0.30','0.761'],['One day of forgetting','0.761 × 0.95','0.723']],widths=[300,710,150],
       termNote='BKT: Bayesian Knowledge Tracing. Guess = 0.20; slip = 0.10; learning = 0.30; daily forgetting = 0.05.\nA worked calculation under assumptions, not an observed learner trajectory.')
change(35,'Who is outside the software boundary?','Context diagram lacked a direct reading instruction.',
       title='System context: professor, student and model provider',foot='Professor configures; student uses support; an optional external model supplies proposals. Application controls remain local.')
change(36,'How are records tied to the right course and goal?','Domain diagram had no stated reason for the associations.',
       title='Stored relationships keep turns and goals in their course scope',foot='UML domain model. Follow Course → Release → Conversation / Goal. Each message retains its citations.')
change(37,'What is committed at publication?','Sequence had a tiny transactional note and generic footer.',
       title='Publication records the approved release and retires old work',foot='UML sequence. The repository transaction replaces the release, withdraws its predecessor and cancels old work.')
change(38,'What exactly happened on rejection?','Repeated generic footer wasted the space needed to identify the branch.',
       title='Historical verifier: rejection ended with no action',foot='C: proposal plus analytic lookahead. V: accept/reject verifier. Follow [reject] to the missing replacement.')
change(39,'How do all learner and timing combinations compare?','Full table omitted units and the comparison scope.',
       intro='Study E: 240 learners per condition. Compare estimates and timing together; all outcomes are simulated.',
       title='All learner-model and timing combinations',
       termNote='MSE: hidden-state mean squared error, lower is better. Mastery: day-30 hidden state. Messages: per learner.\nWaste: contact at mastery ≥0.85 or while unreceptive. Oracle uses hidden information as a comparison bound.')
s[39]['rows'][0]=['Estimator + timing','MSE ↓','Messages','Waste ↓','Mastery']
change(40,'What supports the historical model allocation?','Slash-separated results mixed folds without explaining the decision.',
       title='Model allocation: small effects and a completion constraint',
       intro='Separate studies below. Compare alternatives within each row, not between rows.',
       rows=[['Comparison','Recorded result','Decision meaning'],['Fold 004: planner A / B / C / H','.7860 / .7564 / .7807 / .7880 utility','All obeyed tested action rules'],['Study C: rules A / guarded H','.7954 / .8002 utility','Small synthetic gain'],['Study D: Luna / Terra planner','.7935 / .7938 utility','Effect interval includes zero'],['Study D: Luna / Mini wording','100% final valid output, including fallback','Output validity includes recovery'],['Terra planner + Luna wording','238 / 240 generator calls completed','Failed the 99.5% completion requirement']],
       compact=True,points=['Study D retained Luna for both roles under its recorded selection rule.'])
change(41,'Where is the evidence for each decision?','Reference page used opaque decision language.',
       title='Evidence index: what each study supports',foot='Study IDs identify separate comparisons. Exact source paths appear in the speaker notes.')
s[41]['rows'][3][2]='Continue testing; no learning claim';s[41]['rows'][4][2]='Further study; BKT not integrated'
change(42,'How should corrected runs and the demo be used?','Reference labels lacked plain explanations.',
       title='Evidence index: invalid claims and the separate demo',
       foot='Read corrections with original results. The newer demo does not validate the historical model configuration.')
change(43,'When does a goal stop generating work?','Lifecycle diagram needed its software meaning stated.',
       title='Goal lifecycle: active, completed, expired or cancelled',foot='These are software states. An attempt limit stops more work but leaves the goal active; completed is not validated mastery.')
change(44,'Is the reported utility the planner’s own score?','Formula symbols were crowded in prose.',
       title='The planner’s score and the evaluator’s score are separate',
       items=[['Used to choose an action','U(a) = G + 0.45O + F + B − 0.9R − I\n\nG: gain; O: observation; F: future value; B: misconception bonus; R: evidence risk; I: interruption.'],['Used to evaluate that choice','Average registered value of the selected action across contexts.\n\nThe evaluator uses state information and a seeded hidden learner outcome.']],
       takeaway='Both depend on authored assumptions. Neither is measured student learning.',
       foot='Still missing: direct analytic selection without a model proposal. Full constants and calculation are in the report appendix.')
change(45,'What could explain the estimator advantage?','The limitations were dense abstractions rather than concrete follow-up controls.',
       title='Stronger controls are needed before choosing a learner model',
       items=[['Challenge the simulator','Current families are BKT-like and logistic-like.\nAdd a third family with different learning and forgetting assumptions.'],['Strengthen the simple baseline','Count has no fitting or forgetting.\nCompare against count with decay before attributing the gain to BKT.']],
       takeaway='PFA improved next-answer Brier by −0.010 [95% CI −0.013, −0.008]. BKT did not.',
       foot='Study E, constant timing. Hidden-state fit, next-answer prediction and educational benefit are separate questions.')
change(46,'Does confidence mean the learner was correct?','Confidence equation had no counterexample to explain its limitation.',
       kind='table',title='Evidence confidence counts attempts, not correct answers',
       intro='The completion rule also checks correctness. Confidence alone cannot establish knowledge.',
       rows=[['Two assessed attempts','Confidence n / (n + 2)','Passes the correctness condition?'],['Both correct','2 / 4 = 0.50','Yes, for this target'],['Both incorrect','2 / 4 = 0.50','No'],['One correct, one incorrect','2 / 4 = 0.50','No']],widths=[365,360,435],
       points=['Completion still requires the exact target, ≥2 correct and no incorrect assessments.'],
       foot='Confidence is capped at 0.95. These are illustrative cases of the software rule; assessment and mastery validity remain open.')
change(47,'Where do application, workers and records run logically?','Container labels were accurate but dense; the reading path was unstated.',
       title='Logical deployment: web app, services, workers and stores',foot='Read Web application → API → Runtime records; then the workers below. This is a logical view, not a scaling benchmark.')
change(48,'What do the learner and evaluation terms mean?','Glossary was useful but had a generic scope footer.',
       title='Glossary: learner models and evaluation',foot='For learner methods, see slides 17–20. BKT example: 34. Stronger controls: 45.')
change(49,'What do retrieval and planner labels mean?','Glossary needed direct navigation after reordering.',
       title='Glossary: retrieval, planner labels and scores',foot='For factual results, see slides 10–13. Planner alternatives: 14–16. Score definitions: 44.')

# Make the actual historical failure nodes visually identifiable, preserving UML.
for n,replacements in {
    10:{'Require whole-question coverage':'Require evidence for the\nwhole question wording'},
    17:{'Keep baseline A':'Keep the rule-based\nbaseline A'},
    23:{'Set probability proxy\n(n + 1) / (n + 2)':'Set planner “mastery” input\n(n + 1) / (n + 2)'},
}.items():
    f=ROOT/s[n]['image'];tree=E.parse(f.with_suffix('.drawio'))
    for c in tree.findall('.//mxCell'):
        v=c.get('value','')
        if v in replacements:
            c.set('value',replacements[v]);c.set('style',c.get('style','')+'fillColor=#FFF0E9;strokeColor=#A95438;fontStyle=1;')
    dest=OUT/(f.stem+'-focused.drawio');tree.write(dest,encoding='utf-8',xml_declaration=True)
    subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--format','png','--scale','1.5','--border','8','--embed-diagram','--output',str(dest.with_suffix('.png')),str(dest)],check=True,stdout=subprocess.DEVNULL)
    s[n]['image']=str(dest.with_suffix('.png').relative_to(ROOT))

# Reorder: concrete use, evidence and failures, then status and next work.
order=[1,2,3,5,8,7,9,12,10,11,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,4,31,32,33,6]+list(range(34,50))
mapping={old:new for new,old in enumerate(order,1)}
for i,old in enumerate(order,1):
    s[old]['number']=i;s[old]['backup']=i>=33;s[old]['old_number']=old
    # Avoid old, unused fields influencing future authoring or inspection.
    s[old].pop('gloss',None)
data['slides']=[s[n] for n in order]
data['main_slide_count']=31
(BUILD/'deck-content.json').write_text(json.dumps(data,indent=2))
(BUILD/'clarity-slide-map.json').write_text(json.dumps(mapping,indent=2))
lines=['# Full-slide clarity audit and revision','',
       '8 September 2026. All 49 source slides were inspected visually and for narrative clarity. The revised deck contains 31 main slides, Questions, and 17 backup slides. No study values were re-evaluated.',
       '', '| Old | New | Audience question | Finding and revision focus |','| --- | --- | --- | --- |']
for n in range(1,50):
    question,problem=audit[n];lines.append(f'| {n} | {mapping[n]} | {question} | {problem} |')
lines += ['', '## Cross-deck changes','',
          'Concrete workflow and actual inbox crops replace the abstract opening. Detailed publication moves to backup. The answer-completeness example precedes the factual failures. Status against the brief follows the evaluation evidence. All study IDs remain scoped to their source comparisons.',
          '', 'Charts retain source values, denominators and uncertainty where reported. Explanatory examples are marked as illustrative. Existing critical failures, invalid runs and missing ablations remain visible. Technical terms are explained on relevant pages and in backup glossaries.',
          '', 'All notes and Q&A references must be synchronized to the new order. Final rendering and validation status are recorded after build, not assumed from this audit.']
(ROOT/'reports/presentation/full-slide-clarity-audit.md').write_text('\n'.join(lines))
print('Applied clarity revision to all 49 pages; 31 main, Questions, 17 backup.')
