# Presentation structure revision 11: audience understanding

8 September 2026. Storyboard revision following the user’s review of slides 2–5. This document supersedes the opening logic of the previous proposal for planning purposes. The current deck and script are preserved; this is not a claim that replacement slides have already been produced.

## Diagnosis

The previous structure covered the right subjects, but the slides did not establish the relationships needed to understand them. The revised deck accumulated acceptance qualifications and research abstractions before introducing a concrete course-support interaction. More natural narration did not resolve that visual and conceptual gap.

| Current page | What makes it hard to follow | Editorial decision |
| --- | --- | --- |
| 2: participants | Three text columns describe roles. The title describes continued support, while the subtitle introduces demo statistics and the footer introduces the research question. There is no visible interaction. | Replace with one concrete course-support scenario and an explicit explanation of what the professor, student and software do. |
| 3: contribution | Required-fact contracts, fallback composition and exact-objective evidence appear before the audience has seen the problems they address. | Explain contributions through the subsequent examples and summarize them at the end. Remove the abstract contribution slide from the opening. |
| 4: delivery against the brief | The audience must interpret quality gates, releases, fidelity and composition before seeing the system. Every row introduces another unresolved idea. | Retain the evidence, but place the detailed status table near the conclusion, after those terms and results are meaningful. State the narrow prototype scope briefly at the start. |
| 5: demo | The poster contains a whole interface with small text. Its relevant event is not visually isolated. Earlier pages do not establish an expected sequence. | Give the viewer a specific event to recognize before playback. Use an actual frame emphasizing the scheduled message as the poster. Review whether the video itself makes the event identifiable. |

The original outline also put a detailed acceptance table too early. The problem is partly in the outline, as well as in how it was turned into slides.

## Opening storyboard

### 1. Course Digital Twin

Audience question: What did this project build?

Visible statement: “A professor-configured course assistant that answers questions and can follow up later.”

Use the project title, author and this plain scope statement. Avoid a second abstract thesis sentence. State orally that this is a research prototype evaluated with synthetic users.

### 2. A course assistant for the professor and students

Audience question: What do these people actually do with this software?

Show one course scenario. The professor supplies the course material and teaching settings. A student asks a question or submits an attempt. The assistant responds using the published course information.

Visual: a small standard UML activity diagram with professor, application and student partitions, authored in draw.io. Use concrete action labels. Keep publication mechanics, database objects and policy branches for later pages or backup. Actual screen crops can provide recognizable input/output examples, but should not become a second competing diagram.

Takeaway: “The professor configures the course assistant; students use it for course support.”

Do not introduce demo account counts, evaluation metrics or research-contribution terminology on this page.

### 3. A follow-up can arrive without a new student question

Audience question: What is autonomous about it?

Visual: two readable crops from the same verified recording history, showing the earlier interaction and the later inbox message. Label the virtual times and identify the student consistently. Describe the intervening behavior in one sentence: saved state and scheduled work can lead to a follow-up. Do not imply that the system diagnosed a misconception or that the message was useful unless the selected evidence supports it.

Takeaway: “The system can start the next contact after the student stops typing.”

This is a concrete example of implemented behavior. It does not need BKT, a general definition of autonomy, or the full runtime architecture.

### 4. Demo: setup, interaction and scheduled follow-up

Audience question: Can I recognize that behavior in the application?

Use the actual recording, with the simple spoken viewing instruction: “Watch the student's inbox after their last question, then watch what happens when support is paused.” Match that instruction to verified scenes before finalizing it.

Use a poster frame that clearly shows the inbox event. Keep the disclosure concise and readable: actual software, synthetic users, accelerated virtual time. Account counts belong in a small recording caption, not the main explanation of the product.

Review the video for readable crops, visible before/after events and captions naming the action. Speed-up should compress waiting, not remove the moment needed to understand a state change. Do not silently substitute an idealized simulation or re-record the product without a separate concrete production need.

Takeaway: “The recording demonstrates how the support workflow executes.”

### 5. The components behind the demonstrated workflow

Audience question: What software makes that happen, and where were the design choices?

Visual: a simplified, standard UML component view from draw.io. Reuse the factual product boundaries. Introduce the evidence selector as the component that finds course facts, the planner as the component that chooses support, and the wording generator as the component that writes the response. Show that observations and the adapter supply planner inputs. Keep detailed provider and deployment relationships in backup.

Takeaway: “The experiments compare specific decisions inside this workflow.”

The narration now has concrete references: the answer and follow-up the audience just saw. Introduce technical names after identifying their jobs.

## Proposed main sequence

The count is a planning estimate, not a requirement. Combining pages must not result in smaller text or a diagram plus a second full page of results squeezed beside it.

