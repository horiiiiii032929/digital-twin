# Local retrieval and source evidence

## Decision

Sprint 2 established the inspectable term-overlap and Okapi BM25 rankers over
the same approved chunks. BM25 remains the explicit rollback baseline.

The frozen cross-course comparison then selected M2, course-scoped BM25 plus
local Qwen3 dense retrieval fused with reciprocal rank fusion. On the one-time
60-case held-out split, M2 reached 85.0% complete evidence at 3, 87.0% evidence
recall at 5, 0.867 nDCG@10, and 164 ms warm p95 latency. M1 regressed on quality
and latency. M3 reached higher quality but failed the 10-second p95 gate. See
[`cross-course-retrieval-v1-heldout-results.md`](../research/05_evaluation/cross-course-retrieval-v1-heldout-results.md)
and its [machine record](../research/05_evaluation/records/cross-course-retrieval-v1-heldout.json).

The selected profile uses a local, revision-pinned Qwen3 embedding binding
behind a provider-neutral runtime boundary; no hosted search service, live web
source, or LMS connector is part of this decision. BM25 is the explicit
provider-failure and unconfigured-runtime rollback. Product activation and
end-to-end tutoring evidence remain F3 work.

### Frozen M2 binding

The experimental profile freezes M2 as heading-aware BM25 (`k1=1.2`,
`b=0.75`) plus `Qwen/Qwen3-Embedding-0.6B` at revision
`97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`. The local embedder runs with the
frozen course-retrieval query instruction, 2,048-token maximum input, MPS
float16 execution, and reciprocal-rank fusion with rank constant 60 and 20
candidates. The returned limit is 10 and no reranker is part of M2. The full
machine-readable binding is in
[`student-tutor-v1.json`](../research/05_evaluation/profiles/student-tutor-v1.json);
the original provider-pair freeze remains in
[`cross_course_provider_qualification_v1.json`](../research/05_evaluation/instruments/cross_course_provider_qualification_v1.json).

Evidence-sufficiency v1 made the next boundary explicit and compared the
current any-hit behavior with calibrated BM25 raw score, lexical coverage, and
BGE-small semantic agreement. No candidate passed calibration or held-out hard
gates. Semantic agreement was best, but still accepted 5/18 unrelated questions
and rejected 8/32 answerable ones. The decision remains **Refine, no
selection**; see
[`evidence-sufficiency-v1-results.md`](../research/05_evaluation/evidence-sufficiency-v1-results.md).

## Source boundary

The reproducible evaluation uses five approved synthetic sources: four
committed TXT or Markdown files and one generated selectable-text PDF with an
embedded figure. Parsing and chunking produce nine chunks with stable source
identity, version, locator, and permission state.

All 13 official IT5002 lecture PDFs are copied under the Git-ignored
`data/raw/course_materials/it5002_full/lecture/` directory. Their sanitized
inventory is committed in
[`it5002_lectures_v1.manifest.json`](../research/05_evaluation/it5002_lectures_v1.manifest.json).
The earlier lectures 5-9 subset remains historical local preparation evidence.
The full snapshot must not enter tutor retrieval until an explicit professor
approval record grants tutoring permission. Personal notes are non-
authoritative question-design material only. Tutorials, assignments, exams,
quizzes, solutions, answer files, secrets, and student records remain excluded.

## Retrieval flow

```text
DocumentChunk[]
  -> keep retrieval_allowed chunks
  -> keep only the active source version
  -> deterministic lexical tokenization
  -> rank with selected M2 hybrid or BM25 rollback
  -> deterministic source/document/ordinal tie-break
  -> RetrievalHit(chunk + normalized and raw ranker score)
  -> provider/runtime fallback telemetry without query or content logging
  -> swappable evidence-sufficiency gate
       |- insufficient: return no evidence for generation
       `- sufficient: retain ranked approved hits
```

An explicit active-version map can be supplied by the caller. Without one, the
retriever keeps the highest approved chunk version for each source artifact.
Chunks without tutoring permission are always excluded.

Queries containing no lexical token raise `EmptyQueryError`; limits below one
raise `InvalidRetrievalLimitError`; a valid query with no matching approved
evidence returns an empty list. Every hit exposes the source artifact, document
identity, source version, human-readable locator, chunk text, and score.

## Algorithms

Both rankers lowercase text and extract ASCII alphanumeric tokens. The baseline
uses unique tokens and scores a chunk as:

```text
matched unique query terms / all unique query terms
```

BM25 uses `k1 = 1.2` and `b = 0.75`. For a query term `t` and chunk `d`:

```text
IDF(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))

