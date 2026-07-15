# Retrieval and source-evidence learning log

## Component

Deterministic term-overlap and Okapi BM25 retrieval over approved, versioned
document chunks, plus a reproducible 25-question evaluation and failure
analysis.

## Prediction

I expected BM25 to improve the first relevant result because it gives rare
terms more value and corrects for repeated terms and chunk length. I expected
the main failure to be lexical mismatch rather than latency or memory. I also
expected ambiguous queries to be harder than direct factual questions.

## How it works

The retriever receives chunks produced by the existing parser and chunker. It
first removes every chunk without tutoring permission. It then keeps only the
active source version, either from an explicit caller-provided map or from the
highest approved version present.

Both algorithms tokenize the query and chunks with the same lowercase
alphanumeric rule. The control counts the unique query terms found in a chunk
and divides by the number of unique query terms. This is easy to inspect but
treats frequent and rare words equally.

BM25 counts term frequency in each chunk and document frequency across the
eligible chunk collection. Its inverse-document-frequency term rewards words
that occur in fewer chunks. `k1` causes repeated occurrences to saturate rather
than grow without limit. `b` compares each chunk length with the average length
so a long chunk does not win merely because it contains more words. We used
`k1 = 1.2` and `b = 0.75`, ranked by the raw BM25 score, and normalized the
displayed score against the best result for the current query.

Equal scores are resolved by source artifact ID, document ID, chunk ordinal,
and chunk ID. Empty lexical queries and invalid limits raise explicit errors. A
valid query with no matching approved evidence returns an empty list.

The evaluation resolves each gold judgment to an approved source artifact and
a stable phrase inside a chunk. It measures Recall@1, Recall@5, Mean Reciprocal
Rank, no-evidence accuracy, mean latency, and peak memory. Failed cases are
classified as source, chunking, query, or ranking failures.

## Evidence

- Tests: 68 Python tests and 15 frontend tests passed in `npm run check`.
- Focused verification: ingestion and retrieval commands passed.
- Dataset: 25 synthetic questions, five per required category.
- Clean evaluation revision:
  `eabfee109b9e88ba19999052e1a0b9b5baf1f3db`.
- Term overlap: Recall@1 0.75, Recall@5 1.00, MRR 0.975,
  no-evidence accuracy 1.00, mean latency 0.038 ms, peak memory 157,012 bytes.
- BM25: Recall@1 0.80, Recall@5 1.00, MRR 1.00,
  no-evidence accuracy 1.00, mean latency 0.098 ms, peak memory 160,508 bytes.
- Sensitive-data check: the selected IT5002 PDFs 5-9 and notes are present only
  under Git-ignored `data/raw/course_materials/it5002_selected/` and were not
  used in the synthetic run.

## What failed or surprised me

The first apparent failure came from the evaluation harness. Nine correct gold
passages were marked as unresolved because line wrapping inserted newlines
inside phrases. Collapsing whitespace during gold resolution fixed the problem.
This demonstrated that evaluation code can create misleading algorithm claims
and needs its own regression tests.

BM25 improved ranking, but the control was already strong. Complete Recall@5
looks impressive until considering that five hits cover more than half of a
nine-chunk corpus. Recall@1 and MRR were more informative. BM25 was about 2.6
times slower, but the absolute difference was around 0.06 ms per query.

## What I learned

I can explain BM25 as three interacting ideas rather than as a black box:
rare-term weighting, term-frequency saturation, and length normalization. I can
also explain why deterministic tie-breaking, permission filtering, source
version filtering, and no-evidence behavior are part of retrieval correctness,
not optional implementation details.

I also learned that a metric must be interpreted relative to corpus size and
that evaluation judgments need stable semantic identity without depending on
incidental PDF or Markdown whitespace.

## Next decision

Keep BM25 as the evidence ranker for live grounded generation in issue #24 and
keep term overlap as a control. Do not add embeddings yet. First run the same
evaluation shape on a larger explicitly approved corpus; add stemming, hybrid
retrieval, or reranking only in response to recorded lexical failures.
