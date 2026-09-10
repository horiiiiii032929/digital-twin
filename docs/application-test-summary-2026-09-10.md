# Application testing summary

Updated: 10 September 2026, Singapore. Covers the AWS walkthrough and the subsequent local investigation/fix runs through `scenario-local-008`.

**Result: several application coding defects are repaired and locally validated. The full professor-upload-to-check-in lifecycle is still not verified.** Some teaching replies fail validation, fresh-course publication remains blocked in the tested workflow, and proactive delivery is disabled. Passing code tests does not make those scenarios pass.

## What configuration was tested

The latest 70-slide presentation is the compatibility boundary: SHA-256 `7453cff7de77b597a61abc39766e3cb948ab2f0b3083d9b835a2a91dcb6f6d76`.

The audited AWS/local runs use `audited-presentation-v1`, candidate `v19-luna-luna-medium`: Luna low for planning/drafting, Luna medium for audit/repair, governed graph v2.1 and the existing evidence gate. Models, prompts, assessment rules, evaluation methodology, publication gates and automatic retry limits were preserved. The optional learning configuration remains unselected; proactive outreach remains disabled.

Testing used synthetic Data Systems/Browser Security material and test accounts. Local runs match the selected application configuration, but do not reproduce AWS networking, host capacity or the private lecture corpus. Run 004 used deterministic responses for UI recovery; runs 005 and 006 exercised the audited live-model path locally. Run 007 was entirely offline. Run 008 resumed explicitly authorized paid calls in a fresh synthetic fixture with the same audited configuration.

## Test runs at a glance

The linked reports retain detailed evidence and unsuccessful attempts. Counts overlap across suites and repeated runs; **do not add them into a unique-test total**.

| Run | Where / purpose | Main result |
| --- | --- | --- |
| [AWS browser lifecycle 001](../tests/manual/aws-pilot-lifecycle-001-results.md) | Actual AWS browser; seven personas, three visits each; professor/student flows | 84 core turns; 14 withheld replies. Three coding fixes deployed then. Frontend 89 tests; targeted backend 60 and API 109; lint/build passed. Full lifecycle incomplete. |
| [Slide codefix 001](../research/05_evaluation/slide-codefix-001-results.md) | Audit diagnostics, unchanged decisions, AWS follow-up | 18/18 control comparisons matched. Eight browser turns: two withheld. Focused suites 117, 114 and 81 passed; frontend 89 passed. Diagnostic refinement deployed then. |
| [Slide codefix 002](../research/05_evaluation/slide-codefix-002-results.md) | Local accounting/schema diagnostic repair | 18/18 control comparisons matched; API/services 327, domain 612, frontend 89 passed. No paid calls or deployment. |
| [Scenario investigation 003](../research/05_evaluation/scenario-investigation-003-results.md) | Reproduce suspected UI loading defects | Two probes demonstrated that stalled metadata could lock the composer or hide saved history. These were defect demonstrations, not fixes. |
| [Walkthrough codefix 004](../research/05_evaluation/walkthrough-codefix-004-results.md) | Local UI repairs with delayed/failed metadata | Frontend 98; API/services/accounting 410; 18/18 audit comparisons passed. Browser recovery, account switching, uploads and consent controls checked. Deterministic tutor responses; no model-quality claim. |
| [Slide local 005](../research/05_evaluation/slide-local-005-results.md) | Local audited configuration; seed and Sources-control repairs | Eight new browser turns, no verification failures in this small sample. Existing clarification/refusal limitations reproduced. Seed 3, API 72, frontend 98 tests passed; lint/build passed. |
| [Lifecycle local 006](../research/05_evaluation/lifecycle-local-006-results.md) | Broader local professor/student walkthrough and fault injection | 80/84 planned turns; 16 withheld. Six personas completed three visits, seventh two. Frontend 100, API/services/seed 330, domain/accounting 130 passed; lint/build passed. Budget guard stopped remaining model work. |
| [Root cause 007](../research/05_evaluation/root-cause-007-results.md) | Offline causal investigation and diagnostic repair | 300 focused tests passed. All 80 stored assessment observations matched current rules. Seven-turn control verified recent history and audit bindings. No paid calls, AWS changes or new browser lifecycle claims. |
| [Scenario local 008](../research/05_evaluation/scenario-local-008-results.md) | Paid browser reload/session/network recovery follow-up | Two reproduced frontend defects fixed; ten new turns, one withheld; 20 provider calls, reported USD0.0189028. Frontend 116 and relevant API 115 tests passed; lint/build passed. |

