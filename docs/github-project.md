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
  Interaction, I4 Learning Gap Report, I5 Evaluation and Refinement
- Area: Instructor, Student, AI Agent, RAG, Analytics, Architecture,
  Documentation, Evaluation
- Risk: Low, Medium, High
- Evidence: free text
- Sprint: free text
- Target Date: date

## Local Workflow

1. Keep #1-#13 as roadmap deliverables and use their project status for sprint
   progress.
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
- #24 now requires a prospective prompt/model comparison with at least 40
  development cases and 100 held-out cases. #43 requires a new 60-case
  calibration set and 150-case held-out open-set verifier comparison.
- #25 is blocked by both #24 and #43. Its four illustrative demo cases cannot
  substitute for the required untouched 100-case end-to-end evaluation.
- Canvas is an optional future connector. It should not block or define the core
  ingestion and retrieval architecture.
- The [quality and learning plan](quality-and-learning-plan.md) is the acceptance
  standard for technical depth, evaluation evidence, and student understanding.

### Active Sprint 2 execution

Roadmap issue #7 stays `In Progress` while these sub-issues drive delivery:

| Target | Execution sub-issue |
| --- | --- |
| 2026-07-11 | #19 Refactor onboarding domain boundaries |
| 2026-07-12 | #20 Refactor API and frontend adapters |
| 2026-07-13 | #21 Define grounding contracts and synthetic fixtures |
| 2026-07-14 | #22 Implement local document parsing and chunking |
| 2026-07-15 | #34 Define evaluation architecture and component profiles |
| 2026-07-16 | #23 Implement retrieval and source evidence |
| 2026-07-17 | #37 Benchmark RAG retrieval candidates |
| 2026-07-18 | #41 Evaluate retrieval evidence sufficiency |
| 2026-07-20 | #24 Evaluate grounded generator and prompt candidates |
| 2026-07-23 | #43 Evaluate the open-set evidence verifier |
| 2026-07-25 | #25 Evaluate the grounded tutoring vertical slice |

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
| S2 Grounding | 2026-06-29 to 2026-07-25 | Evaluated local-course RAG vertical slice | #7 | 2026-07-25 |
| S3 Tutoring | 2026-07-26 to 2026-08-01 | Selected student tutoring orchestration and interface | #8 | 2026-08-01 |
| S4 Proactive | 2026-08-02 to 2026-08-08 | Selected or rejected proactive trigger strategy | #9 | 2026-08-08 |
| S5 Gap Report | 2026-08-09 to 2026-08-16 | Selected privacy-preserving learning-gap analytics | #10 | 2026-08-16 |
| S6 Eval Setup | 2026-08-17 to 2026-08-25 | Validated dataset, rubric, and reviewer protocol | #11 | 2026-08-25 |
| S7 Refinement | 2026-08-26 to 2026-09-04 | Blinded baselines and confirmed refinements | #12 | 2026-09-04 |
| S8 Presentation | 2026-09-05 to 2026-09-13 | Frozen evidence, reproducible report, and demonstration | #13 | 2026-09-13 |

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
- Do not close a technical execution issue until its design note, tests,
  experiment evidence, limitations, and learning log satisfy the shared
  definition of done.
