# Completion browser verification

## Scope

Verified on 2026-09-06 using the Playwright CLI and Chromium against isolated
local API (8016) and Vite (5174) processes. Existing Docker services were not
changed. The isolated factory used synthetic fixtures, SQLite and deterministic
tutoring; this is not browser qualification of the live-model candidate.

## Observed journeys

- Opened the professor workspace and course delivery screen.
- Uploaded a synthetic UTF-8 forum example with explicit permission and
  de-identification attestation. The UI reported successful processing and one
  evidence chunk. No private instructor or student material was used.
- Created six synthetic student histories through the API. The instructor
  Learners view showed six distinct active learners and twelve no-evidence
  signals for the selected release, with the reporting window and population
  definition. It did not label the count as course enrollment or mastery.
- Selected **Consider for next release**. The page confirmed the recorded review
  without modifying course material. After browser reload and selecting the
  same course again, the recorded decision remained visible.
- Inspected the 390 × 844 mobile layout and review outcome. Document width was
  390 pixels, matching the viewport; no horizontal document overflow.
- Browser console inspection reported zero errors and zero warnings.

The review also identified and fixed two status defects: autonomy text could
claim activity while disabled, and an upload success notice could survive a
course switch. Final frontend tests, lint and build passed after these changes.

## Evidence and limits

Screenshots are retained locally in
`reports/generated/completion-browser-qa-20260906/`. The mobile review image was
visually inspected. No external model calls were made by this browser journey.
The run does not cover production authentication, accessibility certification,
continuous availability or live-model tutoring capacity. Reload selects the
default course; the review persistence check explicitly reselected its course.

The isolated API, Vite process and named browser session were stopped after QA.
