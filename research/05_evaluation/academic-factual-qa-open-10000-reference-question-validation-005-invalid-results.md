# Independent reference-question validation 005

## Outcome

`invalid-execution`. The duplicate-candidate harness correction worked, but one
OpenAI author response did not complete after 32 successful calls. The zero-retry
instrument correctly stopped; no reference or product quality claim follows.

## Operational evidence

- 32 completed and one failed call were durably recorded; zero retries occurred.
- Completed calls reported 116,096 input and 86,645 output tokens.
- Reported completed-call cost was USD 1.291204; total recorded latency was
  533.175 seconds.
- The failed author-017 call has no accepted output and its batch is unusable.
- No selected package, product response, private source, hidden final gold, or
  sealed 10,000+1,000 case was opened.

## Decision

Attempt 006 is the last provider-resilience correction for reference construction.
It retains the three-candidate method, reduces batches from four to three clusters,
and quarantines isolated non-identity provider failures. Affected clusters are
ineligible; selected clusters must still pass every source, action, span,
naturalness, ambiguity, leakage, uniqueness, lineage, and quota requirement.

## Limitations

No reference-question quality metric is interpretable from this incomplete run.
The failed HTTP response did not expose token usage through the current strict
transport, so USD 1.291204 is the reported completed-call cost, not a claim that
the failed request was free.
