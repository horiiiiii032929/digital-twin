# Student check-ins: first post-report UI improvements

Date: 2026-09-08. This is a frontend change and verification record, not a new model-quality evaluation or release qualification. Submitted report files and manuscript remain unchanged.

## Change and scope

The student can now open unread check-ins directly from the course screen. The panel opens on Inbox; Goals and Settings have separate navigation. All active goals are displayed, with past goals in a separate expandable list. The displayed active count and list use the same status selection, replacing the first-three-records view that hid the active goal behind expired/cancelled goals.

Reply in chat preserves the original message and its source labels beside the composer. It focuses the reply field and preserves an existing draft. Cancel reply removes the association without deleting the draft. A failed send retains both context and the idempotency key; selecting a different reply or cancelling starts a new request association. Course changes clear the context, and a send in progress prevents reply switching/cancellation. The server remains authoritative for recipient, course, release and delivery permissions; no transport or tutoring algorithm changed.

The welcome screen now explains questions and check-ins, and its empty conversation scrolls from the top rather than being forced to the bottom of a chat log. Settings errors remain visible regardless of the selected panel section. Switching sections returns to the panel top.

Professor activity distinguishes no recorded checks from passed checks, names checks that did not pass, and labels next-wake timestamps as historical values recorded with an action. The hard-coded R1.2 and A0/A2 assertions were removed from the changed panel. A returned course override shows its version/mode; a null override is distinguished from data not yet loaded. This endpoint does not expose the effective server/worker candidate, so F02's full configuration reconciliation remains open.

## Sources changed

- [Student workspace](../apps/web/src/components/student/student-workspace.tsx)
- [Student state and reply handling](../apps/web/src/hooks/use-student-workspace.ts)
- [Reply and isolation regression tests](../apps/web/src/hooks/use-student-workspace.test.ts)
- [Professor activity and configuration display](../apps/web/src/components/professor/professor-autonomy-panel.tsx)

The pre-existing scrollability edit in the student panel was preserved. Six broken links in two generated presentation Markdown copies were also corrected when the standard documentation check exposed them. No slide narrative, submitted result, selected evaluation profile, API or worker was changed.

## Environment and interaction checks

CUA in-app browser, existing synthetic recording environment. Student URL: `http://127.0.0.1:5180/student`; professor URL: `http://127.0.0.1:5178/professor/delivery`. Actual observed student viewports: 390×844, 721×863 and 1280×720. Professor: 1280×720. Temporary viewport override was reset. Requested override sizes are not substituted for measured dimensions.

The browser used synthetic accounts and pre-existing messages; no message was submitted, consent changed, material uploaded or external model called during this UI check. Opening a course can create an empty synthetic conversation under existing behavior.

1. Open the student course and use the new unread-check-in button: Inbox opens first, with received messages.
2. Select Goals: the one active goal is visible; three past goals are collapsed separately.
3. Open Settings: consent and pause controls remain reachable. No setting was changed.
4. Select a check-in's Reply in chat: the original text and source labels remain visible; the active element is the reply textarea.
5. Cancel reply: the association disappears and focus remains in the normal question textarea.
6. Inspect mobile and desktop layout: initial heading is readable from the top; original long message scrolls within its reply context; the composer remains visible.
7. Open professor Activity: no-check rows say “No delivery checks recorded”; the 17/18 row names its failed check; the loaded null override is not presented as R1.2 qualification.

| Check | Outcome and limit |
| --- | --- |
| Page identity | Student Tutor / Course Delivery titles and requested local routes matched |
| Meaningful content | Course, inbox, active goal, source labels and professor activity rendered |
| Framework error overlay | No Vite error overlay in the inspected final states |
| Width | At measured 390px and 1280px, document width equalled viewport width |
| Focus and interaction | Reply moves focus to its textarea; cancellation and section navigation work |
| Screenshot inspection | Saved student desktop/mobile, active-goal and professor activity images inspected |
| Browser console | Console logs were not collected; absence of an overlay is not proof of an empty console |
| Live send and backend recovery | Not performed in browser; reply lineage/retry behavior tested through mocked API contracts |
| Accessibility | Limited focus/layout checks only; no full screen-reader, zoom or accessibility conformance audit |

Local screenshots and before-change source hashes are under `/tmp/digital-twin-ui-20260908/`. Accepted images include `start-desktop.png`, `reply-mobile.png`, `goals-desktop.png`, and `professor-activity.png`. These are local QA artifacts, not committed research evidence. The images retain the recording fixture's verbose generated message; no successful tutor response was fabricated for presentation.

## Automated checks and failures retained

- Frontend suite: **77 tests passed**, including six new reply-context cases (success; failed-send retry; cancellation; same-text reply switching; in-flight lock; course isolation/unknown ID).
- Frontend lint and TypeScript/Vite build passed. The existing >500kB chunk warning remains; no build failure is inferred from it.
- `git diff --check` passed. Submitted abstract, report and source archive match `submission-sha256.json`; no tracked manuscript/submission changes were observed.
- An initial build found a missing `runtimeProfile` prop in the overview component. The prop was connected and subsequent builds passed.
- First `npm run check` stopped on six broken local links in existing generated presentation documents. Those links were corrected.
- Second `npm run check` passed the documentation/report-link and preceding checks, then stopped at `verify:repository-execution-freeze`. It reports missing guards on 18 pre-existing, untracked presentation/recording utilities, including `scripts/build_recording_demo.py`, `scripts/record_autonomous_film.py` and diagram builders. This work does not remove or weaken that guard. Later stages of the full check, including the Python suite, were not executed by that invocation. **The full repository check is not green.**

Commands: `npm run test:web`, `npm run lint:web`, `npm run build:web`, `npm run check`, `git diff --check`. Local logs: `npm-check.log`, `npm-check-2.log`, `build-final.log` in the same temporary directory.

## Follow-up

This closes the first UI implementation batch, not the [41-item development inventory](../docs/post-report-development-inventory-2026-09-08-ja.md). U01/U02/U03 have implementation and scoped verification; U04/U05/F02 are improved only in the described areas. Full configuration provenance, cross-browser conversation resumption, semantic assessment, useful proactive targeting, source-specific teaching quality, same-composition qualification and the existing execution-guard integration remain separate work.
