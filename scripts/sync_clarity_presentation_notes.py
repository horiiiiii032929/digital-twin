"""Write the read-aloud script and references for the fully audited deck."""
from pathlib import Path
import html
import json
import re

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'reports/generated/slide-build'
OUT=ROOT/'reports/presentation/deck'
d=json.loads((BUILD/'deck-content.json').read_text())
s={x['number']:x for x in d['slides']}

s[2]['notes']='''Let me start with the interaction this software supports.

The professor provides the course materials and teaching settings, reviews them, and publishes the course assistant. The student then uses that published course to ask questions or submit attempts.

The application answers using the course material. The separate lanes show who is responsible for each step. The professor controls the approved course, the application produces the response, and the student decides what to ask or attempt.

This is the ordinary question-and-answer part of the system. The same course context also carries forward into continuing support. The application can retain observations and goals after the conversation ends.

The next page shows a concrete example of what that allows. It's the same student before and after a scheduled follow-up.'''
s[3]['notes']='''These are two cropped frames from the actual recording, both for student B1 on virtual day three.

On the left, the student has stopped typing and the inbox has no check-ins. On the right, a follow-up has arrived from the system.

The student didn't send another question between those events. The recording environment advances virtual time, and the application processes the work that becomes due. The resulting message appears in the student's inbox.

That's the autonomous behavior I want to make visible: the system can start the next contact using its saved state and scheduled work.

This example establishes that a message was delivered. It doesn't show that the software diagnosed a particular misunderstanding or that the advice improved learning. We'll examine those quality questions through the later studies.

Now I'll show the wider workflow, including setup and the controls around support.'''
s[4]['notes']=s[4]['notes'].replace('Now I\'ll look at the decisions behind that behavior, starting with how the professor\'s course becomes available to students.',"Now I'll show the components behind that workflow, then examine the decisions that were tested.")
s[5]['notes']='''This diagram connects the workflow you just saw to the parts of the software that were compared.

At the top are the tutoring and scheduled-support services. They check permission and save the result. The components below perform more specific jobs.

The evidence selector finds the course facts needed for an answer. The input adapter prepares the learner information that the planner receives. The action planner chooses the next support action. The wording generator writes the text the student sees.

These are separate boundaries. A change to how the system finds evidence doesn't automatically fix how it chooses a follow-up or writes that follow-up.

The studies therefore compare particular components while retaining the relevant shared controls. They don't form a single ranking of every possible complete system.

Before the technical comparisons, I'll show how a teaching preference appears in a saved response. That gives us a concrete way to distinguish a setting reaching the software from the resulting instruction being useful.'''
s[7]['notes']=s[7]['notes'].replace('There are several simulations in this presentation, so let me separate their roles.', 'This table separates three kinds of evidence used in the presentation. Each answers a different question.')
s[18]['notes']=s[18]['notes'].replace('The study also counts messages and wasted contact.', '''The small calculations on the slide illustrate the difference. If a knowledge estimate is zero point seven and the hidden state is zero point eight, the squared error is zero point zero one. If the probability of a correct answer is zero point seven and the next answer is correct, the squared error is zero point zero nine. These are illustrative numbers, not results from the experiment.

The study also counts messages and wasted contact.''')
s[23]['notes']=s[23]['notes'].replace('The old logic used strong concept evidence too broadly.', 'The table shows the consequence for each goal. The old logic used strong concept evidence too broadly.')
s[25]['notes']=s[25]['notes'].replace('The point to follow in the diagram is the boundary between preparing a response and committing its effects.', 'Read the sequence from top to bottom. The final exchange is the boundary between preparing a response and committing its effects.')
s[26]['notes']=s[26]['notes'].replace('The crash window in the diagram is between the message save and the job-result save.', 'The crash window is after the message save and before the job-result save. The lower part of the diagram shows the retry after restart.')
s[29]['notes']='''Now that we've seen the comparisons, this table returns to the project brief.

Course setup, reviewed publication, and student access are implemented. The local workflow checks provide evidence about those operations.

The answer path produces source-based responses with citations. However, the fresh factual comparison didn't meet its answer-quality thresholds. The existence of a citation is therefore not enough to call this requirement complete.

Teaching preferences enter the generation process, and the saved example showed part of the requested sequence. We still need a controlled evaluation of fidelity to the professor's teaching practice.

The application can keep goals and send scheduled messages. The integrated trial also showed that useful, sustained intervention remains unresolved.

Review, pause, and consent controls are available, but the selected components need to be evaluated together before a broader product claim.

This is the current position: a working prototype, specific local and synthetic evidence, and remaining quality requirements. The next slide proposes one focused comparison to address the planner's input gap.'''
s[33]['notes']='''This backup expands the publication process.

The professor provides materials and settings, reviews the draft, and requests preflight checks. A blocker sends the work back for revision. Once the checks pass, the application publishes the reviewed release and an authorized student can access it.

The release identifies the approved course version used by later tutoring and goals. This is why the approval process and the relationship between records matter when permissions or course materials change.'''
s[46]['notes']='''The three rows show why evidence confidence cannot be read as the probability that the student is correct.

With two assessed attempts, the confidence value is one half in every row. It is the same whether the attempts were both correct, both incorrect, or one of each.

The completion rule therefore checks correct and incorrect counts separately, as well as checking the exact target concept. Only the first row passes that correctness condition for the target.

This is an illustration of the software's rule. The audit can check that the rule is enforced, but it doesn't establish that two correct assessments prove mastery. Assessment accuracy, the threshold, and the treatment of earlier mistakes still need validation.'''

