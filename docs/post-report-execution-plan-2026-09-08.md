# Post-report execution plan

The submitted report and final manuscript remain unchanged. This work follows
the 41-item inventory in `post-report-development-inventory-2026-09-08-ja.md`;
conditional extensions are not automatically selected for implementation.

## Execution and budget

User authorized up to US$30 total for additional external-model quality
evaluation on 2026-09-08. The first bounded live run completed at US$0.0600604 (140 calls). See the budget ledger and post-report paired-quality result; it did not justify candidate promotion. Each run must reserve a
worst-case token-cost bound before starting, accumulate actual usage, and stop
before the total would exceed this authorization. Historical results and
selected profiles remain intact. Human review is a separate outstanding input.

Work proceeds through student continuity, runtime/partial-failure visibility,
quality and learning-input comparisons, integrated recovery, recording, then
diagrams and slides. Completion is measured against the inventory conditions,
not merely the number of patches. The first UI batch is documented separately
in `../tests/manual-student-checkins-2026-09-08.md`.

## U06: prospective conversation-resume contract

Decision: can a student resume their current-release conversation when browser
storage is absent? Baseline: browser-local reference or new conversation.
Candidate: authenticated server discovery before creating a new conversation.
Keep explicit New chat as an intentional creation operation.

Only the authenticated student's conversations in an authorized course and its
current published, profile-valid release may be returned. Sort by last update,
with stable ID tie-breaking. Do not transfer old messages to a new release.
Discovery failures must be visible and must not silently create duplicate
conversations. Preserve stale-response protection on course changes.

Deterministic synthetic regression cases cover two students, cross-course
access, revoked enrollment, release replacement, empty history, resumed message
state, explicit New chat, and delayed or failed discovery. All authorization
and isolation assertions are hard gates; no provider call is necessary.
This change does not claim improved answer quality or student learning.

## Recording direction

Use real browser footage, isolated synthetic accounts and virtual dates.
Playwright supplies repeatable browser capture and FFmpeg supplies trimming,
speed changes and subtitles. Validate the existing installed versions before
using APIs. Save a scene/action manifest and inspect exported frames. Do not
replace product responses with hand-authored successful outputs.

Screen Studio and Cap are alternatives for manual editing; introducing a new
editor is justified only if it materially improves the reviewed footage.
