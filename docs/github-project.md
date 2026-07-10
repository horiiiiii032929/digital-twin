# GitHub Project Link

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

1. Create work through the `Research Task` or `Decision Record` issue form.
2. Fill in Iteration, Work Type, Area, Risk, and Evidence in the issue body.
3. After the issue appears on the project board, mirror those values into the
   matching project fields.
4. Link pull requests back to the issue and include verification evidence.

Note: GitHub requires the person opening the issue to have write access to the
target project for automatic project assignment from issue forms.

## Current delivery status

- Sprint 1 onboarding was approved by Prof. Lek with a `Keep` decision.
- The onboarding implementation remains deterministic and provider-neutral; it
  does not yet use a live LLM or real retrieval.
- Sprint 2 is active and targets the smallest grounded tutoring path using
  approved local or synthetic documents, retrieval, tutor-policy enforcement,
  live LLM generation, and visible source evidence.
- Canvas is an optional future connector. It should not block or define the core
  ingestion and retrieval architecture.

## Timeline Through Presentation

Use this schedule to keep `Sprint` and `Target Date` fields consistent on the
project board. The current presentation milestone is tracked through
2026-09-13.

| Sprint | Dates | Focus | Items | Target Date |
| --- | --- | --- | --- | --- |
| S1 Onboarding | 2026-06-22 to 2026-06-28 | I1 scope, setup flow, policy fields, prototype, professor review | #1-#6 | 2026-06-28 |
| S2 Grounding | 2026-06-29 to 2026-07-19 | I2 local source ingestion, live LLM, and RAG baseline | #7 | 2026-07-19 |
| S3 Tutoring | 2026-07-20 to 2026-07-26 | I2 active tutoring flow and sample conversations | #8 | 2026-07-26 |
| S4 Proactive | 2026-07-27 to 2026-07-31 | I3 proactive prompt behavior and prototype stabilization | #9 | 2026-07-31 |
| S5 Gap Report | 2026-08-03 to 2026-08-15 | I4 instructor dashboard and learning-gap summary | #10 | 2026-08-15 |
| S6 Eval Setup | 2026-08-17 to 2026-08-23 | I5 evaluation dataset and rubric | #11 | 2026-08-23 |
| S7 Refinement | 2026-08-24 to 2026-09-01 | I5 baseline comparison and prototype refinements | #12 | 2026-09-01 |
| S8 Presentation | 2026-09-02 to 2026-09-13 | Final report, demo evidence, slides, and rehearsal | #13 | 2026-09-13 |

## Board Maintenance

- Keep one primary project item per major deliverable unless a card becomes too
  large to review.
- Move only the active sprint cards to `In Progress`.
- Add artifact links to `Evidence` when work is ready for review.
- Update `Target Date` before changing scope so timeline drift is visible.
- Keep issue titles compact and timeline-first: `[S# MM/DD] Deliverable`.
- Keep `Sprint` and `Evidence` field values short so the table remains readable.
