# Actual-product autonomy evaluation 006 invalid result

Decision: **Invalid execution — correct the demonstrated prompt/schema runtime
defect, then run one bound successor.**

The new privacy-safe diagnostics identified the repeated T0 failure precisely.
Three completed GPT-5.4 mini Responses calls returned HTTP 200, exact model
identity, valid JSON text, and reported usage, but failed the local
`ModelTutorOutputV2` validation stage. Code inspection then found that the T0
non-intent path used the old `answer`/`citation_ids` prompt while the API schema
and post-parse validator required atomic `claims`. The T1-v2 canary used its
claims-only intent prompt and completed all seven Terra/mini calls normally.

- Persisted canaries: 2/2.
- Bulk cases: 0/818.
- Provider calls: 11 total; seven completed, three schema-invalid, and one
  intentionally unavailable provider-failure probe.
- Reported tokens: 5,123 input and 759 output.
- Reported cost: USD 0.0112615.
- Hidden gold: unopened.
- Raw provider output: not retained.

This is a demonstrated runtime/harness defect, not a valid autonomy-quality
failure and not evidence of provider instability. Attempt 006 is immutable and
its authority is revoked. Successor 007 changes only the non-intent prompt
inheritance so it matches the already-authoritative atomic-claim schema; cases,
hidden gold, retrieval, models, gates, and diagnostic boundary are unchanged.
