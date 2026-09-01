# Actual-product autonomy evaluation 003 invalid result

Decision: **Invalid execution — use the single harness-only correction.**

The provider-backed run stopped after its two canary cases and before all 818
bulk cases. The T0 canary reached the exact GPT-5.4 mini snapshot. The T1-v2
canary's Terra planning request was rejected before inference because the
Pydantic-generated strict schema did not list every defaulted property in
`required`, as required by the current Responses API schema validator.

This is a demonstrated provider-schema transport defect, not an autonomy
quality result. Hidden gold remained unopened and no Keep/Refine product
decision was made.

- Persisted canaries: 2/2.
- Bulk cases: 0/818.
- Run-ledger calls: 9 total; seven completed and two failed, including one
  deliberately injected provider-failure path.
- Reported tokens: 3,438 input and 474 output.
- Reported run cost: USD 0.0047115.
- Exact model identity: GPT-5.4 mini observed; Terra not observed because its
  request failed schema validation.

Two post-stop API probes diagnosed and verified the correction. They are
disclosed as two external diagnostic calls; their exact token/cost totals were
not retained in the immutable run ledger and are not reconstructed.

Attempt 004 changes only provider-side JSON-Schema translation: every object
property is required, unsupported validation keywords are removed, and
Pydantic validation remains authoritative after parsing. Events, hidden gold,
method, model roles, policy, and hard gates are unchanged. No further harness
correction is permitted after attempt 004.
