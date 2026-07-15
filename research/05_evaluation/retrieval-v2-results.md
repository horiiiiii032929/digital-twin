# Retrieval v2 results

## Recorded run

- Date: 2026-07-15
- Clean code revision: `444fcbade92e9f18db21da5975e64921b00c7df4`
- Corpus: `synthetic-web-security-v2`
- Corpus size: 40 chunks, 16 sources, 38 active eligible chunks
- Calibration: 20 queries
- Held-out test: 40 queries, including 6 no-evidence cases
- BM25 cutoff selected on calibration: raw score `0.0`
- Dense cutoff selected on calibration: normalized score `0.775`, equivalent
  to cosine similarity `0.55`
- Reproduction: `npm run benchmark:retrieval`
- Paid API calls: zero

The full per-case artifact is generated locally at
`reports/generated/retrieval-v2.json` and remains ignored. The corpus,
calibration queries, held-out queries, aggregate evidence, and decision record
are committed.

## Held-out comparison

| Candidate | Recall@1 | Recall@3 | Recall@5 | Precision@3 | nDCG@3 | MRR | No-evidence | Mean latency | p95 latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0.569 | 0.711 | 0.799 | 0.294 | 0.682 | 0.737 | 0.833 | 0.27 ms | 0.47 ms |
| BGE-small dense | 0.485 | 0.676 | 0.828 | 0.284 | 0.633 | 0.697 | 1.000 | 7.24 ms | 9.22 ms |
| BM25+dense RRF | 0.485 | 0.755 | 0.902 | 0.324 | 0.680 | 0.712 | 0.833 | 10.90 ms | 21.93 ms |

All candidates returned zero prohibited or superseded chunks. RRF produced the
best coverage, but its nDCG@3 fell slightly below the measured BM25 control,
which is the replacement non-regression threshold. Dense retrieval alone
passed the no-evidence hard gate; BM25 and RRF each returned weak course-policy
hits for one of six no-evidence questions and were disqualified.

## Slice evidence

| Slice | BM25 Recall@3 | Dense Recall@3 | RRF Recall@3 | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Exact | 1.000 | 1.000 | 1.000 | All candidates handle exact terminology. |
| Distractor | 1.000 | 1.000 | 1.000 | Topical distractors did not separate candidates at k=3. |
| Paraphrase | 0.625 | 0.375 | 0.625 | The expected dense advantage did not appear. |
| Multi-evidence | 0.583 | 0.833 | 0.833 | Dense and hybrid improve evidence completeness. |
| Ambiguous | 0.417 | 0.125 | 0.292 | All candidates need refinement, especially dense. |
| Permission/version | 0.500 | 0.625 | 0.625 | Filtering is safe, but ranking remains incomplete. |

The failure slices are more useful than the aggregate alone. Dense retrieval
adds value for multi-evidence questions but loses substantially on paraphrases
and ambiguity in this small domain. RRF recovers BM25's paraphrase score and
most dense multi-evidence gains, yet inherits BM25's false evidence.

## Operational evidence

BM25 index construction took about 0.80 ms. The local ONNX model loaded in
about 1.92 seconds, dense indexing took about 273 ms, and the cache occupied
134,359,280 bytes. Per-query dense and hybrid latency remained below the
recorded experimental budgets of 15 ms mean and 25 ms p95. Python peak
allocations during evaluation were below 0.30 MB, but `tracemalloc` does not
measure ONNX native resident memory; this is a known instrumentation gap.

## Failure analysis

Calibration contained no-evidence queries with no corpus vocabulary. It chose
the unthresholded BM25 control because all five returned no hits. The unseen
economics query `monetary policy inflation central bank interest rate` shared
the generic term `policy` with course policy and CSP chunks. BM25 therefore
returned weak matches, and RRF inherited them. This is calibration-distribution
failure, not a source-permission failure.

No cutoff was adjusted after inspecting the held-out result. Doing so would
turn the test set into training data and overstate confidence.

## Decision

**Refine; select no replacement.** Keep the existing BM25 v1 profile entry as
a provisional rollback baseline from the earlier v1 experiment, but do not
treat it as ready for live generation on the harder benchmark. Dense retrieval
is the only gate-eligible v2 candidate, yet it regresses against BM25 on
Recall@3 and nDCG@3. RRF improves coverage but fails no-evidence behavior and
slightly regresses nDCG@3 against the control.

Next, define evidence sufficiency as a separate testable boundary, expand
calibration negatives with vocabulary-sharing out-of-domain queries, and run a
new frozen held-out set. Reranking is deferred: current evidence says
abstention and ambiguous-query coverage are more urgent than adding another
ranking stage.

## Limitations

- All content and judgments are synthetic and were written by one evaluator.
- Forty chunks are materially better than nine but still much smaller than an
  approved course collection.
- Only one English dense model and one fusion configuration were tested.
- The model cache was warm for the recorded per-query run.
- Latency is a single-machine measurement, not a production service SLO.
- No tables, image pixels, multilingual queries, or real professor-approved
  material were evaluated.
