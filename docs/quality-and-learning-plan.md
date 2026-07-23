# Quality and Learning Plan

Last reviewed: 2026-07-23

## Purpose

This document is the quality and learning contract for the Digital Twin project.
It prevents the prototype from stopping at mocked behavior and makes technical
understanding an explicit project outcome.

Sprint 1 deliberately reduced technical complexity to validate the professor
onboarding direction. That was an appropriate product decision, not the final
research standard. Prof. Lek's positive feedback supports keeping the onboarding
direction; it does not yet validate retrieval quality, tutor effectiveness, or
the complete digital-twin system.

## Quality principles

- Prefer low complexity while maintaining high standards of evidence.
- Build an inspectable baseline before adding opaque infrastructure.
- Evaluate behavior instead of accepting a convincing demonstration alone.
- Preserve source provenance, policy decisions, warnings, and failure states.
- Keep decision-bearing components replaceable behind typed contracts and select
  their versions through recorded evaluation evidence.
- Keep Canvas optional; LMS integration is not a substitute for research depth.
- Do not claim learning effectiveness without an evaluation design that supports
  that claim.
- Treat deployability as an evaluated system property: authentication,
  authorization, persistence, privacy, reliability, synthetic acceptance, monitoring,
  backup/restore, and rollback require the same control-and-evidence discipline
  as retrieval and generation.

## Delivery timeline

| Dates | Deliverable | Required learning outcome |
| --- | --- | --- |
| Complete | Sprint 1: instructor onboarding | Requirements, policy modeling, review UX, and release gates |
| 2026-07-11 to 2026-07-14 | Document parsing and chunking | Normalization, provenance, content boundaries, and deterministic tests |
| 2026-07-15 to 2026-07-16 | Retrieval and source evidence | Lexical ranking, retrieval metrics, citation relationships, and error analysis |
| 2026-07-22 to 2026-07-25 | Evaluation protocol and data governance | Research question, simulated users, data flow, privacy, judge calibration, rubrics, gates, and professor approval |
| 2026-07-26 to 2026-07-31 | Grounded RAG qualification | Generator/prompt, returned-context sufficiency, claim/citation evidence, and end-to-end decision |
| 2026-08-01 to 2026-08-10 | Deployable professor/student application | Authentication, authorization, persistence, private storage, conversation state, staging, and rollback |
| 2026-08-11 to 2026-08-15 | Hardening and professor UAT | Threat modeling, privacy, reliability, load, backup/restore, recovery, and release decision |
| 2026-08-16 to 2026-08-22 | Simulated-user evaluation | Calibrated LLM judging, multi-turn safe completion, synthetic-account acceptance, reliable turns, and claim boundaries |
| 2026-08-23 to 2026-08-26 | Final evaluation and evidence freeze | Blinded comparison, bounded refinement, failure analysis, uncertainty, and frozen evidence |
| 2026-08-27 to 2026-09-03 | Full report draft and figures | Complete argument, claim-to-evidence matrix, main plots, limitations, and professor review |
| 2026-09-04 to 2026-09-09 | Revision and presentation preparation | Resolve review, stabilize demo, prepare slides, rehearse timing, and practice failure recovery |
| 2026-09-10 to 2026-09-12 | Contingency buffer | Correct blocking defects, package the submission, and protect frozen claims from late scope growth |
| 2026-09-13 | Final presentation and submission | Deliver the report, deployed demonstration, presentation, and reproducibility package |

## Strengthened Sprint 2 bar

Sprint 2 is not complete when one plausible answer appears on screen. It must
produce an inspectable, evaluated vertical slice.

### Course corpus

- Use the 13 inventoried official IT5002 lecture PDFs for the full-course pilot;
  keep private content local and block tutoring use until professor approval.
- Support UTF-8 text, Markdown, and selectable-text PDF input.
- Preserve document ID, title, source label, content hash, and a human-readable
  locator through normalization and chunking.
- Reject unsupported, empty, excluded, or unapproved sources explicitly.
- Commit only synthetic fixtures; never commit private course or student data.

### Chunking and retrieval

- Implement a deterministic heading/paragraph-aware chunker with documented
  size and overlap decisions.
- Implement an inspectable lexical or BM25-style retrieval baseline before an
  embedding retriever.
