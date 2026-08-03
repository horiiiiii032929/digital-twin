# Cross-course retrieval v1 held-out plan

Run ID: `cross-course-retrieval-v1-heldout-001`

Date planned: 2026-08-02

## Decision question

Which frozen text-only course-scoped retrieval method, if any, should advance
from the development comparison into the smallest multi-course product slice?

## Prediction

M2 (BM25 plus Qwen3 dense retrieval with reciprocal-rank fusion) is expected to
retain the development quality advantage while remaining operationally eligible.
M0 BM25 remains the rollback. M3 is expected to provide a useful research
comparison but may fail the warm p95 latency ceiling.

## Frozen inputs

- Dataset: `cross-course-retrieval-v1`, `draft-6`, seal
  `cross-course-retrieval-v1-draft-6-seal`.
- Development split: 40 cases; held-out split: 60 cases. The held-out file is
  sealed and remains unread until the guarded command below is run.
- Corpus: `cross-course-portfolio-v2` from the local approved academic vault.
- Provider pair: `local-qwen3-0-6b`; no hosted calls and no paid provider.
- Runtime: MPS, float16, batch 8, embedding batch 16, reranking batch 8,
  embedding max length 2048, reranking max length 1024, rerank candidate limit
  20, result limit 10.
- Thresholds: copied from the declared depth-20 development run and not
  recalibrated on held-out cases.

## Metrics and gates

Primary quality metrics are complete evidence success at 3, evidence recall at
5, nDCG at 10, and MRR. Report seeded case-level bootstrap intervals and paired
comparisons against M0 and between M3 and M2.

The run must complete all 60 cases for all four methods with zero course
isolation violations, provider failures, retries, and external calls, and with
peak process memory at or below 4 GiB. A method is eligible only when its warm
p95 latency is at or below 10 seconds and every primary quality metric is at
least the M0 control value. Keep BM25 as rollback regardless of the result.

## Reproduction

This is a one-time held-out read. The runner requires an explicit confirmation,
marks the access ledger before opening the held-out file, writes a checkpoint
after each case, and prohibits reruns after any started attempt:

```text
npm run benchmark:retrieval-heldout
npm run analyze:retrieval-heldout
```

The raw case matrix remains under ignored `experiments/runs/`. The committed
outputs are the sanitized report, machine-readable record, CSV, and chart.

## Outcome

The run completed on 2026-08-02 with 60 held-out cases and all global hard
gates passed. M2 reached 85.0% complete evidence at 3, 86.96% evidence recall
at 5, 0.867 nDCG@10, 0.866 MRR, and 164 ms warm p95 latency. M0 reached 80.0%
complete evidence at 3 and remains the rollback. M1 regressed on the primary
quality floor and failed the latency ceiling. M3 reached 90.0% complete
evidence at 3 but failed the latency ceiling with 106,544 ms warm p95.

The result is registered as
`cross-course-retrieval-v1-heldout-001`; the durable summary and machine record
are in `research/05_evaluation/`.

## Follow-up rule

Add M2 to the experimental profile with BM25 rollback and build the smallest
complete professor/student journey. Do not reopen the held-out split. This
result does not make image-only or layout-dependent claims; the separate
multimodal V3 study is already dropped.
