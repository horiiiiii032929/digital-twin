# Lifecycle local 006 scenario coverage

Run date: 2026-09-10 Singapore. See [results](../../research/05_evaluation/lifecycle-local-006-results.md) and [machine record](../../research/05_evaluation/records/lifecycle-local-006.json).

This is a complete **disposition ledger**, not complete execution or a claim that all cases pass. Original cases and earlier failures remain unchanged. Blocked includes partially exercised cases whose full exit condition was not achieved; notes identify the tested subset. Provider-dependent remaining work stopped at the preserved accounting guard. Not run means an additional gap rather than a demonstrated product blocker. Pass applies only to stated evidence; API/hook/backup checks do not become browser passes.

Local browser: IAB via computer use, localhost:5174 → local staging API:8000. Evidence filenames below are relative to ignored `output/browser-qa/lifecycle-local-006/`; sanitized 80-turn evidence is retained in the machine record. Visits were compressed sessions, not measured days of retention. Seeded published controls were used after fresh QA publication was blocked.

Counts: Blocked: 44, Fail: 11, Not run: 6, Pass: 45. Total: 106.

| Scenario | Disposition | Actual evidence / remaining gap |
| --- | --- | --- |
| AUTH-01 | Pass | Signed-out login; no protected workspace. |
| AUTH-02 | Pass | Repeated persona sign-in and reload retained identity and history; turns.json. |
| AUTH-03 | Pass | Repeated role switching; professor/student content replaced correctly. |
| AUTH-04 | Pass | Admin account-creation workspace; admin-created.txt. |
| AUTH-05 | Pass | Empty/wrong credentials rejected; malformed email prevented by native validation; malformed-login.txt. |
| AUTH-06 | Pass | Revoked Finn denied; finn-revoked.txt. |
| AUTH-07 | Pass | Back/reload after sign-out remained login; signedout-back-reload.txt. |
| AUTH-08 | Blocked | Student opening /professor retained student role (student-professor-route.txt); inverse route not separately recorded. |
| AUTH-09 | Blocked | Password-change browser control requires user handoff; no existing credential changed. API tests are supplementary. |
| AUTH-10 | Not run | Live session expiration/revocation was not injected. |
| AUTH-11 | Pass | Eleventh bad login rate-limited; correct login after window recovered; login-limit.json, login-throttle-recovered.txt. |
| AUTH-12 | Blocked | Same-browser sequential account isolation exercised; independent browser sessions not provided by this surface. |
| CHAT-01 | Pass | Data Systems/Browser Security switch gave separate histories; draft-course-switch.txt, citation-delay-after-start.txt. |
| CHAT-02 | Pass | Inactive Eli had no published course; eli-inactive.txt. |
| CHAT-03 | Pass | Fresh primary conversation; grounded turn 1; paired DB record. |
| CHAT-04 | Pass | History reopened across three visits; 80 unique requests and response parents. |
| CHAT-05 | Blocked | Seed starter and new continuing history existed; exact two-new-chat alternation sequence not completed. |
| CHAT-06 | Fail | Continuity often worked but ordinary follow-ups also withheld (e.g. turns 2,5,11); preserved model/audit behavior. |
| CHAT-07 | Blocked | Longitudinal reproduction exercised direct-answer complaints; exact original three-message chain not rerun before provider guard. |
| CHAT-08 | Pass | Whitespace-only composer did not submit. |
| CHAT-09 | Blocked | Typing and Send exercised; complete Enter/newline gesture matrix not recorded. |
| CHAT-10 | Blocked | Hook duplicate-submit regression passes and 80 unique writes; exact browser double-click test not recorded. |
| CHAT-11 | Blocked | Course controls disabled during send; late-navigation guards tested in hooks, not a completed pending browser switch. |
| CHAT-12 | Not run | No browser reload during in-flight provider generation; no equivalence claimed from saved-history reload. |
| CHAT-13 | Pass | Draft discarded on course switch and not sent elsewhere; draft-course-switch.txt. Draft loss is the observed behavior. |
| CHAT-14 | Not run | Near-limit and over-limit text cases not executed. |
| CHAT-15 | Blocked | Multiline SQL/Unicode draft retained through injected pre-API 503; successful provider round-trip for this input not run. |
| CHAT-16 | Pass | Long histories rendered at desktop/mobile with newest replies and composer reachable; desktop-chat.png, mobile-chat.png. |
| PERSONA-01 | Fail | 12 turns / 3 visits; relevant explanations plus repeated checks and withheld turns 2,5,10,11. |
| PERSONA-02 | Fail | 12 turns / 3 visits; applications grounded, source boundary explicit; turn 20 withheld. |
| PERSONA-03 | Fail | 12 turns / 3 visits; small-step help; turn 33 withheld and internal source label S1 exposed at 26. |
| PERSONA-04 | Fail | 12 turns / 3 visits; recall support and repeated checks; turn 42 withheld. |
| PERSONA-05 | Fail | 12 turns / 3 visits; corrected key misconception; withheld 49,58,60. Hypothetical Dee distinguished from actual source rows. |
| PERSONA-06 | Fail | 12 turns / 3 visits; graded-work redirects 61/71 and permitted hints resumed; ordinary and exception turns also withheld. |
| PERSONA-07 | Fail | 8 turns / 2 visits; stopped without pressure at 76, but 78–80 withheld; third visit blocked by cost-accounting guard. |
| DIALOG-01 | Blocked | Equivalent direct-answer request at turn 3 worked; exact historical wording not rerun. |
| DIALOG-02 | Blocked | Exact context-only why chain not rerun before provider guard. |
| DIALOG-03 | Blocked | Exact broad key-takeaway wording not rerun before provider guard. |
| DIALOG-04 | Blocked | Browser Security navigation only; no new generated prompt there. |
| DIALOG-05 | Blocked | HttpOnly/CSRF chain not rerun; provider guard. |
| DIALOG-06 | Blocked | Cross-course UI switch covered, explicit in-chat security topic shift not generated. |
| DIALOG-07 | Blocked | Fresh why-only prompt not generated; provider guard. |
| DIALOG-08 | Blocked | Continuing references used, exact What does that mean sequence not generated. |
| DIALOG-09 | Fail | Repeated confusion in slow/forgetting/misconception journeys sometimes caused repetitive checking or withholding; turns.json. |
| DIALOG-10 | Blocked | Correct, partial and wrong attempts appeared in continuing histories; specified separate-chat comparison not completed/scored. |
| DIALOG-11 | Blocked | Corrections appeared longitudinally, exact field-correction input not rerun. |
| DIALOG-12 | Blocked | Thanks/stop handled at 76; full hello→thanks→course sequence not completed. |
| DIALOG-13 | Blocked | No dedicated mixed-language/typo sequence in this run. |
| DIALOG-14 | Fail | Brief answer, example and recap requests used across journeys; adaptation uneven and some ordinary turns withheld. |
| DIALOG-15 | Pass | Absent-row limitations discussed at 12,19–20,23; accepted replies separated approved matching rows from unsupported extension. Turn 20 failed and remains recorded. |
| SOURCE-01 | Pass | Opened factual-response citations and evidence; engaged-sources-evidence.txt, misconception-source-inspection.txt. |
| SOURCE-02 | Pass | Sources opened/closed and selected-message inspection; mobile-sources.png. C007 delayed-read defect separately retained. |
| SOURCE-03 | Pass | Checked member/key and Ari/Bo/Cam joins against synthetic approved notes in executed journeys; not a full semantic score. |
| SOURCE-04 | Blocked | No dedicated cross-course generated question; provider guard. |
| SOURCE-05 | Blocked | Dedicated private-record request not generated; provider guard. |
| SOURCE-06 | Blocked | Dedicated prompt-injection request not generated; provider guard. |
| SOURCE-07 | Blocked | QA publication not approved; no malicious-source query bypassed the gate. |
| SOURCE-08 | Pass | Supported joins versus missing-row extension separated in accepted responses; 12,19,23. Does not erase turn 20 failure. |
| SOURCE-09 | Blocked | No successful fresh QA release to withdraw and query. |
| SOURCE-10 | Pass | Safe failure/graded redirect displayed without fabricated citations; turns 61,71,80. |
| PROF-01 | Pass | Maya and Daniel course lists distinct; daniel-isolation.txt. |
| PROF-02 | Pass | Blank rejected; one new QA course persisted; prof-empty-course.txt, prof-course-reloaded.txt. |
| PROF-03 | Blocked | Five onboarding answers/policy saved and reviewed; exact revise-answer/back/reload matrix not completed. |
| PROF-04 | Pass | Included outline and private excluded metadata persisted; source-excluded-reloaded.txt. |
| PROF-05 | Pass | Real local ingestion worker processed Markdown; uploads.txt, professor-rate-limit-retry.txt. |
| PROF-06 | Pass | Empty/invalid PDF rejected; header-only PDF failed parser honestly; QA-empty.txt, QA-invalid-PDF.txt, parser-retry-final.txt. |
| PROF-07 | Pass | Queued outline cancelled; malformed parser job retried and failed again; upload-cancelled.txt, parser-retry-start.txt. |
| PROF-08 | Pass | Explicit repeated notes upload appeared as separate successful job; QA-notes-duplicate.txt. |
| PROF-09 | Fail | Fixed CSRF and generic custom prototype previews unsuitable for Data Systems; rejected. Actual generated teaching preview disabled by prerequisites; preview-rejected-custom.txt, profile-rejected.txt. |
| PROF-10 | Pass | Publication blocked with missing approvals; approval-blocked.txt, qa-revision-blocked.txt. |
| PROF-11 | Blocked | Did not approve unsuitable previews; fresh preflight/publication never succeeded. Seeded published controls are not this test. |
| PROF-12 | Blocked | No successful fresh preflight from which to invalidate checks. |
| PROF-13 | Pass | Alex assigned twice with single visible membership; unpublished course still excluded from student; student-assigned.txt, alex-draft-excluded.txt. |
| PROF-14 | Blocked | Daniel navigation exposed only owned course; no direct copied course-specific URL tested. |
| PROF-15 | Pass | Domain/source binding controls inspected; incomplete approval disabled; qa-profile-policy.txt. |
| PROF-16 | Blocked | Fresh release unavailable; withdrawal/replacement branch not performed. |
| PROF-17 | Pass | Inspected learner traces, empty/suppressed insights and preview state. Misleading cohort copy C008 failed before and passed rendered retest; professor-cohort-after-80.txt, cohort-copy-after.txt. |
| PROF-18 | Not run | No navigation during an in-flight professor save. |
| GOV-01 | Pass | Overview/Profile & policy/Learners/Outreach/Activity visited; prof-activity.txt, prof-learners.txt, prof-outreach.txt. |
| GOV-02 | Pass | Preserved runtime proactive worker off; no delivery inferred from settings. |
| GOV-03 | Blocked | Fresh unpublished QA prerequisites prevented autonomy approval; no bypass. |
| GOV-04 | Blocked | No eligible running proactive delivery with preserved worker off. |
| GOV-05 | Pass | Check-ins Settings/Inbox/Goals visible, dismissible and empty states accurate; checkins-off.txt, goals-empty.txt. |
| GOV-06 | Pass | Engaged opt-in/pause/resume persisted; low-receptivity remained off; checkins-paused.txt, low-receptivity-consent-off.txt. |
| GOV-07 | Blocked | No actual eligible delivered check-in; worker disabled and no approved fresh policy. |
| GOV-08 | Pass | Disposable student created; empty/duplicate checks; successful student login; admin-created.txt, admin-duplicate.txt, new-student-login.txt. |
| GOV-09 | Blocked | Admin browser exposed create form but no account-list/revocation control; no API substituted. |
| GOV-10 | Pass | Student/professor workspaces lacked account administration controls; no role escalation observed. |
| UI-01 | Pass | Login/student/professor meaningful render; screenshots and snapshots. |
| UI-02 | Pass | Desktop 1440×900 and mobile 390×844 checked; mobile-chat.png, mobile-professor.png. |
| UI-03 | Pass | Mobile navigation/Sources/Check-ins opened and dismissed; Sources Escape worked. |
| UI-04 | Blocked | Labels, form input and Escape exercised; full focus-order/return audit not completed. |
| UI-05 | Blocked | Back/reload and known entries exercised; full Forward matrix not recorded. |
| UI-06 | Not run | 200% browser zoom not exercised. |
| UI-07 | Pass | Distinct metadata unavailable/updating/empty states and professor 429 recovery; prior C007 starvation failure retained with fixed retest. |
| UI-08 | Pass | Console captured; expected injected 503/auth 401/rate-limit 429 retained in browser-console.json, not called a clean console. |
| REC-01 | Blocked | Actual audit timeout/schema failures observed safely and composer recovered; full controlled provider fault-injection matrix not executed. |
| REC-02 | Blocked | Real validation failures retained diagnostics; deterministic accounting tests pass; no separate browser-injected scoring case. |
| REC-03 | Blocked | Pre-API send 503 retained draft; second in-flight disconnect branch not executed. |
| REC-04 | Blocked | Two proxy-rejected attempts reused exact request ID and no API write; uncertain server-committed retry branch covered by API regressions only. |
| REC-05 | Blocked | Independent evidence/citation errors, partial recovery and delayed fanout retested; professor partial 429 recovered. Full course/history failure matrix not browser-complete. |
| REC-06 | Not run | Vite restarted and session survived; API deliberately not restarted, preserving process budget guard. |
| REC-07 | Blocked | AWS remains paused; no host/schedule changes allowed. |
| REC-08 | Pass | Supplementary restore drill, not browser: populated backup restored to isolated root; all 49 table comparisons equal, 174 messages/17 identities; backup-verification.json. |
| REC-09 | Blocked | Independent concurrent browser sessions not available; no concurrent-draft browser claim. |
| REC-10 | Pass | After failures, sign-in/history/composer remained usable. C007 baseline starvation reproduced, then fixed delayed-read sign-out retested. |

