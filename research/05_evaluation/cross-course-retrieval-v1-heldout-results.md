# Cross-course retrieval v1 held-out results

Result ID: cross-course-retrieval-v1-heldout-001

Status: completed one-time held-out comparison.

The frozen text benchmark contained 60 held-out cases: 40 answerable and 20 boundary cases. The 40-case development split, 20-case second-review quota, local Qwen3 binding, thresholds, and runtime configuration were fixed before this run. The held-out file was read once through the guarded runner and the ledger completed.

## Aggregate results

| Method | Complete evidence @3 | 95% bootstrap CI | Evidence recall @5 | nDCG@10 | MRR | No-evidence accuracy | Warm p95 | No regression | Deployment eligible |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| BM25 | 80.0% | 67.5%–92.5% | 87.0% | 0.795 | 0.754 | 90.0% | 75 ms | yes | yes |
| Qwen3 dense | 72.5% | 57.5%–85.0% | 82.6% | 0.783 | 0.765 | 85.0% | 11959 ms | no | no |
| BM25 + dense RRF | 85.0% | 72.5%–95.0% | 87.0% | 0.867 | 0.866 | 85.0% | 164 ms | yes | yes |
| Hybrid + Qwen3 reranker | 90.0% | 80.0%–97.5% | 93.5% | 0.864 | 0.841 | 60.0% | 106544 ms | yes | no |

## Decision

Keep — BM25 + dense RRF ranked highest among methods that passed the global gates, matched or exceeded BM25 on every primary quality metric, and passed the 10-second p95 deployment ceiling; retain BM25 as rollback.

BM25 remains the rollback. The selected method, if any, is a text-only retrieval selection and does not support image-dependent coverage claims.

## Paired comparisons

- M2_vs_M0: +5.0%; 95% paired bootstrap CI -7.5% to +17.5%; wins/losses/ties 4/2/34; sign-test p=0.688.
- M3_vs_M0: +10.0%; 95% paired bootstrap CI -2.5% to +25.0%; wins/losses/ties 6/2/32; sign-test p=0.289.
- M3_vs_M2: +5.0%; 95% paired bootstrap CI -5.0% to +15.0%; wins/losses/ties 3/1/36; sign-test p=0.625.

## Gates and limitations

- All 240 method-case rows completed with zero course-isolation violations, provider failures, retries, and external calls.
- Selection eligibility requires no regression against BM25 on any primary quality metric as well as passing the latency ceiling.
- Thresholds were frozen from the development run and were not recalibrated on held-out cases.
- Latency is single-process workstation evidence, not concurrent capacity evidence.
- The text benchmark excludes image-only claims; multimodal V3 was dropped separately.

Code revision: 04e484d38ebdebd0e2557f8783d37bd9f2c05945; git dirty: yes; implementation hash: 9e6156ad389e171bcb125fd51b34cea1a2bc487a4b192eaed2ddd62e2807c4ce.
