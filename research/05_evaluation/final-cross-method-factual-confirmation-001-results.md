# Evaluation result: final cross-method factual confirmation 001

## Outcome

The fresh, source-disjoint 1,000-case comparison completed validly. All five
actual-product arms persisted their responses before hidden gold was opened.
No provider was called and cost was zero.

BM25 with the dominance-scoped ambiguity gate was the highest-scoring arm,
reaching 63.25% fully grounded factual success (source-family bootstrap 95% CI
58.75%–67.63%), 99.75% answerable-action accuracy, and 96.0% boundary-action
accuracy. It did not meet the preregistered 95% fully grounded or 98% boundary
gates, so the decision is **Refine**, not Keep.

## Comparison

| Arm | Fully grounded | Boundary action | All evidence@3 | Recall@5 | Severe releases |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 + any-hit | 0.00% | 100.00% | 98.00% | 99.38% | 0 |
| BM25 + question-targeted | 63.25% | 95.50% | 98.00% | 99.38% | 0 |
| **BM25 + dominance** | **63.25%** | **96.00%** | **98.00%** | **99.38%** | **0** |
| Qwen3 hybrid + question-targeted | 62.00% | 94.50% | 92.88% | 97.63% | 0 |
| Qwen3 hybrid + dominance | 62.00% | 95.00% | 92.88% | 97.63% | 0 |

The any-hit arm retrieved the evidence but exposed an unrestricted evidence set
to a generator that requires exactly one or two selected atoms, so it safely
abstained on answerable cases. It remains a historical control rather than a
release candidate.

## Interpretation

The comparison answers the selection question without another tuning loop:
Qwen3 hybrid did not improve this corpus, and BM25 plus the dominance gate is
the best measured safe fallback. Retrieval itself was strong, but target-to-
claim selection and mechanically generated structured questions were the main
failure surfaces. A representative example asked for “the source point about
2” while its canonical answer was a raw table row; the system retrieved the
correct region but selected a different routing statement. The sealed case is
retained unchanged and the limitation is disclosed rather than corrected after
the result.

This result therefore supports a safe local research demo with an explicit
quality limitation. It does not support a high factual-quality or real-learning
claim, and the same 1,000 cases must not be used for further tuning.

## Decision

Record **Refine** for the academic factual-quality claim. Use explicit BM25 plus
the dominance-scoped ambiguity gate as the measured release fallback, subject
to exact local requalification. Remove Qwen from the release manifest so the
manifest no longer claims a component that staging silently replaces.
