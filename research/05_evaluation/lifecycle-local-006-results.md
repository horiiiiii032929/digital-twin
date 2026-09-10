# Lifecycle local 006: browser walkthrough and bounded frontend repairs

Decision: **Keep two reproduced frontend repairs locally; Refine demo readiness. The complete professor-to-check-in lifecycle is not verified.** No deployment, AWS change, evaluation-method change or selected component replacement was made in this run.

The browser run completed 80 of 84 planned continuing student turns. Six personas completed three visits of four turns; low-receptivity completed two. Sixteen replies were withheld by the existing pipeline, including an audit timeout and a subsequent accounting-guard rejection. The fresh professor course could not reach approved publication without accepting unsuitable prototype previews; it was left unpublished. Proactive delivery remains disabled by the preserved configuration. These are unresolved limits, not fixes achieved through wording changes.

See the [prospective plan](../04_experiments/2026-09-10-lifecycle-local-006-plan.md), [all 106 case dispositions and 12 chapter exits](../../tests/manual/lifecycle-local-006-coverage.md), and [machine record with paired prompts, replies, traces and runtime identity](records/lifecycle-local-006.json). Previous runs and failures remain intact.

## Identity, permissions and comparison boundary

Run date: September 10, 2026, Asia/Singapore. Revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty workspace with substantial preexisting work. Browser: IAB through computer use, local Vite at `http://localhost:5174`, staging API at `127.0.0.1:8000`, desktop 1440×900 and mobile 390×844. Local requests use the test Origin `https://local.example.test`. The database, credentials, uploads, sessions and failures belong to an isolated synthetic fixture under ignored `output/browser-qa/lifecycle-local-006/`.

The latest authoritative 70-slide deck is identified by SHA-256 `7453cff7de77b597a61abc39766e3cb948ab2f0b3083d9b835a2a91dcb6f6d76`; follow the [slide compatibility plan](../04_experiments/2026-09-09-slide-aligned-code-fix-plan.md). The selected [AWS presentation profile](profiles/aws-presentation-demo-v1.json), CDK runtime environment and running API identity were compared before exercising the app:

- Route `audited-presentation-v1`; candidate `v19-luna-luna-medium`; implementation `question-specific-profile-grounded-v19`.
- GPT-5.6 Luna low planner/draft, medium revision/final audit; 3000 output caps and existing audit/repair limits.
- Server mode `governed-autonomous-tutoring-graph-v2.1`; evidence gate `dominance-scoped-ambiguity-safe-v3`; `learning_configuration: null`.
- Proactive worker disabled. Provider process limits retained: 250 calls, USD 5, concurrency 5. No reset was used to evade the exhausted/failed accounting guard.
- All 328 previously frozen decision/evaluation files matched their control hashes after these repairs. Evidence: `frozen-comparison.json`. Frontend change hashes are in the machine record.

This matches the selected deployed **decision configuration**, not AWS topology, HTTPS transport, host sizing or real latency. The approved source corpus was synthetic `pilot-v1` Data Systems and Browser Security, not the private IT5004 corpus. No instructor/student private records were used. The 14 deterministic seed starter messages are excluded from the 80 new browser turns. Provider-backed generation occurred and reported usage is below; this must not be described as an offline-only fixture run. No AWS API was needed for this local verification.

## Reproduced coding repairs

### C007: optional citation reads occupied browser connections needed by primary actions

Severity P1, frontend integration. Reproduction: open a long saved conversation, delay evidence/citation GETs by 15 seconds in the local proxy, then sign out. Before the repair, parallel citation fetches for every tutor message occupied connections; the signed-out screen did not appear promptly. `citation-fanout-before.txt` records disabled sign-out while metadata was pending. The eventual observed completion was roughly 40.7 seconds, an observation upper bound rather than a precise network timing.

In `apps/web/src/hooks/use-student-workspace.ts`, optional history citation reads now run with at most two concurrent requests. The existing scope/read-sequence guards stop queued work after navigation. Endpoint URLs, payloads, selected-message semantics, citations and tutor decisions are unchanged. No generation retry or timeout was added.

Two regressions reproduced the defect before the patch: eight initial reads instead of two, and queued work failing to stop on navigation. Before: 2 failed / 23 passed in the hook suite (`fanout-before-test.log`). After: all frontend tests passed. The exact browser retest, with the same 15-second metadata delay and fresh course reentry, reached signed-out login in about 1.1 seconds observed (`citation-fanout-after.json`). Original and retest evidence are retained. This supports the local connection-starvation fix; it does **not** establish the cause or resolution of the historical AWS hang.