## Features and scenarios tested

| Area | What was exercised | Current conclusion |
| --- | --- | --- |
| Sign-in and access | Student/professor/admin roles, revoked identity, inactive membership, role switching, sign-out/Back/reload, disposable account creation, duplicate email, login throttle/recovery | Run 008 added valid session-expiry recovery and independent professor/student browser contexts; broader revocation cases remain incomplete. |
| Continuing student chat | Seven personas, repeated turns, return visits, saved history/reload, course switching, direct explanations, misconceptions, graded-work redirects and permitted hints | Persistence worked in the checked histories; teaching failures remain. Run 006 confirmed 80 unique requests and exactly one linked response each. |
| Submit/retry behavior | Duplicate-submit protection in hook tests; failed sends retain request ID and draft; two pre-API failed browser attempts reused the same ID | Tested safeguards passed. Run 008 added paid pending-reload/manual same-request recovery and offline reconnect; all ten new requests had one linked response each. |
| Citations and evidence | Source details, panel close, selected-message associations, delayed reads, independent failures, partial recovery, manual retries, stale-read isolation | Reproduced UI defects repaired. Optional metadata recovery does not intentionally create tutoring requests. |
| Professor course setup | Course creation/validation, ownership separation, setup/delivery navigation, interview/policy/profile review, enrollment and duplicate enrollment | Ordinary tested operations passed; rejected/unfinished approvals stayed rejected. |
| Source ingestion | Real Markdown upload/worker processing, cancellation, duplicate upload, empty/invalid files, malformed PDF parsing and retry, excluded metadata | Success/failure states behaved as observed; malformed data was not falsely reported as successful. |
| Publication and revisions | Missing-prerequisite blocks, unpublished student exclusion, domain/profile controls; automated publication/version/rollback tests | Negative gates passed. Successful fresh-course browser publication and v2 revision were not completed. |
| Check-ins and goals | Consent on/off, pause/resume, account isolation, empty inbox/goals, professor runtime/eligibility views; automated outreach tests | Controls exercised. No actual browser-delivered check-in or complete goal lifecycle established. |
| Professor insights | Actual participation, stored evidence, per-topic/signal privacy grouping | Latest local group maximum was four learners, below the required five; suppression was correct. |
| Usability | Desktop/mobile layouts, navigation, Sources/Check-ins dismissal, pending/empty/error states, console inspection | Targeted checks passed after fixes; full keyboard, 200% zoom and concurrent-session matrix remains incomplete. |
| Recovery | Metadata 503/delay, pre-API send failure, rate-limit retry, frontend restart/session persistence, populated backup restore | Local targeted checks passed. All 49 restored DB tables matched. API/host restart and historical AWS-hang resolution remain unverified. |

## Latest scenario coverage

The original catalog contains 106 scenarios and 12 connected lifecycle chapters. Run 006 assigned every scenario a status:

| Status | Cases | Meaning |
| --- | ---: | --- |
| Pass | 45 | Stated checks passed with the recorded evidence. |
| Fail | 11 | Expected behavior was not fully achieved; includes teaching failures. |
| Blocked | 44 | Prerequisite/configuration/budget prevented completion, or only part of the case was exercised. |
| Not run | 6 | Additional execution gaps. |
| **Total** | **106** | Complete status ledger, not complete execution. |

See the [case-by-case ledger and chapter exits](../tests/manual/lifecycle-local-006-coverage.md). Earlier AWS coverage remains separately recorded: 35 pass, 27 partial, 14 fail, 8 blocked and 22 not run. These are different runs and status conventions, so their counts are not a directly comparable success-rate trend. Offline run 007 did not upgrade unexecuted browser cases to passes. Run 008 adds [targeted browser coverage](../tests/manual/scenario-local-008-coverage.md), without rewriting the run 006 totals.

## Coding fixes verified

