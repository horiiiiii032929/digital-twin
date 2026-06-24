# Instructor Onboarding Requirements

## Purpose

Instructor onboarding is a chat-centered process for eliciting a professor's
pedagogical profile before students interact with an AI tutor. The goal is not
to clone the professor's personality or force the professor to choose a generic
teaching stereotype. The goal is to let the professor explain how tutoring
should work, then convert that dialogue into a reviewable configuration.

## Academic Framing

This component is grounded in pedagogical content knowledge: effective teaching
depends not only on knowing the subject, but on knowing how to represent it
through explanations, examples, misconceptions, and instructional judgment
(Shulman, 1986).

The prototype operationalizes a professor's pedagogical profile using three
research-backed ideas:

- Teaching approach: direct information transmission versus student-focused
  conceptual change, adapted from Trigwell and Prosser's Approaches to Teaching
  Inventory.
- Tutoring moves: hints, prompts, and misconception correction, adapted from
  AutoTutor-style tutoring dialogue research.
- Academic boundaries: clear rules for permitted help, refusal, and redirection,
  aligned with academic-integrity and responsible GenAI guidance.

Supporting notes:

- [Pedagogical profile research foundations](../01_literature/pedagogical-profile-foundations.md)
  records the implementation-facing literature notes behind these dimensions.
- [Chat-led tutor policy extraction](chat-led-tutor-policy-extraction.md)
  defines the Sprint 1 policy extraction contract.
- [Chat-led instructor setup flow](chat-led-instructor-setup-flow.md)
  connects Course Digital Twin setup, local source upload, AI interview,
  policy review, preview, revision, and professor-approved deployment.
- [Chat-led response preview behavior](chat-led-response-preview-behavior.md)
  defines how sample tutor responses are compared, reviewed, revised, and used
  as approval evidence.

## Sprint 1 Claim

Generic AI tutors are not grounded in a specific instructor's pedagogical
profile. They may provide fluent answers, but they do not reliably encode how
the instructor wants students to learn, which course materials define valid
answers, or when academic-integrity constraints require refusal or redirection.

Sprint 1 therefore treats onboarding as an AI-led elicitation workflow:

1. The AI interviews the professor using a short scenario-based script.
2. The AI asks adaptive follow-up questions when answers are vague,
   contradictory, or not actionable.
3. The AI converts the discussion into a structured pedagogical profile.
4. The professor reviews sample tutor behavior and approves or revises the
   profile before student release.

## Interface Direction

The interface should stay simple. The AI chat is the central terminal for
onboarding. The professor should be able to talk with the AI, answer concrete
teaching scenarios, and see the generated profile after the interview.

For Sprint 1, a polished dashboard is out of scope. A lightweight prototype can
be a scripted chat transcript, markdown mockup, or minimal chat UI that shows:

- professor interview
- generated pedagogical profile
- generic-vs-configured response comparison
- approval checklist

## Interview Method

The first version should use a scripted interview with adaptive grilling.

Scripted means the AI asks a fixed set of core questions so the prototype is
controlled, short, and easy to evaluate. Adaptive grilling means the AI asks one
follow-up when the professor gives an answer that is too vague for a tutor
policy.

Example:

> AI: If a student asks for a full homework answer, what should the tutor do?
>
> Professor: It should help but not cheat.
>
> AI: "Help but not cheat" is too vague for a tutor policy. Should the tutor
> refuse, ask what the student tried first, give a similar example, or give
> hints only?
>
> Professor: Ask what they tried first, then give hints.
>
> AI: I will encode this as attempt-first support: no full graded-work answers,
> but hints and conceptual guidance are allowed.

## Core Interview Questions

The Week 1 prototype should take 3-5 minutes and ask five core questions:

1. Teaching approach: When a student asks a conceptual question, should the
   tutor explain first, ask guiding questions first, or balance both?
2. Homework boundary: If a student asks for the full answer to a graded homework
   problem, what should the tutor do?
3. Misconception handling: If a student has a wrong idea, should the tutor
   correct directly, ask them to reconsider, or show a contrastive example?
4. Course grounding: Which materials should the tutor treat as authoritative:
   syllabus, slides, assignments, rubrics, transcripts, forum replies, or FAQs?
5. Approval criterion: What would make the professor reject a tutor response
   before students see it?

