# Pedagogical profile research foundations

Date: 2026-06-24

## Purpose

This note records research foundations for the chat-led instructor onboarding
direction. It should support implementation decisions for tutor policy
extraction, response preview behavior, and later evaluation.

The main product implication is that the system should not ask professors to
choose a vague "teaching style" label. It should elicit a reviewable
pedagogical profile: the professor's preferred ways of explaining concepts,
guiding student thinking, handling misconceptions, scaffolding help, enforcing
academic boundaries, and approving tutor behavior.

## Design stance

Use "pedagogical profile" or "tutor policy" for implementation-facing work.
Avoid using "learning styles" as the conceptual model for the tutor. The
learning-styles literature does not provide strong support for assigning
students to fixed modality categories and then tailoring instruction around
those categories. If learning styles are mentioned, cite them only as a risk to
avoid, not as a system design basis.

## Research-backed dimensions

### Pedagogical content knowledge

Shulman's pedagogical content knowledge argues that effective teaching combines
subject-matter knowledge with knowledge of how to make that subject teachable:
examples, analogies, explanations, demonstrations, and common misconceptions.

Implementation implication: the onboarding chat should ask professors about
common misconceptions, preferred examples, hard-to-teach concepts, and what
makes a response acceptable for their course.

### Teaching approach

Trigwell and Prosser's Approaches to Teaching Inventory distinguishes
information-transmission/teacher-focused approaches from
conceptual-change/student-focused approaches. This is more defensible than
asking for a personality-like "style" label.

Implementation implication: the onboarding chat should ask whether the tutor
should explain first, guide the student with questions first, or balance direct
explanation with guided reasoning. The output should be a policy field, not a
fixed identity label.

### Cognitive engagement target

Chi and Wylie's ICAP framework classifies engagement as passive, active,
constructive, or interactive. The core design value is that tutors should not
only transmit answers. They can ask students to explain, compare, predict,
apply, or revise their own reasoning.

Implementation implication: the tutor policy should include when the tutor
should ask for student reasoning, prompt self-explanation, or turn an answer
into a short interactive exchange.

### Effective study support

Dunlosky et al. reviewed common study techniques and identified practice
testing and distributed practice as high-utility techniques. This gives a
research-backed basis for proactive support that is more concrete than generic
"helpful reminders."

Implementation implication: proactive tutor behavior should prefer retrieval
practice, short checks for understanding, spaced review prompts, and targeted
practice questions when the course policy allows them.

### Feedback policy

Hattie and Timperley frame feedback as powerful but variable in quality. Useful
feedback helps close the gap between current performance and a goal; vague
praise is not enough.

Implementation implication: the tutor policy should distinguish task feedback,
process feedback, and self-regulation feedback. The tutor should avoid generic
encouragement when a student needs actionable correction.

### Scaffolding and tutoring moves

Wood, Bruner, and Ross describe tutoring as scaffolding problem solving through
actions such as recruiting attention, reducing degrees of freedom, maintaining
direction, marking critical features, and controlling frustration. AutoTutor
research and intelligent tutoring systems literature add dialogue-level moves
such as prompts, hints, feedback, misconception correction, and
expectation-based tutoring.

Implementation implication: the onboarding chat should extract allowed tutoring
moves: whether the tutor may give hints, ask guiding questions, show analogous
examples, identify misconceptions directly, or provide partial structure.

### Intelligent tutoring effectiveness

VanLehn's review of tutoring systems is useful for framing why step-based or
dialogue-based tutoring behavior matters. Graesser et al.'s AutoTutor work is a
direct precedent for natural-language tutoring with mixed-initiative dialogue.

Implementation implication: the digital twin should be evaluated as a tutoring
interaction, not only as a question-answering system. Preview tests should
include multi-turn behavior, hints, misconception handling, and refusal or
redirection under academic-integrity constraints.

## Implications for issue #2

Issue #2 should define a generic, reusable chat-extracted tutor policy schema.
It should not define one real professor's course-specific answers. The real
course name, allowed sources, topics, assignments, and grading boundaries should
be collected by the onboarding chat later.

The policy schema should include:

- teaching approach: direct explanation, guided reasoning, or balanced
- engagement target: answer, prompt, self-explanation, practice, or interaction
- tutoring moves: hints, prompts, worked analogies, contrastive examples, and
  misconception correction
- feedback policy: task, process, and self-regulation feedback
- academic-integrity boundary: refuse, ask what the student tried, give hints,
  give analogous examples, or allow full solution only when appropriate
- source-grounding rules: allowed materials, disallowed materials, and citation
  expectations
- proactive support: retrieval practice, spaced review, short checks, or none
- approval criteria: reasons the professor would reject or revise a tutor
  response
- unresolved fields: answers that remain unknown, low-confidence, or blocked
  until professor confirmation

The chat should push back when the professor gives vague or non-operational
answers such as "be helpful," "teach like me," "do not cheat," "use common
sense," or "make it friendly." A usable policy needs concrete behavior rules.

## Source quality note

When writing project documentation, cite canonical journal or publisher pages
where possible. PDFs hosted by universities, personal sites, or repositories may
be useful for reading, but they should not replace the canonical citation.

## References

- Chi, M. T. H., & Wylie, R. (2014). The ICAP framework: Linking cognitive
  engagement to active learning outcomes. Educational Psychologist, 49(4),
  219-243. https://doi.org/10.1080/00461520.2014.965823
- Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham,
  D. T. (2013). Improving students' learning with effective learning
  techniques: Promising directions from cognitive and educational psychology.
  Psychological Science in the Public Interest, 14(1), 4-58.
  https://doi.org/10.1177/1529100612453266
- Graesser, A. C., Chipman, P., Haynes, B. C., & Olney, A. (2005).
  AutoTutor: An intelligent tutoring system with mixed-initiative dialogue.
  IEEE Transactions on Education, 48(4), 612-618.
  https://doi.org/10.1109/TE.2005.856149
- Hattie, J., & Timperley, H. (2007). The power of feedback. Review of
  Educational Research, 77(1), 81-112.
  https://doi.org/10.3102/003465430298487
- Pashler, H., McDaniel, M., Rohrer, D., & Bjork, R. (2008). Learning styles:
  Concepts and evidence. Psychological Science in the Public Interest, 9(3),
  105-119. https://doi.org/10.1111/j.1539-6053.2009.01038.x
- Shulman, L. S. (1986). Those who understand: Knowledge growth in teaching.
  Educational Researcher, 15(2), 4-14.
  https://doi.org/10.3102/0013189X015002004
- Trigwell, K., & Prosser, M. (2004). Development and use of the Approaches
  to Teaching Inventory. Educational Psychology Review, 16(4), 409-424.
  https://doi.org/10.1007/s10648-004-0007-9
- Trigwell, K., Prosser, M., & Waterhouse, F. (1999). Relations between
  teachers' approaches to teaching and students' approaches to learning.
  Higher Education, 37, 57-70. https://doi.org/10.1023/A:1003548313194
- VanLehn, K. (2011). The relative effectiveness of human tutoring,
  intelligent tutoring systems, and other tutoring systems. Educational
  Psychologist, 46(4), 197-221.
  https://doi.org/10.1080/00461520.2011.611369
- Wood, D., Bruner, J. S., & Ross, G. (1976). The role of tutoring in problem
  solving. Journal of Child Psychology and Psychiatry, 17(2), 89-100.
  https://doi.org/10.1111/j.1469-7610.1976.tb00381.x
