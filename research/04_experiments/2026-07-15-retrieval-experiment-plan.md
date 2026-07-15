# Retrieval baseline experiment plan

## Question

Does Okapi BM25 improve the ranking of approved course chunks enough to replace
a unique-term overlap control for Sprint 2, without weakening no-evidence
behavior or adding material operational cost?

## Hypothesis

BM25 will improve Recall@1 or Mean Reciprocal Rank because rare terms and chunk
length affect relevance in ways the overlap fraction ignores. Both rankers
should retain every gold judgment within five hits and return no hit for all
no-evidence cases. On the nine-chunk synthetic corpus, mean retrieval latency
should remain below 5 ms and peak per-ranker evaluation memory below 5 MB.

The most likely failure is not computational cost but lexical mismatch: a
relevant chunk may use a synonym or morphological variant absent from the
query. A second risk is an invalid gold judgment caused by source or chunking
changes.

## Method

- Dataset: `retrieval-v1`, 25 versioned questions with five cases in each of
  direct, misconception, integrity-boundary, ambiguous, and no-evidence groups.
- Corpus: `synthetic-browser-security-v1`, five approved synthetic sources and
  nine chunks; real IT5002 materials remain local-only and unused.
- Baseline: unique query-term overlap fraction.
- Variant: Okapi BM25 with `k1 = 1.2` and `b = 0.75`.
- Shared tokenizer: lowercase ASCII alphanumeric lexical tokens.
- Shared limit: five hits with deterministic source/document/ordinal tie-breaks.
- Quality metrics selected before the run: Recall@1, Recall@5, Mean Reciprocal
  Rank, and no-evidence accuracy.
- Operational metrics selected before the run: mean per-query latency and peak
  per-ranker index/evaluation memory.
- Regression thresholds: Recall@5 at least 0.80, MRR at least 0.60,
  no-evidence accuracy 1.00, and no unresolved source or chunk judgments.
- Failure taxonomy: source, chunking, query, or ranking.
- Reproduction: `npm run verify:retrieval`.

## Results

To be recorded from a clean implementation revision.

## Decision

Pending clean-revision evaluation.
