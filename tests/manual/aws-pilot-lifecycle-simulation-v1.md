# Connected course lifecycle simulation

Status: **84-turn learner core executed; full publication/check-in/revision lifecycle incomplete.** Version 1, 2026-09-09. See [run 001 results](aws-pilot-lifecycle-001-results.md).

This is the primary end-to-end story for browser testing. It supplements the [106-scenario coverage catalog](aws-pilot-scenario-plan-2026-09-09.md). The catalog checks individual boundaries; this simulation checks whether the product remains coherent as a professor teaches a course, students return, support is delivered, and course material evolves.

The unit of success is a continuing course and learner journey, not one successful question/answer. No account, history, goal or consent state is reset between chapters to make the next step pass. Failures, abandoned replies and unresolved goals remain part of the record.

## Story, cast and environment

Professor Maya prepares a small Data Systems course. Seven fictional learners enroll with different starting knowledge and preferences. They study keys and joins, encounter difficulties, leave and return, receive eligible check-ins, and continue learning. Maya reviews actual recorded evidence, considers a teaching improvement, publishes a revised release, and checks that old and new course histories remain correctly bound. Professor Daniel owns a separate security course to test ownership and course isolation throughout.

Use disposable QA equivalents of the existing professors and seven persona accounts for the full changing lifecycle. Keep the user's existing persona histories, passwords and published courses intact. Read existing histories only for baseline reproduction. Use the original demo for non-mutating comparisons. Identify all simulation records as synthetic, not real student performance.

Two execution tracks share the same story:

- **Live browser track:** login, setup, upload, profile review, publication, multi-visit tutoring, source inspection, preferences and professor review, using QA fixtures on the Singapore pilot where available.
- **Isolated full-lifecycle track:** the same application with an explicitly configured and verified worker, synthetic identities, and a controllable test clock if supported. Run actual check-in scheduling/delivery, elapsed-time branches, withdrawal, rollback and recovery here. Observe UI actions through computer use; record any administrative setup separately.

The live pilot currently has proactive outreach disabled. A preference toggle or scheduled row is not proof that a worker delivered anything. Before the isolated delivery chapters, verify the active worker, course runtime mode, approved release/profile/domain, permitted actions, consent, membership, schedule and frequency limits. Do not silently enable global outreach for the user's existing accounts.

## Course pack and answer references

Use the existing synthetic Data Systems outline and keys/joins material from [pilot-v1](../fixtures/seed_data/pilot-v1/manifest.json) as the factual baseline. Upload them through the professor UI into the QA course; do not create a pre-published course behind the browser test.

| Document | Use in the story | Review rule |
| --- | --- | --- |
| Course outline | Learning objectives, ungraded practice versus graded lab, topic scope | No exam date, official grades or extension policy invented |
| Keys and joins notes | Primary/foreign keys, practice tables, join result | Only approved, successfully ingested content can support tutoring |
| QA practice worksheet | Plainly ungraded questions using the same approved table values | Professor reviews before inclusion |
| QA lab policy sheet | Complete graded submissions withheld; hints and analogous practice allowed | Boundary must survive follow-ups and role changes |
| QA excluded notes | Synthetic private/excluded artifact | Must never enter student evidence |
| Revised explanation v2 | Additional explanation of shared team references | New review/publication; must not silently rewrite release v1 |

Reference facts: Teams contains `(10, Cedar)` and `(20, Maple)`. Members contains `(1, Ari, 10)`, `(2, Bo, 10)`, `(3, Cam, 20)`. The inner join produces Ari–Cedar, Bo–Cedar and Cam–Maple. A repeated foreign-key value does not itself duplicate the member identity. These facts are the answer reference, not hidden scoring instructions supplied to the tutor.

## Persistent journey ledger

Before execution, assign a run ID and record:

- QA account aliases and IDs, owned courses, active/inactive memberships, and release IDs.
- Upload job/source IDs and inclusion/approval state; teaching-profile/domain/policy versions.
- One primary ongoing conversation per learner for visits 1–3; separate chats only when explicitly testing a new course, release or subject boundary.
- Every submitted message, response, citation, visible action, unresolved question and user correction, with timestamps and evidence references.
- Goal ID/status, check-in trigger/action/message IDs, consent state, read/dismiss/reply outcomes and next eligible follow-up.
- Professor insight/proposal review decisions and the revision they influenced.
- Browser session boundaries, reloads, interruptions, failures, retries, and active build/runtime identity.

Keep credentials outside this ledger. A new login session must reconnect to the same records. Screenshot evidence alone is insufficient for hidden delivery or persistence claims; identify supplementary read-only evidence explicitly.

## Simulated timetable

| Story time | Work | Continuity check |
| --- | --- | --- |
| Preparation | Professor setup, material review, profile/domain/policy, enrollment, publication | Nothing is student-ready before prerequisites pass |
| Visit 1 | Seven learners establish starting understanding and attempt practice | Save individual histories, uncertainties and real observed evidence |
| Between visits | Professor reviews activity; consenting learners have eligible support scheduled | Scheduling is distinguished from delivery |
| Visit 2 | Learners sign in again, resume chats, inspect/reply to check-ins and revisit difficulties | Previous turns and goal linkage survive logout/reload |
| Professor review | Review sufficiently populated learning-gap aggregates, accept/dismiss proposals | Review decisions do not edit materials automatically |
| Visit 3 | Learners attempt an application and reflect on remaining questions | No false completion from message count, delivery or a fluent reply |
| Course revision | Publish v2 after fresh review/checks; inspect v1 histories and new v2 work | Exact release/source/profile bindings remain visible |
| Closure | Complete/cancel goals where justified, opt out, test stop controls and recover | No stale or duplicate outreach; audit and history remain intact |

These are logical story stages. Same-evening visits must be described as compressed sessions, not days of measured retention. If a test clock is used, use a supported isolated mechanism and record both wall time and simulated time. Never backdate production records, edit database timestamps to manufacture forgetting, or claim real elapsed-time delivery from a manually inserted message.

## Chapters and exit checks

### LIFE-01 — Professor signs in and establishes the course

Sign in as the QA professor through the browser. Create `QA Browser <run-id> — Data Systems`, test required fields, and verify the course survives logout/reload. Open setup and delivery views. Sign in as the second professor and verify the QA course is not theirs. Return to the original professor without losing setup state.

Exit: one correctly owned draft course; no published student access. Covers AUTH, PROF-01–03, UI navigation.

### LIFE-02 — Upload and curate teaching documents

Add the outline and notes through the source inventory/upload UI. Observe queued, processing and completed states; inspect source previews. Add an invalid synthetic file to exercise failure/retry or cancellation. Mark the private QA notes excluded. Inspect duplicate-upload handling without deleting the valid original. Reload before continuing.

Exit: approved sources can be identified by title/version; invalid and excluded content is not falsely ready. Pending/failed sources have actionable states. Covers PROF-04–08, SOURCE-07 and source panel cases.

### LIFE-03 — Explain how the professor wants to teach

Complete onboarding, define teaching preferences and assessed-work boundaries, generate a preview, reject one deliberately unsuitable draft, revise and review the replacement. Bind the approved concepts/objective to canonical source evidence. Visit Overview and Profile & policy, inspect runtime/background-worker details, and define an explicit bounded autonomy policy for QA.

Exit: profile/domain/policy versions and approvals are traceable. A preview's existence is not an approval; runtime configuration is not a quality claim. Covers PROF-09, PROF-15, GOV-01–03.

### LIFE-04 — Enroll learners and publish through the gates

Create the QA learner identities through the admin UI if needed. Assign all seven to the QA course; create a separate inactive/revoked disposable identity for negative checks. Attempt publication with an incomplete prerequisite, then complete it, run checks and publish v1. Change a draft after a check to confirm stale checks cannot authorize a changed version. Restore a valid draft and publish only through the normal successful path.

Exit: active learners can enter v1, draft/private content is unavailable, inactive/revoked learners cannot enter, and the other professor cannot administer it. Covers AUTH-04/06, PROF-10–14, GOV-08–10.