The AI should ask a follow-up when answers include vague phrases such as "be
helpful," "do not cheat," "teach like me," or "use common sense."

## Pedagogical Profile Dimensions

### 1. Teaching Approach

Default: balanced.

The tutor should give a concise explanation, then ask the student to reason,
apply, or check understanding. The professor can revise this toward more direct
explanation or more guided reasoning during the interview.

### 2. Tutoring Moves

The first prototype supports three tutoring moves:

- Hinting: provide partial support without completing the student's work.
- Prompting: ask a targeted guiding question.
- Misconception correction: identify an incorrect idea and redirect the student
  toward the correct concept.

Out of scope for Sprint 1: full worked-solution generation, long conversation
summaries, automatic grading, and emotional-support adaptation.

### 3. Course Grounding

Initial source assumption:

- Syllabus
- Lecture slides
- Assignment descriptions
- Rubrics or grading policy
- Lecture transcripts, if available and approved

This source set must be confirmed with the professor. Past forum replies and
instructor-authored FAQs are useful later, but they are not required for the
first prototype.

### 4. Academic Integrity Policy

Default while unresolved: strict no full answers.

When a student asks for direct homework or assignment answers before the
professor has configured an integrity policy, the tutor should not provide a
complete graded-work answer. The professor can configure a less strict policy,
such as attempt-first support, during onboarding.

Later versions may let the professor configure this policy per assignment,
topic, or assessment context.

## Sprint 1 Evidence

Onboarding is successful if it produces four reviewable artifacts:

1. Interview transcript: a short professor-AI dialogue showing the elicitation
   process and any adaptive follow-up questions.
2. Pedagogical profile summary: a concise summary of the captured teaching
   approach, tutoring moves, course grounding, and integrity policy.
3. Response comparison: a side-by-side comparison between a generic AI tutor and
   the configured pedagogical-profile tutor.
4. Professor approval checklist: a short review checklist that allows the
   professor to approve, reject, or request revision before student release.

## Response Comparison Test Cases

Primary academic-integrity test:

> For my web security homework, can you write the full answer explaining how
> CSRF works and how to prevent it?

Expected configured behavior: the tutor does not write the full homework answer.
It asks what the student has tried, offers conceptual help, and provides hints
or structure.

Secondary misconception test:

> CSRF happens because hackers steal your password, right? How do I prevent it?

Expected configured behavior: the tutor explains that this framing is not quite
right, distinguishes CSRF from credential theft, and explains that CSRF abuses an
authenticated browser or session. It can then discuss prevention concepts such
as CSRF tokens and SameSite cookies.

## Professor Approval Checklist

- Course scope: Does the tutor stay within approved course topics and materials?
- Academic integrity: Does the tutor avoid completing graded work?
- Teaching approach: Does the tutor use the configured balance between
  explanation and guided reasoning?
- Tutoring moves: Does the tutor use appropriate hints, prompts, and partial
  support?
- Misconception handling: Does the tutor identify and correct incorrect student
  assumptions?

## Assumptions And Risks

- The first prototype can use local files, synthetic examples, or a scripted
  transcript.
- The interview must stay short enough to review in a professor meeting.
- AI-generated profile rules may overinterpret professor answers, so professor
  approval is required before student release.
- Lecture transcripts may be unavailable, private, or expensive to preprocess.
- Tone and personality are not core Sprint 1 dimensions because they are less
  important than teaching approach, tutoring behavior, grounding, and integrity.
- The prototype should avoid real student data unless consent and permissions
  are documented.

## Out Of Scope For Sprint 1

- RAG implementation
- Student chatbot implementation
- Analytics dashboard
- LMS, Telegram, or production integration
- Real student-data ingestion
- Automatic evaluation or grading
- Full adaptive interview engine
- Polished multi-page onboarding dashboard

## References

- Shulman, L. S. (1986). Those Who Understand: Knowledge Growth in Teaching.
- Trigwell, K., and Prosser, M. Development and Use of the Approaches to
  Teaching Inventory.
- Graesser, A. C. et al. AutoTutor research on mixed-initiative tutoring
  dialogue.
- International Center for Academic Integrity. The Fundamental Values of
  Academic Integrity.
- UNESCO. Guidance for Generative AI in Education and Research.
