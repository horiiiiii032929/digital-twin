# Professor-fidelity proxy C0–C3 003 analysis correction 001

## Decision

`completed-refine`. The synthetic professor-profile proxy is not selected as
fidelity evidence.

## Why the interpretation changed

The immutable raw runner result remains `invalid-execution` because its generic
exception handler classified every post-parse contract violation as an
execution failure. Ledger inspection shows that transport, exact model identity,
accounting, and all 48 generation calls were valid. The actual failure was three
empty C0 `abstain` responses, which violated the preregistered non-empty response
contract.

That is a model-output quality failure, not a harness or provider failure.
Reclassifying the scientific decision as `Refine` makes the conclusion stricter
without changing any response, case, threshold, or raw artifact.

## Evidence

- Overall non-empty response completeness: 45/48 (93.75%).
- C0 non-empty response completeness: 9/12 (75%).
- C1–C3 non-empty response completeness: 36/36 (100%).
- All 48 generation calls completed with exact GPT-5.4 Mini identity.
- Provider failures, retries, identity drift, and private-data calls: zero.
- Reported usage: 18,196 input tokens, 6,233 output tokens, USD 0.0416955.
- Advisory review did not begin; profile adherence and uplift are unmeasured.

## Consequence

No C1–C3 hard-gate aggregate, C2-over-C1 uplift, or C3 retrieval effect is
claimed. The same packet will not be rerun or tuned. The implemented professor
profile and revision workflow remain part of the technically qualified local
R1.2 product, but issue #24 remains open for a new real-professor-approved
reference and future evaluation design.

## Links

- [Correction record](records/professor-fidelity-proxy-c0-c3-003-analysis-correction-001.json)
- [Raw invalid result](professor-fidelity-proxy-c0-c3-003-invalid-results.md)
- [Issue #24](https://github.com/horiiiiii032929/digital-twin/issues/24)
