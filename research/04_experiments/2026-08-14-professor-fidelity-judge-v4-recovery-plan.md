# Professor-fidelity judge v4 recovery plan

Date frozen: 2026-08-14

Status: Frozen before the public probe and any new private judging

## Decision question

Can the pedagogical judge represent and correctly reject an empty tutor
response while preserving exact-quote auditability, then complete a separately
identified primary anchor judgment run?

## Baseline and failure

The v3 baseline passed empty generator answers to the judge unchanged while
requiring a non-empty exact evidence quote. Primary anchor attempt 001 stopped
after 5/12 completed cases when a case-6 single judgment was invalid. The
unfavorable result is retained as
`professor-fidelity-v2-anchor-002-deepseek-primary-attempt-001-invalid` and
cannot be rerun.

## Candidate contract v4

- Preserve the original response for the source run.
- Display a whitespace-only response to a judge as the literal
  `[EMPTY RESPONSE]`.
- Require every single and pairwise evidence quote to be an exact substring of
  the displayed response.
- Preserve the frozen rubric, labels, blinding, case order, DeepSeek V4 Pro
  high-thinking binding, exact fingerprint, no-retry rule, and USD 1 anchor
  stop.
- Give every judge attempt a stable three-digit attempt identifier and refuse
  to overwrite either its result or checkpoint.

## Public probe and hard gate

Run one public-synthetic single-response probe with an empty response. It passes
only if:

- the displayed response is exactly `[EMPTY RESPONSE]`;
- the judge returns a schema-valid `fail` for `actionability`;
- the evidence quote is exactly `[EMPTY RESPONSE]`;
- the current `deepseek-v4-pro` model and frozen fingerprint are observed;
- there is one call, no retry, no private text, and cost remains below USD 0.25.

An invalid probe is registered and blocks private attempt 002. A passed probe
permits a new full primary attempt 002 from case 1; it does not validate the
judge semantically beyond this defect, authorize development or held-out, or
replace either required human review.

## Subsequent order

1. Run and register the public probe from a clean revision.
2. If it passes, freeze its raw hash into the active anchor judge binding.
3. Run primary anchor attempt 002 once from a clean revision.
4. Only after a valid primary result, run swapped DeepSeek and diagnostic local
   Qwen sensitivity, prepare the blinded reference packet, and compute
   prehuman calibration.
5. Stop for the bounded human reference and the separate 41-case authoring
   audit.
