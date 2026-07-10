# Quality and Learning Plan

Last reviewed: 2026-07-10

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
- Keep Canvas optional; LMS integration is not a substitute for research depth.
- Do not claim learning effectiveness without an evaluation design that supports
  that claim.

## Delivery timeline

| Dates | Deliverable | Required learning outcome |
| --- | --- | --- |
| Complete | Sprint 1: instructor onboarding | Requirements, policy modeling, review UX, and release gates |
| 2026-07-11 to 2026-07-14 | Document parsing and chunking | Normalization, provenance, content boundaries, and deterministic tests |
| 2026-07-15 to 2026-07-16 | Retrieval and source evidence | Lexical ranking, retrieval metrics, citation relationships, and error analysis |
| 2026-07-17 to 2026-07-18 | Live generation and policy enforcement | Prompt construction, provider adapters, policy controls, latency, and cost |
| 2026-07-19 | Grounded tutoring evaluation and demonstration | Integration, baseline comparison, failure cases, and technical explanation |
| 2026-07-20 to 2026-07-26 | Student tutoring prototype | Conversation state, student UX, safety, and operational failures |
| 2026-07-27 to 2026-07-31 | Proactive learning prompts | Explainable triggers, suppression, and student control |
| 2026-08-03 to 2026-08-15 | Learning-gap report | Aggregation, privacy thresholds, uncertainty, and instructor actionability |
| 2026-08-17 to 2026-08-23 | Evaluation dataset and rubric | Experimental design, annotation guidance, and reproducibility |
| 2026-08-24 to 2026-09-01 | Baseline comparison and refinement | Quantitative comparison, regression analysis, and evidence-backed decisions |
| 2026-09-02 to 2026-09-13 | Final report and presentation | Defensible claims, limitations, reproducibility, and research communication |

## Strengthened Sprint 2 bar

Sprint 2 is not complete when one plausible answer appears on screen. It must
produce an inspectable, evaluated vertical slice.

### Course corpus

- Use 4-8 synthetic or explicitly approved course documents.
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
- Report Recall@5 and Mean Reciprocal Rank for retrieval.
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

By 2026-09-13, the project should defend four evidence-backed claims:

1. The end-to-end system works from approved source ingestion through cited
   tutoring output.
2. The professor-configured tutor behaves measurably differently from a generic
   assistant.
3. Evaluation artifacts support the reported strengths and limitations.
4. Permissions, privacy, academic integrity, and professor approval are explicit
   system controls.

If evidence does not support a claim, the report must narrow or reject the claim
rather than presenting the demonstration as proof.
