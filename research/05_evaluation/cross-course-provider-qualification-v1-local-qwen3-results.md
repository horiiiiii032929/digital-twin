# Cross-course provider qualification v1: local Qwen3

Date: 2026-07-30

Result ID: `cross-course-provider-qualification-v1-local-qwen3`

Decision: **Refine; retain the local control and select no provider until the
frozen hosted comparison is complete**

Post-result amendment, 2026-07-31: the original decision above is preserved as
the decision made from this run. Before the hosted candidate executed, the
project retired Jina as a selection dependency and moved to a local quality-
first deployability study. See
[`cross-course-retrieval-deployability-v1-results.md`](cross-course-retrieval-deployability-v1-results.md).

## Scope and validity

This is the completed local-control half of the prospective provider
qualification. It evaluated 40 development cases from sealed
`cross-course-retrieval-v1` draft 6: 35 answerable ranking cases and five
boundary cases. The corpus was the 32 approved PDFs in
`cross-course-portfolio-v2`.

The runner did not open or score the 60-case held-out file. Its ledger remains
`unopened` with zero attempts. The run made no external calls and committed no
private query, passage, or per-case ranking.

The ignored source result is retained at
`experiments/runs/cross_course_provider_qualification_v1/local-qwen3-0-6b/development_result.json`,
SHA-256
`8389b1d294f22c2f731aa327e0987a00af306b5f985ade8ec1e416b61fc96480`.
It used Git revision `6fd2181c8fdc50e6770b051d7e6d9af139935cbf` and
implementation-tree SHA-256
`2637ad8abafe554143ce6c4e336dc00fc146b64b1f12c6fecfe4c93a6b714fca`.
The working tree was dirty only because of pre-existing user-owned report and
plot-script changes outside the measured implementation hash.

Reproduce the measurement and sanitized analysis with:

```bash
npm run qualify:retrieval-provider-local
npm run analyze:retrieval-provider-local
```

The second command validates the complete case-method matrix and hard gates,
then emits ignored JSON, CSV, PNG, and SVG artifacts under
`reports/generated/`.

## Exact configuration

Every method searched only the authorized course index:

- M0: BM25 with `k1=1.2` and `b=0.75`;
- M1: `Qwen/Qwen3-Embedding-0.6B`, revision
  `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`;
- M2: BM25 plus dense reciprocal-rank fusion, `k=60`, candidate depth 20; and
- M3: M2 candidate depth 40 reranked with
  `Qwen/Qwen3-Reranker-0.6B`, revision
  `e61197ed45024b0ed8a2d74b80b4d909f1255473`.

Both models ran locally with Apple MPS, float16, batch size 8 for embedding,
batch size 4 for reranking, and a 2,048-token maximum.

## Development quality

Ranking metrics use the 35 answerable cases. Complete-evidence uncertainty uses
20,000 seeded case-level bootstrap resamples.

| Method | All evidence @3 | 95% bootstrap CI | Evidence Recall @5 | nDCG @10 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0 BM25 | 65.7% | 48.6–80.0% | 84.6% | 0.756 | 0.711 |
| M1 Qwen3 dense | 74.3% | 60.0–88.6% | 89.7% | 0.812 | 0.771 |
| M2 BM25 + dense RRF | 77.1% | 62.9–91.4% | 89.7% | 0.829 | 0.779 |
| M3 hybrid + Qwen3 reranker | 80.0% | 65.7–91.4% | 92.3% | 0.860 | 0.843 |

All-evidence @3 is the proportion of questions for which every required
passage appears in the first three results. Evidence Recall @5 is pooled over
the atomic required evidence units found in the first five results.

All methods achieved 3/3 complete-evidence success on the
cross-course-confusion slice. On the other 32 answerable cases, M0 achieved
20/32 and M3 achieved 25/32 complete-evidence success.

## Paired comparisons

| Comparison | Difference | 95% paired bootstrap CI | Wins / losses / ties | Sign-test p |
| --- | ---: | ---: | ---: | ---: |
| M2 versus M0 | +11.4 pp | +2.9 to +22.9 pp | 4 / 0 / 31 | 0.125 |
| M3 versus M0 | +14.3 pp | 0.0 to +28.6 pp | 6 / 1 / 28 | 0.125 |
| M3 versus M2 | +2.9 pp | -5.7 to +11.4 pp | 2 / 1 / 32 | 1.000 |

The descriptive ranking favors M3, but the paired evidence does not establish
a reliable M3 advantage over M2 on 35 development cases. These results qualify
the local provider pair as the control; they do not select the retrieval method
or provider.

## Hard gates and operations

| Gate | Result |
| --- | --- |
| Complete 40-case run and 160 method rows | Pass |
| Held-out file reads | Pass: 0 |
| Course-isolation violations | Pass: 0 |
| Provider failures and retries | Pass: 0 and 0 |
| External cost | Pass: USD 0 |

The run recorded 687 local model calls over an estimated 586,692 input tokens,
approximately 2.11 GB peak resident memory, a 2.41 GB local model cache, and
302.7 seconds to build the dense indexes. Local median query times ranged from
10 ms for BM25 to 41.2 seconds for M3.

These timings describe this workstation and fixed execution order. Shared
execution warms later methods, so they are not clean cross-method latency
estimates and do not decide retrieval quality. They do show that this exact
local M3 configuration needs operational refinement before interactive use.

## Failures and limitations

- M3 missed complete top-three evidence on seven cases: five from CS5421 and
  two from IT5100B. These remain ranking failures for later case-level review.
- The five boundary thresholds were calibrated and measured on the development
  cases; their perfect diagnostic accuracy is not a generalization result.
- The hosted Jina candidate has not run, so no provider comparison or freeze is
  valid yet.
- The held-out split remains unopened, so no final performance claim exists.
- Development wording and evidence labels may still favor a semantic method;
  the sealed review history limits but does not eliminate that risk.

## Decision

**Refine.** Retain local Qwen3 as the qualified control and BM25 as the simple
rollback. Do not select a provider, retrieval method, or production profile
from this one-sided development result. Run the prospectively frozen Jina
embedding-plus-reranking candidate on the same 40 development cases, then
compare quality, isolation, reliability, cost, and deployment burden before
freezing a provider binding.