| New | Audience question / page purpose | Dominant evidence or visual | Existing material |
| --- | --- | --- | --- |
| 1 | What did you build? | Title and one plain scope sentence | 1 |
| 2 | How do a professor and student use it? | Concrete course scenario, small UML activity | Replace 2; selected 6 material |
| 3 | What happens without another question? | Two actual frames of the same student's history | Recording assets; replace abstract 3 |
| 4 | Can we see the workflow execute? | Existing demo, reviewed viewing focus | 5 |
| 5 | Which components make this happen? | Simplified UML component diagram | 8; detail from 47 only as needed |
| 6 | Did the teaching settings affect the response? | Saved setting and response, annotated exact mismatch | 7 |
| 7 | What was real software and what was simulated? | Compact comparison of demo, operational trial and learner experiment | 9; detailed harness diagram in backup |
| 8 | Why can a relevant passage still give an incomplete answer? | Three-stage source and incomplete answer example | 12 |
| 9 | Why did the first factual designs answer less often? | Historical paths, common failed check, compact same-study result | 10–11 |
| 10 | What improved the answer requirement? | Explicit target example with quality/latency comparison | 13 |
| 11 | Did it pass on fresh sources? | Retrieval-versus-final-answer chart, denominators and outcome | 14 |
| 12 | Did visual evidence solve that gap? | Separate visual comparisons and their decisions | 15 |
| 13 | Why did adding a verifier remove useful actions? | Candidate differences and reject branch, explicit consequence | 16 and backup 38 |
| 14 | Did keeping the baseline help? | Guarded branch and small paired result | 17–18 |
| 15 | How were knowledge and timing represented? | Estimator and policy definitions tied to a concrete decision | 19 |
| 16 | How can those estimates be evaluated? | Observed answer versus hidden simulator target, simple example | 20 |
| 17 | What did BKT actually improve? | Two charts, two prediction targets | 21 |
| 18 | Did sending less support improve the outcome? | Message/mastery/waste comparison | 22 |
| 19 | Does the product use that learner model? | Delivery proxy example and actual adapter boundary | 23 |
| 20 | Could revision preserve the source meaning? | Exact source and necessary/sufficient error | 24 |
| 21 | Why did an unassessed topic become complete? | Two-topic failure, historical and corrected scope | 25 |
| 22 | What did the correction fix, and what did it leave unresolved? | Supported/unsupported counts and support tradeoff | 26 |
| 23 | What if permission changes during generation? | Focused UML sequence and commit boundary | 27 |
| 24 | What if the worker crashes after saving a message? | Focused UML sequence and retry identity | 28 |
| 25 | How did the integrated historical system behave? | Operational counts plus saved generic check-in evidence | 29 |
| 26 | Which results cannot support the original claims? | Specific corrections and surviving evidence | 30 |
| 27 | What remains against the brief, and what should change next? | Concise status table linked to the proposed adapter comparison | 4 and 31; full experiment plan in backup |
| 28 | What did the project contribute? | Concrete deliverable and evidence-backed design findings | 3 and 32 |

A Questions page and the existing relevant backup evidence follow. Re-map all backup references only after the main sequence is settled. Keep worked BKT calculations, model allocation, full grids, formulas, detailed domain/deployment diagrams and source indexes accessible.

## How each research page should work

Use a concrete sequence within each research section: observed problem, design tried, result, explanation and decision. Do not force every page into the same three-column template.

For each page, write these four items before authoring:

1. The one question a new listener should be able to answer afterward.
2. The specific screenshot, diagram, example or chart that answers it.
3. The sentence that states what the evidence supports.
4. The prerequisite idea, introduced on a named earlier page.

Use actual component names consistently, with short explanations at first use. For example, “planner: chooses the next support action.” Avoid unexplained internal language such as “full current composition” when “the selected components running together” carries the intended meaning.

Place the failure location or measured contrast next to the relevant visual. A chart without a named comparison, or a screenshot without an identified event, is incomplete communication even if all the facts appear somewhere in the notes.

Keep material qualifications near the result they limit. Opening scope should remain clear, but it should not become an audit before the audience understands the software. Preserve all unfavorable results and measurement limits in the relevant pages and backup.

## Review gate before full deck rebuilding

First produce the opening five pages as a coherent set and review them without the script. A reader should be able to explain:

- Who configures the system, and what a student does with it.
- What the software can do after a student stops typing.
- What the recording demonstrates.
- Which components the later experiments compare.

Then review the matching spoken script. It should explain the visible material in order, with no hidden prerequisite supplied only by narration. Rebuild later sections using the same question/visual/claim check.

The immediate deliverable is this revised storyboard. Existing finalized slides, video, submitted report and evidence remain unchanged. No new evaluation results are introduced.

## Timing

Plan for approximately 33–35 minutes for the main talk including the existing 4:06 video. Use roughly 8 minutes for the opening and methodology, 20 minutes for design findings and runtime behavior, and 5–7 minutes for integrated evidence, corrections and conclusions. These are allocations, not a rehearsal result. Recompute word count after the rewritten slides establish the story. Do not pad the opening to preserve the previous script's word count.
