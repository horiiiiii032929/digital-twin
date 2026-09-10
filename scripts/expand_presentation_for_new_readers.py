"""Add project-specific orientation, worked examples and experiment questions."""
from pathlib import Path
import json,re
p=Path('reports/generated/slide-build/deck-content.json');d=json.loads(p.read_text());old={s['number']:s for s in d['slides']}
def slide(title,rows,notes,refs,foot='',points=None,intro=None):
 x=dict(title=title,kind='table',rows=rows,widths=[330,830],notes=notes,sources=refs,foot=foot)
 if points:x['points']=points
 if intro:x['intro']=intro
 return x
brief=['research/06_reports/final/chapters/01-objective.tex','research/06_reports/final/chapters/02-course-workflow.tex']
purpose=slide('What this system is designed to do',[
 ['Participant','Role in this project'],
 ['Professor','Publishes approved course materials, teaching preferences and learning objectives; can pause support.'],
 ['Student','Asks questions, submits attempts and chooses whether to receive proactive check-ins.'],
 ['Course digital twin','Answers from the published course; retains observations and goals; may initiate permitted support.'],
 ['Research question','Which designs make this continuing support correct, controlled and useful?']],
 'This project builds a course-specific teaching assistant configured by a professor. The student can ask questions and submit attempts. The system also keeps observations and goals between chats, so support can begin without another question. The professor remains responsible for the published materials and controls whether proactive support is enabled. In this project, digital twin describes that configured course assistant. It does not mean a validated replica of the professor’s judgement. The engineering question is how to connect configuration, evidence and accumulated observations, and which component choices are justified by comparisons.',brief,
 'Project-specific definition: “digital twin” does not imply that instructor identity or teaching fidelity has been validated.',
 intro='The intended experience is continuing, course-specific support between student questions.')
demo=slide('What to watch in the demonstration',[
 ['Recorded stage','What the audience should notice'],
 ['Onboarding and publication','Two professors configure two courses. Four synthetic students use the published course settings.'],
 ['Student asks, then stops typing','Saved activity creates support opportunities; advancing virtual time lets the existing worker process due work.'],
 ['Follow-up arrives','An inbox message appears without a new student question. One student replies; another does not.'],
 ['Pause and consent changes','Professor and student controls affect subsequent delivery; the closing activity view shows recorded actions.']],
 'The video compresses thirty virtual days into four minutes. First watch publication and student access. Then watch what happens after a student stops typing: the software processes due work and a message arrives without a new question. A reply and a non-response lead to different recorded histories. Pause and consent controls are also exercised. This is actual product UI with synthetic accounts, an accelerated clock and deterministic services. It demonstrates the operating loop; historical model-backed studies later examine other configurations. It is not a real classroom trial.',
 ['reports/presentation/recording/live-virtual-demo.md'],
 'Actual UI, synthetic accounts and virtual time; deterministic services. This recording is separate from the historical evaluations.',
 intro='30 virtual days → a 4:06 edited recording. Autonomy means acting—or waiting—without a new request.')
map_=slide('How to read the experimental evidence',[
 ['Evaluation question','Evidence used in this presentation'],
 ['Can it answer correctly?','Compare evidence selection and complete supported answers on cases with known required facts.'],
 ['Does it choose a permitted action?','Compare planners on the same contexts; distinguish valid actions, preferred labels and simulated utility.'],
 ['When should it contact a learner?','Cross learner estimators with timing policies in a controlled 30-day simulator.'],
 ['Does the integrated software behave correctly?','Inspect saved messages, authority checks, recovery and exact-objective completion.']],
 'The results answer several distinct questions. Factual tests have known required evidence and inspect the answer. Planner comparisons inspect action selection on shared contexts. The learner study varies estimation and timing in a simulator. Integrated histories inspect the software’s actual saved actions and state transitions. A high score in one category does not settle the others. Each result slide names its study and sample. We must compare candidates within that study, rather than combining percentages from different datasets into one ranking.',
 ['reports/presentation/design-comparisons.md'],
 'Study letters are local references. Each study has its own dataset, candidates and acceptance criteria.',
 intro='A working demo, a correct answer and useful teaching require different evidence.')
example=slide('Why a relevant passage can still produce a wrong answer',[
 ['Illustrative input','Question: “List all three stages.” Source: “The stages are draft, review and publish.”'],
 ['Retrieved evidence','The complete source sentence is found: retrieval succeeds.'],
 ['Incomplete answer','“Draft and review.” Both items are supported, but one required item is missing.'],
 ['Explicit answer requirement','Target type: a set of stages. Required count: 3. Required items: draft, review, publish.'],
 ['Evaluation consequence','A complete-answer check fails the two-item answer even though the source was retrieved.']],
 'This is an illustrative example of the contract, not a quoted evaluation case. Suppose the question asks for all three stages and the retrieved sentence contains draft, review and publish. An answer containing only draft and review is supported in what it says but incomplete. Retrieval succeeded; the full answer did not. An explicit target describes both the required type of answer and its cardinality. This is why the next comparison tests the required-fact contract, and why high retrieval coverage later does not imply high grounded-answer accuracy.',
 ['research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md'],
 'Illustrative explanation only; these stage names are not presented as a measured evaluation case.',
 intro='Retrieval finds evidence. The answer must still include every fact the question requires.')