- Build a versioned evaluation set with at least 20 questions across direct
  grounding, misconception, integrity-boundary, ambiguous, and no-evidence
  cases.
- Report gold-evidence Recall@3/5, complete-evidence success@3, and nDCG@3 as
  the primary retrieval views; report Mean Reciprocal Rank as a first-useful-
  evidence diagnostic rather than a complete RAG score.
- Record failed queries and explain whether the source, chunking, query, or
  ranking caused each failure.

### Generation and policy enforcement

- Call a live model only through the provider-neutral generator contract.
- Supply retrieved evidence and the approved tutor policy to generation.
- Validate that every displayed citation maps to a retrieved document and
  locator.
- Refuse or redirect requests for full graded-work answers.
- Return an explicit no-evidence response when approved support is absent.
- Handle provider timeout, malformed output, and unavailable-provider cases.
- Record latency, token usage, and approximate cost for the evaluation run.

### Demonstration and evidence

- Demonstrate a normal conceptual question, a misconception, a graded-work
  request, and a no-evidence question.
- Compare the configured grounded tutor with a generic or non-grounded baseline.
- Report retrieval results, citation validity, policy compliance, latency, and
  known limitations.
- Preserve a reproducible command, synthetic dataset version, and evaluation
  summary in the repository.

## Definition of done for technical work

Every implementation issue must provide:

1. A short design note explaining the selected approach and alternatives.
2. Tests using synthetic or anonymized fixtures.
3. A runnable verification or experiment command.
4. Quantitative evidence where the behavior can be measured.
5. Failure cases and limitations, not only successful examples.
6. Updated architecture or usage documentation.
7. A learning log written in the student's own words.
8. A merged pull request with passing CI and no sensitive data.

When the issue proposes or replaces an algorithm, model, prompt, parser,
ranking method, policy mechanism, or agent behavior, definition of done also
requires a control, shared evaluation conditions, hard gates, required metric
thresholds, a machine-readable component record, and an updated experimental
profile. See [evaluation-architecture.md](evaluation-architecture.md).

Architecture choices follow the same rule. Authentication, authorization,
persistence, object storage, deployment, monitoring, backup/restore, and
rollback require alternatives, tradeoffs, threat and failure cases, operational
measurements, a decision record, and a reversal path.

## Component selection and release profiles

The system is assembled from versioned component selections rather than one
permanent stack. Every decision-bearing boundary appears in the
[component inventory](component-inventory.md) and current experimental profile.
Only experimental profiles may contain unresolved components. Before a profile
becomes a release candidate, every component must be selected or explicitly
disabled with evidence.

Selection follows hard gates first, quality and operational thresholds second,
relative performance third, and implementation complexity last. Privacy,
permission, academic-integrity, provenance, and citation failures cannot be
traded against a higher aggregate score.

## Learning contract

The project should be understandable, not merely operational. For each major
component, the student should be able to explain:

- What problem the component solves.
- How data enters and leaves it.
- Why the chosen algorithm or boundary was selected.
- What assumptions it makes.
- How it is tested and measured.
- Where it fails and what should be improved next.

Before implementation, write a prediction about expected behavior and the main
failure risk. During implementation, inspect or implement the central algorithm
rather than treating it as a black box. After verification, complete the
[learning log template](../research/04_experiments/templates/learning-log.md).

The student should own the explanations and final decisions. AI assistance may
accelerate implementation, review, testing, and research, but it must not replace
the student's ability to reproduce and defend the work.

## Final project standard

By 2026-09-13, the project should defend six evidence-backed claims:

1. The end-to-end system works from approved source ingestion through cited
   tutoring output.
2. The professor-configured tutor behaves measurably differently from a generic
   assistant.
3. Evaluation artifacts support the reported strengths and limitations.
4. Permissions, privacy, academic integrity, and professor approval are explicit
   system controls.
5. Scripted professor and student accounts complete deployed acceptance
   journeys without cross-role or cross-course access, with durable state and
   visible recovery.
6. Security, reliability, synthetic interaction behavior, latency, cost,
   rollback, judge validity, and deployment limitations are measured rather
   than inferred from a local demonstration.

If evidence does not support a claim, the report must narrow or reject the claim
rather than presenting the demonstration as proof.

Human usability, satisfaction, engagement, adoption, and learning outcomes are
not evaluated and must not appear as supported claims.
