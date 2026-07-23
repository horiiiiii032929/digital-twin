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
- No live generator/prompt, returned-context verifier, end-to-end RAG profile,
  authentication, durable persistence, or deployment is selected yet.
- The immediate active item is #11: freeze evaluation and data governance before
  new implementation or held-out inspection.

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

Course-specific evaluation is local-only under the researcher-selected working
boundary. Private course material and outputs do not enter an external
provider. Human usability and learning-effectiveness claims are excluded.

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
   protocol.
2. #24 and #43 qualify or reject the generator/prompt and returned-context
   sufficiency verifier.
3. #25 records the frozen end-to-end RAG decision; #7 closes from that evidence.
4. #8 adds evaluated authentication, authorization, persistence, storage,
   professor/student journeys, and staging deployment.
5. #9 hardens security/reliability and records the researcher evaluation-release
   Go / Refine / No-Go; real student release authorization remains separate.
6. #10 runs calibrated LLM-judge, simulated-student, and deployed
   synthetic-account evaluation.
7. #12 runs the blinded final comparison and freezes evidence.
8. #13 delivers the final report, deployed demo, reproducibility package, and
   presentation.
9. #44 records every researcher checkpoint, professor critique, and genuine
   release decision separately.

## Tight roadmap

| Date | Required outcome | Professor checkpoint |
| --- | --- | --- |
| 2026-07-24 | Researcher-selected method, preliminary results, claim boundary, and next experiment reported | P0 method/results critique |
| 2026-07-25 | #11 protocol frozen | Researcher freeze record |
| 2026-07-29 | #24 and #43 qualified or rejected | Included in P1 |
| 2026-07-31 | #25 and #7 end-to-end RAG decision | P1 RAG result critique |
| 2026-08-10 | #8 authenticated persistent staging deployment | P2 staging and architecture review |
| 2026-08-15 | #9 hardening and risk review | P3 researcher Go / Refine / No-Go |
| 2026-08-22 | #10 simulated-student, LLM-judge, and synthetic-account evaluation | P4 evidence and claim decision |
| 2026-08-26 | #12 final evaluation and evidence freeze | Written freeze confirmation |
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
- Stop new architecture, model, metric, and feature work after 2026-08-26.
- Protect 2026-08-27 through 2026-09-13 for report writing, figures, slides,
  demo stabilization, rehearsal, and contingency.
- A working demo without security, operations, simulated interaction evidence,
  evaluator calibration, and aggregate evidence is not a deployable-system
  result.

The durable rescope is maintained at
`research/00_admin/2026-07-22-deployable-pilot-rescope.md`.
