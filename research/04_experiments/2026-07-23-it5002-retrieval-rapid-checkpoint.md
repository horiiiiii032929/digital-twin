# IT5002 retrieval rapid checkpoint

Date: 2026-07-23

Deadline: within 24 hours, no later than 2026-07-24

Status: prospectively frozen; private dataset construction, runtime binding,
execution, analysis, and professor delivery are pending

GitHub execution issue: #46

## Purpose

Produce a valid course-specific retrieval result for the professor within one
day without pretending that a small screening study is the final retriever
selection.

The rapid checkpoint answers:

> Does the frozen R5 contextual hybrid Qwen3 reranker show enough improvement
> over the R1 heading-aware BM25 rollback on all 13 IT5002 lectures to justify
> immediate confirmatory study and provisional end-to-end integration?

The larger retrieval-v3 experiment remains the final component-selection
study. Rapid cases cannot be reused in its sealed split.

## Frozen comparison

- `R1`: heading-aware BM25 with `k1=1.2`, `b=0.75`, top 5.
- `R5`: deterministic course/lecture/heading/locator context; BM25 plus
  `Qwen/Qwen3-Embedding-0.6B`, RRF with `k=60`, top 20 from each first stage,
  then `Qwen/Qwen3-Reranker-0.6B`, top 5.
- The professor-facing comparison uses only R1 and R5.
- R2-R4 may run on development data for failure diagnosis but cannot replace R5
  or become a post-hoc headline.
- R6 decomposition, BGE-M3, GraphRAG, RAPTOR, visual retrieval, and NotebookLM
  are excluded from this 24-hour run.

Exact model revisions, files, package versions, device, precision, batch size,
and cache identity must be recorded before development scoring. Private course
text stays local.

## Rapid dataset

Create `it5002-retrieval-rapid-v1` in ignored local storage. Case families are
disjoint across development, rapid held-out, and the later full retrieval-v3
benchmark.

### Development

- 26 cases total.
- 13 answerable cases: one from every lecture.
- 13 no-evidence cases: at least two from every open-set category, with one
  additional high-risk trap.
- Development may set only the frozen R1/R5 relevance or abstention threshold
  and runtime batch size.

### Sealed rapid set

- 59 cases total.
- 39 answerable cases: three from every lecture.
- The 39 answerable cases contain 13 exact/terminology, 13
  paraphrase/misconception, and 13 reasoning/multi-evidence cases.
- 20 no-evidence cases: at least three from every frozen open-set category,
  plus two additional prohibited or superseded traps.
- Every answerable case maps required claims to one or more essential evidence
  units with source, page/slide locator, and content hash.
- Every no-evidence case identifies the tempting but insufficient, prohibited,
  or superseded evidence and has expected action `abstain`.
- The ordered case manifest is hashed and access-disabled before development
  scoring.

The sample deliberately favors complete lecture and failure-category coverage
over narrow statistical power. It can detect large directional failures and
benefits; uncertainty must remain visible.

## Primary metrics

Use the same three metrics as the full retrieval-v3 study:

1. complete-evidence success@3 over the 39 answerable cases;
2. gold-claim context coverage@3 over the 39 answerable cases; and
3. no-evidence accuracy over the 20 no-evidence cases.

Report raw numerators and denominators, paired R5-R1 differences, 95% paired
bootstrap intervals with 10,000 replicates and seed `5002`, and the exact
two-sided McNemar result as descriptive evidence. Report latency p50/p95, peak
RSS, cached artifact size, model load time, and operational failures.

## Hard gates

R5 is ineligible if any of these occurs:

- any prohibited, superseded, unapproved, or wrong-course passage is returned;
- any private source text is committed or written to ordinary logs;
- any result lacks source/version/passage/locator provenance;
- any silent model fallback occurs;
- no-evidence accuracy is below `19/20`;
- answerable complete-evidence success is more than two cases below R1;
- warm retrieval p95 exceeds 5 seconds;
- peak RSS exceeds 8 GiB; or
- cached retrieval artifacts exceed 5 GiB.

Missing, malformed, timeout, and operational failures stay in the denominator.

## One-day decision

Apply gates first.

- `Drop`: a privacy/provenance gate fails, no-evidence is below `19/20`, or the
  candidate exceeds the local resource limits.
- `Refine`: the run is valid but R5 has fewer than four net additional
  complete-evidence successes over R1, regresses claim coverage, or has more
  than two answerable regressions.
- `Go Deeper`: every gate passes, R5 has at least four net additional
  complete-evidence successes, claim coverage does not regress, and the
  representative wins are not annotation artifacts.
- `Keep` is unavailable at this checkpoint. Final selection requires the larger
  retrieval-v3 confirmatory run.

R1 remains the rollback in every outcome.

## Twenty-four-hour execution clock

| Elapsed time | Required output |
| --- | --- |
| 0-2 hours | Rapid protocol committed; exact runtime and local permission boundary bound |
| 2-7 hours | Development and sealed cases authored, validated, deduplicated, hashed, and sealed |
| 7-11 hours | R1/R5 implementation and synthetic feasibility preflight pass |
| 11-14 hours | Development run completes; threshold and batch size freeze |
| 14-16 hours | One sealed run executes once |
| 16-19 hours | Independent metric recomputation, failure classification, and data-quality review |
| 19-22 hours | One comparison table, at most two figures, cases, limitations, and decision drafted |
| 22-24 hours | Result registered, repository checks pass, and compact professor message is sent |

If a reproducibility, permission, split, or tooling defect invalidates the run,
register the invalid result. Send the professor the verified existing evidence
and the concrete blocker; do not substitute an unsealed or cherry-picked run.

## Professor package

The professor receives:

1. the question and why R1/R5 were frozen;
2. the `39` answerable and `20` no-evidence denominators;
3. one table with all three metrics, intervals, gates, latency, memory, and
   cache footprint;
4. one quality-versus-latency figure and, only if useful, one error-slice
   figure;
5. one R5 win, one R1 win, and one no-evidence case;
6. the `Go Deeper`, `Refine`, or `Drop` decision; and
7. one critique question: whether the observed failure categories and claim
   boundary are academically meaningful.

The message must say that this is a rapid screening result over one course, not
a final SOTA, learning-effectiveness, usability, or production-readiness claim.