score(t, d) = IDF(t) *
              tf(t, d) * (k1 + 1)
              -----------------------------------------------
              tf(t, d) + k1 * (1 - b + b * |d| / average_dl)
```

The query score is the sum over its unique terms. `IDF` gives rare terms more
weight, `k1` makes repeated term occurrences saturate, and `b` corrects for
chunk length. Ranking uses the raw score. Displayed relevance is divided by the
best raw score for that query so it stays between zero and one; it is meaningful
only within the same query.

## Evaluation

The versioned set at
[`retrieval_v1.json`](../research/05_evaluation/retrieval_v1.json) contains 25
questions: five each for direct grounding, misconceptions, integrity
boundaries, ambiguous queries, and no-evidence behavior. Gold judgments identify
the source artifact and a stable passage phrase. Whitespace is normalized when
resolving that phrase so PDF or Markdown line wrapping does not change the
judgment.

The evaluator records per-case hits and classifies failures as source,
chunking, query, or ranking problems. Aggregate metrics are:

- Recall@1 and Recall@5: the mean fraction of gold judgments retrieved within
  the first one or five hits.
- Mean Reciprocal Rank: the mean inverse rank of the first relevant hit.
- No-evidence accuracy: the fraction of no-evidence questions returning no hit.
- Mean retrieval latency and per-ranker peak index/evaluation memory.

The clean-revision measurements, interpretation, and decision are recorded in
[`retrieval-v1-results.md`](../research/05_evaluation/retrieval-v1-results.md).

Run the reproducible comparison with:

```bash
npm run verify:retrieval
```

To retain the full local JSON artifact, run:

```bash
uv run python -m scripts.evaluate_retrieval \
  --output reports/generated/retrieval-v1.json
```

Generated run files remain ignored; the durable result and decision summary is
stored alongside the evaluation set.

The v2 benchmark adds a 40-chunk synthetic corpus, separate 20-query
calibration and 40-query held-out sets, Recall/Precision at k=1/3/5, nDCG@3,
category slices, safety violations, p95 latency, a local dense adapter, and RRF.
Run it with:

```bash
npm run benchmark:retrieval
```

The optional benchmark dependency and approximately 134 MB model cache are not
required by the normal test suite. The model cache is stored under ignored
`data/external/`; no paid provider is called.

The evidence-sufficiency comparison uses a separate 30-case calibration set and
50-case held-out set. Run calibration without touching held-out results, then
the frozen benchmark, with:

```bash
npm run calibrate:evidence-sufficiency
npm run benchmark:evidence-sufficiency
```

The gate evaluator reports answerable recall, no-evidence accuracy, balanced
accuracy, false-answer and false-abstention counts, unconditional and
conditional ranking metrics, permission/version violations, slices, and added
gate latency. Conditional ranking is diagnostic only because abstention can
remove hard cases and inflate it.

## Limitations

- Token matching is lexical: synonyms, spelling variants, multilingual queries,
  morphology, and conceptual paraphrases can fail.
- The nine-chunk synthetic corpus makes Recall@5 relatively easy; MRR and
  Recall@1 are more discriminating at this size.
- BM25 scores are not calibrated probabilities and cannot be compared across
  different queries.
- Figure captions and surrounding selectable text can be retrieved, but image
  pixels are not semantically ranked.
- Diagrams, charts, tables, equations, screenshots, scans, annotations, and
  photos are scoped in the separate
  [`multimodal retrieval plan`](../research/04_experiments/2026-07-31-multimodal-retrieval-v1-plan.md).
  Audio and video remain a later temporal-retrieval decision.
- The local IT5002 bundle has a sanitized source inventory and is selected for
  local research evaluation. This does not authorize external processing or a
  real student-facing release.
- Cross-encoder verification, calibrated answerability classification,
  reranking, and layout-aware retrieval remain candidates until a newly held-out
  experiment passes both abstention and ranking gates.
