# Live virtual-time demo production

The current video records the actual product UI against one isolated runtime,
with two professors, two courses and four students. It supersedes the explanatory
replay preview as the presentation demo direction.

## Runtime boundary

`uv run python -m scripts.start_recording_workspace` launches the six actor origins
and one loopback API. The recording factory explicitly selects existing T1-v2.1,
the deterministic generator/planner and v3 evidence gate. It is a synthetic
recording configuration, not a replacement of the selected release profile or
a repetition of the historical provider-backed 30-day run. No hosted model calls
are required.

A temporary SQLite database is shared by tutoring and autonomous services.
`/__recording/advance` advances the injected UTC clock one day at a time, calls
`observe_events`, and calls `process_due`. It never inserts messages or
opportunities. `days: 0` sweeps the current instant; advancing beyond Day 30 is
refused. Controls exist only in the recording factory and require a loopback
client plus the `X-Recording-Control: local-synthetic-only` header. This header
is a local control marker, not production authentication.

The controlled inputs are synthetic student text, professor policy/consent
actions and virtual elapsed time. The goals, opportunities, selected actions,
messages and response results are produced by existing product services.

## Capture and provenance

Playwright CLI records only browser content at 1600 × 900. No desktop, browser
chrome, notifications or microphone are captured. Raw clips, snapshots and daily
service logs live under `output/playwright/autonomous-film/`. `lineage.json`
links the two recorded onboarding sessions to their actual published releases.

Both onboarding interviews, PDF uploads and publish clicks were performed in
the UI. Repetitive review approvals, teaching profiles, memberships and approved
course domain models were prepared through the same runtime APIs/services off
camera. PDF ingestion also occurred while preparing checked drafts; the filmed
upload repeats the identical bytes. It is an edited walkthrough, not an uncut
record of every setup operation. No prior-run footage is used.

`record_autonomous_film.py` provides the CLI capture and clock helpers.
`edit_autonomous_film.py` reads the raw directory's edit plan, compresses waits
and burns English subtitles into browser footage. It adds no explanatory slides,
simulated product screens, replacement message text or fabricated outcomes.

## Review findings and correction

The original Check-ins layout reserved most height for preference, goals and
learning evidence, leaving a very small independently scrolling inbox. The
student component now scrolls the entire panel, allowing the delivered message
and Reply in chat control to be visible together. Product data and behavior
are unchanged. Browser plugin not available; existing Playwright CLI was used
for visual checks.

The deterministic baseline can ask for clarification between a text block and
a PDF diagram region. Autonomous messages can quote the whole synthetic page,
including fixture labels. These are actual limitations, not removed or rewritten
for the demo. Do not imply personalized learning effectiveness.

## Verification

- Recording integration checks cover observer-created goals, next-day delivery,
  professor pause, retry without extra delivery, and the 30-day bound.
- Frontend: 71 tests passed, lint passed and production build passed. The build
  retains its existing large-chunk advisory.
- Final media and screenshot review results are appended after editing.

## Completed video and review

Final file: `reports/generated/autonomous-film/digital-twin-30-day-demo.mp4`.
4:06, 1920 × 1080, 30 fps, H.264; silent with burned-in English subtitles.
The edit plan, resolved source trims, provenance hashes and review results remain
with the raw/generated artifacts. No explanatory slides are included.

All 29 chapter sample frames were inspected, including the readable delivery
frame at full resolution. The complete MP4 decoded without an error. No unrelated
apps, desktop content or browser chrome appear. Two early clips retain the old
Check-ins layout before its scroll correction; subsequent message reading,
reply and B1's automatic arrival use the corrected product panel.

Actual runtime checks: Day 2 A1/A2 each had one message while paused B1/B2 had
none; Day 3 B1/B2 each had one after reactivation. A1 stayed at four messages
from Day 10 through Day 19 while opted out. Day 30 inbox counts were A1=8,
A2=12, B1=12, B2=12. Message IDs were unique and all messages remained in their
correct course. These counts describe this synthetic operating scenario only.

Panel QA flow: student route → Check-ins → scroll to complete message → Reply in
chat → response draft visible. Passed at desktop 1600 × 900 and mobile 390 × 844;
mobile document width equalled viewport width, with the Reply control in bounds.
Page identity and meaningful content passed; no framework overlay was observed;
final UI console check returned zero errors/warnings. Mobile screenshot evidence
is local under `/tmp/recording-checkins-mobile.png`, desktop under
`/tmp/recording-checkins-desktop.png`. Other browsers were not tested.

The recording workspace remains available with its clock at Day 30. It does not
advance or initiate additional work without an explicit local clock-control call.
