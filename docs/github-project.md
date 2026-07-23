# Digital Twin Delivery

Project board: https://github.com/users/horiiiiii032929/projects/1

This repository is scaffolded to create issues that are automatically added to
the linked GitHub Project by using the `projects: ["horiiiiii032929/1"]` key in
the issue form templates.

## Project Fields

The project currently exposes these planning fields:

- Status: Todo, In Progress, Done
- Decision: Pending, Keep, Refine, Go Deeper, Drop
- Work Type: Feature, Research, Design, Prototype, Documentation, Evaluation, Bug
- Iteration: I1 Instructor Onboarding, I2 Student Active Tutoring, I3 Proactive
  Interaction, I4 Learning Gap Report, I5 Evaluation and Refinement. I3 and I4
  remain historical options; their original scopes are deferred from the final
  critical path.
- Area: Instructor, Student, AI Agent, RAG, Analytics, Architecture,
  Documentation, Evaluation
- Risk: Low, Medium, High
- Evidence: free text
- Sprint: free text
- Target Date: date

## Local Workflow

1. Keep #1-#13 as roadmap/history items, use #44 for professor gates, and use
   their project status for delivery progress.
2. When a sprint becomes active, create bounded execution issues with the
   `Research Task` form and attach them as sub-issues of the roadmap item.
3. Fill in Iteration, Work Type, Area, Risk, Sprint, and Target Date on each
   execution item.
4. Leave `Evidence` empty during planning. Add a document, test run, demo, or
   merged pull request only after that artifact exists.
5. Use the `Decision Record` form only for evaluated product or research choices.
   Implementation tasks do not receive a placeholder decision.
6. Link pull requests to the execution sub-issue. Update evidence when a real
   result or check exists and again after merging.

Note: GitHub requires the person opening the issue to have write access to the
target project for automatic project assignment from issue forms.

## Current delivery status

- Sprint 1 onboarding was approved by Prof. Lek with a `Keep` decision.
- Approved local ingestion, evaluated BM25 retrieval, the harder retrieval v2
  benchmark, replaceable generation controls, and durable evaluation-result
  governance are implemented.
- Retrieval v2 produced a `Refine` decision with no replacement. BM25 v1
  remains the provisional rollback baseline while evidence sufficiency is
  addressed.
- Draft PR #36 passes the deterministic 25-case generation/policy preflight and
  contains the local Ollama benchmark path. The exploratory Gemma 3 4B run
  passed structural checks but only 15/18 model answers passed a post-run
  support audit, so no generator or prompt is selected.
- #41 evaluated any-hit, BM25-score, lexical-coverage, and semantic-agreement
  evidence gates on 30 calibration and 50 held-out cases. The decision is
  `Refine` with no selection.
- The system is not deployable yet: authentication, authorization, persistence,
  private storage, student tutoring, staging, monitoring, backup/restore,
  rollback, professor release review, and simulated evaluation evidence are
  absent.
- #11 is the immediate active execution item. Its instrument-contract portion
  is complete; exact runtime bindings and private split validation remain
  before any development scoring or held-out inspection.
- #7 completes the retrieval-v3 ablation and held-out decision by 2026-08-05.
  #43, #24, and #25 then qualify or reject the returned-context verifier,
  generator/prompt, and frozen end-to-end RAG profile by 2026-08-15.
- #8 delivers authenticated persistent professor/student staging by
  2026-08-21.
- #9, #10, and #12 complete hardening, simulated evaluation, final comparison,
  and the evidence freeze by 2026-08-26.
- #44 records decision-bearing professor critiques and final rehearsal; routine
  planning updates remain internal.
- Proactive triggers, full learning-gap analytics, Canvas, multimodality,
  institution-wide SSO, public signup, and learning-effectiveness claims are
  deferred.
- The [quality and learning plan](quality-and-learning-plan.md) is the acceptance
  standard for technical depth, evaluation evidence, and student understanding.

### Active critical path

Roadmap issue #7 stays `In Progress`; #11 is the current bounded execution gate.

