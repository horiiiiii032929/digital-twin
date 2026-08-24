# Evidence-sufficiency v2 independent-review 008 result

## Decision

**Drop this independent reviewer for the frozen evidence-sufficiency contract,
revoke authorization, and do not open the 120-case bulk review.**

The direct provider path worked, but the reviewer failed the prospective
sensitivity gate. It approved all six clean controls and detected five of six
deliberate defects. The required rates were 100% specificity and 100% defect
detection, so the sensitivity-first stop correctly suppressed all 12 bulk
batches.

## Execution

- Clean execution revision: `d55f256f591467b2d950b92468827b04b12db20e`.
- Provider and model: direct official DeepSeek API, exact
  `deepseek-v4-pro`.
- Returned provider revision:
  `a307abda487cd1b463329ccb945ce396`.
- Instrument SHA-256:
  `3581fa696ad6c24bc5252d63638bbee979f2a3ec27361f86b6f9e30e850717c6`.
- Review-packet SHA-256:
  `30f8070557083463e1a311479e95b30c62250f75bef1f40f3f10057482673011`.
- Reviewer-binding SHA-256:
  `5971e35e5bad974fbb554471e2735f2d93723d7c68ec729f9c7898fb5d5e1cdc`.
- Runner SHA-256:
  `a3a7a652f880b06373b0c4e6a87b11ec3a6d27dd468316014ffb3c26d23607bc`.
- Raw ignored output SHA-256:
  `abc2bd208be0930c9d59a266b9b2562787fba17a0c272dc9e71fd03ad2487800`.
- Data boundary: synthetic-public only; no private or held-out data read.

## Observed result

- Calls attempted / provider responses: 1 / 1.
- Bulk calls attempted: 0 / 12.
- Sensitivity judgments accepted: 12 / 12.
- Clean specificity: 6/6, or 100%.
- Deliberate-defect detection: 5/6, or 83.33%, below the 100% gate.
- Provider-reported input / output tokens: 3,819 / 1,282.
- Provider-reported cost: USD 0.002776605.
- Latency: 12,626.21 ms.
- Input/output token-limit violations: 0 / 0.
- Final state: `completed-reviewer-unreliable`.

The missed defect was `esv2-review-defect-01`. Its base case asks, “What
ordering does linearizability require?” and supplies an active source stating
that each completed operation must appear at one instant between invocation
and response. The mutation replaced the correct `answer` action and lineage
with `abstain`, no claims, no evidence, and `no-approved-evidence`. The reviewer
incorrectly approved that mutation.

## Cross-review finding

The response contract, exact model identity, fingerprint, source boundary,
accounting, and sensitivity scoring are internally consistent. The missed
wrong-action mutation is unambiguous and is a genuine reviewer-quality failure,
not a harness or provider failure. No priority packet exists because the
prospective sensitivity gate stopped the bulk review.

## Valid and invalid conclusions

This run supports dropping direct DeepSeek V4 Pro as the independent reviewer
for this exact contract. It does not evaluate the 120-case decision draft or
any evidence-sufficiency candidate because the bulk cases remained unopened.
It therefore cannot select a production answerability gate or freeze a dataset.

## Next gate

Keep review 008 immutable and authorization revoked. Do not begin another
provider or prompt search. Issue #105 should move to the remaining method-level
option: deterministic source/action/claim/evidence checks plus a bounded
researcher audit of the decision packet. Candidate evaluation, dataset freeze,
deployment, private sources, and held-out execution remain unauthorized.