bkt=slide('BKT example: updating one concept after an answer',[
 ['Step','Probability that the concept is known'],
 ['Before the attempt','Start at 0.30. A correct answer is possible even when the concept is unknown.'],
 ['Observe a correct answer','Bayesian update: (0.30 × 0.90) / [(0.30 × 0.90) + (0.70 × 0.20)] ≈ 0.659.'],
 ['Allow learning from the attempt','0.659 + (1 − 0.659) × 0.30 ≈ 0.761.'],
 ['One day without new evidence','Apply daily forgetting: 0.761 × 0.95 ≈ 0.723.']],
 'This calculation uses the evaluated BKT configuration. Start with a thirty-percent belief that one concept is known. The model permits a correct guess when it is unknown, and a slip when it is known. After a correct answer, Bayes’ rule gives about sixty-six percent. Allowing learning from the attempt raises the belief to about seventy-six percent. One day of the configured forgetting reduces it to about seventy-two percent. These values are model estimates under assumptions, not observed percentages of learning. The evaluation must therefore test how well the estimates agree with hidden simulator state and subsequent assessed outcomes.',
 ['src/digital_twin/student/learner_estimators.py','research/05_evaluation/successor-learner-timing-simulation-001-results.md'],
 'Worked calculation, not a recorded learner trajectory. Guess = 0.20; slip = 0.10; learning = 0.30; daily forgetting = 0.05.',
 intro='BKT models uncertainty: a correct answer does not prove that the learner knows the concept.')
# Questions supply the missing comparison context on result slides.
intros={
 2:'What was implemented, and which parts still lack sufficient acceptance evidence?',
 10:'Do hierarchy and explicit retrieval planning improve factual answering over the lexical control?',
 11:'Does specifying the required facts help more than adding another ranking stage?',
 12:'On fresh course sources, does retrieving all evidence produce a complete grounded answer?',
 13:'Does adding access to visual source regions improve the final answer, or only retrieval?',
 14:'Should extra model-based decision stages replace the deterministic action rule?',
 16:'The estimator tracks a concept; the timing policy decides whether to contact the learner.',
 17:'Fit on development seeds, then compare methods on held-out simulated learners.',
 18:'Hold timing fixed to compare estimators; hold the estimator fixed to compare timing.',
 22:'Did limiting evidence to the exact objective remove unsupported goal completion?',
 25:'Can the combined software operate for 30 virtual days—and what did it actually send?',
 26:'Which earlier claims must be withdrawn or narrowed after the evaluation audit?',
 27:'Change the planner’s input evidence while holding its other components fixed.'}
for n,t in intros.items():old[n]['intro']=t
# Replace local shorthand in the primary reading path.
old[10]['rows'][0]=['Design tried','Added mechanism','Grounded answers','Answers when possible']
old[14]['rows'][0]=['Local design','How it chooses an action','Finding']
old[18]['rows'][0]=['Estimator + timing','MSE ↓','Messages','Waste ↓','Day-30 mastery']
# Put key interpretation in ordinary-size body text on the closing slide.
old[28]['sections'][1][1]='Explicit required facts helped answering. Reject-only verification lost useful actions. Exact-objective evidence removed invalid completions.'
order=[1,'purpose',2,'demo',3,4,5,6,7,8,'map',9,10,'example',11,12,13,14,15,16,'bkt',17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37]
extras={'purpose':purpose,'demo':demo,'map':map_,'example':example,'bkt':bkt};new=[extras[k] if isinstance(k,str) else old[k] for k in order]
q=next(i for i,s in enumerate(new) if s['kind']=='questions')
for i,s in enumerate(new,1):s['number']=i;s['backup']=i>q+1
words=sum(len(re.findall(r"\b[\w’'-]+\b",s['notes'].split('\n\nTerminology')[0])) for s in new[:q])
d.update(slides=new,main_slides=q,main_word_count=words);p.write_text(json.dumps(d,indent=2))
lines=['# Reader-focused presentation script','',f'{q} main slides, Questions, {len(new)-q-1} backup slides. {words} narration words; video 4:06.','',f'At 170 words/min plus video: {words/170+4.1:.1f} minutes, before transitions. Definitions are reading support; avoid reading them twice.','']
for s in new:lines += [f"## {s['number']}. {s['title'].replace(chr(10),' ')}",'',s['notes'],'','Sources: '+', '.join(s['sources']),'']
Path('reports/presentation/speaker-script-reader.md').write_text('\n'.join(lines))
print(len(new),'slides;',q,'main;',words,'words')
