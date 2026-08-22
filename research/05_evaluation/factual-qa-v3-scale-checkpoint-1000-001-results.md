# Factual-QA 1,000-case checkpoint attempt 001

## Decision

**Invalid execution.** Correct the harness prospectively and rerun the same
additional-900 scope as attempt 002. No dataset, method, or model-quality
conclusion is allowed from this attempt.

## What happened

- Clean revision: `795fc2f48e3117a6f4e6f00b72b3e2e741481dae`
- DeepSeek author canary: passed.
- Independent-reviewer canary: rejected locally before provider I/O.
- Root cause: its generated task identifier was 67 characters while the shared
  task contract permits at most 64.
- Bulk calls: 0.
- Provider responses: 1 of 2 attempts.
- Reported cost: USD 0.00004092.
- Raw ignored artifact SHA-256:
  `9749c4fbc48ade6d5307b76c9be249cccf77d6afbf2e63c0584cd3235696a4eb`.

The one-time attempt-001 authorization is revoked. Attempt 002 changes only the
task identifiers to fixed short values; truth packages, model bindings, gates,
and the remaining-9,000 boundary are unchanged.
