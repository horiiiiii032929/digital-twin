# Digital Twin Delivery

Project board: https://github.com/users/horiiiiii032929/projects/1

The board implements the authoritative
[frontier Digital Twin scope](../research/00_admin/2026-07-27-frontier-digital-twin-scope.md).
Repository issue forms add new issues to the Project automatically.

## Planning fields

- Status: Todo, In Progress, Done
- Decision: Pending, Keep, Refine, Go Deeper, Drop
- Work Type: Feature, Research, Design, Prototype, Documentation, Evaluation, Bug
- Iteration: historical product iterations; use Sprint for the compressed plan
- Area: Instructor, Student, AI Agent, RAG, Analytics, Architecture,
  Documentation, Evaluation
- Risk: Low, Medium, High
- Evidence: links or concise result references that already exist
- Sprint: short delivery-phase name
- Target Date: current prospective target

## Current state

Completed work includes professor-approved chat-led onboarding, governed local
ingestion, retrieval baselines/candidates, deterministic generation controls,
evaluation instruments, component profiles, and result governance.

The cross-course text qualification is complete: on the one-time 60-case
held-out comparison, M2 hybrid BM25 plus dense RRF is selected for the
experimental profile and BM25 remains the rollback. M1 regressed on quality and
latency; M3 had the best quality but failed the 10-second p95 gate. IT5002
pilot results remain context, not final selection evidence. Jina was retired
before hosted execution. The scoped multimodal development study under #60 is
complete: V3 was dropped, V0 is retained as the visual/text rollback, and no
multimodal profile is selected. The final multi-course product and end-to-end
evidence do not yet exist.

As of 2026-08-18, #12 and #80 are complete. PR #81 merged the repository-owner
`Keep` decision for the professor conversation-plus-tool direction. #82 is the
sole implementation issue in `In Progress`; it is a bounded student-workspace
extension of the existing synthetic publication and tutoring core. It does not
alter the frozen component profile or authorize model or held-out execution.
The repository remains an experimental, not release-ready baseline. Issue #24
is `Todo / Refine (Paused)`: its corrected anchor evidence is preserved, both
human packets are deferred, and a tracked execution policy blocks development
and held-out access. GitHub Support closed ticket #4659958 after completing the
public-object purge; remote API and web checks confirm the superseded SHA is
unavailable. #8 remains the parent foundation; #25, #10, and #9 remain queued.
See the
[current project status](current-status.md) for the exact execution order.

## Active roadmap

| Phase | Dates | Required evidence |
| --- | --- | --- |
| F1 Scope and architecture lock | 2026-07-27 to 2026-07-29 | Authoritative scope, roadmap, repository architecture, archived superseded plans |
| F2 Cross-course method qualification | 2026-07-30 to 2026-08-08 | Course portfolio, ingestion QA, verified benchmark, provider qualification, M0-M3 sealed result, selected/rollback retrieval profile |
| F3 Product and end-to-end validation | 2026-08-09 to 2026-08-16 | Integrate M2 with BM25 rollback, then validate professor/student journeys, fidelity, pedagogy, publication control, isolation, recovery, capacity, and local deployment package |
| F4 Evidence and final communication | 2026-08-17 to 2026-09-13 | Analysis, report, figures, presentation, reproducibility, demo stabilization, contingency |

Technical and evidence work froze on 2026-08-18, two days after the target.
The target professor presentation is 2026-09-04; final submission is
2026-09-13. Until feedback authorizes a post-freeze change, work is limited to
report, presentation, and demonstration preservation.

## Issue workflow

1. Keep roadmap parents open and create bounded execution issues for concrete
   decisions or deliverables.
2. Move only active execution work to `In Progress`.
3. Before implementation, record the decision, prediction, control, candidates,
   evaluation data, metrics, hard gates, operational measures, and rollback.
4. Leave `Evidence` empty until an artifact exists.
5. Register every named evaluation result, including failed, invalid,
   inconclusive, and no-selection runs.
6. Close an issue only after design, tests, evidence, limitations,
   documentation, learning log, and checks satisfy the shared definition of
   done.

## Professor checkpoints

Use issue #44 for the Monday/Wednesday/Friday communication ledger. A checkpoint
is not a formal report. When new evidence exists, provide:

- one decision or result;
- exact sample size and two to four numbers;
- one compact table or at most two charts;
- one important limitation; and
- the next decision and date.

Routine code progress stays on the board. Do not ask the professor to choose
ordinary implementation details or treat general encouragement as provider,
data, or student-release permission.

## Board maintenance

- Preserve issue and result history; supersede or close obsolete work with a
  link to its replacement.
- Use milestone dates as hard phase boundaries and Target Date for individual
  items.
- Keep project fields concise and evidence-backed.
- Do not silently replace a component profile or repair/rerun sealed evidence.
- Hardware latency and cost are operational metrics, not retrieval-quality
  criteria.
- The product priorities are professor fidelity, pedagogical tutoring,
  evaluation-before-publication, grounding, then supporting platform breadth.
