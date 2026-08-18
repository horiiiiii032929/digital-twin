# Current project status

Status date: 2026-08-19

This is the operational starting point for prospective work. Frozen experiment
plans, result records, corrections, profiles, and the technical evidence freeze
remain authoritative for the historical runs and claims they document.

## Current outcome

The project has moved from an experimental local-demo goal to a deployed,
invite-only real-world Course Digital Twin goal. The new prospective baseline is
the [real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md).

PR [#83](https://github.com/horiiiiii032929/digital-twin/pull/83) merged the
reviewed conversation-first professor and student workspaces into `main` at
`acaaecd`. Issues #82 and #84 are `Done / Keep`. The merged flow passed the
recorded repository checks, 19/19 synthetic publication/student checks,
responsive browser QA, and independent Impeccable review. This establishes the
product UX baseline; it does not establish human usability or production
readiness.

GitHub Project 1 is reorganized around product goal
[#8](https://github.com/horiiiiii032929/digital-twin/issues/8) and three active
gates:

- P1 — Multimodal Product Grounding;
- P2 — Deployable Product Foundation; and
- P3 — Pilot Validation and Release.

The older F2 milestone is closed. Open F3 work was reassigned into P1-P3. F4
continues to hold report, presentation, and professor-communication work.

## Evidence state

| Boundary | Current decision | Established | Missing before product release |
| --- | --- | --- | --- |
| Product UX | Keep as baseline | Professor and student conversation-first workspaces; responsive synthetic flows | Human workflow/usability evidence and complete real source/account lifecycle |
| Text retrieval | Keep experimentally | M2 hybrid BM25 plus local Qwen3 dense RRF selected on the one-time cross-course held-out comparison; BM25 rollback | Release-candidate end-to-end quality against realistic workload |
| Multimodal retrieval | Refine; no selection | Region-aware tables/cells/diagrams/equations/OCR, scanned-PDF API ingestion, original crop citations, 13/13 synthetic complete@3 and lineage; unfavorable historical and V2 attempt results preserved | Production OCR/layout qualification, representative real-PDF quality and end-to-end latency; frozen relative micro-p95 gate still failed |
| Generator and prompt | Historical experimental selection plus later Refine evidence | Versioned DeepSeek and deterministic boundaries and unfavorable results preserved | Stable currently available candidate, independently calibrated semantic review, and release binding |
| Professor fidelity | Refine / Paused | Invalid C0-C3 comparison and correction preserved; execution policy protects held-out | Independent expert calibration, valid prospective development comparison, and hard-gate pass |
| Publication/student core | Keep as bounded foundation | 19/19 synthetic isolation, persistence, citation, publication replacement, withdrawal, rollback, and stale-release checks | Credentialed identity, complete source administration, durable production storage, jobs, deployment, observability, recovery, capacity, and usability |
| Large factual QA | Planned | Professor suggestion and issue #87 define a separate scale benchmark | Larger dummy document corpus, multimodal slice, multi-model generation/cross-check, source validation, human audit, and result |

## Immediate critical path

| Order | Issue | State | Exit condition |
| ---: | --- | --- | --- |
| 1 | [#85 Correct multimodal evaluator](https://github.com/horiiiiii032929/digital-twin/issues/85) | Done / Refine | Metric suite corrected and tested; historical V3 analysis corrected; Drop unchanged; held-out unopened |
| 2 | [#86 Region-aware multimodal product grounding](https://github.com/horiiiiii032929/digital-twin/issues/86) | In progress / Refine evidence recorded | Foundation, product ingestion, crop citations, and prospective decision implemented; close after repository/Project handoff |
| 3 | [#88 Deployable product foundation](https://github.com/horiiiiii032929/digital-twin/issues/88) | Todo / blocked by #86 | Credentialed RBAC, durable data/storage, jobs, HTTPS staging, observability, backup/restore, security, rollback |
| 4 | [#87 Large factual QA benchmark](https://github.com/horiiiiii032929/digital-twin/issues/87) | Todo / blocked by #86 | Quality-gated pilot and scale run approaching 10,000 source-linked factual cases |
| 5 | [#24 Fidelity calibration](https://github.com/horiiiiii032929/digital-twin/issues/24) | Todo / Refine / blocked by #86 | Automated evaluator calibrated against independent expert labels and valid prospective comparison |
| 6 | [#9 Production operations](https://github.com/horiiiiii032929/digital-twin/issues/9) | Todo / blocked by #88 | Isolation, recovery, observability, backup/restore, security, latency, cost, and capacity evidence |
| 7 | [#25 Deployed end-to-end validation](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / blocked by #24, #86, #88 | One immutable staging release candidate passes or receives explicit Refine/Drop decision |
| 8 | [#10 Real-workflow pilot](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / blocked by #9 and #25 | Approval-gated professor/student workflow evidence; usability remains separate from learning outcomes |

Issue #85 is complete. Issue #86 now has a tested product foundation and three
registered prospective development attempts. Attempt 003 passed 13/14 gates:
all quality, safety, action, text-control, and lineage gates passed; relative
warm p95 failed at 0.053 ms versus 0.023 ms. No multimodal profile was selected,
and the historical held-out split was not opened.

## Known multimodal correction

The suspected duplicated `for hit in raw_hit_rows` loop was not present in the
committed runner, and the preserved values match the single-pass legacy
formula. The actual defect was duplicate gain: overlapping OCR, layout, and
description records could each add discounted IoU for the same gold region,
after which the unnormalized total was capped at one.

Issue #85 replaces that metric with one-to-one region matching and normalized
discounted IoU, tests page/region ranking, IoU thresholds, complete evidence,
atomic recall, and nDCG, and registers a no-model correction. V2 changes from
0.212 to 0.0676 and V3 from 0.186 to 0.0756 on corrected region nDCG. Complete
evidence remains tied at 1/3, V3 atomic recall remains worse at 1/3 versus
V2's 2/3, and the V3 online-model gate still fails. The Drop decision and
text-only rollback therefore remain unchanged. The 24-case held-out split was
not read.

The prospective path now models columns, table rows/cells, figures, diagrams,
equation-like blocks, OCR, reading order, page/region checksums, and original
crops. Scanned PDFs work when an approved OCR provider is injected. Gemma
remains excluded. A production OCR/layout or replacement vision model is
selected only through a new prospective qualification and representative
course evidence.

## Large benchmark interpretation

Issue #87 adopts the stronger, product-relevant interpretation of the
professor's suggestion: build a larger permission-safe dummy document corpus,
then derive and cross-check factual QA toward 10,000 cases. This tests corpus
and factual-answer scale rather than repeatedly sampling only the existing 32
PDFs. It includes a meaningful multimodal slice and remains separate from the
verified 100-case benchmark and Professor Digital Twin fidelity.

## Human and safety boundary

A real-user pilot is now a product gate, but recruitment is not automatically
authorized. Issue #10 requires consent, privacy, recruitment, and supervisor
approval before exposure to real users. Until then, use synthetic accounts and
approved or dummy content.

Private course data, generated review packets, `.env`, build output,
dependencies, model artifacts, and bulky run outputs remain ignored. Do not use
solutions, answer keys, submissions, student data, credentials, or consent
records as committed fixtures.

## Source-of-truth order

When status statements conflict, use:

1. immutable run records and registered corrections for historical results;
2. versioned component/release profiles and the technical evidence freeze;
3. the prospective real-world product scope;
4. this dated operational status;
5. the live GitHub Project fields and dependencies;
6. component guides and historical plans.

Never edit an old result to make it appear successful. Add a correction or a
new prospective run and retain the original evidence.
