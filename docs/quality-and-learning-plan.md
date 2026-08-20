# Quality and Learning Plan

Last reviewed: 2026-08-20

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
| 2026-07-27 to 2026-07-29 | Scope and architecture lock | Multi-course product thesis, research questions, roadmap, repository architecture, and preserved decision history |
| 2026-07-30 to 2026-08-02 | Course portfolio and benchmark freeze | Permission inventory, heterogeneous ingestion QA, about 100 verified cases, second review, and sealed split |
| 2026-08-03 to 2026-08-08 | Cross-course retrieval qualification | Bounded provider qualification, shared M0-M3 implementation, development analysis, prospective freeze, one sealed run, result registration, and profile decision |
| 2026-08-09 to 2026-08-12 | Pedagogical Digital Twin product | Multi-course professor configuration, evaluation-before-publication, invite-only student tutoring, persistence, citations, withdrawal, and rollback |
| 2026-08-13 to 2026-08-16 | End-to-end validation and evidence freeze | Professor fidelity, pedagogy, synthetic journeys, isolation, failure recovery, bounded capacity, local deployment package, and frozen claims |
| 2026-08-17 to 2026-08-31 | Analysis and report foundation | Complete analysis, claim-to-evidence matrix, main figures, report foundation, demo stabilization, and appointment preparation |
| 2026-09-01 to 2026-09-09 | Presentation and revision | Complete draft, target 2026-09-04 professor presentation, revise evidence and communication, and rehearse failure recovery |
| 2026-09-10 to 2026-09-12 | Contingency buffer | Correct blocking defects, package the submission, and protect frozen claims from late scope growth |
| 2026-09-13 | Final presentation and submission | Deliver the report, deployed demonstration, presentation, and reproducibility package |

## Cross-course research bar

Sprint 2 is not complete when one plausible answer appears on screen. It must
produce an inspectable, evaluated vertical slice.

### Course portfolio

- Use roughly four heterogeneous, explicitly permitted courses for the final
  evaluation. IT5002 is a pilot and may be one portfolio course.
- Support UTF-8 text, Markdown, and selectable-text PDF input.
- Preserve document ID, title, source label, content hash, and a human-readable
  locator through normalization and chunking.
- Reject unsupported, empty, excluded, or unapproved sources explicitly.
- Commit only synthetic fixtures; never commit private course or student data.

### Chunking and retrieval

- Implement a deterministic heading/paragraph-aware chunker with documented
  size and overlap decisions.
- Compare exactly M0 heading-aware BM25, M1 dense, M2 BM25+dense hybrid, and M3
  hybrid plus reranking under shared chunks, queries, filters, and metrics.
- Qualify provider/model candidates on development data, then freeze one
  embedding and reranking configuration for the final comparison.
- Build about 100 researcher-verified cases: 60 answerable and 40 no-evidence,
  cross-course confusion, or adversarial cases. Independently second-review at
  least 20%.
- Treat complete-evidence success@3, atomic-claim coverage@3, no-evidence
  accuracy, and course-isolation violations as primary. Report Recall@k, nDCG,
  MRR, latency, cost, and failure type as diagnostics.
- Record failed queries and explain whether the source, chunking, query, or
  ranking caused each failure.
- Keep black-box products outside internal ranking comparisons when candidate
  rankings are hidden. Report them only as dated qualitative product references.

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

- Validate the exact judge, simulator, run-record, and analysis freeze with
  `npm run verify:evaluation-instruments` before provider calls or sealed
  inspection.
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

By 2026-09-13, the project should defend seven evidence-backed claims:

1. Multiple professors can independently configure, evaluate, publish,
   withdraw, and roll back course Digital Twins.
2. The selected or rollback retrieval profile has defensible cross-course
   evidence against M0-M3 controls.
3. The professor-configured tutor behaves measurably differently from grounded
   and non-grounded generic controls.
4. Students receive course-isolated, persistent, cited tutoring or an explicit
   safe action when evidence or policy is insufficient.
5. Permissions, privacy, academic integrity, and evaluation-before-publication
   are explicit system controls.
6. Scripted and simulated journeys exercise isolation, provider failure,
   recovery, and bounded capacity without being presented as human usability.
7. Reliability, latency, cost, rollback, judge validity, portability, failures,
   and limitations are measured rather than inferred from a demonstration.

If evidence does not support a claim, the report must narrow or reject the claim
rather than presenting the demonstration as proof.

Human usability, satisfaction, engagement, adoption, and learning outcomes are
not evaluated and must not appear as supported claims.
