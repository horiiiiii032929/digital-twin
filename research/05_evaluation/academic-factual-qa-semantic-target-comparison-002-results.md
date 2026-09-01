# Semantic-target grounding comparison attempt 002 result

## Decision

`Refine`. Reject `semantic-target-resolution-v3`, retain
`typed-target-evidence-v1` as the best protocol-valid development baseline,
and keep every final or autonomy stage closed.

## Result

The corrected network-free run completed all 500 fresh cases for both
conditions from clean revision `b62e9f8`. All public responses were durable
before hidden gold opened. There were no operational failures, provider calls,
tokens, paid cost, private data, or severe unsupported releases.

| Metric | Typed-target baseline | Semantic-target v3 | Gate |
| --- | ---: | ---: | ---: |
| Fully grounded factual success | 91.0% | 81.0% | 95% |
| Source-family lower 95% bound | 87.0% | 76.5% | 93% |
| Answerable action accuracy | 97.75% | 95.25% | 95% |
| Boundary action accuracy | 100% | 100% | 98% |
| Atomic-claim precision / recall | 91.75% / 91.75% | 83.13% / 83.13% | 98% / 95% |
| Citation precision / recall | 93.63% / 93.63% | 85.0% / 85.0% | 98% / 95% |
| All-evidence@3 / Recall@5 | 98.25% / 98.5% | 97.25% / 97.75% | 90% / 95% |
| Source-version validity | 100% | 99.75% | 100% |

The semantic candidate underperformed most clearly on paraphrased questions
(70% grounded), multi-evidence questions (75.68%), and structured tables
(62.5%). Both methods retrieved most required evidence, but neither converted
that coverage into release-quality claim and citation lineage. This localizes
the remaining problem to source-side semantic atom representation and exact
claim assembly rather than boundary routing or raw top-k retrieval.

## Method decision

- Do not tune or rerun either method on these 500 now-known cases.
- Drop the question-side IDF/bonus semantic resolver.
- Retain the typed-target method only as rollback and regression control.
- Design any successor around source-side, self-contained semantic evidence
  atoms with canonical ranges and explicit multi-atom relations, then evaluate
  it on new source-disjoint evidence.
- Do not open the fresh 1,000, known 10,000+1,000, or 820-case autonomy stages
  until a successor passes its development gates.

## Limits

This is fresh development evidence, not release confirmation. Extractive,
provider-free generation isolates grounding architecture. It supports no
professor-fidelity, real usability, learning-outcome, visual, or provider-backed
autonomy claim.
