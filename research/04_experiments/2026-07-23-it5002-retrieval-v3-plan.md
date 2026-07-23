# IT5002 retrieval v3 experiment

Date: 2026-07-23

Status: candidate set and analysis contract frozen; implementation, private
dataset completion, feasibility preflight, calibration, and held-out run are
pending

## Decision question

On the complete approved IT5002 lecture corpus, does deterministic contextual
hybrid retrieval with a learned reranker retrieve all essential evidence more
reliably than the current heading-aware BM25 control under the same top-K
evaluation boundary, while preserving safe no-evidence behavior and a practical
local resource budget?

A conditional secondary question asks whether one frozen question-
decomposition round improves complete-evidence retrieval on multi-evidence
questions enough to justify its latency and query-drift risk.

## Prediction

- R1 BM25 will remain competitive on exact terminology and identifiers.
- R2 dense retrieval will improve some paraphrases but will admit semantically
  close distractors.
- R3 hybrid retrieval will improve candidate coverage.
- R4 deterministic course, lecture, section, and locator context will reduce
  ambiguous-chunk failures without introducing generated facts.
- R5 reranking will improve complete-evidence success@3 and gold-claim context
  coverage by promoting evidence-bearing passages over topical duplicates.
- R6 decomposition will help multi-evidence questions but may regress latency
  or drift away from the original question.
- The main safety risk is a high-scoring, topically similar passage on a
  no-evidence query. The main usefulness risk is a threshold that prevents false
  answers by rejecting too many answerable questions.

## Scope

### Included

- All 13 inventoried selectable-text IT5002 lecture PDFs, 508 pages, under the
  frozen corpus manifest.
- English questions over the five existing topic strata.
- Exact, paraphrase, misconception, multi-evidence, ambiguity, no-evidence,
  assessed-work, and permission/version cases.
- Locally run open retrieval and reranking candidates.
- A separately reported, optional NotebookLM black-box product reference.

### Excluded

- Generator or tutoring-prompt selection.
- Claims about learning, satisfaction, adoption, or human usability.
- Public signup, deployment architecture, or commercial product selection.
- GraphRAG, RAPTOR, fine-tuning, and unbounded model search.
- Visual retrieval unless a versioned, adjudicated diagram/table slice is
  created before its own freeze.

## Stable component contract

- Input: one normalized question, an eligible corpus revision, and a requested
  result limit.
- Output: ordered eligible passage records with stable source, version,
  passage, locator, score, method, and latency metadata.
- Invariants:
  - prohibited, superseded, unapproved, or wrong-course evidence is never
    returned;
  - original source text and locator remain recoverable after contextualization;
  - deterministic representations have stable hashes;
  - candidate identities are hidden during judgment;
  - an empty result is valid and distinct from an operational failure; and
  - every final passage fits the same K boundary used by the metrics.

## Corpora and datasets

### Course cases

Reuse the `course-tutor-v1` gold case and evidence graph:

- development/calibration: 48 cases;
- sealed final: 104 cases;
- case families never cross splits; and
- required claims map to essential evidence independently of candidate output.

The existing 12-case researcher anchor verifies the instrument and does not
contribute to performance estimates.

### Open-set companion

Add `it5002-retrieval-open-set-v1` to strengthen the no-evidence denominator:

- development/calibration: 24 hard-negative cases;
- sealed final: 52 hard-negative cases; and
- categories: near-domain absent, vocabulary collision, plausible non-course,
  unsupported precision, prohibited trap, and superseded trap.

The companion contains no answerable cases. The course and open-set files are
analyzed separately before any pooled operational summary. Private questions,
passages, and course text remain in ignored local storage; committed examples
are synthetic.

The sealed retrieval run therefore requests 156 cases: 104 course cases plus 52
open-set cases. The exact answerable, partially answerable, and not-answerable
denominators from `course-tutor-v1` must be printed before analysis.

## Representations and conditions

### Shared representation settings

