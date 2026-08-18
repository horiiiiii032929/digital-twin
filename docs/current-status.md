# Current project status

Status date: 2026-08-18

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
| Multimodal retrieval | Refine; no selection | Historical development failures and localization evidence preserved; V0 text fallback | Trustworthy corrected metrics, region-aware extraction, product ingestion, precise visual citations, and prospective selection |
| Generator and prompt | Historical experimental selection plus later Refine evidence | Versioned DeepSeek and deterministic boundaries and unfavorable results preserved | Stable currently available candidate, independently calibrated semantic review, and release binding |
| Professor fidelity | Refine / Paused | Invalid C0-C3 comparison and correction preserved; execution policy protects held-out | Independent expert calibration, valid prospective development comparison, and hard-gate pass |
| Publication/student core | Keep as bounded foundation | 19/19 synthetic isolation, persistence, citation, publication replacement, withdrawal, rollback, and stale-release checks | Credentialed identity, complete source administration, durable production storage, jobs, deployment, observability, recovery, capacity, and usability |
| Large factual QA | Planned | Professor suggestion and issue #87 define a separate scale benchmark | Larger dummy document corpus, multimodal slice, multi-model generation/cross-check, source validation, human audit, and result |

## Immediate critical path

| Order | Issue | State | Exit condition |
| ---: | --- | --- | --- |
| 1 | [#85 Correct multimodal evaluator](https://github.com/horiiiiii032929/digital-twin/issues/85) | In Progress / Pending | Duplicate-loop defect fixed, metric suite audited, regression tests added, historical V3 result corrected or confirmed, held-out unopened |
| 2 | [#86 Region-aware multimodal product grounding](https://github.com/horiiiiii032929/digital-twin/issues/86) | Todo / blocked by #85 | Real table/column/figure/equation/scan regions, product ingestion and visual citations, deployable decision and text fallback |
| 3 | [#88 Deployable product foundation](https://github.com/horiiiiii032929/digital-twin/issues/88) | Todo / blocked by #86 | Credentialed RBAC, durable data/storage, jobs, HTTPS staging, observability, backup/restore, security, rollback |
| 4 | [#87 Large factual QA benchmark](https://github.com/horiiiiii032929/digital-twin/issues/87) | Todo / blocked by #86 | Quality-gated pilot and scale run approaching 10,000 source-linked factual cases |
| 5 | [#24 Fidelity calibration](https://github.com/horiiiiii032929/digital-twin/issues/24) | Todo / Refine / blocked by #86 | Automated evaluator calibrated against independent expert labels and valid prospective comparison |
| 6 | [#9 Production operations](https://github.com/horiiiiii032929/digital-twin/issues/9) | Todo / blocked by #88 | Isolation, recovery, observability, backup/restore, security, latency, cost, and capacity evidence |
| 7 | [#25 Deployed end-to-end validation](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / blocked by #24, #86, #88 | One immutable staging release candidate passes or receives explicit Refine/Drop decision |
| 8 | [#10 Real-workflow pilot](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / blocked by #9 and #25 | Approval-gated professor/student workflow evidence; usability remains separate from learning outcomes |

Only #85 is currently in progress. The dependency graph, milestones, priority
labels, target dates, and issue bodies are recorded on GitHub Project 1.

## Known multimodal correction

The V3 development runner constructs region relevance using a duplicated
`for hit in raw_hit_rows` loop. That can repeat every relevance value and
corrupt region@k and nDCG. Issue #85 repairs and tests the metric boundary first.
The old V3 result remains immutable and receives a linked correction or
invalidation; it is not edited to look successful.

The next multimodal candidate must also replace the shallow layout proxy:
current grouping does not model columns, table rows/cells, figures, equations,
or reading order, and product ingestion still rejects scanned PDFs. Gemma is
excluded from the new candidate path. A replacement vision model is selected
only through a prospective provider/model qualification and project-specific
evidence.

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
