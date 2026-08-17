# Generator qualification v2 cross-model review v2 plan

Date frozen: 2026-08-14

Status: prospectively frozen after invalid Qwen review attempt 001

## Purpose and unchanged boundary

This plan repairs only the local review method. The source V4 Pro run, all 48
public-synthetic cases, source hashes, exact Qwen model digest, loopback-only
boundary, no-retry rule, and eight review dimensions remain unchanged from
the v1 plan. Gemma, private course text, generator held-out data, human audit
artifacts, and professor-fidelity condition mappings remain prohibited.

The first Qwen attempt is invalid because every case copied the example's
approval reason and the reviewer approved an obvious clarification failure.
None of its decisions are reused.

## Prospective repairs

- Prompt version: `generator-qualification-v2-qwen-review-v2`.
- Remove the filled approve object from the prompt.
- Require a concise case-specific reason naming a concrete action, claim, or
  source; reject the copied v1 reason.
- Before candidate review, run five fixed public probes: one valid answer and
  four failures covering clarification action, unsupported claims, missing
  citations, and assessed-work completion.
- Every probe must return the expected approve/revise decision, required false
  fields, no uncertainty, and a non-generic reason. Any miss writes an invalid
  stress-gate artifact and stops before candidate case 1.
- If the gate passes, review all 48 cases with stable per-case seeds and no
  retry. A repeated-reason ceiling prevents another all-template result.

Passing this review still cannot repair the two deterministic generator
failures, select V4 Pro, open generator held-out, or bypass the 41-case
independent-human authoring audit. It only provides a more credible
cross-family classification for the next prompt/orchestration revision.
