# Ambiguity-safe grounding comparison 001 invalid result

Decision: **Invalid execution — one harness-only correction is permitted.**

The authorized network-free run persisted all 500 baseline and 500 candidate
responses before opening hidden gold. It then stopped during aggregate decision
assembly because the runner looked for `fully_grounded_factual_success` at the
aggregate root instead of under the scorer's `metrics` namespace.

This is a demonstrated harness defect, not a grounding-quality result. No
candidate is selected and none of the partially computed metrics are used for a
decision. The response artifacts remain preserved under the ignored generated
output directory with hashes recorded in the machine-readable record.

- Provider calls, tokens, and paid cost: zero.
- Response packages persisted: 2/2 (1,000 total responses).
- Hidden gold opened only after both response packages were durable.
- Method, cases, source truth, scoring profile, and hard gates were unchanged.
- Authorization for attempt 001 was revoked.

Attempt 002 corrects only the metric-path lookup and uses a fresh exclusive
output directory. It does not change questions, responses, methods, scoring, or
decision thresholds.
