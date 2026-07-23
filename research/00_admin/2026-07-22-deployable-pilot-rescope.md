# Deployable pilot rescope

Date: 2026-07-22

Status: active planning baseline; implementation has not started under this
rescope.

## Scope decision

The final project will deliver and evaluate a small, deployable Digital Twin
tutoring system for one professor and one course. The project is no longer
scoped as only a local RAG demonstration. Authentication, durable storage,
student and professor roles, deployment, privacy controls, monitoring, recovery,
simulated-student evaluation, and scripted synthetic-account acceptance are
part of the required outcome.

The target is a controlled one-course research deployment, not an
institution-wide production service. Student recruitment is out of scope.
Professor review is used to approve course truth and evaluation instruments;
frozen simulated students and synthetic accounts provide multi-turn and
deployment stress tests. The professor and institution must still approve
course-material tutoring use and the model-provider data boundary.

## Research contribution

The project will not claim that its model or retrieval algorithm is universally
state of the art. It will make a stronger and more defensible contribution:

> Build a deployable professor-configurable, course-grounded tutor and evaluate
> every replaceable method and architecture boundary under shared data, safety,
> grounding, pedagogy, reliability, latency, and cost criteria.

The final system comparison will hold the generator constant and separate the
effects of approved evidence and professor policy:

1. generic assistant without course evidence or professor policy;
2. approved oracle evidence with a generic tutoring policy;
3. the same oracle evidence with the professor-approved policy; and
4. retrieved evidence with the professor-approved policy.

This design distinguishes generator, policy, and retrieval effects. It also
keeps unfavorable or no-selection outcomes publishable.

## Required deployed user journeys

### Professor

1. Sign in and create or open a course.
2. Add course material and record its permission, sensitivity, and tutoring-use
   status.
3. Configure the tutor through the existing chat-led policy workflow.
4. Preview grounded responses, inspect sources, revise policy, and explicitly
   approve or withdraw student release.
5. Review a minimized audit of failures and synthetic feedback without exposing
   private course content unnecessarily.

### Student

1. Sign in and join only an authorized course.
2. Ask a course question in a persistent conversation.
3. Receive a professor-policy-compliant answer with inspectable citations, or a
   clear refusal or insufficient-evidence response.
4. Open a source locator and understand why the tutor answered, redirected, or
   abstained.
5. Submit lightweight synthetic feedback and exercise deletion or correction
   through the documented acceptance flow.

## Required product boundaries

- One course and one professor for the evaluated research deployment.
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
- A staging environment for synthetic-account acceptance and professor review.

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
is not automatically approved for private course data. Before any
course-specific provider call, the project must record:

- the exact model and API endpoint;
- the applicable privacy policy, terms, retention, training-use, location, and
  subprocessors;
- the institution's approval or rejection;
- fields removed or pseudonymized before provider calls;
- deletion and incident handling; and
- an approved fallback when the external provider is unavailable or prohibited.

If this gate is not approved, all course-specific tutoring, simulation, and
judging run locally. No real student or participant data is required.

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
| Generator | Deterministic structural control and local fallback | One exact DeepSeek configuration | Required-claim recall, claim support, contradiction count, stability, latency, tokens and cost | Zero private course data before approval; zero high-severity unsupported claims |
| Prompt and professor policy | Generic prompt/policy condition | Grounded generic and professor-policy conditions with the same model and evidence | Blinded pedagogy, misconception repair, integrity action, citation correctness and completeness | Same questions, model, decoding, and evidence across paired comparisons |
| Conversation orchestration | Stateless single-turn control | Deterministic persisted state machine; graph orchestration only after a recorded failure | State consistency, duplicate handling, recovery success, multi-turn grounded success | Zero cross-user or stale-response leakage |
| Authentication and authorization | Current unauthenticated local prototype as a negative control | One managed or standards-based identity design selected before implementation | Role-matrix tests, invite completion, session expiry/revocation, auth latency and recovery | Zero professor/student or cross-course authorization bypass |
| Persistence and storage | Current in-memory repository as a negative durability control | Transactional database plus private object storage | Restart survival, migration and rollback success, backup/restore time, query latency | Zero cross-course access; deletion and retention rules enforced |
| Deployment | Local development run | One managed deployment architecture compatible with FastAPI and Vite | Deployment success, p50/p95 latency, error rate, cost, rollback and recovery time | TLS, secret isolation, health checks, staging, backup, and incident runbook |
| LLM judge | Authored/deterministic rubric labels | Calibrated fixed judge plus distinct-family sensitivity judge | Expert agreement, exact agreement, order/repeat consistency, false passes | No hard-gate override; diagnostic only if calibration fails |
| Multi-turn tutoring | Authored scripted turns | Frozen simulated-student trajectories | Safe trajectory completion, checkpoint actions, recovery, policy drift, simulator validity | Simulator never judges success; no human-outcome claim |
| Deployed acceptance | Local API/UI checks | Scripted professor/student synthetic accounts | Journey completion, role isolation, persistence, recovery, latency | Operational evidence only; no human-usability claim |

