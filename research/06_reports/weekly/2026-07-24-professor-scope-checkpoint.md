# Professor checkpoint: deployable tutor and evaluation scope

Date: 2026-07-24

GitHub checkpoint: #44 / P0

## Decision requested

Please `Keep` or `Refine` the rescope to a deployable, evaluated tutoring system
for one course and one professor, without student recruitment. Approval here
authorizes planning and instrument design; it does not yet authorize tutoring
use of the private course corpus or external-provider processing.

## Status

Amber. Instructor onboarding and the RAG/evaluation foundations exist, but the
system is not deployable. No safe returned-context verifier, exact live
generator/prompt, end-to-end RAG profile, authentication, persistent database,
private storage, student flow, staging environment, or evaluation release is
selected.

## What is already supported

| Area | Current evidence | Decision |
| --- | --- | --- |
| Professor onboarding | Chat-led policy, preview, revision, and release workflow; professor review recorded | Keep |
| Parsing/chunking | Permission-aware text/Markdown/PDF baseline with provenance | Keep / Refine settings later |
| Retrieval | BM25 beat the term-overlap control in v1; dense/RRF did not justify replacing it in v2 | Keep BM25 provisionally |
| Context sufficiency | Existing gates confused corpus answerability with returned-context sufficiency and failed safety/usefulness gates | Refine; no selection |
| Generation | Deterministic control works; exploratory Gemma support audit passed 15/18 model answers | Refine; no selection |
| Deployment | Current API uses in-memory state and has no authentication or persistent student flow | Not started |

## Proposed final contribution

Build a deployable professor-configurable, course-grounded tutor and evaluate
every replaceable method and architecture boundary against a control. The final
comparison uses the same generator for:

1. generic assistant;
2. approved evidence plus generic tutoring policy;
3. the same evidence plus professor policy; and
4. retrieved evidence plus professor policy.

The additional evaluation uses deterministic hard gates, a professor-reviewed
course benchmark, calibrated LLM judges for subjective pedagogy, frozen
simulated-student trajectories for multi-turn stress, and scripted synthetic
accounts for role isolation, persistence, privacy, reliability, latency, cost,
recovery, and rollback.

This can support claims about the tested tutor and deployment revision. It
cannot support claims about human usability, student satisfaction, engagement,
learning gains, or classroom effectiveness.

## Decisions needed from the professor

1. May all 13 inventoried official IT5002 lectures be processed and used for
   tutor grounding, with notes and assessed/answer material excluded?
2. Do you approve a no-participant evaluation using simulated students and
   synthetic accounts, with no human-usability or learning-effectiveness claim?
3. May any approved course text be sent to an external DeepSeek API?
   If not, should the live pilot use an institution-approved provider, a local
   model, or synthetic-only external qualification?
4. Can you approve the 12 anchor expected actions and review 8-12 calibration
   outputs so the LLM judge can be checked against expert labels?
5. Can the professor attend or asynchronously answer the P1-P6 checkpoints on
   2026-07-31, 08-10, 08-15, 08-22, 09-03, and 09-09?
6. Are proactive prompts, full learning-gap analytics, Canvas, multimodality,
   and learning-outcome claims acceptable as deferred future work?

## Proposed decision and consequence

- Proposed decision: `Keep` the deployable-system direction and `Refine` the
  evaluation to professor-reviewed offline cases, simulated students, calibrated
  LLM judges, and synthetic-account deployment tests.
- If approved: freeze the evaluation, privacy, dataset, rubric, thresholds, and
  architecture decision protocol by 2026-07-25 before implementation resumes.
- If refined: update the corpus, provider, evaluator calibration, or critical
  path before any code or model call.
- If professor output review is unavailable: keep LLM-judge results diagnostic
  and narrow the pedagogical claim.

## Next checkpoint

- Date: 2026-07-31
- Required evidence: #11 protocol approval plus #24, #43, and #25 grounded RAG
  decisions.
- Consequence of delay: staging by 2026-08-10 becomes at risk; deployment scope
  must be cut before evaluation or privacy controls.

## Professor response

- Decision:
- Conditions:
- Approved course/provider/evaluator boundary:
- Rationale:
- Follow-up owner and date:
