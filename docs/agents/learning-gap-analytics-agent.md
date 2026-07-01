# Learning Gap Analytics Agent

## Purpose

Summarize recurring student misunderstandings and support needs for instructors
without exposing unnecessary student-identifying information.

## Current status

Planned. No analytics agent implementation exists in Sprint 1.

## Inputs

- Anonymized or permissioned student interaction summaries.
- Tutor policy categories.
- Course topic taxonomy.
- Instructor feedback on useful reporting granularity.

## Outputs

- Learning-gap clusters.
- Topic-level summary.
- Evidence counts and limitations.
- Suggested teaching follow-ups for instructor review.

## Guardrails

- Do not expose raw student interactions unless consent and policy allow it.
- Aggregate before reporting by default.
- Keep uncertainty and sample-size limitations visible.
- Separate observed confusion from inferred teaching recommendations.

## Evaluation

- Synthetic interaction fixtures.
- Privacy exclusion tests.
- Cluster quality review.
- Instructor usefulness review.

## Open work

- Define anonymization and retention model.
- Design instructor dashboard metrics.
- Add evaluation rubric for useful learning-gap summaries.
- Connect to student tutoring only after privacy review.

