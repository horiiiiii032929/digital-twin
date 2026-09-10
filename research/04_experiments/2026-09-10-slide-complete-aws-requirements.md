# Latest-slide functional completeness for AWS

Recorded: 10 September 2026, Singapore.
Status: user requirement recorded; gap review only, not implementation or deployment validation.

## User requirement and authority

The user requires AWS to support, as fully as possible, the working software workflows demonstrated in the latest presentation, including proactive check-ins. An audited chat-only demo is not the target acceptance scope. This explicitly expands the earlier coding-only scope; excluding worker activation from that earlier patch plan must not be used to exclude it from this new work.

Authority: the 70-slide Desktop presentation, SHA-256 `7453cff7de77b597a61abc39766e3cb948ab2f0b3083d9b835a2a91dcb6f6d76`, rechecked on 10 September. Path: `/Users/hikaru/Desktop/Course Digital Twin — Final Presentation/Course Digital Twin.pptx`.

Completeness preserves the slides' distinction between working demonstrations, experimental options and research limitations. It does not automatically promote Decay/BKT/PFA or the optional model assessor, change model roles or audit limits, bypass publication/privacy/consent gates, or authorize copying private lecture material. Embedded demo videos still need direct review and a workflow-by-workflow acceptance mapping; the prior alignment review did not replay them frame by frame.

## Evidence-backed gaps to resolve or explicitly qualify

| Priority | Area | Recorded gap | Required acceptance evidence |
| --- | --- | --- | --- |
| P0 | Background check-ins, S38–43 | Outreach disabled; no active autonomy policy, worker heartbeat or delivery established in the AWS pilot. | Eligible synthetic course and consenting test learner; real worker scheduling/event handling, one delivery, reply/dismissal and applicable goal-state transitions; no duplicates or unauthorized delivery. |
| P0 | New professor onboarding and publication | Course-specific preview uses legacy CSRF/generic fixtures; successful fresh-course browser publication and revision incomplete. | New course upload, ingestion, relevant preview, review, publication and student access; version/revision behavior, rejected prerequisites and isolation remain correct. |
| P0 | Connected lifecycle | No complete upload-to-check-in-to-goal-completion browser evidence. | Trace one connected synthetic professor/student lifecycle through the actual AWS deployment, including persisted evidence and permitted goal completion. Record blocked branches honestly. |
| P1 | Reply generation after latest deployment | Deployment 009 checked authentication, reads and settings, but generated no new model answers. Earlier AWS and local model tests exist. | Fresh AWS browser model turns on the deployed version, including valid reply, withholding, reload/recovery and citation access. |
| P1 | Professor insights, S61–64 | Latest local group reached four distinct learners, below the five-person per-topic/signal threshold. Positive complete insight/review path not established by that run. | Synthetic eligible five-learner group, truthful aggregate, saved professor decision; below-threshold privacy control; no automatic material rewrite. |
| P1 | Recovery and operation | Historical AWS hang not proven resolved; API/host restart and full concurrent-session coverage incomplete. | Targeted AWS recovery/concurrency checks and measured outcomes, preserving data and request identity. |
| Classification | Assessment and learner models, S44–52 | Base lexical path selected; conversational praise may differ from saved assessment. Optional assessor and research estimators are not selected. | Map each slide demonstration to its exact configuration; retain experimental labels and evaluate separately if activation is proposed. Do not equate software completeness with better learning. |
| Classification | Teaching corpus and videos | AWS uses synthetic material; slides use private IT5004 excerpts. Video capture/runtime correspondence not yet fully audited. | Review actual video steps and identify functional parity versus content differences; obtain applicable permission before any private-source transfer. |

## Execution boundary and completion

This record changes the target scope, not the running system. EC2 and its automatic power schedules remain stopped/disabled as last recorded. No service activation, delivery, model call or deployment was performed for this gap review. Define a separate reproducible implementation/evaluation plan before changing behavior; use synthetic accounts and sources, preserve the existing research results and rollback, and record both failures and successes.

Completion requires a slide/video-to-AWS acceptance matrix with evidence for each implemented workflow, exact deployed configuration, remaining limitations and any intentionally experimental items. A worker flag, passing unit tests or a settings match alone is not completion. Full repository checks must report their actual state; the latest summary records an execution-freeze packaging blocker.

## Sources

- [Earlier slide-aligned coding scope and differences](2026-09-09-slide-aligned-code-fix-plan.md)
- [Application test summary through run 008 and deployment addendum](../../docs/application-test-summary-2026-09-10.md)
- [Deployment 009 and stopped state](../../reports/aws-pilot/deployed-state-2026-09-10.md)

These are historical observations from the named runs, not a fresh AWS status inspection or an exhaustive video audit.
