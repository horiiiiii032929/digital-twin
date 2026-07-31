# Cross-course retrieval deployability v1 results

Date: 2026-07-31

Result ID: `cross-course-retrieval-deployability-v1-batch8-context1024`

Decision: **Refine; preserve the quality result but do not freeze this M3
configuration for deployment**

## Scope and validity

This development-only run tested whether a larger reranking batch and shorter
reranker context could preserve the highest observed local M3 quality while
improving latency. It used all 40 sealed development cases: 35 positive ranking
cases and five boundary calibration cases. The 60-case held-out file was not
read; its ledger remains `unopened` with zero attempts.

The ignored source result is retained at
`experiments/runs/cross_course_retrieval_deployability_v1/local-qwen3-0-6b/development_result.json`,
SHA-256
`c3401d33ea7f2bf84bc9ad663ff2f61a9838706ac7fd192045cfbe95b46c2c78`.
It used Git revision `7722544490c02252825249c5c09a313cdbd6aeb2` and
implementation-tree SHA-256
`c2a7f0cd3938e0599ae9dd9dbb985818949668fa51253d95cd57a2f4fcdc2233`.
The working tree was dirty with this prospective implementation and
pre-existing user-owned report/plot changes.

## Configuration

- Embedding: `Qwen/Qwen3-Embedding-0.6B`, pinned revision
  `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`;
- reranking: `Qwen/Qwen3-Reranker-0.6B`, pinned revision
  `e61197ed45024b0ed8a2d74b80b4d909f1255473`;
- Apple MPS, float16;
- embedding batch 16, maximum length 2,048;
- reranking batch 8, maximum length 1,024;
- M3 candidate depth 40 and output depth 10; and
- zero external calls and USD 0 API cost.

## Quality

The optimized runtime reproduced the previous rankings exactly at aggregate
level.

| Method | Complete evidence @3 | Evidence Recall @5 | nDCG @10 | MRR |
| --- | ---: | ---: | ---: | ---: |
| M0 BM25 | 65.7% | 84.6% | 0.756 | 0.711 |
| M1 Qwen3 dense | 74.3% | 89.7% | 0.812 | 0.771 |
| M2 hybrid RRF | 77.1% | 89.7% | 0.829 | 0.779 |
| M3 local reranker | **80.0%** | **92.3%** | **0.860** | **0.843** |

M3 therefore passed the prospective quality-preservation gate: 28/35 positive
cases retained complete evidence in the first three results, with no aggregate
regression in the secondary ranking metrics.

Case-level comparison found changed non-gold ordering in three IT5002 cases.
Their gold ranks and every recorded per-case ranking metric were unchanged, so
the shorter context introduced no measured quality change in those cases.

## Operations

| Measure | Result | Gate |
| --- | ---: | ---: |
| M3 warm p50 latency | 31.43 seconds | Descriptive |
| M3 warm p95 latency | 61.92 seconds | **Fail: must be at most 10 seconds** |
| M2 warm p50 / p95 | 96 / 129 ms | Pass |
| M1 warm p50 / p95 | 3.63 / 10.43 seconds | p95 slightly above deployment ceiling |
| Offline embedding-index build | 208.69 seconds | Report separately |
| Peak resident memory | 2.08 GiB | Pass: at most 4 GiB |
| Local model cache | 2.25 GiB | Descriptive |
| Provider failures / retries | 0 / 0 | Pass |
| Course-isolation violations | 0 | Pass |
| External calls / API cost | 0 / USD 0 | Pass |

Compared with the earlier development run's approximately 41.2-second M3
median, this candidate reduced median latency by about 24% while preserving
quality. It remains far outside the interactive deployment ceiling, and its
long tail worsens the student-facing risk.

The fixed M0-M3 execution order and shared model process make these timings
workstation development evidence, not a capacity result. They are sufficient
to reject this exact runtime as deployment-ready, not to claim a general Qwen3
service limit.

## Gates and failures

- Pass: complete 40-case run and complete method matrix.
- Pass: zero held-out reads; pristine unopened ledger.
- Pass: zero course-isolation violations.
- Pass: zero model failures and retries.
- Pass: peak memory below 4 GiB.
- Pass: M3 quality preserved at 28/35.
- **Fail: M3 warm p95 latency was 61.92 seconds, over six times the ceiling.**

The failed gate is classified as an operational/runtime failure, not a ranking,
provider, data, or privacy failure.

## Decision

**Refine.** Keep M3 in the final research comparison because it remains the
development quality leader. Do not freeze this batch-8/context-1,024 runtime as
the deployable configuration. Next, test the prospectively declared bounded
candidate depth and tokenizer-path optimization on development data. If M3
cannot meet the ceiling without falling below 28/35, mark it deployment-
ineligible and retain M2 as the highest-quality operational candidate.

Follow-up: the depth-20 candidate completed and preserved 28/35, but its
28.13-second p95 still failed the deployment gate. The stop rule was applied;
see
[`cross-course-retrieval-deployability-v1-depth20-results.md`](cross-course-retrieval-deployability-v1-depth20-results.md).

## Limitations

- Development quality does not establish held-out generalization.
- Five boundary cases are calibration diagnostics, not independent open-set
  evidence.
- The latency run is single-process workstation evidence, not concurrent load
  testing.
- No generator latency is included.
- Shorter context changed non-gold ordering in three cases while preserving
  their gold ranks and metrics; a future configuration change requires the same
  case-level comparison before freeze.