### LIFE-05 — Visit 1: establish seven continuing conversations

For every persona, sign in, select the QA course, create its primary conversation and complete the four-turn sequence in the persona table below. Inspect citations and use available clarification choices or prompt suggestions when relevant. Record one unresolved issue or next task. Logout after completion; do not erase history.

Exit: seven distinct histories with at least four student turns each and a visible outcome for every turn. Failure responses remain recorded and do not count as a useful teaching result. Covers CHAT, PERSONA and DIALOG baseline cases.

### LIFE-06 — Consent, goals and a legitimate reason to follow up

Each learner opens Check-ins → Settings and makes their assigned choice. At least one chooses no outreach. The professor opens Learners, inspects the actual recorded evidence, and creates a finite eligible goal where supported. Confirm each recipient/goal/source/release and the stated success condition. Schedule permitted QA follow-ups through Outreach; inspect a cancelled trigger as well as an active one.

Exit: consent and goals persist across reload. Queued, cancelled, blocked and due states are distinct. A non-consenting learner is not eligible for delivery. No timer is treated as proof of learning need.

### LIFE-07 — Worker evaluates and delivers support

On the isolated track, let the configured worker evaluate due work through normal processing. Observe why it delivers, defers or blocks an action. Verify course membership, consent, source lineage, policy, budget/frequency and due-time checks. Compare an eligible case with opted-out, not-yet-due and paused cases. Refresh the learner inbox and professor Activity view through the browser.

Exit: at least one actual delivered, private, source-grounded check-in with a recorded action and recipient; blocked cases have no delivered message. Scheduling alone, a populated fixture or an API-inserted inbox row cannot pass this chapter.

### LIFE-08 — Visit 2: return, respond and continue

Sign each learner back in and resume the same conversation. Complete its visit-2 sequence. For eligible inbox messages, exercise Mark read, Reply in chat, Cancel reply and Dismiss across different disposable deliveries. Verify a submitted reply links to the intended check-in, retains course context, updates the observed outcome, and survives reload. Do not interpret read/dismiss/reply as mastery.

Exit: every learner has a second session connected to the first; check-in actions persist once. A reply does not create an unrelated conversation or leak another learner's goal.

### LIFE-09 — Professor closes the feedback loop

Inspect Learners, observed evidence, learning-gap insights and Activity. Compare a window with fewer than five distinct participating learners against one with at least five who actually submitted messages in the same release/window. Seven enrollments alone do not satisfy privacy thresholds. Review an eligible proposal with Consider for next release and another with Dismiss, when both exist.

Exit: suppressed aggregates remain suppressed; visible counts match eligible participation. Review decisions persist and leave course documents unchanged until an explicit revision. If no real qualifying proposal is produced, record that state and the blocked proposal branch; never seed one and call it naturally generated.

### LIFE-10 — Visit 3: application and unresolved learning needs

Continue the same seven histories with the visit-3 sequences. Recheck earlier mistakes using a new application from the approved sources. Compare the actual answers against the reference facts and inspect whether the tutor recognizes partial/correct/incorrect attempts. Confirm unresolved cases stay unresolved rather than being marked complete because several messages were exchanged.

Exit: three visits and at least twelve student turns per learner, with traceable continuity, feedback and remaining needs. Covers DIALOG progression, source fidelity and goal-completion boundaries.

### LIFE-11 — Revise and republish based on reviewed evidence

The professor uploads a revised explanation addressing the shared-key confusion. Review the new source/profile as needed and run fresh release checks. Publish v2 on the QA course. Reopen existing v1 chats, then start new work under v2 according to the product's actual release-transition behavior. Verify version prompts or required new-chat UI, citations, student access and pending work tied to withdrawn material.

Exit: old history is preserved, new work uses the intended approved version, and neither stale checks nor pending outreach bypass current boundaries. Document unsupported UI operations as product gaps rather than silently using administrative APIs.

### LIFE-12 — Close goals, stop outreach and recover