### C008: suppressed-insight explanation implied total course size was sufficient

Severity P2, presentation copy. After seven actual learners participated, professor view still showed no qualifying insight, while its text referred only to “small cohorts.” Backend inspection confirmed the unchanged threshold is five distinct learners **within each topic and signal-type group**, not five course participants overall.

The professor panel now explains that grouping explicitly. The rendered before/after snapshots are `professor-cohort-after-80.txt` and `cohort-copy-after.txt`. No aggregation, privacy threshold, proposal eligibility or learner decision changed. Absence of a qualifying proposal remains a real scenario blocker.

Earlier composer/history metadata repairs, course-selection behavior, unpublished-autonomy gate, source-dialog control repair, seed-password repair and failure accounting/diagnostics remain in place. This run does not take credit for preexisting modifications as new fixes.

## What the browser actually exercised

Maya created an owned QA Data Systems course, including required-field validation. Through real browser uploads and a real local ingestion worker, the run exercised cancellation, successful Markdown ingestion, an explicit duplicate upload, empty/invalid file rejection, and a header-valid malformed PDF that failed parsing and failed again after manual Retry. Excluded private source metadata persisted after reload. Failed parsing is expected for that malformed fixture, not a newly discovered parser defect.

The professor completed five interview answers, edited source-boundary policy, rejected the irrelevant fixed CSRF preview and generic custom preview, reviewed profile expectations, and marked the profile not ready. Missing approvals blocked release preparation. The actual generated teaching-preview control remained disabled by prerequisites. No unsuitable preview was accepted to manufacture successful publication. Enrollment of Alex was repeated without duplicate membership; the unpublished course remained unavailable to that student. Daniel saw only his owned course. Learners, Outreach, Activity, evidence and runtime details were inspected.

The continuing learner journeys used explicitly identified **seeded published controls**, not the new uploaded QA course. They covered key distinctions, join applications, recall, misconceptions, graded-work refusal followed by permitted hints, requests for concise/direct explanations and stop requests. Each persona returned to the same saved conversation; failure turns remained visible. Sources/evidence were inspected against the synthetic notes. Consent, pause/resume, empty inbox/goals and a separate opted-out learner were checked. No fabricated delivery or mastery was inferred.

Authentication checks included revoked and inactive fixtures, role replacement, student entry at the professor route, sign-out/Back/reload, disposable admin-created student, duplicate email rejection, and the login throttle: the eleventh bad attempt returned a rate-limit message and later correct sign-in recovered. The professor authenticated-request rate limit also appeared during rapid navigation; partial data errors were named and manual Retry recovered (`professor-rate-limit-retry.txt`).

Local fault middleware returned independent metadata 503s, partial citation/evidence recovery and delayed reads. Saved history remained visible. Two pre-API failed send attempts retained the draft and identical request ID; neither forwarded a tutoring request. The local frontend was restarted and the server session/history survived. Mobile and desktop chat/professor controls were inspected; Sources and Check-ins were dismissible. Complete keyboard, zoom, independent concurrent-session and in-flight API-restart branches are not claimed.

A populated runtime backup was restored into a disposable data root. Read-only comparison found all 49 database tables equal, including 174 messages and 17 credential identities. This is supplementary utility evidence, not a browser lifecycle pass. Initial restore used a target outside its allowed data root and correctly rejected it; the corrected harness path succeeded. Other harness failures retained in ignored logs include an initial worker Origin mismatch and an incorrect local upload path; these were corrected before valid product observations and are not classified as application defects.

## Outcomes and measurements

| Measure | Observed result |
| --- | --- |
| Planned/actual continuing turns | 84 / 80; remaining four blocked |
| New student messages / linked responses | 80 / 80, unique client IDs and one response parent each |
| Answer / question / graded-work redirect | 54 / 8 / 2 |
| Safe withheld replies | 16 / 80 (20% of this selected scenario sample) |
| Complete three-visit personas | 6 of 7; seventh has two visits |
| Scenario dispositions | 45 Pass, 11 Fail, 44 Blocked (including partial), 6 Not run; 106 total |
| New successful browser publication / actual proactive delivery | 0 / 0 |
| Provider calls | 198 of 250; 191 completed, 7 failed; peak concurrency 1 |
| Reported provider tokens | 430,568 input + 103,792 output = 534,360 |
| Reported provider cost | USD 0.210664; one unknown-cost call, not a complete bill |
| Provider-call latency | p50 4,948 ms; p95 12,274 ms; excludes browser and multi-call turn overhead |
| Stored turn-trace latency | median 10,938 ms; nearest-rank p95 30,307 ms; 5 above 30 s, maximum 46,733 ms |

