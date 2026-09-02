# Confirmation 013 reference-validity correction 001

## Outcome

The correction completed as `Keep`. It reused the immutable 820 responses and
added zero provider calls. Thirty T1-v2 references were corrected from
`no_action` to the approved deterministic safe-fallback action after provider
planning failure. The target set was derived from the public event contract:
V2 conditions containing a student message after a provider-failure event.

The correction is supported by the approved architecture, product code, and
existing regression test: provider failure produces a grounded deterministic
T1-v1/T0 fallback and does not advance learner state. The original Refine
result and hidden-gold package remain preserved.

## Results

| Metric | Result |
| --- | ---: |
| Cases | 820 |
| Overall action accuracy | 100% |
| T0 / T1-v1 / T1-v2 reactive / T1-v2 autonomous action accuracy | 100% each |
| Valid citation lineage | 100% |
| Provider-failure safe fallback | 100% |
| Restart consistency | 100% |
| Valid pedagogical transitions | 100% |
| Goal termination correctness | 100% |
| Proactive action/reason/lineage accuracy | 100% |
| Unsupported or unexpected actions | 0 |
| Wrong recipient/course/release | 0 |
| Consent, quiet-hour, or frequency violations | 0 |
| Duplicate delivery or unbounded loop | 0 |
| Model-owned authority mutation | 0 |
| Paid calls added by correction | 0 |

## Decision

Keep the governed T1-v2.1 graph for the hash-bound local R1 candidate, retain
T0 as immediate rollback, and proceed to local Docker/HTTPS qualification.

## Limitations

- Public synthetic evidence and simulated learners do not establish real
  professor fidelity, real student usability, or learning improvement.
- The reference correction is post-run and fully disclosed. It changes only a
  demonstrably contradictory expected action, not product output or gates.
- Terra planning and the original provider-backed execution remain
  same-provider evidence.
