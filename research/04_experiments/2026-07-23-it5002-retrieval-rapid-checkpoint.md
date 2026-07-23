# IT5002 retrieval rapid checkpoint

Date: 2026-07-23

Deadline: within 24 hours, no later than 2026-07-24

Status: prospectively frozen; private dataset construction, runtime binding,
execution, analysis, and professor delivery are pending

GitHub execution issue: #46

## Purpose

Produce a valid course-specific retrieval ablation for the professor within
one day without pretending that a small screening study is the final retriever
selection.

The rapid checkpoint answers:

> Does the frozen R5 contextual hybrid Qwen3 reranker show enough improvement
> over the R1 heading-aware BM25 rollback on all 13 IT5002 lectures to justify
> immediate confirmatory study and provisional end-to-end integration?

The larger retrieval-v3 experiment remains the final component-selection
study. Rapid cases cannot be reused in its sealed split.

## Frozen comparison

- `R0`: fixed-window BM25 representation control.
- `R1`: heading-aware BM25 rollback control.
- `R2`: heading-aware Qwen3 dense retrieval.
- `R3`: heading-aware BM25 plus Qwen3 dense retrieval with RRF.
- `R4`: deterministic course/lecture/heading/locator context plus hybrid RRF.
- `R5`: R4 candidates reranked by `Qwen/Qwen3-Reranker-0.6B`.
- `R6`: one frozen decomposition round followed by R5, evaluated only on the
  predeclared multi-evidence slice.
- `O1`: gold-evidence oracle ceiling on answerable cases; it is not a deployable
  retrieval method.

Run R0-R5 on all 59 sealed cases. Run R6 only on the 13 multi-evidence cases
and O1 only on the 39 answerable cases. The single primary decision contrast
remains R5 versus R1. The following adjacent contrasts are descriptive
ablations:

- R0 to R1: fixed-window versus heading-aware representation;
- R1 to R2: lexical versus dense first-stage retrieval;
- R2 to R3: dense-only versus hybrid fusion;
- R3 to R4: effect of deterministic contextual fields;
- R4 to R5: effect of learned reranking; and
- R5 to R6: effect of bounded decomposition on multi-evidence cases.

BGE-M3 remains a frozen feasibility fallback only if Qwen3 cannot run under the
local limits. GraphRAG, RAPTOR, and visual retrieval remain excluded because no
observed rapid-case failure has yet justified their added architecture.
NotebookLM remains a separately reported black-box product reference because
its passage candidates and rankings cannot enter the same Recall@K or nDCG
comparison.

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
- Development may set only the frozen per-condition relevance or abstention
  thresholds and runtime batch size. It cannot change the condition set,
  representations, fusion, instructions, candidate depths, or final K.

### Sealed rapid set

- 59 cases total.
- 39 answerable cases: three from every lecture.
- The 39 answerable cases contain 13 exact/terminology, 13
  paraphrase/misconception, and 13 multi-evidence cases.
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

Report raw numerators and denominators for every eligible condition, paired
R5-R1 differences, 95% paired bootstrap intervals with 10,000 replicates and
seed `5002`, and the exact two-sided McNemar result as descriptive evidence.
Adjacent ablations and R6 are descriptive to avoid a post-hoc multiple-testing
claim. Report latency p50/p95, peak RSS, cached artifact size, model load time,
and operational failures per condition.

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
| 7-11 hours | R0-R6 implementation and synthetic feasibility preflight pass |
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

1. the question, the full R0-R6 ladder, and why R5 versus R1 is primary;
2. the `39` answerable and `20` no-evidence denominators;
3. one table with all three metrics, intervals, gates, latency, memory, and
   cache footprint;
4. one quality-versus-latency figure and, only if useful, one error-slice
   figure;
5. one useful adjacent-ablation case, one R1 win, and one no-evidence case;
6. the `Go Deeper`, `Refine`, or `Drop` decision; and
7. one critique question: whether the observed failure categories and claim
   boundary are academically meaningful.

The message must say that this is a rapid screening result over one course, not
a final SOTA, learning-effectiveness, usability, or production-readiness claim.
