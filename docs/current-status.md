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

Issue [#88](https://github.com/horiiiiii032929/digital-twin/issues/88) remains
in progress with a **Go Deeper** local architecture result, but is now marked
externally blocked while a public host and domain are selected. The deployable
candidate passed 41/41 synthetic checks across credentialed access, professor
upload/publication, student answer/original-region citation, restart,
backup/clean restore, security, lifecycle, and bounded capacity. The measured
100-request error rate was 0%, API p50/p95 was 2.345/2.964 ms, ingestion was
52.455 ms, and peak RSS was 0.30 GiB on the development host. The professor UI
now supports resumable course/student/source/release delivery, and rendered
desktop/mobile QA passed without console errors. Public DNS/TLS, host-side
restore, and the staging walkthrough remain before #88 can close.
The tested local candidate is frozen at revision `e619df9` by
`deployable-product-foundation-freeze-v1`; its three external gates remain
explicitly pending.
The subsequent container rehearsal found and corrected a duplicate-image build
race and an eager demo-store import, then hardened Caddy to a non-root user. At
clean revision `1fcd6fd`, the exact images built and passed 15/15 live HTTPS
journey checks, 5/5 after a separate-project clean restore, and 5/5 after
switching back to the untouched original volume. Local Caddy TLS is now proven;
public DNS/trusted certificate issuance and the same rehearsal on the selected
host remain external gates.
The current candidate is bound by `deployable-product-foundation-freeze-v2` at
evidence revision `7e980a6`; V1 remains a historical freeze for the earlier
unclaimed-build result.
PR [#93](https://github.com/horiiiiii032929/digital-twin/pull/93) merged the
foundation into `main` at `adf39af`; this accepts the local/container-qualified
implementation without promoting the still-pending public deployment claim.

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
| Publication/student core | Go Deeper as single-host staging candidate | Earlier 19/19 publication slice, 41/41 in-process foundation checks, built images, 25/25 live local-HTTPS/recovery checks, deterministic preflight, and A0 demo rollback | Public trusted HTTPS/target-host restore, real-workflow usability, representative source quality, and release-candidate evaluation |
| Large factual QA | Go Deeper / audit pending | Attempt 002 passed every machine gate: 24/24 retained, 7/7 safe boundary actions, 6/6 multimodal retained, zero leakage/duplicates, and complete dual review | Complete the preserved six-case human audit; refine on any failure, otherwise freeze a separate scale-stage plan |

## Immediate critical path

| Order | Issue | State | Exit condition |
| ---: | --- | --- | --- |
| 1 | [#87 Factual-QA dataset quality](https://github.com/horiiiiii032929/digital-twin/issues/87) | In Progress / Go Deeper | Complete the six-case audit preserved from attempt 002; refine on failure or freeze the scale-stage method on pass |
| 2 | [#88 Deployable product foundation](https://github.com/horiiiiii032929/digital-twin/issues/88) | In Progress / Go Deeper / blocked | Local 41/41 and 25/25 HTTPS/recovery checks passed; complete public DNS/TLS, target-host restore, and public staging walkthrough after host/domain selection |
| 3 | [#24 Fidelity calibration](https://github.com/horiiiiii032929/digital-twin/issues/24) | Todo / Refine | Calibrate the automated evaluator against independent expert labels; keep this separate from factual QA |
| 4 | [#9 Production operations](https://github.com/horiiiiii032929/digital-twin/issues/9) | Todo / blocked by #88 | Isolation, recovery, observability, backup/restore, security, latency, cost, and capacity evidence on the target host |
| 5 | [#25 Deployed end-to-end validation](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / blocked by #24 and #88 | One immutable staging release candidate passes or receives an explicit Refine/Drop decision |
| 6 | [#10 Real-workflow pilot](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / blocked by #9 and #25 | Approval-gated professor/student workflow evidence; usability remains separate from learning outcomes |

Issues #85 and #86 are complete and archived from the live Project view. PR #91 merged the tested multimodal product
foundation and three registered prospective development attempts. Attempt 003 passed 13/14 gates:
all quality, safety, action, text-control, and lineage gates passed; relative
warm p95 failed at 0.053 ms versus 0.023 ms. No multimodal profile was selected,
and the historical held-out split was not opened. Issue #87 is now at its
bounded human-audit gate after attempt 001 exposed method defects and the
prospective attempt 002 passed all machine gates. This qualifies the
dataset-building method, not a model benchmark. Issue #88 remains active but externally
blocked; its implementation and local qualification are complete enough for a
controlled host rehearsal, not for a real-user pilot.

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

The active model policy now blocks every Gemma call and all retired local
Qwen3 general-reviewer calls before provider I/O. DeepSeek V4 Flash/Pro,
Claude Sonnet 5, and the selected task-specific Qwen3 Embedding binding remain
current for their recorded roles. `qwen3.5:4b` is the prospective local general
and vision-language replacement, but it is not selected until a new instrument
passes its project-specific gates. See
[the current model policy](../research/00_admin/2026-08-19-current-model-policy.md).

## Large factual-QA interpretation

Issue #87 adopts the stronger, product-relevant interpretation of the
professor's suggestion: build a larger permission-safe dummy document corpus,
then derive and cross-check factual QA toward 10,000 cases. This is not a model
leaderboard. The bounded pilot evaluates whether the source-constrained method
produces trustworthy cases; failed gates require method revision. It includes a
meaningful multimodal slice and remains separate from the verified 100-case
benchmark and Professor Digital Twin fidelity.

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
