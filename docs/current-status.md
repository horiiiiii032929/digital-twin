# Current project status

Status date: 2026-08-12

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
  check for draft 004 passed 246 Python tests, 15 frontend tests,
  documentation and evaluation validators, lint, and the production build.
- Private course data, generated review packets, `.env`, build output,
  dependency folders, and Python caches remain ignored. They are intentionally
  not reorganized into Git.

## Evidence state

| Boundary | Current decision | What is established | What is not established |
| --- | --- | --- | --- |
| Text retrieval | Keep experimentally | M2 hybrid BM25 plus local Qwen3 dense RRF selected on the one-time cross-course held-out comparison; BM25 retained as rollback | Final end-to-end tutor quality |
| Generator and prompt | Keep experimentally | Exact DeepSeek V4 Flash non-thinking binding and strict-evidence P2 qualified on the separate synthetic boundary; deterministic fallback retained | Professor-policy fidelity on valid course cases |
| Professor fidelity | Refine; draft 004 ready for independent human review | Drafts 001-003 and their unfavorable findings are preserved privately; corrected v1.2.3 passes expanded privacy, split-isolation, citation-binding, policy, and semantic checks with 114 clear, 38 uncertain, and 0 unresolved LLM-detected defects | Independent human authoring approval, no-evidence absence, multi-evidence necessity, C0-C3 effects, safe grounding, semantic citation completeness, and pedagogy |
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
| 1 | [#24 Professor fidelity and tutoring policy](https://github.com/horiiiiii032929/digital-twin/issues/24) | In Progress / Refine | Complete human authoring review, corrected development execution, and blinded semantic/citation/pedagogy review |
| 2 | [#8 Multi-course professor/student core](https://github.com/horiiiiii032929/digital-twin/issues/8) | Todo / Pending | Complete credentialed identity and professor/source lifecycles after the current fidelity gate |
| 3 | [#25 End-to-end validation](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / Pending | Run the frozen complete profile only after #24 produces valid development evidence |
| 4 | [#10 Pedagogical and simulated journeys](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / Pending | Evaluate calibrated multi-turn behavior |
| 5 | [#9 Isolation, recovery, capacity, and packaging](https://github.com/horiiiiii032929/digital-twin/issues/9) | Todo / Pending | Produce bounded operational evidence |
| 6 | [#12 Technical evidence freeze](https://github.com/horiiiiii032929/digital-twin/issues/12) | Todo / Pending | Freeze only the claims and profiles supported by completed evidence |

The schedule is high risk: the technical evidence freeze is 2026-08-16. Do not
compensate by opening held-out data early, silently changing gates, or promoting
diagnostic metrics into selection evidence.

## Next decision sequence

1. Start with the 38 cases in the ignored
   `course-tutor-v1.2.3-llm-cross-review/human_uncertainty_focus.md` packet.
   These are the 19 no-evidence cases requiring corpus-wide absence review and
   the 19 multi-evidence cases requiring confirmation that both passages are
   genuinely necessary.
2. A non-Codex human then independently confirms all six checks for all 48
   development and 104 held-out cases in the ignored
   `course-tutor-v1.2.3-authoring-review` packets. The 114 advisory-clear cases
   are a prioritization aid, not automatic approval. Do not run or inspect
   held-out tutor outputs.
3. Any failed or uncertain case is revised and reviewed again. The sealer
   refuses partial approval, missing checks, Codex-assisted certification, or
   an unbound review file.
4. After all cases pass, create the immutable v2 seal and unopened held-out
   ledger.
5. Run the corrected hash-bound development comparison only.
6. Complete condition-blinded semantic, citation, context-sufficiency, and
   pedagogy review.
7. Register the development decision. Open the one-time held-out split only if
   every prospective development gate permits it.

The immediate user action is steps 1 and 2. Drafts 001-003 and their
unfavorable findings remain preserved privately; the official draft-004 review
template is blank and explicitly requires `human_review: true` and
`codex_assisted: false`. After that completed template is returned, the
remaining sealing, development execution, analysis, registry, and board
updates are implementation work for Codex.

## Source-of-truth order

Use the following order when status statements conflict:

1. immutable run records and registered result corrections;
2. the selected experimental component profile;
3. this dated operational status;
4. the live GitHub Project fields;
5. component guides and historical plans.

Never edit an old result to make it appear successful. Add a correction or new
run and retain the original evidence.
