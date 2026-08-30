# Atomic M2 actual-product checkpoint 001 results

## Decision

**Refine and stop factual scaling.** Retrieval remained above its selected
development gates, but the actual T0 tutoring service did not reliably decide
when to answer, stay focused on the requested fact, or clarify ambiguity. The
sealed 10,000-case set remains unopened and the program authority is revoked.

## Results

| Measure | Candidate | Gate | Result |
| --- | ---: | ---: | --- |
| Fully grounded factual success | 44.25% | ≥95% | Fail |
| Source-family lower 95% bound | 38.89% | ≥93% | Fail |
| Answerable action accuracy | 71.50% | ≥95% | Fail |
| Boundary action accuracy | 89.00% | ≥98% | Fail |
| Atomic-claim precision / recall | 50.85% / 59.50% | ≥98% / ≥95% | Fail |
| Citation precision / recall | 55.65% / 65.13% | ≥98% / ≥95% | Fail |
| Complete evidence@3 | **96.25%** | ≥90% | Pass |
| Evidence Recall@5 | **97.25%** | ≥95% | Pass |
| Provider completion | **100%** | ≥99.5% | Pass |
| Severe ambiguity releases | 5 | 0 | Fail |

On the paired 100 cases, candidate boundary safety was 90% versus 95% for the
any-hit control. Supported-answer retention was −5.26 percentage points, with a
lower 95% bound of −15.79 points, so neither paired gate passed.

The run persisted 500 candidate and 100 control responses through 572 exact
GPT-5.4 mini calls. There were zero failed calls or retries, 426,021 input and
88,380 output tokens, and USD 0.71722575 reported cost. Both response ledgers
were complete before hidden gold opened.

## Failure interpretation

The main failure is downstream of retrieval. Of 400 answerable cases, the
product answered 286, abstained on 61, and requested clarification on 53. It
also answered five deliberately ambiguous questions instead of clarifying
them. Direct audit confirmed all five as genuine policy/action defects.

Strict target precision also penalized broader answers: 114 answered cases
included source-supported claims beyond the question's canonical target, and
96 included extra source-supported citations. These are off-target expansions,
not necessarily hallucinations, but they still violate the frozen concise,
question-specific contract. Some deterministic questions—especially markup and
table labels—are weak proxies for real student wording; that limitation does
not explain the severe ambiguity releases or the broad action-accuracy failure.

The next method decision should separate a deterministic boundary/action router
from generation and constrain generation to the question-required evidence.
That requires a fresh confirmation tranche, not tuning or rerunning these 500
known cases.

## Boundaries

This result evaluates public text and structured-text evidence through the
actual T0 service. It does not evaluate true visual understanding, professor
fidelity, real-user usability, learning outcomes, or the final 10,000 cases.
The audit is Codex-assisted researcher review and not independent external
human annotation.

## Evidence

- Machine record:
  `research/05_evaluation/records/academic-factual-qa-atomic-m2-product-checkpoint-001.json`
- Priority audit:
  `research/05_evaluation/judgments/academic-factual-qa-atomic-m2-product-checkpoint-001-codex-audit.json`
- Ignored runtime ledgers:
  `reports/generated/academic-factual-qa-atomic-m2-product-checkpoint-001/`
- Execution revision: `294e9c4`