| Defect | What changed | Delivery status |
| --- | --- | --- |
| Failed model calls looked like “not called” with zero usage | Retained known failed-call usage/provenance while withholding rejected content | Initial repair deployed during AWS run 001; later accounting refinements local. |
| Professor course changed during setup/delivery navigation | Preserved the authorized selected course | Deployed during AWS run 001; later local regressions passed. |
| Autonomy Save enabled despite missing publication | Disabled invalid action and explained the existing prerequisite | Deployed during AWS run 001; gate unchanged. |
| Completed chat remained busy while evidence loaded | Released composer and cleared completed request before optional refresh | Fixed locally in run 004. |
| Saved history remained hidden during metadata failure | Displayed primary history independently; added metadata states/retries and stale-response guards | Fixed locally in run 004. |
| Random seed passwords occasionally violated password policy | Shared generation helper guarantees required character classes | Fixed locally in run 005. |
| Sources Close overlapped the account control | Adjusted desktop control spacing; browser retested | Fixed locally in run 005. |
| Long-history citation reads delayed primary browser actions | Limited optional citation reads to two concurrent requests; stopped stale queued work | Fixed locally in run 006; delayed-read sign-out retest passed. |
| Insight explanation implied total class size met privacy threshold | Explained five distinct learners per topic/signal group | Copy fixed locally in run 006; aggregation unchanged. |
| Initial provider errors lost their specific diagnostic code | Retained bounded budget/timeout/etc. code in saved traces | Fixed locally in run 007; five baseline failures reproduced, then regressions passed. |
| Pending send lost recovery state after reload | Account/conversation-scoped tab storage restores draft and original request ID for manual recovery | Fixed locally in run 008; paid browser retest passed. |
| Expired session left protected workspace stuck | Protected 401 returns to sign-in; stale earlier-session failures ignored | Fixed locally in run 008; clean browser retest and regressions passed. |

Synthetic-preview labels were also clarified. That wording does not fix course-specific preview generation or complete publication.

## What remains unresolved, and why

- **Withheld replies:** run 006 had six hash-pattern failures, four binding mismatches, three rejected repairs, one unchanged repair, one timeout and one subsequent budget rejection. Invalid output must still be withheld. Raw historical audit details are insufficient to explain every semantic rejection.
- **Repetitive teaching:** recent history passed the seven-turn transport control, but model teaching behavior remains uneven. Changing prompts, context length or teaching decisions needs separate evaluation.
- **Assessment disagrees with praise:** all 80 stored observations reproduced the current lexical rules. Those rules do not provide semantic mastery assessment; praise is not a saved score.
- **Budget stops after timeout:** unknown cost deliberately closes new admissions. Low reported spending does not override that guard.
- **Fresh publication:** the tested onboarding path uses fixed CSRF/generic prototype previews. They stayed rejected for Data Systems; no approval bypass was used.
- **Check-in delivery:** disabled worker and missing eligible policy/goals prevent the complete delivery/reply/dismiss/closure story.
- **Policy false positive:** the existing “write my” matching can refuse a permitted self-check. Changing it changes a decision rule and remains deferred.
- **AWS hang:** local citation starvation was repaired; the historical AWS incident is not proven resolved.

The [root-cause report](../research/05_evaluation/root-cause-007-results.md) explains these distinctions in detail.

## Validation limits and current readiness

Run 008 passed 116 frontend tests, 115 relevant API tests, lint and production build, retaining the existing large-bundle warning. The full `npm run check` now passes documentation-link verification but stops at a separate execution-freeze coverage issue in the two professor-evidence packaging scripts. That guard was not bypassed and downstream stages are not claimed to pass. Frozen backend/configuration controls match the final run 007 state.

Test fixtures are synthetic. Browser conversations are adaptive, correlated examples—not independent benchmark trials or proof of learning effectiveness. Some runs use real providers and others deterministic injected clients; their results must retain that distinction. No aggregate independent teaching-quality rubric pass was established.

**The local coding repairs are ready for review. Full lifecycle/demo readiness remains conditional on the failed and unverified branches above.** Later local fixes have not been deployed. AWS was left paused/untouched during local work; this document does not perform a new infrastructure status check. Run 008 performed the additional authorized local tests and paid calls described above; no AWS deployment or infrastructure operation occurred.

## Subsequent AWS deployment

The local runtime repairs through run 008 were deployed in [aws-local-fixes-009](../reports/aws-pilot/deployed-state-2026-09-10.md). Public HTTPS/authentication, professor/student course reads and unchanged runtime settings passed. This supersedes the earlier local-only delivery status for the included runtime files; it does not mean every local seed utility was deployed or that the full browser lifecycle was rerun. EC2 was then stopped and both EventBridge power schedules disabled.
