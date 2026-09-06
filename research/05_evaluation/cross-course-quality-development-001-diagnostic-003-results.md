# Cross-course targeted diagnostic 003

## Decision

**Go Deeper.** Two actual model calls completed and delivered source-supported
explanations. The remaining response-schema failure from live 002 did not recur,
so this small diagnostic does not establish its cause or resolution.

The selected known development cases were `scheduler-paraphrase` and
`scheduler-misconception`, each run through incumbent and candidate: four product
cases, two external calls, zero injected failures. Both arms passed their two
mechanical source-containment diagnostics. This was a bounded reproduction
attempt before any full 88-case repeat, not a new quality confirmation.

The candidate returned the source's earliest-deadline ordering sentence and its
paused-task exclusion sentence. Both were accurately quoted and delivered as
explanations. Assistant review therefore supports the revised explanatory
rendering on these cases. It is not an independent human review, population
quality estimate or evidence of real-instructor fidelity.

## Accounting and boundaries

- Model: `gpt-5.6-luna`; two accepted responses, zero provider errors.
- Input/output/total tokens: 1,339 / 268 / 1,607.
- Reported cost: USD 0.0005894.
- Candidate and transport changed since 002; this is not a single-variable
  attribution of improvement.
- No schema error occurred, so the new schema-error diagnostics supplied no
  evidence about the unresolved rejection cause.
- Product citations establish paragraph containment, not exact claim offsets;
  semantic quality remains unscored in the automatic summary.

The [machine record](records/cross-course-quality-development-001-diagnostic-003.json)
retains the dirty revision, configuration and execution hashes. Raw artifacts
remain under `reports/generated/cross-course-quality-development-001-diagnostic-003/`.
Keep live 001 and 002 failures unchanged; use a bounded targeted follow-up to
capture the remaining error rather than claiming success from this subset.
