# Cross-course retrieval development pilot

Date: 2026-07-28

Status: prospective development-only protocol amendment

## Decision question

On the assistant-QC development portion of the private cross-course benchmark,
which retrieval ladder is promising enough to carry into the fully verified
evaluation: M0 BM25, M1 Qwen3 dense retrieval, M2 reciprocal-rank fusion, or M3
hybrid retrieval plus Qwen3 reranking?

This pilot does not select a production retriever. The benchmark is not frozen:
only 1/100 cases is researcher-verified and 0/100 is independently reviewed.
The 60 `heldout_draft` cases must not be loaded into a retrieval runtime.

## Frozen pilot configuration

- Dataset: private `cross-course-retrieval-v1` draft 5.
- Cases: all 40 development cases only.
- Corpus: approved `cross-course-portfolio-v2`, using the selected
  page-bounded heading/paragraph chunks.
- Permission boundary: build a separate index for each target course. A
  condition fails if it returns a chunk outside the target course.
- Boundary context: because the five development boundary cases intentionally
  have no target course, assign them deterministically in case-ID order across
  the four sorted course IDs, wrapping once. This tests the product's
  course-scoped behavior without exposing a global cross-course index. Report
  the assignment and do not interpret five cases as comprehensive negative
  coverage.
- M0: Okapi BM25, `k1=1.2`, `b=0.75`.
- M1: `Qwen/Qwen3-Embedding-0.6B`, pinned local revision, cosine ranking.
- M2: M0 and M1 top-20 reciprocal-rank fusion, `k=60`.
- M3: M2 top-40 candidates reranked by
  `Qwen/Qwen3-Reranker-0.6B`, pinned local revision.
- Final diagnostic depth: 10; primary evidence depth: 3.
- Device: local Apple MPS, float16, batch size 8, maximum length 2,048.
- External provider calls: prohibited.

## Metrics

Ranking metrics use the unthresholded ranked lists:

- complete-evidence success@3;
- evidence-unit Recall@1, Recall@3, and Recall@5;
- nDCG@10; and
- mean reciprocal rank.

Development-only action diagnostics use one threshold per method set just
above that method's maximum score on the five development boundary cases.
Because threshold selection and reporting use the same development cases,
no-evidence accuracy and action accuracy are calibration diagnostics, not
generalization estimates.

Record per-query latency, index construction time, model load time, peak
resident memory, model-cache size, and provider cost. Hardware latency is
operational evidence only and is not a quality-selection gate.

## Interpretation rules

- Report denominators and slice results; do not report only an overall score.
- Do not call any method state of the art.
- Do not access, score, tune on, or summarize the 60 `heldout_draft` cases.
- Do not update the selected component profile from this pilot.
- A promising method advances only after 100/100 researcher verification,
  independent review of at least 20 cases, a new dataset seal, and a prospective
  final-run protocol.
- If the pilot fails operationally, retain the failure and do not manufacture
  a comparison from partial conditions.

## Attempt history

Attempt 001 stopped after 32/40 cases with `KeyError: None` because the initial
implementation assumed every development case had a target course. The failure
occurred before aggregate calculation or result-file creation. No partial
metric was retained and no heldout-draft case was accessed. The boundary
context rule above and per-case checkpointing were added before attempt 002.
