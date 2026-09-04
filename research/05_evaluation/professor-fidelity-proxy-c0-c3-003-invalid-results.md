# Professor-fidelity proxy C0–C3 003 invalid result

## Raw runner decision

`invalid-execution`. The runner stopped after generation because three parsed
responses violated the preregistered non-empty response contract. The blinded
review stage did not begin, so this raw result contains no C0–C3 profile-uplift
estimate.

## What happened

The schema-corrected direct OpenAI execution completed all 48 planned
GPT-5.4 Mini generation calls. Exact model identity, accounting, and transport
remained valid. Forty-five responses were non-empty. The following three C0
generic-control outputs selected `abstain` but returned an empty response:

- `generate:C0:pfp-003`
- `generate:C0:pfp-004`
- `generate:C0:pfp-006`

The runner then raised `ProfessorProxyCheckpointError: generator response
length drifted`. This was not an internet interruption, provider failure,
identity drift, ledger defect, or unsupported-schema failure.

## Accounting and boundary

- Provider attempts/completed/failed: 48/48/0.
- Reported input/output tokens: 18,196/6,233.
- Reported cost: USD 0.0416955.
- Maximum latency: 4,237.192 ms.
- Non-empty response completeness: 45/48 (93.75%).
- C0 non-empty response completeness: 9/12 (75%).
- C1–C3 non-empty response completeness: 36/36 (100%).
- Advisory reviews: 0/24; not entered.
- Private data used: no.

The separate analysis correction classifies the scientifically relevant outcome
as `Refine`: this is a valid model-output contract failure even though the raw
runner used the broader `invalid-execution` label. No C1–C3 hard-gate aggregate,
profile uplift, or professor-fidelity claim is made, and these 12 cases will not
be tuned or rerun.

## Links

- [Raw machine-readable record](records/professor-fidelity-proxy-c0-c3-003-invalid.json)
- [Analysis correction](professor-fidelity-proxy-c0-c3-003-analysis-correction-001-results.md)
- [Issue #24](https://github.com/horiiiiii032929/digital-twin/issues/24)
