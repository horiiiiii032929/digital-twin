# Cross-course retrieval deployability v1 depth-20 results

Date: 2026-07-31

Result ID: `cross-course-retrieval-deployability-v1-depth20`

Decision: **Refine; mark local M3 deployment-ineligible on the reference
hardware and retain M2 as the operational candidate**

## Scope and validity

This was the final prospectively declared local M3 optimization. It evaluated
all 40 sealed development cases with candidate depth reduced from 40 to 20,
while retaining the batch-8, 1,024-token reranker configuration. The reranker
also used a token-equivalent manual left-padding path verified against the
previous tokenizer output before the run.

The 60-case held-out file was not read. Its ledger remains `unopened` with zero
attempts. The ignored raw result is retained at
`experiments/runs/cross_course_retrieval_deployability_v1_depth20/local-qwen3-0-6b/development_result.json`,
SHA-256
`c74bc0bfb069874b50392ad73dea5f8e55debf884a89bff304360010a53a958c`.

The run used Git revision `7722544490c02252825249c5c09a313cdbd6aeb2`,
implementation-tree SHA-256
`52452bba0934bad056b416b9cbbcdfe31822ed0d65c40c2de16ed9da294454aa`,
and a dirty tree containing the prospective implementation plus pre-existing
user-owned report and plot changes.

## Configuration

- Local Qwen3 embedding and reranking 0.6B models at the previously pinned
  revisions;
- Apple MPS, float16;
- embedding batch 16 and maximum length 2,048;
- reranking batch 8 and maximum length 1,024;
- M3 candidate depth 20 and result depth 10; and
- zero external calls and USD 0 API cost.

## Quality

| Method | Complete evidence @3 | Evidence Recall @5 | nDCG @10 | MRR |
| --- | ---: | ---: | ---: | ---: |
| M0 BM25 | 65.7% | 84.6% | 0.756 | 0.711 |
| M1 Qwen3 dense | 74.3% | 89.7% | 0.812 | 0.771 |
| M2 hybrid RRF | 77.1% | 89.7% | 0.829 | 0.779 |
| M3 depth 20 | **80.0%** | **92.3%** | **0.865** | **0.843** |

Depth 20 preserved the 28/35 complete-evidence result and every other primary
quality metric. nDCG increased from 0.860 to 0.865. Case-level comparison found
36 changed top-ten orderings, but only `ccr1-it5100b-04` changed a recorded
ranking metric, improving nDCG without changing evidence completeness, Recall,
or MRR. No case changed its complete-evidence outcome.

## Operations

| Measure | Depth 40 | Depth 20 | Gate |
| --- | ---: | ---: | ---: |
| M3 p50 latency | 31.43 s | **14.63 s** | Descriptive |
| M3 p95 latency | 61.92 s | **28.13 s** | **Fail: at most 10 s** |
| M2 p50 / p95 | — | 74 / 139 ms | Pass |
| M1 p50 / p95 | — | 1.00 / 3.97 s | Pass in this run |
| Peak resident memory | 2.08 GiB | 1.97 GiB | Pass: at most 4 GiB |
| Offline index build | 208.69 s | 299.13 s | Report separately |
| Failures / retries | 0 / 0 | 0 / 0 | Pass |
| Isolation violations | 0 | 0 | Pass |

Depth 20 reduced M3 median latency by 53% and p95 by 55% relative to the prior
depth-40 candidate while preserving quality. It nevertheless remained 2.8
times over the deployment ceiling at p95. The offline index-build variation
does not affect student request latency and was not used for selection.

## Decision

**Refine and stop local M3 optimization for this freeze.** The two declared
quality-preserving candidates both failed the latency gate. Mark the exact
local M3 configuration deployment-ineligible on the reference hardware. Keep
M3 in the final one-time research comparison because it remains the development
quality leader. Retain M2 hybrid RRF as the highest-quality operational
candidate and BM25 as the simple rollback; do not update the active profile
until the sealed M0-M3 comparison makes the final method decision.

This decision does not claim that Qwen3 reranking is generally undeployable.
It applies to the pinned 0.6B local model, this corpus, this MPS workstation,
and the tested configurations.

## Gates and failures

- Pass: complete 40-case run and method matrix.
- Pass: quality preserved at 28/35.
- Pass: zero held-out reads, external calls, isolation violations, failures,
  and retries.
- Pass: peak memory below 4 GiB.
- **Fail: 28.13-second M3 p95 versus the 10-second ceiling.**

The failure is operational/runtime. It is not a ranking, data, provider,
privacy, or isolation failure.

## Limitations

- These are development metrics, not held-out generalization evidence.
- The five boundary cases remain calibration diagnostics.
- Timings are single-process workstation evidence, not concurrent capacity
  evidence.
- The final deployed retrieval profile remains pending the one-time sealed
  M0-M3 study.