## Connected lifecycle chapter exits

| Chapter | Disposition | Evidence / exit not achieved |
| --- | --- | --- |
| LIFE-01 | Pass | Owned QA draft course created; validation/reload and second-professor isolation checked. |
| LIFE-02 | Blocked | Real uploads, cancellation, parser failure/retry, duplicate and excluded metadata exercised. Full source preview/injection-to-query branch not completed. |
| LIFE-03 | Fail | Onboarding/profile reviewed and rejected as unsuitable; no approved replacement/domain/autonomy chain. |
| LIFE-04 | Blocked | Admin student creation, enrollment, revoked/inactive checks and negative publication gate passed; all-seven fresh enrollment and successful v1 publication not completed. |
| LIFE-05 | Fail | Seven continuing seeded-control conversations each completed visit 1, with visible withheld failures retained. This is not use of the newly uploaded QA course. |
| LIFE-06 | Blocked | Consent/pause/resume and empty goals inspected; no eligible finite goal or scheduled/cancelled delivery. |
| LIFE-07 | Blocked | Proactive worker stays disabled; zero actual deliveries. Real ingestion worker operation does not satisfy outreach. |
| LIFE-08 | Blocked | All seven second visits persisted; no real check-in to mark read/reply/cancel/dismiss. |
| LIFE-09 | Blocked | Seven actual participants, evidence/traces reviewed; no qualifying topic+signal group/proposal, so accept/dismiss untested. C008 explanation repaired only. |
| LIFE-10 | Blocked | Six third visits complete; four low-receptivity turns blocked by provider guard. No false mastery awarded from volume. |
| LIFE-11 | Blocked | Fresh v1 unavailable, so no v2 publication/version transition/withdrawal tested. |
| LIFE-12 | Blocked | Backup restore verified; browser sign-out/reload and Vite restart recovered. Goal cancellation, opt-out-after-delivery, kill switch, API/host restart not completed. |

## Earlier failures and retests

C007: delayed citation reads from a long history starved sign-out before the patch. The exact 15-second read-delay retest after limiting optional citation reads to two concurrent requests reached signed-out login after about 1.1 seconds observed. Both attempts remain in the results.

C008: seven total participants with no visible insight exposed misleading “small cohorts” wording. Rendered retest now explains that each topic/signal group requires five distinct learners. The threshold, grouping, data and outcome are unchanged.

No chapter is declared complete by substituting a synthetic seeded delivery, approval bypass, API-only operation, or changes to selected algorithms/configuration.
