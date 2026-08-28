# Open 10,000 factual-QA development checkpoint 003 — attempt 002

Result ID: `academic-factual-qa-open-10000-development-checkpoint-003-attempt-002-invalid`

Decision: **Invalid execution / stop the checkpoint**

Attempt 002 started from clean correction revision `bd1f7d4` with a fresh
ledger. GPT-5.4 completed the first four-control batch with the exact
`gpt-5.4-2026-03-05` identity. The ledger records one call, 2,177 input tokens,
506 output tokens, 4.869 seconds latency, and USD 0.0130325 reported cost.

The corrected schema produced only the five normalized defect labels. The
response identified one unsupported-claim mutation and one invalid-citation
mutation, but marked both candidate records `case_semantically_valid: true`.
That contradicts the frozen invariant that a record with a detected claim or
citation defect is not semantically valid. The deterministic parser rejected
the batch and stopped before hidden labels were opened.

This remains operationally invalid rather than evidence that GPT-5.4 passed or
failed the 40-control quality gates. No provider retry occurred. No wording,
T0 candidate, any-hit control, private-data, or final 10,000-case call occurred.
Across both invalid checkpoint attempts, two provider calls cost USD 0.02635.

The ignored attempt-002 ledger is
`reports/generated/academic-factual-qa-open-10000-openai-reviewer-calibration-002.sqlite3`
with SHA-256
`f53788c4b6fa0b529fb023c0f342c99b1dc8a25d251307765228e4ee9d73b884`.
Checkpoint-003 authorization is revoked. Any successor requires an explicit
reviewer-method decision rather than another silent prompt or schema revision.
