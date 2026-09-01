# Actual-product autonomy evaluation 004 invalid result

Decision: **Invalid execution — stop this evaluation portfolio.**

The final permitted provider-backed attempt stopped after its two canary cases
and before all 818 bulk cases. The schema correction worked: the T1-v2 canary
completed three exact `gpt-5.6-terra` planning calls and four exact
`gpt-5.4-mini-2026-03-17` generation calls. The T0 canary's single GPT-5.4 mini
generation response was classified as malformed before a response identity or
token usage could be accepted. A brief connectivity interruption cannot be
excluded, but the next seven calls succeeded and unrestricted response content
was not retained, so the exact transient cause is unresolved. With zero retries
and an exact canary gate, the runner failed closed.

This is an operationally invalid execution, not an autonomy-quality result.
Hidden gold remained unopened and no Keep/Refine product decision is valid.

- Persisted canaries: 2/2.
- Canary cases passing the exact model-role gate: 1/2.
- Bulk cases: 0/818.
- Provider calls: 8 total; seven completed and one failed.
- Reported tokens: 3,824 input and 461 output.
- Reported cost: USD 0.00900625.
- Observed exact identities: `gpt-5.6-terra` and
  `gpt-5.4-mini-2026-03-17` in the successful T1-v2 canary.

Attempt 004 consumed the one preregistered harness-only correction. The user
subsequently requested one explicit connectivity retry, now frozen as attempt
005 with no method, prompt, schema, case, gold, model, or gate change. The
820/820 network-free result remains valid infrastructure evidence, but
provider-backed T1-v2 promotion and an autonomous release claim remain
unsupported unless 005 produces a valid result.
