# Atomic M2 confirmation 001 results

## Decision

**Keep unchanged M2 and Go Deeper once to actual-product development.** On a
fresh source-family-disjoint 500-case package with unique, non-overlapping
authoritative evidence atoms, the small BM25 + OpenAI embedding hybrid passed
every prospective retrieval gate. The added marginal-coverage selector also
passed, but was slower and less accurate, so it is not selected.

## Results

| Method | Complete evidence@3 | Evidence Recall@5 | Boundary accuracy | p95 latency | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| M2 unchanged small hybrid | **96.25%** | **97.25%** | **100.00%** | **23.23 ms** | Keep |
| M2C marginal-coverage selector | 94.50% | 97.25% | 100.00% | 27.77 ms | Not selected |

The frozen gates were 90% complete evidence@3, 95% Evidence Recall@5, 98%
boundary accuracy, retrieval p95 no greater than two seconds, and zero severe
release, course, source-version, private-data, or leakage violations. M2 missed
complete top-three evidence on 15 of 400 answerable cases; M2C missed 22.

The run completed 15 direct OpenAI embedding calls with zero retries and cost
USD 0.00057628. All public rankings were durable before hidden gold opened.
The public source package contains corpus chunks and sanitized cluster metadata,
but no reference targets, canonical claims, or gold evidence spans.

## Interpretation and next boundary

This prospective result confirms that AFQC-103's apparent failure was dominated
by overlapping parent/child reference semantics, not by a need for a more
complex retrieval selector. The selected method is the simpler unchanged M2
over atomic evidence units.

This is retrieval evidence only. It does not establish generated-answer
quality, professor fidelity, visual grounding, human usability, or the final
10,000-case result. The factual branch may now perform one 500-case candidate
plus 100-case control actual-product evaluation. The sealed 10,000+1,000 stage
remains closed until that product checkpoint passes.

## Evidence

- Machine-readable record:
  `research/05_evaluation/records/academic-factual-qa-atomic-m2-confirmation-001.json`
- Ignored rankings and runtime evidence:
  `reports/generated/academic-factual-qa-atomic-m2-confirmation-001/`
- Execution revision: `fa38820`
- Public rankings SHA-256:
  `0dd3664301287523496457022b5dbd558827f36c7475f524d8103ba76b4e394e`
