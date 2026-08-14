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
  check passed 256 Python tests, 15 frontend tests,
  documentation and evaluation validators, lint, and the production build.
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
| Generator and prompt | Go deeper with V4 Pro/P3 as anchor-only candidate; historical V4 Flash selection preserved | V4 Pro/P3 passed 48/48 public-synthetic deterministic checks and a five-probe, 48/48 same-family DeepSeek semantic review at one exact fingerprint; Qwen is rejected for citation clearance; deterministic fallback remains | Independent evidence, professor-fidelity anchor calibration, and any prospective profile replacement |
| Professor fidelity | Go deeper to the frozen 41-case blinded human audit | Corrected v1.2.3 passes expanded deterministic checks; v6 completed all 456 committee records with DeepSeek V4 Pro plus two frozen local Qwen artifacts; the required audit union is 41 cases, below the 48-case cap; the GitHub purge dependency is satisfied | Independent-human approval, an immutable seal, corrected C0-C3 effects, safe grounding, semantic citation completeness, pedagogy, or professor approval |
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

1. Preserve completed V4 Pro/P3 `anchor-002` generation and the invalid primary
   judge attempt 001. The public empty-response judge-v4 probe passed; run
   separately identified primary attempt 002, swapped DeepSeek, diagnostic
   local Qwen, blinded packet preparation, and prehuman calibration. Stop at
   the bounded human reference; no generator held-out is authorized.
2. A non-Codex human reviews the blinded 16-case sample, all 19
   no-evidence cases, and every disagreement, revise, invalid, or missing model
   result: 41 cases total. Do not inspect the ensemble verdicts while completing
   that packet. The completed model boundary is recorded in the
   [v6 result](../research/05_evaluation/course-tutor-hybrid-authoring-review-v6-001-results.md).
3. Any failed or uncertain human-audited case blocks sealing and requires a
   revised candidate plus a fresh full ensemble and sample. Unsampled cases
   require unanimous three-model approval.
4. If every audited case passes, validate the frozen ensemble and human audit
   together, then create the immutable v2 seal and unopened held-out ledger.
5. Run the corrected hash-bound development comparison only after one exact
   available generator candidate is prospectively accepted for development.
6. Complete condition-blinded semantic, citation, context-sufficiency, and
   pedagogy review. The prepared
   [post-audit v3 plan](../research/04_experiments/2026-08-14-professor-fidelity-post-audit-v3-plan.md)
   uses DeepSeek V4 Pro as the primary pedagogical judge, a swapped-order
   DeepSeek sample, and local Qwen sensitivity; Gemma is not active.
7. Register the development decision. Open the one-time held-out split only if
   every prospective development gate permits it.

The immediate unavoidable user action is the bounded blinded human packet in
step 2. Codex must not complete it because the frozen instrument requires an
independent reviewer who has not inspected model decisions. After that review,
Codex can validate and continue the sequence. A later bounded anchor-output
reference may also be required to qualify automated pedagogy scoring. Drafts
001-005 and unfavorable or invalid attempts remain preserved. No full-152
human-approval or professor-validation claim is allowed.

## Source-of-truth order

Use the following order when status statements conflict:

1. immutable run records and registered result corrections;
2. the selected experimental component profile;
3. this dated operational status;
4. the live GitHub Project fields;
5. component guides and historical plans.

Never edit an old result to make it appear successful. Add a correction or new
run and retain the original evidence.
