# Professor checkpoint: deployable pilot scope

Date: 2026-07-24

GitHub checkpoint: #44 / P0

## Decision requested

Please `Keep` or `Refine` the rescope to a deployable, evaluated tutoring pilot
for one course, one professor, and a provisional cohort of 5-15 invited adult
students. Approval here authorizes planning; it does not yet authorize real
course or student data.

## Status

Amber. Instructor onboarding and the RAG/evaluation foundations exist, but the
system is not deployable. No safe returned-context verifier, exact live
generator/prompt, end-to-end RAG profile, authentication, persistent database,
private storage, student flow, staging environment, or pilot approval is
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

The deployed-pilot evaluation adds professor/student task completion, role and
course isolation, persistence, privacy, reliability, latency, cost, recovery,
and rollback.

## Decisions needed from the professor

1. Which one course and which 4-8 documents may be used for the pilot?
2. Is a cohort of 5-15 invited adult students appropriate, and what institutional
   approval or consent process is required?
3. May any approved course or student text be sent to an external DeepSeek API?
   If not, should the live pilot use an institution-approved provider, a local
   model, or synthetic users only?
4. What student-content retention period is acceptable, and who may inspect raw
   conversations?
5. Can the professor attend or asynchronously answer the P1-P6 checkpoints on
   2026-07-31, 08-10, 08-15, 08-22, 09-03, and 09-09?
6. Are proactive prompts, full learning-gap analytics, Canvas, multimodality,
   and learning-outcome claims acceptable as deferred future work?

## Proposed decision and consequence

- Proposed decision: `Keep` the deployable-pilot direction and `Refine` the
  exact data/provider boundary through #11.
- If approved: freeze the evaluation, privacy, dataset, rubric, thresholds, and
  architecture decision protocol by 2026-07-25 before implementation resumes.
- If refined: update the cohort, course, provider, data retention, or critical
  path before any code or model call.
- If rejected: fall back to a deployed synthetic-user research demonstration and
  remove real-user usability claims.

## Next checkpoint

- Date: 2026-07-31
- Required evidence: #11 protocol approval plus #24, #43, and #25 grounded RAG
  decisions.
- Consequence of delay: staging by 2026-08-10 becomes at risk; deployment scope
  must be cut before evaluation or privacy controls.

## Professor response

- Decision:
- Conditions:
- Approved course/data/provider boundary:
- Rationale:
- Follow-up owner and date:
