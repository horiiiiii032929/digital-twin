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

Clean code revision: `eabfee109b9e88ba19999052e1a0b9b5baf1f3db`.

| Ranker | Recall@1 | Recall@5 | MRR | No-evidence accuracy | Mean latency | Peak memory |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Term overlap | 0.75 | 1.00 | 0.975 | 1.00 | 0.038 ms | 157,012 bytes |
| BM25 | 0.80 | 1.00 | 1.000 | 1.00 | 0.098 ms | 160,508 bytes |

Both rankers cleared every regression threshold and produced no source,
chunking, query, or ranking failure on the final run. BM25 improved Recall@1 by
0.05 and MRR by 0.025. It used about 3.5 KB more measured peak memory and was
about 2.6 times slower, but the absolute latency remained below 0.1 ms per query
on this corpus.

The first evaluation attempt incorrectly categorized nine cases as chunking
failures because gold phrases used spaces where PDF or Markdown text contained
line breaks. Normalizing whitespace in the judgment matcher resolved the
evaluation defect without changing query text, ranking, or gold wording.

## Decision

Keep BM25 as the Sprint 2 retrieval baseline and retain term overlap as the
control. The first-result gain is useful for supplying generation with the most
relevant evidence, while the added cost is negligible at this scale. Refine the
evaluation with a larger approved corpus before considering embeddings, hybrid
retrieval, stemming, or reranking. Do not generalize these results into a SOTA
claim.
