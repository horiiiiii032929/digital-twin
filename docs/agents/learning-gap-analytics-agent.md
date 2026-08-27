# Learning Gap Analytics Agent

## Purpose

Summarize recurring student misunderstandings and support needs for instructors
without exposing unnecessary student-identifying information.

## Current status

Issue [#132](https://github.com/horiiiiii032929/digital-twin/issues/132)
owns the implementation. The first build-only checkpoint now provides the
versioned signal, privacy policy, keyed pseudonymization, idempotent SQLite
storage, retention deletion, minimum-cohort aggregation, and deterministic
professor-review draft contracts.

It is not connected to live T1 turns yet, has no professor API or interface,
and cannot modify a course, policy, release, prompt, or learner state. T0
remains selected for release and T1 remains unpromoted.

## Autonomous-loop position

```text
committed T1 turn
      |
      v
privacy-minimized signal  -- no transcript, answer, name, or direct student ID
      |
      v
idempotent retained store -- keyed learner/turn pseudonyms only
      |
      v
minimum-cohort gate       -- fewer than five learners stays suppressed
      |
      v
deterministic aggregate   -- counts, scope, uncertainty, limitations
      |
      v
professor-review draft    -- cannot execute or publish a change
      |
      v
future professor decision -- accepted changes create a separately governed release
```

The online tutoring graph and the course-improvement loop have different
authority. The online graph may adapt a response and bounded learner state for
one authenticated conversation. The improvement loop may only summarize
eligible committed outcomes and prepare a draft for the course owner.

## Inputs

- Versioned privacy-minimized signals emitted after an atomic T1 turn commit.
- Course and release identifiers plus a bounded course-taxonomy topic key.
- Keyed pseudonymous learner and turn tokens used only for cohort suppression
  and idempotency.
- Tutor policy categories.
- Course topic taxonomy.
- Instructor feedback on useful reporting granularity.

## Outputs

- Learning-gap clusters.
- Topic-level summary.
- Evidence counts and limitations.
- Suggested teaching follow-ups for instructor review.

## Guardrails

- Never store raw student questions, answers, transcripts, names, direct account
  IDs, conversation IDs, message IDs, or unrestricted model output in an
  analytics signal.
- Aggregate before reporting by default.
- Suppress every topic/signal group below the configured distinct-learner
  threshold; suppressed cells expose only how many groups were withheld.
- Keep course and release scope immutable and reject cross-scope writes or
  aggregation.
- Treat duplicate source turns idempotently and reject conflicting replays.
- Expire and delete signals under the versioned retention policy.
- Keep uncertainty and sample-size limitations visible.
- Separate observed confusion from inferred teaching recommendations.
- Keep every recommendation at `draft-awaiting-professor-review`; analytics
  cannot mutate or publish course behaviour.

## Evaluation

- Synthetic interaction fixtures.
- Privacy exclusion tests.
- Cluster quality review.
- Instructor usefulness review.

## Open work

- [x] Define the first anonymization, suppression, and retention contracts.
- [x] Add deterministic aggregation and non-executable proposal contracts.
- [x] Add idempotent local persistence and expiry deletion.
- [ ] Emit signals only after the complete T1 turn and learner state commit.
- [ ] Add professor-authorized aggregate and draft review endpoints.
- [ ] Add a professor workspace review surface without student-level drill-down.
- [ ] Define release withdrawal, account deletion, and production key-rotation
  operations.
- Design instructor dashboard metrics.
- Add evaluation rubric for useful learning-gap summaries.
- Connect to student tutoring only after the remaining privacy and deletion
  review.