- R0 fixed-window chunks: 1,200 characters with 160-character overlap.
- R1-R3 heading-aware chunks: current `HeadingParagraphChunker`, 1,200
  characters with 160-character whole-segment overlap.
- R4-R6 contextual representation: prepend only deterministic approved fields:
  pseudonymous course ID, lecture ID, lecture title, heading path, and page or
  slide locator.
- Context text is indexed, but the original passage alone is cited and supplied
  as evidence.
- No LLM-generated summary or hypothetical question is indexed in v3.

### Frozen internal conditions

| ID | Candidate |
| --- | --- |
| R0 | Fixed-window chunks plus BM25 `k1=1.2`, `b=0.75` |
| R1 | Heading-aware chunks plus BM25 `k1=1.2`, `b=0.75` |
| R2 | Heading-aware chunks plus `Qwen/Qwen3-Embedding-0.6B` cosine retrieval |
| R3 | R1 plus R2, top 20 from each, deduplicated and fused with RRF `k=60` |
| R4 | Deterministically contextualized R3 |
| R5 | R4 candidate pool reranked by `Qwen/Qwen3-Reranker-0.6B`, final top 5 |
| R6 | R5 plus one frozen decomposition round only for `multi_evidence` cases |
| O1 | Independently annotated essential gold evidence |

R5 versus R1 is confirmatory. R0 and R2-R4 are ablations. R6 is a conditional
comparison on the multi-evidence denominator. O1 is an upper bound and cannot
be selected.

Exact model revisions, file hashes, runtime package versions, numerical
precision, device, batch size, and cache identity must be recorded by the
feasibility preflight before any development scoring. A model whose exact
revision cannot be bound is ineligible.

### Frozen Qwen instruction

Use this English instruction for both dense retrieval queries and reranking:

> Given a student question about the approved IT5002 course, retrieve passages
> that together contain all evidence needed to answer accurately and safely.

Documents receive no retrieval instruction. Any instruction change creates a
new candidate version and cannot be made after calibration begins.

### NotebookLM reference

NotebookLM B1 is exploratory and separate:

- run only after source permission and account terms are recorded;
- use the same source revision and a prospectively selected 40-case stratified
  subset;
- record date, plan/tier, selected sources, query order, conversation-history
  treatment, answer, visible citations, and latency;
- score observable claim support, citation correctness/completeness,
  abstention, and failures; and
- do not report Recall@K, nDCG, candidate rankings, or a component-selection
  decision for NotebookLM.

If independent chat state cannot be established, label B1 exploratory and
potentially history-confounded rather than silently treating queries as
independent.

## Metrics

### Primary selection measures

1. **Complete-evidence success@3:** proportion of answerable or partially
   answerable course cases for which every essential evidence unit needed for
   the permitted action is represented in the first three results.
2. **Gold-claim context coverage@3:** macro mean, across eligible course cases,
   of required claims supported by at least one first-three passage divided by
   all required claims.
3. **No-evidence accuracy:** proportion of all corpus-not-answerable and
   open-set cases for which the deployed retrieval/sufficiency threshold
   returns no answerable context.

Every proportion includes numerator, denominator, and a Wilson 95% interval.

### Diagnostics

- complete-evidence success@5;
- gold-evidence Recall@1/3/5;
- graded nDCG@3 using `0=irrelevant`, `1=helpful`, `2=essential`;
- context Precision@3/5;
- MRR for first-useful-evidence behavior;
- answerability precision and recall;
- false-answer and false-abstention counts;
- per-scenario, topic, difficulty, and stressor slices;
- duplicate and parent-expansion burden;
- index build time, index size, model load time, warm p50/p95 retrieval latency,
  peak resident memory, and query-decomposition calls; and
- failure attribution to source, parsing, chunking, contextualization, query,
  dense representation, fusion, reranking, threshold, permission/version
  filtering, or operation.

## Gates and decision thresholds

### Hard gates

- Zero prohibited, superseded, unapproved, or wrong-course passages returned.
- Zero sealed-set access before dataset, candidate, model-revision, threshold
  search, metric, and analysis freeze.
