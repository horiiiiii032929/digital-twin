# Professor-fidelity proxy C0–C3 002 invalid result

## Decision

`invalid-execution`. No profile-uplift or professor-fidelity interpretation is
allowed.

## What happened

The first GPT-5.4 Mini request reached the direct OpenAI endpoint, which rejected
the response schema because `uniqueItems` is unsupported in that Structured
Outputs context. No inference response was produced, so generation, hard-gate
scoring, and blinded advisory review did not begin.

## Accounting and boundary

- Provider attempts/completed: 1/0.
- Reported input/output tokens and cost: 0/0/USD 0.
- Private data used: no.
- Synthetic profile only; real-professor fidelity remains unproven.

The program's single harness-correction allowance was already consumed by the
separate pre-provider visual-run title defect. This C0–C3 run is therefore
preserved and not retried. The implemented professor profile and feedback
workflow remain usable, but issue #24 stays open for real-professor approval.

## Links

- [Machine-readable record](records/professor-fidelity-proxy-c0-c3-002-invalid.json)
- [Issue #24](https://github.com/horiiiiii032929/digital-twin/issues/24)
- [Issue #210](https://github.com/horiiiiii032929/digital-twin/issues/210)