## Pilot-level outcome measures

The final evaluation will emphasize three decision metrics:

1. **Unconditional safe grounded task success:** proportion of all evaluation
   cases that receive a correct supported answer when answerable or the correct
   refusal/abstention when not, with correct citations and policy action.
2. **Professor-policy pedagogical success:** proportion of applicable cases
   passing every required pedagogy dimension after the LLM judge passes frozen
   expert-anchor calibration.
3. **Multi-turn safe trajectory completion:** proportion of valid frozen
   simulated-student trajectories that pass every expected-action checkpoint
   and reach the stop state without leakage, policy drift, unsupported claims,
   or operational failure.
4. **Reliable turn completion:** proportion of authorized tutoring turns that
   complete within the frozen latency limit without timeout, malformed output,
   duplicate state, or unrecovered provider failure.

Guardrails are privacy/authorization violations, unsupported high-severity
claims, assessed-work violations, citation failures, p95 latency, cost per turn,
and judge/simulator validity. Pedagogical scores are diagnostic unless the
judge passes calibration. Human usability and learning are explicitly
unmeasured.

## Revised GitHub roadmap

| Target | Issue | Evaluated outcome | Professor report |
| --- | --- | --- | --- |
| 2026-07-24 | Professor checkpoint issue | No-participant scope, course boundary, evaluator design, provider gate, and critical path approved | P0 scope and evaluation decision |
| 2026-07-25 | #11 | Method matrix, datasets, rubrics, thresholds, privacy protocol, and reporting plan frozen | Incorporated into P0 follow-up; written approval required before held-out runs |
| 2026-07-29 | #24 and #43 | Exact generator/prompt and context-sufficiency candidates qualified or rejected | Development evidence included in P1 |
| 2026-07-31 | #25 and #7 | Frozen end-to-end RAG result and selected or rejected grounded profile | P1 RAG method decision |
| 2026-08-10 | #8 | Authenticated, persistent professor/student application deployed to staging | P2 staging demonstration and architecture decision |
| 2026-08-15 | #9 | Security, privacy, reliability, rollback, professor review, and synthetic release gates passed or failed | P3 evaluation-release go/no-go |
| 2026-08-22 | #10 | Simulated-student, calibrated LLM-judge, and deployed synthetic-account evaluation completed | P4 evaluation evidence and supported-claim decision |
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

Evaluator data classes, trust boundaries, role separation, threats, and stop
conditions are frozen in the
[evaluation data-flow and threat model](../../docs/evaluation-data-flow-and-threat-model.md).

## Stop and fallback rules

- No product implementation starts until #11 freezes the evaluation and data
  governance protocol.
- No private professor or course data enters an external provider until
  permission and provider processing are approved.
- No sealed simulated-student or synthetic-account evaluation begins until #9
  passes authorization, privacy, recovery, and professor review hard gates.
- A failed RAG candidate produces a documented no-selection result; it does not
  delay authentication, persistence, and staging work if a safe rollback control
  can be used.
- Human-participant recruitment, human usability, and learning-effectiveness
  claims are out of scope rather than contingency items.
- No new architecture, model, metric, or feature begins after the 2026-08-26
  evidence freeze.
- Reserve 2026-08-27 through 2026-09-13 for report writing, figures,
  presentation work, demo stabilization, rehearsal, and contingency. Do not use
  this runway to recover deferred feature scope.
- Proactive triggers, full analytics, Canvas, multimodality, and learning-outcome
  claims are cut before any core deployability or evidence requirement.
