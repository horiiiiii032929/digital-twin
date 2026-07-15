# Retrieval v1 results

## Recorded run

- Date: 2026-07-15
- Code revision: `eabfee109b9e88ba19999052e1a0b9b5baf1f3db`
- Working tree: clean
- Dataset: `retrieval-v1`
- Corpus: `synthetic-browser-security-v1`
- Sources: 5 approved synthetic sources
- Chunks: 9
- Questions: 25
- Result limit: 5
- BM25 parameters: `k1 = 1.2`, `b = 0.75`
- Reproduction: `npm run verify:retrieval`

The full per-case JSON was generated locally at
`reports/generated/retrieval-v1-clean.json`. Generated run output remains
Git-ignored; the versioned questions and regression assertions are committed.

## Comparison

| Ranker | Recall@1 | Recall@5 | MRR | No-evidence accuracy | Mean latency | Peak memory |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Term overlap v1 | 0.75 | 1.00 | 0.975 | 1.00 | 0.038 ms | 157,012 bytes |
| BM25 v1 | 0.80 | 1.00 | 1.000 | 1.00 | 0.098 ms | 160,508 bytes |

No source, chunking, query, or ranking failures remained in either final run.
All five no-evidence questions returned no hit. Every returned result included
the chunk ID, document ID, source artifact and version, locator, and normalized
relevance score.

## Interpretation

BM25 improved the fraction of all gold judgments returned at rank one by five
percentage points and placed a relevant result first for every evidence-bearing
question. The unique-term overlap control already performed strongly, and both
rankers achieved complete Recall@5. BM25's approximately 2.6-times latency and
3.5 KB peak-memory increase are operationally negligible here because the
absolute measured cost stayed below 0.1 ms and 161 KB.

The corpus is too small for Recall@5 to be discriminating: five results cover
more than half of its nine chunks. Recall@1 and MRR provide the more meaningful
signal for this run. The result supports BM25 as the next baseline, not as a
final architecture or state-of-the-art claim.

## Failure analysis and limitations

The first run reported nine false chunking failures. Relevant phrases crossed
source line wraps, while the evaluator compared raw substrings. The matcher now
collapses whitespace before comparison, preserving words and source identity
while removing formatting sensitivity.

Remaining risks are lexical rather than operational:

- synonyms and conceptual paraphrases can miss all matching tokens;
- morphology such as `rotate` versus `rotated` is not normalized;
- query stop words can create weak matches because no stop-word filter exists;
- BM25 display scores are normalized within a query and are not probabilities;
- PDF figure pixels are not searched, only selectable text and captions;
- private IT5002 materials have not been evaluated because they still require
  an explicit professor permission record.

## Decision

Keep BM25 for issue #24's evidence supply, retain term overlap as a regression
control, and go deeper only after an approved larger corpus reveals lexical
failures that justify stemming, embeddings, hybrid retrieval, or reranking.
