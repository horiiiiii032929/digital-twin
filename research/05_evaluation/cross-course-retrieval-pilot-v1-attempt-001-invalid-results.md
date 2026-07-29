# Cross-course retrieval pilot attempt 001 — invalid

Date: 2026-07-28

Run ID: `cross-course-retrieval-pilot-v1-development-attempt-001-invalid`

## Outcome

The local development pilot stopped after completing 32 of 40 cases. The
course-scoped runtime attempted to resolve a boundary case whose
`target_course_id` is intentionally null and raised:

```text
KeyError: None
```

The failure occurred before aggregation and before a result file was written.
No partial quality metric is retained or interpreted. No external provider was
called, and none of the 60 `heldout_draft` cases was loaded or scored.

## Classification and decision

- Failure class: integration / evaluation-context routing.
- Cause: the initial runtime assumed every case had a target course, while
  no-evidence and adversarial boundary cases are course-independent at the
  dataset layer.
- Data impact: none; the private draft and review state were unchanged.
- Decision: **Refine**. Keep the failed attempt visible, define a deterministic
  course context for development boundary cases, add per-case checkpoints, and
  run a new development attempt. This failure cannot inform method selection.
