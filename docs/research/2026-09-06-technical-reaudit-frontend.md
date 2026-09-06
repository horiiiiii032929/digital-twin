# Frontend technical re-audit — 6 September 2026

Scope: `apps/web` state transitions, API binding, authentication mutation admission, student course/outreach lifecycle, professor governance/profile preview lifecycle, and build configuration. Existing dirty G2/G3 work was preserved. No model/provider calls, real data, deployments, or backend changes were made in this audit.

## Findings and fixes

1. **Delayed student outreach writes crossed course boundaries.** An opt-in request started for course A could finish after selecting B and overwrite B's displayed preference. Old preferences also remained visible while B loaded. Reproduced both defects with deferred promises before changes: two tests failed, each observing `true` where B's disabled/default preference must be `false`. Course-scoped generations now invalidate old mutation/poll completions and clear prior course outreach on selection. Snooze, read, dismiss, and error paths use the same guard. A newer saved preference/read/dismiss also invalidates an older poll so it cannot undo the visible change. Starting another conversation in the same course retains course preferences.
2. **Course access removal left optional student state live.** Empty course reload now clears learner evidence, clarification, draft/request references, and loading state; it invalidates outreach requests so late results cannot repopulate the withdrawn workspace. Conversation restoration now checks request generation before stale-reference repair or new conversation creation. Optional learner-evidence fetch after message completion checks the same generation before applying or clearing a newer draft.
3. **Professor governance state persisted across course/release changes.** The same panel instance previously retained profiles, policy, learner traces and actions until the next refresh completed; its generated-preview child could temporarily receive the new course with an old profile. The panel is now keyed to course and release. Its approved-profile callback includes course identity, and the parent rejects a completion for a different selected course. Student/professor app instances are also keyed to authenticated account identity. Server authorization remains authoritative; this fix prevents misleading stale UI and wrong-scope requests, not an asserted backend authorization bypass.
4. **Authentication mutations admitted repeated events before repaint.** `submitting` disabled controls only after React rendered. Two synchronous submit events could start two credential requests; password/logout could similarly overlap. A shared synchronous ref admits one mutation until its promise settles, including failure cleanup. Existing error and logout semantics are retained.

## Verification

`npm run test --workspace=web -- --run`: **15 files / 71 tests passed**, including seven new deferred-request tests:

- delayed A opt-in cannot change B;
- old outreach is cleared while B is loading;
- delayed A snooze error cannot affect B;
- old poll cannot undo a newer opt-in;
- pending outreach cannot repopulate a workspace after all course access disappears;
- only one credential mutation is admitted before repaint;
- a failed login releases admission for retry.

`npm run lint --workspace=web`: passed without warnings after cleanup.

`npm run build --workspace=web`: passed TypeScript and Vite production build. Existing aggregate-JS chunk warning (>500 kB minified, approximately151 kB gzip) remains a performance observation, not a correctness failure. No dependency or bundling changes were justified by this audit.

Raw local check logs: `/tmp/frontend-reaudit-tests.log`, `/tmp/frontend-reaudit-lint.log`, `/tmp/frontend-reaudit-build.log`.

## Method and limits

The new tests execute actual hook functions and their asynchronous callbacks using a small deterministic hook adapter with state/ref slots, dependency-aware callbacks/effects, and deferred API promises. They are Node regression tests, not React DOM/browser scheduling tests. The professor key/callback change was inspected and type/build-checked; it was not separately browser-replayed during this audit. The earlier G2 live-browser evidence predates these fixes and is not relabeled as their verification.

Reviewed session-mode client headers and existing Vite `build-configuration.json` marker. The frontend still intentionally supports demo and session modes; this audit does not claim demo mode is production authentication. Session enforcement remains the backend's responsibility. No exhaustive absence-of-bugs claim, real-user concurrency test, cross-tab authentication synchronization test, or visual redesign is implied.
