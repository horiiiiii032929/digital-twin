# Current project status

Status date: 2026-08-14

This is the operational starting point for the repository. Frozen experiment
plans and historical result documents remain authoritative for their own runs,
but they do not override this page for current sequencing.

## Repository state

- Active branch: `codex/close-issue-24-professor-fidelity`.
- Active pull request: draft PR
  [#75](https://github.com/horiiiiii032929/digital-twin/pull/75).
- Local worktree was synchronized with the branch remote at the start of this
  status audit.
- PR #75 CI passes at the currently pushed revision. The latest full local
  check for draft 004 passed 249 Python tests, 15 frontend tests,
  documentation and evaluation validators, lint, and the production build.
- Private course data, generated review packets, `.env`, build output,
  dependency folders, and Python caches remain ignored. They are intentionally
  not reorganized into Git.
- Privacy incident requiring owner action: superseded public commit `02dbf8d`
  embedded private source-derived authoring constants. It has been removed from
  the active branch history, but GitHub still serves the object by SHA. Treat
  the remote privacy boundary as open until GitHub Support removes cached views
  and pull-request references and runs server-side garbage collection. Support
  request #4659958 has been submitted and remains open.

## Evidence state

| Boundary | Current decision | What is established | What is not established |
| --- | --- | --- | --- |
| Text retrieval | Keep experimentally | M2 hybrid BM25 plus local Qwen3 dense RRF selected on the one-time cross-course held-out comparison; BM25 retained as rollback | Final end-to-end tutor quality |
| Generator and prompt | Keep experimentally | Exact DeepSeek V4 Flash non-thinking binding and strict-evidence P2 qualified on the separate synthetic boundary; deterministic fallback retained | Professor-policy fidelity on valid course cases |
| Professor fidelity | Refine; frozen hybrid authoring review is the active gate | Drafts 001-003 and their unfavorable findings are preserved privately; corrected v1.2.3 passes expanded local privacy, split-isolation, citation-binding, policy, and semantic checks; a prospective three-model plus targeted-human protocol replaces the unrealistic 152-case manual checklist | Completed 456-decision local ensemble, bounded independent-human audit, GitHub server-side purge confirmation, C0-C3 effects, safe grounding, semantic citation completeness, and pedagogy |
| Multimodal retrieval | Refine; no selection | Development study and failure evidence are recorded; V0 text remains rollback | A selected multimodal profile or complete visual-course coverage |
| Student/publication core | Keep as bounded foundation | Synthetic course isolation, persistence, citations, fallback, publication replacement, withdrawal, rollback, and stale-release denial pass 19/19 checks | Credentialed identity, complete professor/source administration, migration, backup/restore, concurrency, capacity, and usability |

The historical professor-fidelity comparison is invalid for selection because
the cases lacked independent human authoring review, C2/C3 prompts leaked case
labels, C3 used a drifted chunk corpus, and required condition and policy/prompt
bindings were absent. The unfavorable result remains registered; no profile
selection was changed.

## Active execution queue

Only one bounded execution issue should be `In Progress`.

| Order | Issue | Board state | Purpose |
| ---: | --- | --- | --- |
| 1 | [#24 Professor fidelity and tutoring policy](https://github.com/horiiiiii032929/digital-twin/issues/24) | In Progress / Refine | Complete hybrid authoring review, corrected development execution, and blinded semantic/citation/pedagogy review |
| 2 | [#8 Multi-course professor/student core](https://github.com/horiiiiii032929/digital-twin/issues/8) | Todo / Pending | Complete credentialed identity and professor/source lifecycles after the current fidelity gate |
| 3 | [#25 End-to-end validation](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / Pending | Run the frozen complete profile only after #24 produces valid development evidence |
| 4 | [#10 Pedagogical and simulated journeys](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / Pending | Evaluate calibrated multi-turn behavior |
| 5 | [#9 Isolation, recovery, capacity, and packaging](https://github.com/horiiiiii032929/digital-twin/issues/9) | Todo / Pending | Produce bounded operational evidence |
| 6 | [#12 Technical evidence freeze](https://github.com/horiiiiii032929/digital-twin/issues/12) | Todo / Pending | Freeze only the claims and profiles supported by completed evidence |

The schedule is high risk: the technical evidence freeze is 2026-08-16. Do not
compensate by opening held-out data early, silently changing gates, or promoting
diagnostic metrics into selection evidence.

## Next decision sequence

1. Complete and commit the hybrid review implementation from the prospective
   [`course-tutor-hybrid-authoring-review-v1`](../research/04_experiments/2026-08-13-course-tutor-hybrid-authoring-review-v1-plan.md)
   plan.
2. Run the three frozen local model artifacts over all 152 cases, producing
   all 456 attempt records. The 32-case baseline is selected by stable hash
   before verdicts are read.
3. If the required human set exceeds 48, preserve the result and refine the
   instrument. Otherwise, a non-Codex human reviews the blinded 32-case sample
   plus every disagreement, revise, invalid, or missing model result. Do not
   inspect the ensemble verdicts while completing that packet.
4. Any failed or uncertain human-audited case blocks sealing and requires a
   revised candidate plus a fresh full ensemble and sample. Unsampled cases
   require unanimous three-model approval.
5. Wait for GitHub Support request #4659958 to confirm server-side purge, then
   create the immutable v2 seal and unopened held-out ledger.
6. Run the corrected hash-bound development comparison only.
7. Complete condition-blinded semantic, citation, context-sufficiency, and
   pedagogy review.
8. Register the development decision. Open the one-time held-out split only if
   every prospective development gate permits it.

Codex can complete steps 1-2. The only unavoidable user action is the bounded
blinded human packet produced by step 3 and forwarding any GitHub Support
response. Drafts 001-003 and their unfavorable findings remain preserved
privately. No full-152 human-approval or professor-validation claim is allowed.

## Source-of-truth order

Use the following order when status statements conflict:

1. immutable run records and registered result corrections;
2. the selected experimental component profile;
3. this dated operational status;
4. the live GitHub Project fields;
5. component guides and historical plans.

Never edit an old result to make it appear successful. Add a correction or new
run and retain the original evidence.