lines=['# Read-aloud script for the audited presentation','',
       'Read the paragraphs. Headings and the single video cue are navigation aids. Main talk: slides 1–31. Questions: 32. Optional backup responses: 33–49.','']
sections=[]
words=0
for x in d['slides']:
    number=x['number'];body=x['notes']
    lines += [f'## {number}. {x["title"].replace(chr(10)," ")}','',body,'']
    if number<=31:words+=len(re.sub(r'\[VIDEO CUE[^]]*\]','',body).split())
    ps=[]
    for p in body.split('\n\n'):
        tag='aside' if p.startswith('[VIDEO CUE') else 'p'
        ps.append(f'<{tag}>{html.escape(p)}</{tag}>')
    label='MAIN TALK' if number<=31 else ('QUESTIONS' if number==32 else 'OPTIONAL BACKUP')
    sections.append(f'<section id="slide-{number}"><small>{label} · SLIDE {number}</small><h2>{html.escape(x["title"])}</h2>{"".join(ps)}</section>')
d['main_word_count']=words
(BUILD/'deck-content.json').write_text(json.dumps(d,indent=2))
md='\n'.join(lines)
(OUT/'speaker-script-audited.md').write_text(md)
(ROOT/'reports/presentation/script/audited-narration.md').write_text(md)
page=(OUT/'speaker-script-natural.html').read_text()
options=''.join(f'<option value="slide-{x["number"]}">{x["number"]}. {html.escape(x["title"])}</option>' for x in d['slides'])
page=re.sub(r'(<select[^>]+>).*?(</select>)',lambda m:m[1]+options+m[2],page,flags=re.S)
intro=f'<h1>Audited presentation script</h1><div class="intro">Read the paragraphs. The shaded video cue is not spoken. Backup starts at slide 33.<br>{words:,} words in the main talk, plus the 4:06 video. Approximately {words/180+4.1:.1f}–{words/170+4.1:.1f} minutes at 180–170 words per minute, before pauses.</div>'
page=re.sub(r'<main>.*?</main>',lambda m:'<main>'+intro+''.join(sections)+'</main>',page,flags=re.S)
(OUT/'speaker-script-audited.html').write_text(page)
mapping=json.loads((BUILD/'clarity-slide-map.json').read_text())
q=(OUT/'defence-notes-natural-script.md').read_text().replace('digital-twin-presentation-natural-script.pptx','digital-twin-presentation-audited.pptx').replace('32 main slides','31 main slides').replace('sixteen backup','seventeen backup')
q=re.sub(r'(?i)(slide\s+)(\d{1,2})',lambda m:m[1]+str(mapping.get(m[2].lstrip('0'),int(m[2]))).zfill(2),q)
q=q.replace('Slide 03 / 32: What is the research contribution?', 'Slide 31: What is the research contribution?').replace('Reviewed: 7 September 2026.', 'Reviewed: 8 September 2026.')
(OUT/'defence-notes-audited.md').write_text(q)
print(f'Synchronized all 49 notes. Main script: {words} words; video on slide 4.')
