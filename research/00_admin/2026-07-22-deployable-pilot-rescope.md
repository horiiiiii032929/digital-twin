# Deployable pilot rescope

Date: 2026-07-22

Status: active planning baseline; implementation has not started under this
rescope.

## Scope decision

The final project will deliver and evaluate a small, deployable Digital Twin
tutoring pilot that a professor and an invited group of students can use through
authenticated web accounts. The project is no longer scoped as only a local RAG
demonstration. Authentication, durable storage, student and professor roles,
deployment, privacy controls, monitoring, recovery, and supervised pilot use are
part of the required outcome.

The target is a controlled one-course pilot, not an institution-wide production
service. The provisional pilot size is one professor and 5-15 invited adult
students. The professor and institution must approve the actual cohort, course
materials, consent language, retention period, and model-provider data boundary
before real use.

## Research contribution

The project will not claim that its model or retrieval algorithm is universally
state of the art. It will make a stronger and more defensible contribution:

> Build a deployable professor-configurable, course-grounded tutor and evaluate
> every replaceable method and architecture boundary under shared data, safety,
> usability, reliability, latency, and cost criteria.

The final system comparison will hold the generator constant and separate the
effects of approved evidence and professor policy:

1. generic assistant without course evidence or professor policy;
2. approved oracle evidence with a generic tutoring policy;
3. the same oracle evidence with the professor-approved policy; and
4. retrieved evidence with the professor-approved policy.

This design distinguishes generator, policy, and retrieval effects. It also
keeps unfavorable or no-selection outcomes publishable.

## Required real-world user journeys

### Professor

1. Sign in and create or open a course.
2. Add course material and record its permission, sensitivity, and tutoring-use
   status.
3. Configure the tutor through the existing chat-led policy workflow.
4. Preview grounded responses, inspect sources, revise policy, and explicitly
   approve or withdraw student release.
5. Review a minimized audit of failures and student feedback without exposing
   unnecessary student content.

### Student

1. Sign in and join only an authorized course.
2. Ask a course question in a persistent conversation.
3. Receive a professor-policy-compliant answer with inspectable citations, or a
   clear refusal or insufficient-evidence response.
4. Open a source locator and understand why the tutor answered, redirected, or
   abstained.
5. Submit lightweight feedback and request deletion or correction through the
   documented pilot process.

## Required product boundaries

- One course and one professor for the evaluated pilot.
- English text, Markdown, and selectable-text PDF sources.
- Invited accounts only; no public signup.
- Professor and student role separation plus explicit course membership.
- Durable course, source, policy, release, conversation, message, citation,
  feedback, and audit records.
- Private document storage and server-side provider credentials.
- Data minimization: raw prompts and course content must not appear in ordinary
  application logs.
- Health checks, structured redacted logs, rate limits, timeouts, backup and
  restore evidence, rollback instructions, and a visible provider-failure path.
- A staging environment before any approved pilot environment.

## Deferred scope

- Canvas or another LMS connector.
- Institution-wide single sign-on unless the institution provides a low-risk
  test integration during the schedule.
- Multilingual, OCR, audio, video, and multimodal tutoring.
- Proactive learning triggers.
- Full learning-gap analytics or individual student profiling.
- Automatic grading, grade prediction, or assessed-work completion.
- Claims that the system improves grades, retention, or learning outcomes.
- Open public registration, multi-institution tenancy, or production-scale
  service-level commitments.

Proactive interaction and full analytics remain future-work candidates. They
are removed from the critical path rather than recorded as completed.

## Provider and data-governance gate

DeepSeek remains the fixed generator family for synthetic qualification, but it
is not automatically approved for real student or private course data. Before a
live pilot, the project must record:

- the exact model and API endpoint;
- the applicable privacy policy, terms, retention, training-use, location, and
  subprocessors;
- the institution's approval or rejection;
- student disclosure and consent or another valid institutional basis;
- fields removed or pseudonymized before provider calls;
- deletion and data-subject request handling; and
- an approved fallback when the external provider is unavailable or prohibited.

If this gate is not approved, the deployed application may still be evaluated
with synthetic invited testers, but it must not be represented as a real-student
pilot.

## Evaluation contract for every method

Every method or architecture choice must have a prospective plan before
implementation or held-out inspection. Each plan names:

- decision question and prediction;
- simplest control and bounded candidate set;
- shared development, calibration, and held-out inputs;
- primary metric, diagnostic metrics, and operational measures;
- privacy, permission, integrity, and reliability hard gates;
- sample-size or coverage rationale;
- failure taxonomy and rollback path; and
- Keep, Refine, Go Deeper, or Drop decision artifact.

