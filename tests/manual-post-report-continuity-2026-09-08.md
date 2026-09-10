# Post-report continuity and recording verification

The submitted report and final manuscript are unchanged. Work is ongoing;
this record does not declare all inventory items complete.

## Student continuity

Added authenticated GET `/api/student/courses/{course_id}/conversations`.
It returns only the student's authorized current-release history. Browser
startup discovers that history; a saved browser selection is preferred only
when still present in the authorized list. Explicit New chat creates a new
conversation. Failed discovery shows an error instead of creating a duplicate.

`uv run pytest -q tests/api/test_student_api.py`: 30 passed.
`npm run test --workspace apps/web -- --run`: 80 passed.
The new cases cover cross-student/course discovery, role and inactive-account
denials, release replacement/withdrawal, no browser storage, explicit new chat,
discovery failure and stale completion after a course switch. The saved-chat selector was verified in a fresh browser, after deleting the scoped local-storage key, and after creating a second conversation and selecting the earlier two-message conversation. Server counts confirmed no duplicate conversation on restoration.

## Professor partial failure

The 13 section reads (including observed runtime/worker status) settle independently. Successful sections remain usable;
failed section names and Retry loading are shown. Summary metrics say
Unavailable instead of zero when their read fails. Course/release transitions
clear the previous section data and invalidate outstanding reads.

On the actual synthetic UI at port 5178, Playwright injected a 503 response only
for `**/autonomy-traces`, then reloaded. The error named Activity traces while
Approved v1, Active, two active goals and 20 delivered actions remained visible.
Reviewed screenshot: `output/playwright/post-report-partial-failure.png`.
After removing the route override, Retry loading removed the error. Browser
console errors were the injected 503 responses; this is not a complete
accessibility or cross-course browser audit.

## Recording foundation

Playwright CLI and FFmpeg are installed. A second isolated runtime runs on API
8019 with actor UIs 5184–5189; the existing 8018 workspace was not restarted.
The launcher now supports explicit nonoverlapping port sets and writes a
runtime manifest. Recorder operations verify the recording-factory identity,
and browser scripting verifies an allowed local actor origin.

An in-process rehearsal with two professors and four students confirmed that
opening an empty conversation and opting in creates four goals on virtual day
1; day 2 creates four spaced-review opportunities and one real service message
per inbox. Conversation message histories stay empty: no initial student
question was submitted. Processing the same time again does not duplicate
delivery. Added this as an integration regression, separate from quality or
learning-effect evaluation.

`uv run pytest -q tests/test_recording_virtual_clock.py tests/test_validate_repository_execution_freeze.py`:
9 passed. Earlier recording fixture tests also passed. The first new video
attempt failed before capture because the CLI sandbox does not expose the URL
constructor; the origin check now uses exact origin or origin-plus-slash
matching. This failure produced no finished demo.

## Global verification status

Frontend lint and production build passed; the existing bundle-size warning
remains. Recording/presentation scripts were explicitly classified by purpose
in the execution-freeze validator; historical evaluation restrictions remain
active. Its validation passes with 201 protected/registered entrypoints and
zero missing guards.

The next `npm run check` attempt advanced past this gate, then stopped because
the versioned correctness audit's hash for `.gitignore` is stale. The audit
must reflect reviewed changes and new tooling; it has not been blindly
regenerated or declared passed. Log: `/tmp/digital-twin-post-report-check.log`.

Additional external-model evaluation budget authorized: US$30 total.
New external calls: 169; reported total US$0.1375708, zero unknown-cost calls. Both live runs require refinement and independent review. See the result registry and budget ledger.

The stale correctness hashes were reviewed and updated. A subsequent full check
found a fixed-August simulation using the real clock; its injected clock now
keeps goal creation and recovery in the intended simulated period. A regression
with a 2040 host clock passes. Full check attempt3 finished with 2,580 passed, one clock-dependent failure, and 28 deselected. The remaining fixed-August provider-integration simulation now uses its injected virtual clock; its four targeted tests pass, including a 2040 host-clock regression. A single clean full-suite rerun is not claimed. The new result records separately
pass `npm run verify:evaluation-results`.

Recording retakes preserved the earlier material-contamination finding: PDF
headers/permission notices appeared in generated outreach. Version2 fixture
PDFs separate each concept onto a text-only page and store permission metadata
in `source-permissions.json`. Actual ingestion and both recording-clock tests
pass. Current raw takes are in `output/playwright/post-report-demo-final/`;
the final 134-second 1080p edit and representative frame review are complete. The four-student overview is assembled from separate recordings on the same virtual day, followed by readable individual views. See video and scope (local presentation artifact: `../reports/presentation/recording/demo-2026-09-08.md`).

## Final mobile and verification pass

At 390 × 844, the saved conversation restored its two messages without horizontal overflow. Opening the 12-unread check-in dialog kept Tab focus inside; Escape closed it and returned focus to its trigger. The visible badge reads 9+ while the accessible label retains the exact count. Reviewed `output/playwright/post-report-continuity-mobile-final.png`. This is scoped keyboard/mobile verification, not a screen-reader or full WCAG audit.

After the final UI edits, all 80 frontend tests, lint and production build passed (`/tmp/post-report-web-latest.log`, `/tmp/post-report-lint-latest.log`, `/tmp/post-report-build-latest.log`). The existing bundle-size warning remains. The recorded takes predate the final 9+ badge wording and disclose that difference in the video manifest.
