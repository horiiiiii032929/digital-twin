# Persona wording bank 022 attempt 001 — invalid execution

## Outcome

`invalid-execution / Refine`. The first provider response reached the local
transport, but the provider binding omitted the required
`provider_display_name` field. The runner raised `KeyError` before it could
persist parsed usage or accept any generated wording.

## Scope and accounting

- Requirements: 1,104 public-synthetic semantic frames from 78 deterministic
  actual-product histories.
- Attempted provider requests: 1.
- Completed and accepted requests: 0.
- Bulk execution: not started.
- Ledger-reported cost: USD 0; actual first-request cost is unavailable because
  the harness failed before usage persistence.
- Private data: none.

## Decision

Preserve this attempt without quality interpretation and revoke its authority.
Attempt 002 changes only the missing binding field, uses a new exclusive ledger
and output path, and retains the same requirements, model, prompt, gates,
46-call ceiling, zero retries, and USD 1 emergency stop.
