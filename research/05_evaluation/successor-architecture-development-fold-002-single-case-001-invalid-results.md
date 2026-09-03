# Successor architecture development fold 002 — invalid attempt 001

The first single-case execution is `invalid-execution`; no architecture-quality
result is available.

- Both canaries and all 120 planner attempts ran. Two transient connection
  failures were preserved as intended safe-fallback evidence.
- Actual-graph materialization then failed because the runtime prefixed a valid
  provider reason after validating it at the same 128-character output limit.
- The ledger records 122 calls, 62,187 input tokens, 31,811 output tokens,
  USD 0.0506106, and zero retries.
- No graph cells were persisted and hidden gold remained unopened.

This is a demonstrated runtime/harness boundary defect, not model or
architecture quality. Authority is revoked and the output path will not be
reused. One fresh harness-only correction may normalize composed reason codes
without changing the model, prompts, cases, gold, gates, or evaluation method.
