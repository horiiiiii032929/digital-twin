# Local retrieval deployability v1 plan

Date: 2026-07-31

Status: completed; both declared M3 candidates preserved quality but failed the
latency gate; the sealed held-out split remains unopened

Decision: mark the exact local M3 runtime deployment-ineligible on the
reference hardware, retain M3 in the research comparison, and carry M2 forward
as the operational candidate pending sealed evaluation. Results are registered
in `cross-course-retrieval-deployability-v1-results.md` and
`cross-course-retrieval-deployability-v1-depth20-results.md`.

## Decision question

Can the highest-quality local Qwen3 M3 configuration retain its development
retrieval quality while reducing warm-query latency and memory enough to remain
eligible for the final M0-M3 comparison and a bounded deployment?

This plan does not select a retrieval method. It qualifies an operational M3
configuration for the later one-time comparison. Quality leads selection, but
the selected method must clear a minimum deployment floor.

## Decision amendment

The hosted Jina pair from provider qualification v1 is retired before
execution. It is not required for the research question, would transmit
approved private course passages to an external provider, and would not resolve
the target deployment server's local resource constraint. Its adapters and
unfavourable/no-result history remain visible, but it is not a gate for the
final M0-M3 study.

Local Qwen3 remains the fixed semantic provider binding. BM25 remains the
simple rollback. The final method study still compares:

- M0: heading-aware BM25;
- M1: local Qwen3 dense retrieval;
- M2: BM25 plus dense reciprocal-rank fusion; and
- M3: M2 plus local Qwen3 reranking.

## Data and privacy boundary

- Use only the 40 sealed development cases and the approved 32-PDF corpus.
- Verify the seal and pristine held-out ledger without reading `heldout.json`.
- Make zero external provider calls and incur zero API cost.
- Keep private queries, passages, rankings, and raw timings in ignored run
  storage. Commit only sanitized aggregate evidence.

## Baseline and candidates

The control is the completed local run: M3 candidate depth 40, reranker maximum
length 2,048, reranker batch size 4, MPS float16.

Optimize one variable group at a time on development data:

1. increase reranking batch size while preserving depth 40 and length 2,048;
2. reduce maximum reranking length to 1,024 only if no gold-supporting passage
   is truncated past required evidence and aggregate quality is preserved; and
3. test candidate depth 20 only as a fallback if depth 40 cannot clear the
   latency floor.

Document embeddings are built during ingestion/index preparation and reused;
their construction time is reported separately from warm query latency. The
deployed request path still computes one query embedding and, for M3, reranks a
bounded candidate set.

## Primary quality metrics

- complete-evidence success@3;
- atomic evidence Recall@5;
- nDCG@10; and
- MRR.

The optimization may replace the M3 runtime control only if complete-evidence
success@3 is no worse than the control's 28/35 (80.0%) and the other three
quality metrics do not materially regress. Any changed ranking case receives
case-level review before freeze.

## Operational measures and gates

Record warm p50 and p95 latency per method, model load time, offline index build
time, peak resident memory, model-cache size, batch size, maximum length,
candidate depth, failures, and retries.

The deployment eligibility floor is:

- zero course-isolation violations;
- zero provider failures;
- zero held-out reads and zero external calls;
- complete output for all 40 development cases;
- M3 warm p95 retrieval latency no greater than 10 seconds on the declared
  reference hardware; and
- peak process memory no greater than 4 GiB.

The 10-second threshold is an eligibility ceiling, not a latency target. If no
M3 configuration clears it without quality loss, retain M3 in the research
comparison but mark it deployment-ineligible; M2 becomes the highest-quality
deployment candidate unless the final held-out evidence changes the ranking.

## Reproduction

Run the first quality-preserving candidate with:

```bash
npm run benchmark:retrieval-deployability-local
```

The command records independent embedding/reranking batch sizes, maximum
lengths, effective candidate depth, exact model revisions, code revision,
dirty state, and operational measurements under ignored experiment storage.
Register every named full development run, including failed or slower runs,
before freezing the one-time held-out configuration.

## Stop rules

- Do not inspect or run the 60 held-out cases during optimization.
- Do not select M3 from its descriptive 2.9-point development advantage over
  M2 alone.
- Do not lower the quality gate merely to meet latency.
- Do not introduce another hosted provider or model without a new prospective
  decision question.
- Stop optimization after one configuration clears both the quality and
  deployment gates, or after the declared candidates fail and M3 is marked
  deployment-ineligible.
