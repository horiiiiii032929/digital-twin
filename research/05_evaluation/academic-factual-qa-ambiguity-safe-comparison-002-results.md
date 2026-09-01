# Ambiguity-safe grounding comparison 002 result

## Decision

`Keep` the ambiguity-safe source-semantic evidence-atom candidate for the next
provider-backed product confirmation. Retain `source-semantic-evidence-atoms-v1`
as rollback. This is a development-method selection, not an autonomous-product
release decision.

## Result

The sole corrective network-free attempt ran from clean revision `a7d6922` on
500 fresh cases across 100 source-range-disjoint clusters. Both conditions
persisted all 500 responses before hidden gold opened. There were no provider
calls, tokens, paid cost, operational failures, severe unsupported releases,
private data, or final-set access.

| Metric | V1 baseline | Ambiguity-safe V2 | Gate |
| --- | ---: | ---: | ---: |
| Fully grounded factual success | 97.75% | 97.75% | 95% |
| Source-family lower 95% bound | 95.5% | 95.5% | descriptive |
| Answerable / overall action accuracy | 100% / 100% | 100% / 100% | 95% |
| Boundary action accuracy | 100% | 100% | 98% |
| Atomic-claim precision / recall | 98.25% / 98.25% | 98.25% / 98.25% | 98% / 95% |
| Citation precision / recall | 100% / 100% | 100% / 100% | 98% / 95% |
| All-evidence@3 / Recall@5 | 100% / 100% | 100% / 100% | 90% / 95% |
| Source-version validity | 100% | 100% | 100% |
| Severe unsupported releases | 0 | 0 | 0 |

Every frozen hard gate passed. The candidate is non-inferior to the baseline on
the fresh comparison. The two methods are intentionally identical for a
reference-unique answerable question, so the equal fresh-set score is expected:
the V2 change is exercised when public evidence is non-unique.

## Ambiguity evidence

- All six planted relationship controls passed: unique, alternate-valid,
  partial, conflicting, unrelated, and genuinely ambiguous.
- All 16 known non-unique predecessor questions now route to `clarify` before
  generation. They are regression diagnostics only and were not rescored.
- All 400 answerable questions in the fresh package were pre-seal
  reference-unique, so they establish non-regression rather than a fresh
  ambiguity-effect estimate.

This combination supports selecting V2: planted and known-regression evidence
shows the intended fail-closed behavior, while the fresh comparison shows that
the safeguard does not reduce grounded quality on unambiguous questions.

## Execution history

Attempt 001 remains an immutable `invalid-execution` result. It persisted all
1,000 responses but used the wrong scorer metric namespace during final decision
assembly. Attempt 002 changed only that harness lookup, used a fresh exclusive
output, and kept the same methods, cases, hidden gold, scoring profile, and
gates.

## Release implication and limits

- Issue #172 can close as `Done / Keep` for the grounding-method correction.
- The previous autonomous LLM-backed **No Release** decision is not changed by
  this development comparison.
- Provider-backed actual-product autonomy evaluation remains a separate
  checkpoint under #157; no authority for it is granted here.
- This result does not establish professor fidelity, usability, real student
  learning improvement, true visual reasoning, or deployed-product quality.