| Boundary | Control | Bounded candidate | Primary evidence | Hard gates |
| --- | --- | --- | --- | --- |
| Parsing and chunking | Current heading/paragraph parser and chunker | One fixed-token or layout-aware alternative only if representative course failures justify it | Extraction completeness, boundary loss, required-claim coverage, latency | Approved source and provenance retained; unsupported input rejected |
| Retrieval | Term overlap regression control and selected BM25 v1 baseline | Existing dense/RRF result or one targeted successor; no broad model search | Complete-evidence success@3/5, gold-evidence recall, nDCG, no-evidence behavior, latency and footprint | Zero prohibited or superseded evidence |
| Context sufficiency | Any-hit rollback control | One prospectively selected verifier family | Complete/partial/none classification, answerability precision/recall, false answers and abstentions, calibration | Actual returned context is labeled; no corpus-category proxy; safety threshold frozen |
| Generator | Deterministic structural control and local fallback | One exact DeepSeek configuration | Required-claim recall, claim support, contradiction count, stability, latency, tokens and cost | Zero private pilot data before approval; zero high-severity unsupported claims |
| Prompt and professor policy | Generic prompt/policy condition | Grounded generic and professor-policy conditions with the same model and evidence | Blinded pedagogy, misconception repair, integrity action, citation correctness and completeness | Same questions, model, decoding, and evidence across paired comparisons |
| Conversation orchestration | Stateless single-turn control | Deterministic persisted state machine; graph orchestration only after a recorded failure | State consistency, duplicate handling, recovery success, multi-turn grounded success | Zero cross-user or stale-response leakage |
| Authentication and authorization | Current unauthenticated local prototype as a negative control | One managed or standards-based identity design selected before implementation | Role-matrix tests, invite completion, session expiry/revocation, auth latency and recovery | Zero professor/student or cross-course authorization bypass |
| Persistence and storage | Current in-memory repository as a negative durability control | Transactional database plus private object storage | Restart survival, migration and rollback success, backup/restore time, query latency | Zero cross-course access; deletion and retention rules enforced |
| Deployment | Local development run | One managed deployment architecture compatible with FastAPI and Vite | Deployment success, p50/p95 latency, error rate, cost, rollback and recovery time | TLS, secret isolation, health checks, staging, backup, and incident runbook |
| Professor usability | Existing deterministic onboarding walkthrough | Deployed professor workflow | Task completion, time, errors, source/policy comprehension, release confidence | Professor can block release and inspect evidence |
| Student usability | Scripted synthetic conversation | Supervised deployed student workflow | Task completion, citation and abstention comprehension, ease rating, feedback, failed-turn rate | Consent and withdrawal path; zero privacy or integrity violation |

## Pilot-level outcome measures

The final evaluation will emphasize three decision metrics:

1. **Unconditional safe grounded task success:** proportion of all evaluation
   cases that receive a correct supported answer when answerable or the correct
   refusal/abstention when not, with correct citations and policy action.
2. **Professor and student task completion:** proportion of required deployed
   tasks completed without researcher intervention, reported separately by role.
3. **Reliable turn completion:** proportion of authorized tutoring turns that
   complete within the frozen latency limit without timeout, malformed output,
   duplicate state, or unrecovered provider failure.

Guardrails are privacy/authorization violations, unsupported high-severity
claims, assessed-work violations, citation failures, p95 latency, cost per turn,
and deletion/retention failures. Numeric usability and latency targets remain
provisional until the protocol issue records pilot baseline evidence and the
professor approves them.

## Revised GitHub roadmap

| Target | Issue | Evaluated outcome | Professor report |
| --- | --- | --- | --- |
| 2026-07-24 | Professor checkpoint issue | Scope, users, data boundary, provider gate, and critical path approved | P0 scope and governance decision |
| 2026-07-25 | #11 | Method matrix, datasets, rubrics, thresholds, privacy protocol, and reporting plan frozen | Incorporated into P0 follow-up; written approval required before held-out runs |
| 2026-07-29 | #24 and #43 | Exact generator/prompt and context-sufficiency candidates qualified or rejected | Development evidence included in P1 |
| 2026-07-31 | #25 and #7 | Frozen end-to-end RAG result and selected or rejected grounded profile | P1 RAG method decision |
| 2026-08-10 | #8 | Authenticated, persistent professor/student application deployed to staging | P2 staging demonstration and architecture decision |
| 2026-08-15 | #9 | Security, privacy, reliability, rollback, and professor UAT gates passed or failed | P3 pilot go/no-go |
| 2026-08-22 | #10 | Approved supervised pilot completed and analyzed, or synthetic-user fallback explicitly reported | P4 pilot evidence and supported-claim decision |
| 2026-08-26 | #12 | Blinded comparison, failure analysis, limited refinement, and evidence freeze | Written evidence-freeze confirmation |
| 2026-09-03 | #13 | Full report draft, figures, and claim-to-evidence matrix | P5 report review |
| 2026-09-09 | Professor checkpoint issue | Timed demo and failure-recovery rehearsal completed | P6 final rehearsal |
| 2026-09-10 to 2026-09-12 | #13 | Contingency only: blocking corrections, packaging, and final checks without new claims | No routine checkpoint; escalate only a blocker |
| 2026-09-13 | #13 | Final report, deployed demonstration, and reproducibility package delivered | Final presentation |

## Professor checkpoint format

Each report is a short conversational update with one durable page under
`research/06_reports/weekly/`. It contains:

1. the exact decision requested;
2. status against the critical path: green, amber, or red;
3. the most important evidence table or figure;
4. the most important failure, privacy concern, or limitation;
5. the proposed Keep, Refine, Go Deeper, or Drop decision; and
6. the next checkpoint and consequences of delay.

Professor decisions are copied into `research/00_admin/decision-log.md` and the
corresponding GitHub issue. A meeting or polished demonstration without a
recorded decision is not a passed gate.

## Stop and fallback rules

- No product implementation starts until #11 freezes the evaluation and data
  governance protocol.
- No real professor or student data enters staging until permission, retention,
  and provider processing are approved.
- No student pilot begins until #9 passes authorization, privacy, recovery, and
  professor UAT hard gates.
- A failed RAG candidate produces a documented no-selection result; it does not
  delay authentication, persistence, and staging work if a safe rollback control
  can be used.
- If real-student approval is unavailable by 2026-08-15, run the deployed pilot
  with synthetic accounts and explicitly narrow the usability claim.
- No new architecture, model, metric, or feature begins after the 2026-08-26
  evidence freeze.
- Reserve 2026-08-27 through 2026-09-13 for report writing, figures,
  presentation work, demo stabilization, rehearsal, and contingency. Do not use
  this runway to recover deferred feature scope.
- Proactive triggers, full analytics, Canvas, multimodality, and learning-outcome
  claims are cut before any core deployability or evidence requirement.