The 16 withheld turns were 2, 5, 10, 11, 20, 33, 42, 49, 58, 60, 62, 66, 70, 78, 79 and 80. Trace diagnostics distinguish six provider schema/hash-pattern failures, four audit binding mismatches, three rejected repairs, one unchanged repair, one timeout and one subsequent guard rejection. Those categories describe retained diagnostics, not proof that every underlying defect is algorithmic or coding-only.

Turn 79's audit request timed out. The accounting state then recorded one unknown-cost call and `cost_reporting_failed: true`, with USD 0.0066634 uncertain reservation. Turn 80 saved a safe failure without another provider call. Further provider scenarios stopped; 52 nominal calls remaining do not override the failed cost-reporting guard. Changing that guard, increasing limits or resetting the process to keep testing would change the agreed execution boundary.

Browser snapshots include observed completion timing, but some locator waits expired despite enabled UI and therefore give upper bounds. Stored trace timing is reported separately and is not end-to-end user latency. No fabricated exact browser SLO, uncertainty interval, population failure rate, retention gain, learning-effectiveness score or historical-result update is claimed. The sample was fixed by the existing seven-persona lifecycle, interrupted at the guard; it is not random or independently blinded. The original per-turn 0–2 semantic rubric was not comprehensively rescored, so this report does not claim that teaching-quality gate passed. No dataset, split, rubric, threshold or release selection changed.

## Unresolved findings and fix boundary

| Finding | Classification / disposition |
| --- | --- |
| Ordinary valid-looking requests sometimes produce generic safe failure | Model/audit/integration diagnostics above. Withholding invalid output stays required. No validator weakening, binding bypass, prompt or repair-limit change in this patch. Root-cause proposals need separate reproduction/control work. |
| Repeated basic questions after a correct attempt; occasional source label such as S1 in prose | Model/pedagogy presentation behavior; preserved. Conversation praise is not persisted assessment. |
| Seven participants but no actionable group insight | Existing per-topic/per-signal privacy and eligibility design. Only explanatory copy repaired; no proposal fabricated. |
| Fast learner's many observations but no assessed evidence/active goal | Existing runtime learning configuration and evidence rules; preserved, not treated as a frontend scoring bug. |
| Fixed CSRF and generic custom previews unsuitable for this course | Synthetic prototype path remains unsuitable for positive approval; labels do not repair preview content or establish current generated-preview success. |
| No delivered check-in / no publish-to-delivery chain | Preserved worker/policy/publication prerequisites. Browser delivery, read/reply/dismiss and closure remain blocked. |
| Provider timeout leads to fail-closed accounting guard | Operational/accounting boundary retained. No budget reset, changed timeout or retry policy. |
| Course draft discarded on switch; reload selects initial professor course | Observed navigation behavior, not changed in this batch; no misdirected write observed. |
| Historical AWS hang | Not reproduced on AWS and not declared solved. Local metadata starvation was independently reproduced and fixed. |

The “write my” false-positive policy boundary and other earlier decision findings remain documented in previous reports. Dedicated private-record, injection, cross-course query and several exact historical wording scenarios were not rerun before the guard. Absence of an observed leak in the inputs actually executed is not coverage of those unexecuted cases.

## Verification and delivery

- Frontend after repair: **100 tests passed**, 18 files (`frontend-after-fanout.log`).
- API/services/seed regressions: **330 passed**, 6 warnings (`api-services-tests.log`).
- Relevant autonomy/checkpoint/audit/accounting regressions: **130 passed**, 5 warnings (`domain-accounting-tests.log`).
- Frontend lint and production build passed. Existing approximately 549 kB bundle warning remains.
- `npm run check` passed its infrastructure stage, then stopped at `check:docs` because two existing absolute Desktop links in `docs/final-report-vs-latest-slides-2026-09-09.md` were reported broken. This is separate from the focused passing checks; the full repository command did not pass.
- Frozen comparison: 328 files unchanged. No backend API, persisted schema, migration, deployment, algorithm, model role, prompt, metric or publication permission changed for these two repairs.

Browser evidence and sensitive fixture credentials remain ignored; durable machine evidence contains synthetic test interactions only. Local services are stopped at delivery and the browser is signed out. AWS was left untouched. Deployment readiness remains conditional on the explicitly failed/blocked scenarios; this run is not a claim of zero bugs or full lifecycle coverage.
