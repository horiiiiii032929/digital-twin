# Current project status

Status date: 2026-08-18

This is the operational starting point for the repository. Frozen experiment
plans and historical result documents remain authoritative for their own runs,
but they do not override this page for current sequencing.

## Repository state

- Professor-fidelity evidence and the Option A closeout were merged through PR
  [#75](https://github.com/horiiiiii032929/digital-twin/pull/75). The corrective
  interpretation is registered separately and the execution path now reads a
  tracked `paused` policy before any sealed development or held-out data.
- Development and held-out execution are unauthorized. Their active commands
  are non-executing preflights; anchor and Gemma reproduction commands are
  historical and require an explicit caller confirmation.
- The 2026-08-18 technical-freeze check passed 299 Python tests, 15 frontend tests,
  documentation and evaluation validators, frontend lint, and the production
  build without making a model call.
- Dependency/security PR
  [#78](https://github.com/horiiiiii032929/digital-twin/pull/78) upgraded the
  independently compatible Python and frontend stack. The tested major ML
  group was dropped after two of 40 exact top-three rankings changed. npm has
  zero findings; the optional local ML environment has nine exact, expiring,
  machine-enforced exceptions and zero unreviewed findings.
- The technical baseline is frozen as experimental, not release-ready. The
  [freeze report](../reports/technical-evidence-freeze-2026-08-18.md),
  [claim matrix](../reports/claim-to-evidence-matrix.md), and machine manifest
  [`technical-evidence-freeze-v1`](../research/05_evaluation/profiles/technical-evidence-freeze-v1.json)
  preserve supported results, negative results, limitations, reproducibility,
  and rollback.
- Post-freeze issue
  [#80](https://github.com/horiiiiii032929/digital-twin/issues/80) is the only
  active implementation item. It is a demo-UX refactor of the existing
  professor console, not a component-profile change or new evaluation claim.
  The candidate now has a single five-stage route, evidence-adjacent workbench,
  updated design system, and passing engineering QA; subjective professor and
  human-usability review remain pending.
- Private course data, generated review packets, `.env`, build output,
  dependency folders, and Python caches remain ignored. They are intentionally
  not reorganized into Git.
- The remote privacy incident is closed. Superseded public commit `02dbf8d`
  was removed from active history; GitHub Support closed request #4659958 after
  confirming zero references and completing server-side garbage collection and
  cached-view clearance. The authenticated commit API no longer finds the SHA,
  and the public commit URL returns HTTP 404. See the
  [purge closure record](../research/00_admin/2026-08-14-github-public-history-purge-closure.md).

## Evidence state

| Boundary | Current decision | What is established | What is not established |
| --- | --- | --- | --- |
| Text retrieval | Keep experimentally | M2 hybrid BM25 plus local Qwen3 dense RRF selected on the one-time cross-course held-out comparison; BM25 retained as rollback | Final end-to-end tutor quality |
| Generator and prompt | Refine after anchor-only V4 Pro/P3; historical V4 Flash selection preserved | V4 Pro/P3 passed 48/48 public-synthetic checks and same-family review, then completed the 48-response anchor at one exact fingerprint; Qwen is rejected for citation clearance; deterministic fallback remains | Independent evidence, calibrated professor-fidelity scoring, or any prospective profile replacement |
| Professor fidelity | Refine / Paused; report the corrected diagnostic outcome | Anchor-002 completed 48/48 V4 Pro/P3 responses; the primary judge completed but agreed on only 33/48 dimension labels across two repeated cases; swapped DeepSeek and local Qwen stopped invalid; the hidden citation-hard-gate disagreement is a cross-layer diagnostic, not a pedagogy-calibration gate; an unfilled blinded 48-response packet and the separate 41-case authoring packet remain ready | Calibrated automated pedagogy, independent-human approval, an immutable seal, corrected development C0-C3 effects, semantic citation completeness, learning outcomes, or professor approval |
| Multimodal retrieval | Refine; no selection | Development study and failure evidence are recorded; V0 text remains rollback | A selected multimodal profile or complete visual-course coverage |
| Student/publication core | Keep as bounded foundation | Synthetic course isolation, persistence, citations, fallback, publication replacement, withdrawal, rollback, and stale-release denial pass 19/19 checks | Credentialed identity, complete professor/source administration, migration, backup/restore, concurrency, capacity, and usability |

The historical professor-fidelity comparison is invalid for selection because
the cases lacked independent human authoring review, C2/C3 prompts leaked case
labels, C3 used a drifted chunk corpus, and required condition and policy/prompt
bindings were absent. The unfavorable result remains registered; no profile
selection was changed.

## Post-freeze queue

Issue #80 is the sole active post-freeze item. It may improve the professor demo
without changing frozen model, retrieval, profile, or research-evidence
decisions. Resume any other queued item only after a new explicit decision,
ideally from professor feedback.

| Order | Issue | Board state | Purpose |
| ---: | --- | --- | --- |
| 1 | [#80 Professor review console redesign](https://github.com/horiiiiii032929/digital-twin/issues/80) | In Progress / Pending | Evidence-led demo UX candidate is implemented and technically checked; await subjective review before Keep/Refine |
| 2 | [#12 Technical evidence freeze](https://github.com/horiiiiii032929/digital-twin/issues/12) | Done / Keep | Experimental profile, claims, limitations, reproducibility, report, and demo smoke are frozen |
| 3 | [#24 Professor fidelity and tutoring policy](https://github.com/horiiiiii032929/digital-twin/issues/24) | Todo / Refine (Paused) | Preserve the diagnostic result and deferred human packets; resume only as a separately authorized evaluator redesign |
| 4 | [#8 Multi-course professor/student core](https://github.com/horiiiiii032929/digital-twin/issues/8) | Todo / Pending | Preserve the 19-check foundation; do not start new feature development after the technical freeze |
| 5 | [#25 End-to-end validation](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / Pending | Retain for a future validated complete profile; do not open blocked fidelity held-out data |
| 6 | [#10 Pedagogical and simulated journeys](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / Pending | Retain as future work; calibrated multi-turn evaluation is not established |
| 7 | [#9 Isolation, recovery, capacity, and packaging](https://github.com/horiiiiii032929/digital-twin/issues/9) | Todo / Pending | Limit current work to reproducibility and demo-preserving checks |

The 2026-08-16 target was missed by two days; the technical evidence was frozen
on 2026-08-18. Do not start new feature or method development, open held-out
data, silently change gates, or promote diagnostic metrics into selection
evidence without a new post-freeze decision.

## Frozen closeout sequence

1. Report the professor-fidelity result as `Refine / Paused`; the durable
   professor-facing report is
   [Professor fidelity evaluation closeout](../reports/professor-fidelity-closeout-2026-08-17/report.html).
   Analysis correction 001 at code revision `dbd7a71` supersedes the original
   false-pass interpretation: C3 citation-source correctness is 4/8 applicable
   cases, and the hidden-hard-gate disagreement is diagnostic only.
2. Preserve PR #75 and its correction as unfavorable but decision-bearing
   evidence. Issue #24 remains open and is out of active execution.
3. Issue #12 is complete: only claims and profile selections supported by
   registered evidence are frozen, and the report plus local professor demo
   pass rendered smoke checks.
4. Do not rerun primary attempt 001, swapped attempt 001, Qwen attempt 001, or
   any professor-fidelity held-out evaluation. Partial agreement remains
   diagnostic only.
5. Defer both human packets. If a future evaluator-redesign iteration is
   separately authorized, a non-Codex reviewer must complete the frozen
   instruments before any calibration or professor-approval claim.

There is no immediate human action. Both bounded blinded packets are deferred,
but neither is passed or waived.
Codex must not complete them because the frozen instruments require an
independent reviewer who has not inspected model decisions. Drafts 001-005 and
all unfavorable or invalid attempts remain preserved. No full-152 human
approval or professor-validation claim is allowed.

## Source-of-truth order

Use the following order when status statements conflict:

1. immutable run records and registered result corrections;
2. the versioned technical-freeze manifest and selected experimental profile;
3. the frozen claim-to-evidence matrix;
4. this dated operational status;
5. the live GitHub Project fields;
6. component guides and historical plans.

Never edit an old result to make it appear successful. Add a correction or new
run and retain the original evidence.
