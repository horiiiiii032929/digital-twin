# Digital Twin Delivery

This Project tracks an evaluation-first path to a deployable, controlled
professor-configurable tutoring system. Code is not complete until its method,
privacy, security, grounding, pedagogy, reliability, cost, evaluator validity,
and rollback evidence is recorded.

## Current position

- Instructor onboarding is professor-approved and complete.
- Parsing, chunking, BM25 retrieval, dense/hybrid comparisons, evaluation
  contracts, deterministic generation controls, and result governance exist.
- BM25 v1 remains the provisional retriever; harder retrieval and
  evidence-sufficiency comparisons selected no replacement or safe verifier.
- Exact judge, simulator, run-record, analysis, and stop-rule contracts are
  frozen and validated under `research/05_evaluation/instruments/`.
- No live generator/prompt, returned-context verifier, end-to-end RAG profile,
  authentication, durable persistence, or deployment is selected yet.
- The immediate active work is the #7 IT5002 retrieval-v3 comparison under the
  #11 freeze. No model download, private development scoring, or held-out
  inspection is allowed until exact runtime bindings and split controls are
  recorded.

## Final-project scope

Deliver and evaluate one authenticated web deployment for one professor and one
course, without student recruitment. The project requires:

- professor and student roles plus course membership;
- approved private course sources and professor release control;
- persistent conversations, citations, feedback, and minimized audit records;
- explicit returned-context sufficiency and safe refusal/abstention;
- staging, TLS, secret isolation, redacted logs, health checks, rate limits,
  backup/restore, rollback, and incident handling;
- calibrated LLM judging, frozen simulated-student trajectories, and scripted
  synthetic-account acceptance; and
- reproducible offline comparisons and a deployed demonstration.

Internal course-specific retrieval evaluation remains local. A NotebookLM
black-box reference is separate and may use private material only after the
source permission, account terms, and run boundary are recorded. Human
usability and learning-effectiveness claims are excluded.

## Deferred from the critical path

- Proactive learning triggers
- Full learning-gap analytics and individual profiling
- Canvas or another LMS connector
- Public signup, multi-institution tenancy, and institution-wide SSO
- Multilingual, OCR, audio, video, or multimodal tutoring
- Automatic grading and claims of improved learning outcomes
- Universal SOTA or institution-wide production-readiness claims

## Dependency order

1. #11 freezes the method, data-governance, rubric, threshold, and reporting
   protocol. The instrument-contract portion is complete.
2. #46 runs the separate 59-case R1-versus-R5 rapid checkpoint and produces
   the first professor result within 24 hours.
3. #7 completes the course-specific retrieval-v3 comparison of BM25, Qwen3
   dense, hybrid, deterministic contextual, reranked, and bounded-decomposition
   conditions.
4. #43 qualifies or rejects the returned-context sufficiency verifier using the
   selected retriever or BM25 rollback.
5. #24 qualifies the exact generator/prompt; #25 records the frozen end-to-end
   RAG decision and #7 closes from that evidence.
6. #8 adds evaluated authentication, authorization, persistence, storage,
   professor/student journeys, and staging deployment.
7. #9 hardens security/reliability and records the researcher evaluation-release
   Go / Refine / No-Go; real student release authorization remains separate.
8. #10 runs calibrated LLM-judge, simulated-student, and deployed
   synthetic-account evaluation.
9. #12 runs the blinded final comparison and freezes evidence.
10. #13 delivers the final report, deployed demo, reproducibility package, and
   presentation.
11. #44 records every researcher checkpoint, professor critique, and genuine
   release decision separately.

## Tight roadmap

| Date | Required outcome | Professor checkpoint |
| --- | --- | --- |
| 2026-07-23 | #11/#46 freeze a separate 59-case R1-versus-R5 rapid screen | Internal freeze |
| 2026-07-24 | #46 execute one rapid sealed run and validate the result | P1 rapid experiment result |
| 2026-07-28 | #7/#43 complete expanded retrieval-v3 and context sufficiency | Decision addendum if material |
| 2026-07-31 | #24/#25 generator and end-to-end RAG decision | P2 end-to-end result package |
| 2026-08-04 | #8 authenticated persistent staging deployment | Demonstration link |
| 2026-08-08 | #9/#10/#12 final evaluation and evidence freeze | P3 final evidence package |
| 2026-09-03 | Full report draft and figures | P5 report review |
| 2026-09-09 | Timed demo and recovery rehearsal | P6 final rehearsal |
| 2026-09-10 to 2026-09-12 | Contingency only; no new scope or claims | Escalate blockers only |
| 2026-09-13 | #13 final delivery | Final presentation |

## Evaluation contract

Every replaceable method and architecture boundary must:

- define the decision, prediction, simplest control, and bounded candidates;
- use shared development, calibration, and untouched held-out inputs;
- predeclare primary metrics, diagnostics, hard gates, sample rationale, and
  analysis before held-out inspection;
- report privacy, permission, authorization, integrity, reliability, p50/p95
  latency, cost, and recovery where applicable;
- preserve raw failure counts, representative cases, uncertainty, and failure
  attribution;
- retain successful, failed, invalid, inconclusive, and no-selection results;
- record Keep / Refine / Go Deeper / Drop and an explicit rollback; and
- update the selected profile only when every required gate passes.

The primary complete-system outcomes are unconditional safe grounded task
success, calibrated professor-policy pedagogical success, multi-turn safe
trajectory completion, and reliable turn completion.

## Operating rules

- Keep roadmap parents in progress while only the current bounded execution item
  is active.
- Evidence fields link only to artifacts that exist.
- Do not send real professor, course, or student data to an unapproved provider.
- Do not infer private-course external-provider permission or evaluator
  validity from general encouragement.
- Do not tune on sealed data or rerun until a favorable result appears.
- Reserve professor contact for a decision-bearing result package or a genuine
  permission/deadline blocker, not ordinary progress reporting.
- Stop new architecture, model, metric, and feature work after 2026-08-08
  unless a frozen result explicitly justifies a bounded product improvement.
- Protect 2026-08-09 through 2026-09-13 primarily for report writing, figures,
  slides, demo stabilization, rehearsal, contingency, and evidence-backed
  product continuation.
- A working demo without security, operations, simulated interaction evidence,
  evaluator calibration, and aggregate evidence is not a deployable-system
  result.

The durable rescope is maintained at
`research/00_admin/2026-07-22-deployable-pilot-rescope.md`.
