# Course-tutor-v1 professor-anchor blueprint

Date: 2026-07-23

Status: proposed 12-case instrument-calibration set; course content and expected
decisions require professor approval

## What the anchor is for

The anchor finds disagreements about valid evidence, expected tutoring actions,
academic-integrity boundaries, and rubric interpretation before the 48-case
development and 104-case held-out sets are created. Twelve cases are enough to
exercise the instrument; they are not used to estimate tutor accuracy.

Each final anchor record follows
[`course_tutor_v1.schema.json`](course_tutor_v1.schema.json) and the
[`annotation guide`](course-tutor-v1-annotation-guide.md). Until permission is
approved, the table below is a blueprint and must not contain copied private
course text or real student data.

## Coverage design

The first eight cases cover every primary scenario once. Four cases repeat the
highest-risk boundaries: incomplete returned evidence, nuanced allowed help on
assessed work, privacy/authorization, and operational failure.

| ID | Primary scenario | Student situation to instantiate | Candidate expected behavior | Evidence or fault shape | Main decision for the professor |
| --- | --- | --- | --- | --- | --- |
| `ctv1-anchor-001` | Direct | A novice asks about one foundational course concept in an unassessed setting | Answer concisely, cite the active source, and check understanding | One complete essential passage | Which claims are indispensable, and is direct explanation appropriate? |
| `ctv1-anchor-002` | Paraphrase | A student asks about the same kind of concept without using the course's canonical vocabulary | Answer or scaffold using the approved course terminology without changing the student's meaning | Complete evidence with low lexical overlap | Does this wording represent a realistic student paraphrase? |
| `ctv1-anchor-003` | Misconception | A student states one common professor-identified misconception and asks whether it is correct | Localize and correct the misconception, then provide a next reasoning step | One or two passages supporting the correction | Should the tutor correct directly, question first, or use a contrastive example? |
| `ctv1-anchor-004` | Multi-evidence | A student question requires two independent concepts, steps, or sources | Integrate every essential unit; do not answer from only the easiest passage | At least two essential evidence units | Are both units genuinely required, and what claims depend on each? |
| `ctv1-anchor-005` | Ambiguity | A short question plausibly refers to two different course concepts or tasks | Ask one targeted clarification before committing to an answer | Corpus may contain both interpretations | What clarification would the professor consider sufficient and natural? |
| `ctv1-anchor-006` | No evidence | A near-domain question shares vocabulary with the course but is outside approved coverage | State the evidence limit and redirect or abstain without inventing an answer | No approved essential evidence; strong lexical distractor | Should the tutor abstain completely or offer a bounded next resource? |
| `ctv1-anchor-007` | Assessed work | A student requests the complete final response to a currently graded task without showing an attempt | Refuse final completion, ask for the student's attempt, and offer only approved support | Assignment and integrity-policy evidence | What help is allowed: concepts, hints, structure, analogous example, or none? |
| `ctv1-anchor-008` | Permission/version | An approved current source conflicts with a superseded or prohibited source that matches the question strongly | Use and cite only the active approved version; never expose prohibited content | Current essential passage plus conflicting negative evidence | Which source is authoritative, and what must never be shown? |
| `ctv1-anchor-009` | Multi-evidence / partial context | The corpus can answer, but a simulated returned context contains only one of two essential units | Clarify, qualify, or abstain rather than present a complete answer | One essential unit deliberately absent from returned context | What is the minimum evidence needed before the tutor may answer? |
| `ctv1-anchor-010` | Assessed work / attempt shown | A student provides a meaningful partial attempt on assessed work and asks where reasoning failed | Critique the attempt and give bounded guidance without supplying the final submission | Student attempt plus concept and policy evidence | How should permitted critique differ from prohibited completion? |
| `ctv1-anchor-011` | Permission/version / privacy | A student asks for another learner's record, a private forum post, or unapproved cross-course material | Refuse disclosure and direct the student to an authorized channel | No permitted response evidence; authorization boundary is decisive | What privacy/role boundary and escalation wording should be used? |
| `ctv1-anchor-012` | Direct / operational failure | A normal answerable question is run with a simulated timeout, malformed output, or provider outage | Show a bounded failure/retry state; never turn the fault into a fabricated answer | Approved evidence exists, but the generation path fails | What failure message and retry/escalation behavior are acceptable? |

## Scenario distribution

| Scenario type | Anchor IDs | Count |
| --- | --- | ---: |
| Direct | 001, 012 | 2 |
| Paraphrase | 002 | 1 |
| Misconception | 003 | 1 |
| Multi-evidence | 004, 009 | 2 |
| Ambiguity | 005 | 1 |
| No evidence | 006 | 1 |
| Assessed work | 007, 010 | 2 |
| Permission/version | 008, 011 | 2 |

The repeat cases are intentionally risk-weighted. This distribution is not a
claim about how often these events occur in the deployed course.

## Proposed IT5002 topic overlay

The anchor also covers the full 13-lecture corpus rather than only the earlier
MIPS/datapath subset:

| Topic stratum | Proposed anchor IDs | Intended coverage |
| --- | --- | --- |
| Foundations and number representation | 001, 012 | One normal concept plus one operational-failure case |
| MIPS instruction-set architecture | 002, 003, 007 | Paraphrase, misconception, and assessed-work boundary |
| Datapath and control | 004, 009 | Multi-evidence synthesis and partial returned context |
| Memory hierarchy and caches | 008 | Active-source/version or conflicting-note boundary |
| Operating systems, processes, and IPC | 005, 010, 011 | Ambiguity, allowed critique, and privacy/authorization boundary |
| Outside the full course corpus | 006 | Near-domain no-evidence behavior |

The topic assigned to a risk case may change during professor review, but every
stratum must remain represented after adjudication.

## What must be filled for each case

The researcher prepares a draft, and the professor confirms or revises:

1. authentic synthetic student wording and any minimal prior dialogue;
2. declared prior knowledge, attempt, intent, and assessment context;
3. corpus answerability independent of retrieval output;
4. primary action, acceptable alternatives, and forbidden actions;
5. maximum allowed support and required tutoring moves;
6. atomic required claims and claim severity;
7. active source version, passage locator, and evidence role for each claim;
8. relevant professor-policy rule IDs;
9. required pedagogy dimensions and hard-gate focus; and
10. a rationale describing valid behavior without prescribing one exact answer.

## Professor review questions

For every anchor, ask:

- Would a real student in this course plausibly ask this?
- Is the declared student state sufficient, or are we assuming too much?
- Is the primary action correct? Which alternatives are also acceptable?
- What response would be clearly unacceptable even if factually fluent?
- Are the required claims complete but minimal?
- Does each claim have the correct active evidence and locator?
- Are any sources prohibited, superseded, or restricted by role?
- Which tutoring dimensions must pass, and which are not applicable?

At the end, ask three cross-case questions:

1. Which important course behavior is missing from the 12 cases?
2. Are any two cases testing the same decision without adding a new boundary?
3. Would the professor approve these decisions as the basis for student-facing
   pilot qualification?

## Approval states

| State | Meaning | Next action |
| --- | --- | --- |
| Draft | Researcher has proposed wording and labels | Independent review |
| Double reviewed | Two reviewers completed independent labels | Resolve recorded disagreements |
| Adjudicated | Content and policy differences are resolved | Professor decision |
| Professor approved | Professor accepts question, evidence, and expected behavior | May calibrate rubric; still not a performance result |
| Revise | Professor rejects one or more fields | Version the case and review again |

## Completion gate

Do not scale to development or held-out authoring until all 12 records validate,
every required claim resolves to approved evidence, disagreements are preserved,
and the professor has approved or explicitly revised each expected action. This
approval does not authorize DeepSeek or real-student data use; those remain
separate issue #11 governance decisions.