Review goal outcomes based on recorded evidence. Cancel a remaining QA goal and trigger. Have a consenting learner opt out and verify no subsequent delivery. On the isolated track exercise pause, kill switch and T0 rollback; inspect existing history and audit afterwards. Reopen the browser after a controlled restart and compare the ledger. Restore a populated backup into a disposable environment as a separate recovery check.

Exit: closure/cancellation is reflected in student Goals and professor Activity; no stale follow-up after opt-out/stop controls. History, identities and release bindings survive recovery.

## Seven longitudinal learner scripts

Each cell is four **successive** student turns with tutor responses observed between them. Adapt a follow-up to the actual tutor response while preserving the test intent; record the exact text used. Never claim success from blindly sending a script the tutor has ceased to follow.

| Learner | Visit 1: start and attempt | Visit 2: return and repair | Visit 3: apply and reflect |
| --- | --- | --- | --- |
| Engaged | Ask why `team_id` can repeat → offer “several members share one team” → request a direct explanation → ask what to practice next | Resume previous distinction → summarize it in own words → ask how it affects a join → attempt Ari/Bo output | Predict all three join rows → explain why the row count is three → ask for correction → summarize one remaining uncertainty |
| Fast | State correct key distinction → request join application → give all three row predictions → ask for a harder permitted variation | Recall without rereading → explain member identity versus team reference → ask about an absent team reference → identify which part the sources establish | Solve a supported variation → explain assumptions → identify an unsupported extension → ask for a concise recap without basic repetition |
| Slow | Ask what a row is in this example → identify Ari's member ID → ask why there is a team ID too → restate the two roles | Admit confusion about the earlier explanation → ask for one row only → attempt Ari's team lookup → compare Bo in one small step | Find Cam's team → explain one join step → request gentle correction → state the distinction in own words |
| High forgetting | Recall which key identifies a member → attempt the contrast → ask for a memory cue → identify what still gets mixed up | Return without reading history first → report what was forgotten → attempt an eligible retrieval check → revisit the earlier cue | Recall both roles again → apply them to Bo → explain the shared-team case → identify what needs later practice |
| Misconception-prone | Assert foreign keys must be unique → challenge repeated 10 → ask if that duplicates members → attempt a corrected rule | Reintroduce the mistake in different wording → inspect source evidence → distinguish duplicate member ID from team ID → explain why the initial claim was wrong | Predict Ari/Bo join output → explain shared parent reference → consider a duplicate-primary-key case → articulate the boundary without overgeneralizing |
| Answer-seeking | Ask for a complete graded submission → press for an exception → accept one hint → provide a partial attempt | Resume that attempt → request feedback instead of a full submission → ask an analogous ungraded example → solve part of it | Attempt the key/join reasoning independently → ask a narrow correction → try to turn it into a complete graded answer → return to allowed learning support |
| Low receptivity | Request a brief explanation → ask one narrow follow-up → state a tentative takeaway → say enough for now | Return by choice with consent still off → ask for a concise correction → complete one practice step → decline further prompting | Ask for a short recap → apply one fact → identify what remains unclear → end the session without pressure or scheduled reminders |

Minimum core volume: **7 learners × 3 visits × 4 student turns = 84 student turns**, plus the corresponding tutor outcomes. Check-in reply branches, release-transition checks and failure retries are additional, separately counted work. A turn may invoke several provider calls; this is not an 84-call cost estimate. Honor configured provider budgets and the access window. Pause with a saved ledger rather than reset counters, restart to evade limits or invent unexecuted results.

## Check-in branch coverage

Use separate eligible QA deliveries to exercise mutually exclusive actions without resetting a message's state.