- Zero private source text committed to Git or ordinary logs.
- Zero missing provenance or unresolvable evidence identifiers.
- Zero silent model fallback or candidate substitution.
- Every missing, malformed, timed-out, or failed attempt remains in the primary
  denominator as a failure.

### Quality and operational eligibility

- No-evidence accuracy at least `0.95` on the combined sealed no-evidence
  denominator.
- Answerable recall may not be more than 5 percentage points below R1.
- Warm retrieval p95 no greater than 5 seconds for R1-R5 on the named project
  machine.
- R6 full retrieval p95 no greater than 8 seconds and no more than one
  decomposition round.
- Peak resident memory no greater than 8 GiB for an eligible deployed
  retriever/reranker condition.
- The complete cached retrieval artifacts, excluding generator models, may not
  exceed 5 GiB.

These are project decision constraints, not universal quality targets.

### Minimum useful effects

- R5 should improve complete-evidence success@3 over R1 by at least 5
  percentage points.
- R5 should improve gold-claim context coverage@3 over R1 by at least 5
  percentage points.
- R6 should improve complete-evidence success@3 on multi-evidence cases over R5
  by at least 10 percentage points.

Failure to reach an effect is reportable and does not authorize tuning on the
held-out set.

## Calibration and held-out discipline

1. Validate all schemas, hashes, source permissions, and split-family
   separation.
2. Bind exact model revisions and complete a resource-only feasibility
   preflight using synthetic text.
3. Use only development and anchor data to implement, debug, select thresholds,
   and decide whether the bounded BGE-M3 fallback is needed.
4. Freeze the selected threshold and every runtime/configuration field.
5. Record a clean code revision and dirty state.
6. Execute the held-out run once.
7. Preserve every failure and invalidation. If a tooling defect invalidates the
   run, register it before creating a versioned rerun.

The sealed set cannot decide chunk size, overlap, instruction, candidate pool,
RRF parameter, reranker depth, decomposition prompt, threshold, or model.

## Analysis

- R5 versus R1 complete-evidence success uses exact two-sided McNemar.
- R5 versus R1 claim coverage and nDCG use a paired 10,000-replicate bootstrap
  with seed `5002`.
- R5 versus R1 no-evidence decisions use exact McNemar plus raw false-answer
  counts.
- R6 versus R5 is analyzed only on the predeclared `multi_evidence` cases.
- H1-H3 confirmatory p-values use Holm correction at family alpha `0.05`.
- All other candidate and slice comparisons are descriptive.
- Latency reports the paired distribution and p50/p95; it is not averaged
  across cold model loading.
- Missing and operational failures are unfavorable outcomes, never exclusions.

No candidate is selected from a higher average alone. Apply hard gates first,
eligibility thresholds second, confirmatory evidence third, and implementation
complexity last. Retain R1 as the rollback control unless R5 qualifies.

## Planned result package

The professor receives a result, not a planning update:

1. one-page question, dataset, comparison, and decision memo;
2. a table with raw denominators, intervals, gates, latency, memory, and cost;
3. a complete-evidence versus p95-latency plot;
4. a safe-answer coverage or false-answer/false-abstention plot;
5. favorable and unfavorable representative cases;
6. failure taxonomy and bounded limitations; and
7. Keep / Refine / Go Deeper / Drop plus the retained rollback.

Do not contact the professor merely to announce this plan. The first checkpoint
follows a valid decision-bearing course-specific result.

## Stop rules

- Stop before private data enters an unapproved runtime or account.
- Stop if a split-family duplicate, evidence-hash mismatch, or source-version
  mismatch is found.
- Stop if the exact Qwen model revision or local numerical behavior cannot be
  bound reproducibly.
- Stop R6 if decomposition produces prohibited content, more than one
  retrieval round, or malformed subqueries above 5% in development.
- Do not add GraphRAG, RAPTOR, another embedding leaderboard, or visual
  retrieval during v3.
- A no-selection result is valid and should be reported rather than repaired by
  inspecting held-out failures.
