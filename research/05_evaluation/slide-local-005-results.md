# Evaluation result: slide-local-005

## Decision and authority

**Keep two additional coding fixes locally.** This run uses the actual audited teaching configuration rather than the deterministic default used in walkthrough-codefix-004. It does not promote a model/profile or certify a bug-free application. AWS stayed paused; nothing was deployed. Local test servers were stopped after signing out.

Date: 10 September 2026. Revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty. Authoritative presentation: 70 slides, SHA-256 `7453cff7de77b597a61abc39766e3cb948ab2f0b3083d9b835a2a91dcb6f6d76`, reverified against the actual Desktop deck. [Prospective plan](../04_experiments/2026-09-10-slide-local-005-plan.md); [machine record](records/slide-local-005.json).

Decision question: do repeated local browser interactions reveal simple coding defects while the slide/report behavior remains unchanged? Prediction: primary UI recovery fixes preserve requests and persisted outcomes. Baseline: archived deployed runtime and scenario evidence. Candidate: current local UI plus unchanged audited domain/runtime. This is operational QA, not an algorithm replacement or semantic-quality comparison.

## Configuration and data

The local app starts through `create_pilot_app`, using the tracked pilot runtime environment with local data paths, credential-authenticated staging, unchanged 250-call/USD5 configured process limits and the existing qualification binding. Before serving requests, it asserts equality against the deployed record for generator/planner implementations and models, learning configuration, tutoring mode, evidence gate, experimental version and the entire experimental configuration, including observed transport settings.

Verified: `audited-presentation-v1` / `v19-luna-luna-medium`; Luna low planning/drafting, Luna medium audit/repair; 3000 output caps; governed graph v2.1; dominance-scoped ambiguity-safe V3; no optional context retrieval or assessor selection. No outreach worker or autonomous action activation. No prompt, validator, decision threshold, selected profile or research result changed. The 328 prior fingerprinted backend/profile/dataset files remain unchanged.

The corpus is the same repository-authored pilot-v1 synthetic Data Systems source pack used by the AWS scenario, with fresh local identities, release records and histories. It is not the private IT5004 lecture corpus and not a clone of old learner state. The seeding fixture uses deterministic transports only to prepare accounts/releases; seeded starter replies are excluded. All eight new browser turns use the verified live audited runtime. Therefore, runtime configuration equality is established; full infrastructure/data/history equality is not claimed.

Local URL `http://localhost:5174`, CUA in-app browser, desktop 1280×720. A local proxy substitutes the synthetic allowed HTTPS Origin for the staging API, as in the prior local test; production TLS is not under test. Credentials remain in ignored private fixture files. No private lecture material was uploaded or sent. Browser prompts and retained responses are synthetic. Eight targeted turns cover the selected paths; no random seed, held-out split, independent repetition or statistical reliability estimate applies.

## Reproduced coding defects and fixes

| ID | Before | Repair and evidence |
| --- | --- | --- |
| C-005 | `token_urlsafe(20)` sometimes lacks a required character class. Initial persona seed failed with HTTP409 `weak_password`. | Both seeding utilities now use a shared helper with the required upper/lower/digit prefix plus the same 20 random bytes. Existing credentials and identity policy are untouched. Regression injects four single-class random outputs; each satisfies the unchanged validator. Full fresh seed/repeat tests pass. |
| C-006 | Fixed account control overlaps the desktop citation panel's Close sources button. Browser clicking Close sources opened Account security and left Sources open. | Reserve horizontal room for the fixed account control in the non-dialog Sources header. Repeated browser close succeeds without opening the account menu. Mobile dialog behavior is untouched. Before/after screenshots retained. |

These were discovered during the planned run, then reproduced before repair. They are integration/presentation defects, not algorithm changes. Initial failure logs are retained. A previously saved invalid password is not silently rotated: the fresh isolated seed directory avoids changing live or existing identities.

## Live scenario results

| Turn | Scenario | Result |
| --- | --- | --- |
| 1 | Replay earlier failing member_id/team_id question | Cited answer plus check question |
| 2 | Concrete learner explanation | Cited confirmation |
| 3 | “Why?” | Existing generic clarification |
| 4 | Explain three join rows | Cited explanation |
| 5 | Reload and continue the same example | History restored; cited explanation |
| 6 | Deliberately wrong team_id answer | Cited correction |
| 7 | “I will write my own assignment” self-check | Existing false graded-work redirect reproduced |
| 8 | Fresh-chat replay of turn 1 | Cited answer plus check question |

Six answers, one clarification, one redirect; no verification failure in this small sample. This does not demonstrate that the earlier intermittent failures are resolved. Exactly sixteen messages across the two new conversations (14 and 2), eight unique student request IDs and eight unique tutor parent IDs were confirmed from the local database in read-only mode. No blind resubmission or provider-budget reset occurred. Two browser locator waits timed out while observing UI; they did not cause resubmission.

Positive citation details displayed `systems-notes.md`, version 1 and current release lineage. History survived reload and returning from the fresh chat. The evidence panel displayed revision7; foreign/primary key each 7 observations and 0 assessed, join 7 observations/2 assessed/2 partial. The stored belief has the same values. This verifies transport, not the educational correctness of assessment. Professor login, selected Release Governance course → setup → delivery continuity, and disabled autonomy Save with publication prerequisite all passed. Sampled browser warning/error logs were empty; no framework overlay observed.

## Tests and operational measurements

| Check | Result |
| --- | --- |
| Seed integration, repeat/idempotency and password regression | 3 passed, 6.57s |
| Authentication/student API regressions | 72 passed, 8.91s |
| Frontend suite after layout repair | 98 passed, 708ms |
| Lint / production build | Pass; existing large-bundle warning remains |
| Runtime configuration parity | Exact equality for the listed fields and experimental configuration |
| Persisted turn uniqueness / UI evidence match | Pass |

Recorded generation usage: 33,503 tokens and approximately USD0.0134226. Median generation latency including deterministic outcomes: 9.206s; maximum 24.921s. These figures exclude unreconciled planner and other operations, so are not a full provider bill or complete call-count reconciliation. Browser observation durations include time between inspections and are upper bounds, not precise end-to-end latency. Memory was not measured. AWS calls: zero. No repeat of the full repository check was needed for these bounded edits; its prior two absolute Desktop-link blockers remain unresolved and no all-green repository claim is made.

## Reproduction and retained evidence

```sh
uv run pytest -q tests/infra/test_pilot_seed.py
uv run pytest -q tests/api/test_auth_api.py tests/api/test_student_api.py
npm --workspace apps/web test -- --run
npm --workspace apps/web run lint
npm --workspace apps/web run build
```

Local run scripts, exact settings, seed failures/successes, snapshots, read-only message/belief extracts and screenshots are retained at `output/browser-qa/slide-local-005/`. The runtime refuses restarting the same marked run directory to prevent budget reset. Do not rerun its server merely to reread evidence. Durable machine evidence includes all eight prompt/reply/trace records and repaired-file hashes. The source-control dirty revision alone does not identify the exact code; use those hashes and runtime identity.

## Limitations and next boundary

Retain the known current-message clarification, refusal-rule false positive, assessment/praise distinction, legacy preview/publication limitations and disabled-worker branches. The original 84-turn/106-scenario reports remain intact. This run narrows the coding risk for the checked paths; it is not an exhaustive lifecycle, live IT5004 demonstration, AWS performance test or proof that no coding bugs remain. Any further defect must be reproduced before repair, and deployment remains a separate step after local review.
