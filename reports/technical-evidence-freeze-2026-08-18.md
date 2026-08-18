# Technical evidence freeze

Freeze ID: `technical-evidence-freeze-v1`

Date: 2026-08-18

Decision: **Keep the current repository as an experimental technical baseline;
do not promote it to release candidate or production.**

This closes the evidence-freeze task by preserving what passed, what failed,
what remains pending, and how to reproduce or roll back the baseline. It does
not complete the deferred product and research work merely because the
calendar freeze has arrived.

## Frozen profile

The active profile remains
[`student-tutor-v1`](../research/05_evaluation/profiles/student-tutor-v1.json)
at stage `experimental`: seven components selected, seven pending, and none
disabled. Every selected component now links directly to one or more IDs in the
[result registry](../research/05_evaluation/result-registry.md).

| Component | Frozen selection | Rollback or limitation |
| --- | --- | --- |
| Source adapter | Local files v1 | Approved local TXT/Markdown/PDF boundary only; revert through profile/Git history |
| Parser | PyMuPDF selectable-text v1 | No OCR or layout-completeness claim |
| Chunker | Page-bounded heading/paragraph v1 | Earlier configuration remains in Git; visual tuning pending |
| Retriever | M2 BM25 + frozen Qwen3 dense RRF | BM25 v1 runtime rollback |
| Generator | DeepSeek V4 Flash non-thinking | Deterministic grounded generator rollback |
| Prompt | Strict-evidence P2/v3 | Direct grounded prompt control retained |
| Tutor policy | Structured professor policy v1 | Structural requirements foundation only; behavioral effect is unverified and paused |

Pending components remain visibly pending: reranker, figure description,
policy enforcement, citation validation, conversation orchestration, proactive
trigger, and learning-gap analytics. The profile is deliberately not promoted
while those boundaries and end-to-end fidelity remain unresolved.

## Required freeze boundaries

| Boundary from issue #12 | Frozen finding | Evidence/disposition |
| --- | --- | --- |
| Cross-course retrieval | Pass, experimental | M2 reached 85.0% complete-evidence@3 versus BM25's 80.0% on the one-time 60-case run, with 164 ms warm p95 and no isolation/provider/retry failures; BM25 retained |
| Professor fidelity | Fail / paused | Automated evaluator repeat agreement was 33/48 labels across two repeated cases; sensitivity attempts invalid; human reference 0/48; no condition selected |
| Pedagogy | Unresolved | No calibrated independent judge, completed human reference, multi-turn simulated-student result, or learning outcome |
| Synthetic journeys | Pass, bounded | 19/19 deterministic publication/student checks; synthetic identities, embedder, generator, and data only |
| Isolation | Pass, bounded | Zero cross-course retrieval violations and tested fail-closed synthetic account/course/release paths |
| Recovery | Partial | Provider fallback, restart reload, publication withdrawal, stale-release denial, and release rollback pass; backup/restore, migration, and operator recovery do not |
| Capacity | Not established | No concurrent load or capacity run; no service-level claim |
| Cost | Partial | Recorded evaluation costs and caps exist; no production workload/cost model |
| Local deployment packaging | Not established | Locked installs, CI, API/web development commands, production frontend build, and same-origin local API routing work; no deployment artifact, health package, backup/restore procedure, or hosting qualification |

The authoritative claim wording is frozen in the
[claim-to-evidence matrix](claim-to-evidence-matrix.md). Unsupported claims are
not future-tense footnotes: they are explicit exclusions from the report and
presentation until new evidence exists.

## Dependency and security boundary

Dependency PR #78 retained independently passing API, test, and frontend
upgrades. The Torch 2.13.0 / Transformers 5.15.0 / Sentence Transformers 5.7.0
group was dropped because two of 40 exact M2 top-three rankings changed even
though aggregate quality tied and latency improved.

- npm audit: zero known findings.
- Python audit: zero unreviewed findings.
- Optional local ML environment: nine exact temporary reviewed findings in
  Torch 2.9.1 and Transformers 4.57.6.
- Exception expiry: 2026-09-15; any advisory, version, fix-version set,
  occurrence, or expiry drift fails CI.
- The optional ML environment is local-evaluation-only and is not approved as
  a public student-facing service.

## Reproducibility package

From the repository root on Python 3.12 and Node 24:

```bash
uv sync --locked --dev
npm ci
npm run audit:dependencies
npm run verify:technical-freeze
npm run check
```

For the local professor demonstration, start `npm run dev:api`, then
`npm run dev:web`, and open <http://localhost:5173>. The frontend uses
same-origin `/api` requests; Vite proxies them to the local API. An explicit
`VITE_API_BASE_URL` still overrides this default when deployment topology
requires it.

The machine-readable
[`technical-evidence-freeze-v1.json`](../research/05_evaluation/profiles/technical-evidence-freeze-v1.json)
binds the evidence base revision, profile, result links, claims, required
boundary dispositions, hashes, reproduction commands, and change-control rule.
Generated per-case/private artifacts remain intentionally ignored; their
durable sanitized hashes and summaries remain in registered result documents.

## Rendered smoke verification

The flow under test was: app loads → first meaningful professor-review screen
renders → one suggested onboarding answer advances the interview and workflow
trace.

| Check | Result |
| --- | --- |
| Page identity and meaningful content | Pass: `Professor Review Console`, explicit `draft only` state |
| Framework/error overlay | Pass after same-origin API repair |
| Console errors/warnings | Pass: none on clean desktop or mobile loads |
| API integration | Pass: session POST returned 201 through the Vite `/api` proxy |
| Interaction | Pass: source-permission suggestion advanced to `teaching approach` and added the second workflow event |
| Responsive first viewport | Pass at 390×844; no observed horizontal clipping or overlap |
| Professor closeout report | Pass: correct title, `Refine` headline, 68.75% repeat result, failed sensitivity gates, and 0% human reference rendered with no console errors |

The initial in-app Browser loopback attempt could not reach the host service;
testing continued through the server's advertised LAN address. That exposed the
hardcoded API-host defect and led to the same-origin fix. This is a rendered
demo smoke test, not human usability evidence.

## Rollback and change control

- Retrieval may fall back at runtime from M2 to BM25 as recorded in the active
  profile and synthetic workflow evidence.
- Generation may fall back to the deterministic grounded generator; the prompt
  retains its direct grounded control.
- The complete pre-freeze repository remains reachable at evidence-base commit
  `7abdd291cd2e0455afd6385ca3ad44557f2daf92`.
- Revert the freeze PR to restore the prior docs/profile/API routing if the
  freeze implementation itself causes a regression.
- Never alter a registered historical result. Add a correction or a new run.
- Any change to a selected implementation, configuration, claim status,
  evidence interpretation, security exception, or demo-critical route requires
  a new freeze ID, updated hashes, and full audit/check commands.
- Professor-fidelity development and held-out access remain blocked by the
  tracked execution policy; this freeze grants no new authorization.

## Professor-facing summary

The short report point is:

> We froze a reproducible experimental baseline. Cross-course text retrieval,
> the synthetic generator qualification, and 19 synthetic publication/student
> checks have bounded positive evidence. The professor-fidelity evaluator did
> not pass reliability, so fidelity and pedagogy remain paused and are not
> claimed. Capacity, backup/restore, public deployment, human usability,
> learning outcomes, and professor approval also remain unproven. The next work
> should be chosen from professor feedback, not continued implementation by
> default.
