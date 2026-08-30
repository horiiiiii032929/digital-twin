# Independent reference-question validation 004

## Outcome

`invalid-execution`. Seven direct OpenAI calls were durably recorded before the
runner terminated while locally parsing an author response containing duplicate
candidate wording. This is a harness classification defect, not a reference-
question quality result.

## Operational evidence

- 7/80 planned calls completed with exact model identities and zero retries.
- 23,040 input and 17,375 output tokens were reported.
- Reported cost was USD 0.2426915; total provider latency was 103.864 seconds.
- The response that exposed the defect remains in the ignored, hash-bound ledger.
- No selected package, product response, private source, hidden final gold, or
  sealed 10,000+1,000 case was opened.

## Correction

Attempt 005 changes only failure handling. Candidate duplicates remain durable
and are rejected as per-candidate quality failures instead of invalidating the
entire execution. It retains the same source pool, cases, prompts, model roles,
gold, quotas, 80-call limit, zero retries, and acceptance gates.

## Limitations

No question-quality or product-quality metric is interpretable from this
incomplete attempt. The seven-call spend is included in cumulative program
accounting and is not discarded.