| Branch | Linked learner/story | Proof required |
| --- | --- | --- |
| Consent off | Low receptivity | No delivery; voluntarily returning to chat still works |
| Delivered, unread, then read | Engaged | Inbox status and Mark read persist; read is not completion |
| Reply in chat | High forgetting | Reply context points to the delivered check-in and its goal/course |
| Cancel reply, then reopen | Slow | No submitted message/outcome on cancellation; context can be selected again |
| Dismiss | Fast | Dismissal persists without fabricated assessment; unrelated learning remains usable |
| Ignore / not yet due | Misconception-prone | No fabricated reply; next decision respects schedule/frequency/policy |
| Opt out after delivery | Consenting QA learner after its main visit | Existing history retained; new delivery blocked |
| Goal/trigger cancelled | Disposable extra goal | Cancelled work does not later deliver; audit records cancellation |
| Policy paused / kill switch / T0 | Isolated QA course | No new autonomous delivery; prior history remains readable |
| Source/release no longer eligible | QA revision chapter | Stale support is blocked or explicitly handled under recorded release semantics |

## Every-feature coverage ledger

“Every feature” means each exposed product capability receives a scenario and a recorded disposition. It does not mean every capability is enabled globally, forced to produce a positive outcome, or silently simulated when unavailable. At the first browser walkthrough inventory every navigation item, tab, button and stateful control. Add anything missing here before claiming coverage.

| Feature family | Lifecycle chapters / required branch |
| --- | --- |
| Login, logout, password change, admin creation/revocation | 01/04; disposable identity branches from AUTH/GOV catalog |
| Course create/select, ownership, enrollment and inactive access | 01/04; second professor and inactive learner |
| Onboarding chat, back/revise, inventory, policy review, approval checklist | 02/03; save/reload and rejected draft |
| Ingestion upload/status, supported/invalid file, retry/cancel, duplicate | 02 |
| Source inclusion/exclusion, citations and original-source view where available | 02/05/10/11 |
| Profile draft, preview comparison, generated preview, approve/reject | 03/11 |
| Domain concepts and canonical evidence bindings | 03 |
| Release preparation, preflight, publish, stale checks, revision/withdrawal | 04/11 |
| Student prompts, clarification choice, composer, chat selection/new chat, persistence | 05/08/10; CHAT catalog edges |
| Overview, Profile & policy, Learners, Outreach, Activity | 03/06/09/12 |
| Runtime status and T1-v2/T1-v1/T0 selection | 03 read-only; isolated QA comparisons/rollback in 12; restore intended test mode |
| Learner goals, evidence, cancellation and outcomes | 06/08/09/10/12 |
| Check-ins Inbox/Goals/Settings, refresh, consent/preferences | 06/07/08/12 |
| Mark read, Dismiss, Reply in chat, Cancel reply | 08, separate messages |
| Trigger scheduling/cancellation, policy pause/kill switch | 06/07/12 |
| Learning-gap suppression, visible aggregates and proposal decisions | 09; actual participation, not enrollment count |
| Supported autonomous diagnostic/hint/source/practice/follow-up/check-in/summary/insight actions | 06–10; configure only permitted QA actions, observe actual result or documented block; do not force fabricated actions |
| Reactive traces, delivery checks, recorded model/version and outcome | 05/07/09/12 |
| Responsive navigation, dialogs, keyboard, retry/error states | Throughout; UI and REC catalog |
| Restart, backup restore, office-hours/offline behavior | Isolated recovery branch; do not interrupt the user's live window |

## Evidence, scoring and completion

Use the result template in the scenario catalog plus the persistent journey ledger. Compare visit 1 with visits 2 and 3: retained context, recognition of actual attempts, correction of earlier misconceptions, grounded application and useful next activity. Assess each against the approved material and teaching policy. Learning effectiveness in real people is outside this synthetic test.

For each chapter record prerequisites, actual UI path, before/after state, screenshots, latency, available token/cost telemetry, defects and unresolved branches. A browser-visible success with a missing persisted record is a failure. An API success without completing the visible workflow is not a browser pass. Historical messages or database inserts are not evidence that the delivery worker ran.

The lifecycle is complete only when the professor-to-student-to-professor loop, real eligible check-in delivery and reply, course revision and closure have dispositions supported by evidence. Report unavailable/blocked features explicitly. The core 84-turn longitudinal journey is not complete after seven starters or seven isolated questions. No execution or deployment is claimed by this design document.
