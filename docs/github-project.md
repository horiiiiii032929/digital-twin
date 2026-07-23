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
- #11 is the immediate active execution item. It freezes the deployable-pilot
  evaluation and data-governance protocol before new implementation, provider
  calls, or held-out inspection.
- #24 and #43 then qualify or reject the exact DeepSeek/prompt and actual
  returned-context sufficiency methods. #25 and parent #7 record the frozen RAG
  decision by 2026-07-31.
- #8 delivers authenticated persistent professor/student staging by 2026-08-10;
  #9 hardens it and records professor evaluation-release Go / Refine / No-Go by
  2026-08-15.
- #10 runs the simulated-student, LLM-judge, and deployed synthetic-account
  evaluation by 2026-08-22.
- #44 tracks seven professor decisions from scope approval through rehearsal.
- Proactive triggers, full learning-gap analytics, Canvas, multimodality,
  institution-wide SSO, public signup, and learning-effectiveness claims are
  deferred.
- The [quality and learning plan](quality-and-learning-plan.md) is the acceptance
  standard for technical depth, evaluation evidence, and student understanding.

### Active critical path

Roadmap issue #7 stays `In Progress`; #11 is the current bounded execution gate.

| Target | Issue and required outcome |
| --- | --- |
| 2026-07-24 | #44 P0 professor scope and evaluator-governance decision |
| 2026-07-25 | #11 freeze pilot evaluation and data governance |
| 2026-07-29 | #24 and #43 qualify or reject generator/prompt and returned-context verifier |
| 2026-07-31 | #25 and #7 record the end-to-end RAG decision |
| 2026-08-10 | #8 deploy authenticated persistent professor/student staging |
| 2026-08-15 | #9 pass hardening and professor evaluation-release review, or record No-Go |
| 2026-08-22 | #10 complete simulated-student, LLM-judge, and synthetic-account evaluation |
| 2026-08-26 | #12 complete final evaluation and freeze evidence |
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
| S2 Protocol and RAG | 2026-07-22 to 2026-07-31 | Frozen protocol and qualified/rejected grounded RAG profile | #7, #11, #24, #25, #43 | 2026-07-31 |
| S3 Deployable App | 2026-08-01 to 2026-08-10 | Authenticated persistent professor/student staging deployment | #8 | 2026-08-10 |
| S4 Hardening and Review | 2026-08-11 to 2026-08-15 | Security, privacy, reliability, recovery, and professor evaluation-release decision | #9 | 2026-08-15 |
| S5 Simulated Evaluation | 2026-08-16 to 2026-08-22 | Calibrated LLM judge, simulated-student trajectories, and deployed synthetic-account acceptance | #10 | 2026-08-22 |
| S6 Evidence Freeze | 2026-08-23 to 2026-08-26 | Blinded comparison, bounded refinement, and frozen claims | #12 | 2026-08-26 |
| S7 Report and Presentation | 2026-08-27 to 2026-09-13 | Report, figures, deployed demo, reproducibility, slides, rehearsal, and three-day contingency | #13, #44 | 2026-09-13 |

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
- Record each professor checkpoint in #44 and copy the decision to the local
  decision log; general encouragement does not approve private-course provider
  use or evaluator calibration.
- Do not close a technical execution issue until its design note, tests,
  experiment evidence, limitations, and learning log satisfy the shared
  definition of done.