| Target | Issue and required outcome |
| --- | --- |
| 2026-07-26 | #11/#7 freeze retrieval-v3 candidates, data contract, metrics, gates, and held-out lock; no professor message |
| 2026-07-30 | #7 validate private development and sealed IT5002 retrieval cases and bind exact runtime revisions |
| 2026-08-02 | #7 finish development ablations and freeze the confirmatory condition and thresholds |
| 2026-08-05 | #7 complete one held-out retrieval-v3 decision and send the first result package |
| 2026-08-11 | #43 qualify or reject the returned-context sufficiency verifier |
| 2026-08-15 | #24/#25 qualify or reject the generator/prompt and end-to-end RAG profile |
| 2026-08-21 | #8 deploy authenticated persistent professor/student staging |
| 2026-08-26 | #9/#10/#12 complete hardening, simulated evaluation, final comparison, and evidence freeze |
| 2026-09-03 | #44 P5 professor report-draft review |
| 2026-09-09 | #44 P6 professor rehearsal |
| 2026-09-10 to 2026-09-12 | Contingency only: correct blocking defects, package submission, and preserve frozen claims |
| 2026-09-13 | #13 final report, deployed demo, and reproducibility package |

Follow-up PR #39 makes every named decision-bearing evaluation result durable
through a registry, reusable template, and CI validator. Attach this evidence to
#34 and the parent #7 rather than creating a retrospective execution issue.

## Evaluation contract

Every decision-bearing component must expose a stable runtime contract and a
rollback control, compare plausible alternatives under shared conditions, and
separate development, calibration, and untouched held-out data. Metrics,
thresholds, reviewer protocol, and analysis must be declared before held-out
inspection.

Safety, privacy, permission, provenance, and integrity gates run before relative
quality. Results must include raw counts, failure slices, uncertainty, latency,
tokens, cost, and footprint where applicable. Successful, failed, invalid, and
inconclusive named runs remain registered. A profile changes only after every
required gate passes; no selection is a valid outcome.

The contract also applies to authentication, authorization, persistence,
storage, conversation state, deployment, backup/restore, rollback, judge
calibration, simulator validity, and synthetic-account acceptance. A local
algorithm score cannot compensate for a privacy, authorization, integrity, or
reliability failure in the deployed system.

Minimum sample sizes in issue bodies are floors. If important slices remain
underpowered or uncertainty is too wide, record `Refine` and collect more
evidence rather than treating the minimum as proof.

## Timeline through presentation

Use this schedule to keep `Sprint` and `Target Date` fields consistent on the
project board. The current presentation milestone is tracked through
2026-09-13.

| Sprint | Dates | Focus | Items | Target Date |
| --- | --- | --- | --- | --- |
| S1 Onboarding | 2026-06-22 to 2026-06-28 | I1 scope, setup flow, policy fields, prototype, professor review | #1-#6 | 2026-06-28 |
| S2 Retrieval Research | 2026-07-22 to 2026-08-05 | Frozen retrieval-v3 protocol, private course/open-set benchmark, ablations, held-out result, and result-focused professor report | #7, #11 | 2026-08-05 |
| S3 Grounded RAG | 2026-08-06 to 2026-08-15 | Qualified/rejected context-sufficiency, generator/prompt, and end-to-end RAG profile | #24, #25, #43 | 2026-08-15 |
| S4 Deployable App | 2026-08-16 to 2026-08-21 | Authenticated persistent professor/student staging deployment | #8 | 2026-08-21 |
| S5 Hardening and Evidence Freeze | 2026-08-22 to 2026-08-26 | Security, privacy, reliability, recovery, calibrated judging, simulated-student and synthetic-account evaluation, blinded comparison, and frozen claims | #9, #10, #12 | 2026-08-26 |
| S6 Report and Presentation | 2026-08-27 to 2026-09-13 | Report, figures, deployed demo, reproducibility, slides, rehearsal, and three-day contingency | #13, #44 | 2026-09-13 |

## Board Maintenance

- Keep parent issues for roadmap progress and sub-issues for active execution.
- Retain the three-status workflow: Todo, In Progress, and Done.
- Move only the active execution item to `In Progress`; completed sub-issues are
  `Done`, and future work remains `Todo`.
- Add artifact links to `Evidence` only when the artifact exists.
- Use `Decision` only after a product or research choice has been evaluated.
- Register every named decision-bearing result; retain failed, invalid, and
  inconclusive runs rather than silently replacing them.
- Update `Target Date` before changing scope so timeline drift is visible.
- Keep issue titles compact and timeline-first: `[S# MM/DD] Deliverable`.
- Keep `Sprint` and `Evidence` field values short so the table remains readable.
- Record each researcher decision and any professor critique separately in #44
  and the local decision log; general encouragement does not approve
  private-course provider use, evaluator calibration, or student release.
- Do not close a technical execution issue until its design note, tests,
  experiment evidence, limitations, and learning log satisfy the shared
  definition of done.
