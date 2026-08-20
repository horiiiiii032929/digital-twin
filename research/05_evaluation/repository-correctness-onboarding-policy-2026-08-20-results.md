# Repository correctness onboarding and policy checkpoint — 2026-08-20

Status: complete checkpoint; repository-wide correctness program remains active

## Decision

Keep the corrected professor onboarding, tutor-policy review, and course-release
handoff. Continue the repository audit before any new dataset generation,
model/provider evaluation, held-out execution, deployment qualification, or
release claim.

## Corrected findings

- Added optimistic session revisions in memory and SQLite so a stale professor
  edit cannot overwrite a newer update. Session IDs cannot be taken over by a
  different owner.
- Bound each onboarding session to exactly one professor-owned course before a
  release draft can be created.
- Required at least one approved included source, forced sensitive-looking
  sources to remain excluded, and rejected contradictory approved/unapproved
  source labels.
- Versioned behavior-affecting policy changes, regenerated previews, and
  invalidated stale preview decisions and final professor approval.
- Required every added custom preview to be accepted at the current policy
  version and made pending revision proposals explicit release blockers.
- Revoked source, policy, preview, and final-approval confirmations when their
  reviewed basis changes.
- Corrected the staging frontend to send successful server-owned ingestion job
  IDs rather than browser-returned chunk payloads. Newly discovered evidence is
  returned to professor review before a release is frozen.
- Added bounded onboarding inputs and fail-closed validation for invalid source
  metadata, policy values, and custom prompts.

## Verification

- `npm run check`: passed
- Python: 518 tests passed
- Frontend: 32 tests passed
- Frontend lint and production build: passed
- Repository execution freeze: 50/50 protected entrypoints guarded
- Repository correctness inventory: 427 files accounted for; 80 audited and
  347 pending
- Rendered browser QA: professor setup and course-delivery screens loaded,
  navigation changed to `/professor/delivery`, meaningful content rendered,
  and no relevant console warning or error was present

Focused regressions cover stale session writes, owner takeover, course binding,
source sensitivity, contradictory permissions, policy-version invalidation,
stale decisions, multiple custom previews, pending revisions, withdrawn
approval, staging browser-chunk exclusion, and release course mismatch.

## Boundaries and limitations

This checkpoint used synthetic/public local fixtures only. It made no
model/provider call, read no private or held-out source content, and changed no
component selection. Browser QA covered the desktop setup-to-delivery
navigation and visible release state; file upload and the complete release
interaction remain covered by synthetic API/integration tests rather than a
browser upload. Mobile and cross-browser rendered checks remain pending in the
broader frontend audit.

Historical retrieval and deployment results remain bound to their recorded
revisions. The deployable V6 current-match claim remains suspended. Retrieval,
generation, evaluation tooling, remaining frontend, and evidence/claim audits
are still pending.

Decision: **Keep / continue audit**.
