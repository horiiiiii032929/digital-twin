# RAG retrieval v2 experiment

## Decision question

Does a small local dense retriever or BM25+dense reciprocal-rank fusion improve
evidence retrieval enough to replace the selected BM25 baseline on a harder
synthetic course benchmark?

## Prediction

- BM25 should lead on exact terminology and identifiers.
- Dense retrieval should lead on conceptual paraphrases.
- RRF should produce the best Recall@3 and Recall@5 by combining both signals.
- Dense and hybrid retrieval will add model load, index build, and per-query
  latency, but should remain practical for a local prototype.
- The most likely hard-gate failure is false evidence on absent-answer queries;
  the most likely quality failure is incomplete multi-evidence retrieval.

## Conditions

- Corpus: `synthetic-web-security-v2`, 40 chunks from 16 synthetic sources.
- Ineligible evidence: one prohibited chunk and one superseded source version.
- Calibration set: 20 queries used only to select BM25 and dense cutoffs.
- Held-out set: 40 queries across exact, paraphrase, multi-evidence,
  distractor, ambiguous, permission/version, and no-evidence slices.
- Control: Okapi BM25, `k1 = 1.2`, `b = 0.75`.
- Dense candidate: `BAAI/bge-small-en-v1.5` through FastEmbed 0.8.0.
- Hybrid candidate: BM25+dense reciprocal-rank fusion with `k = 60`.
- No paid calls or private course material.

## Metrics and gates

Primary quality metrics are Recall@3, Recall@5, and nDCG@3. A replacement must
at least match the measured BM25 control on each; this defines a relative
non-regression threshold without inventing an absolute universal score.
Recall@1, Precision@1/3/5, MRR, category slices, failures, mean/p95 latency,
Python allocation peaks, model load, index build, and cache size are diagnostic
or operational measures.

Hard gates require zero prohibited or superseded hits, no-evidence accuracy of
1.00, resolvable source judgments, and synthetic-only committed data. A failed
gate disqualifies the candidate regardless of aggregate retrieval quality.

## Calibration rule

For each candidate cutoff, require the source/version and no-evidence gates,
then maximize Recall@3, nDCG@3, and MRR in that order. Prefer the lower cutoff
on an exact tie. The held-out set is not used for threshold adjustment.

## Reproduction

```bash
npm run benchmark:retrieval
```

The full generated artifact is written to
`reports/generated/retrieval-v2.json` and remains Git-ignored.

## Result and prediction check

RRF did produce the best Recall@3 and Recall@5. BM25 led dense retrieval on
exact queries, as predicted, but dense did not lead the paraphrase slice. More
importantly, BM25 and RRF failed the held-out no-evidence gate on a query that
shared the generic word `policy` with the corpus. Dense passed that gate but
regressed against BM25 on Recall@3 and nDCG@3. No candidate was selected; the
decision is Refine.

The held-out failure was not used to retune the calibration thresholds. The
next experiment must add a new calibration set with topically absent queries
that share generic corpus vocabulary, introduce an explicit evidence-
sufficiency boundary, and evaluate it on a newly frozen held-out set.
