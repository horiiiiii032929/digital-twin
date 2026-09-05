# Runtime correctness audit before report drafting

## Scope and decision criteria

The report is paused while the actual program is reviewed. This audit uses
synthetic regression fixtures and the repository checks, not consumed factual
or autonomy evaluation data. It introduces no model, ranking, prompt, or release
profile selection. Historical qualification 010 remains bound to its original
revision; source changes here are not a newly qualified container release.

## Turn authority race

Decision question: can an answer commit after an administrator withdraws its
release or revokes student access while generation is in flight?

Baseline: the service checks authority before awaiting generation; `save_turn`
checks record lineage but not current account, membership, or publication state.
Three deterministic event-barrier regressions using a second SQLite connection
reproduce the defect: release withdrawal, membership deactivation, and account
revocation all allow the answer to return when rejection is required.

Prediction: a conditional write at the beginning of the turn transaction can
revalidate the exact conversation, active student account/membership, and
published release atomically with every message and learner-state write.
An additional service-only check would leave a cross-worker race between the
check and commit, so the repository boundary is required. SQLite obtains the
write lock before evaluating the guarded update; rejection rolls back the turn.
No database lock is held across generation. A typed error becomes HTTP 409.

Acceptance: each revoked case rejects without messages or learner-state updates;
normal turns, concurrent duplicate requests, restart, and rollback still pass.
This is regression evidence for a correctness fix, not a new factual-quality
estimate. No paid/provider or consumed-dataset execution is part of the audit.

## Request and clarification boundary failures

Two additional synthetic regressions reproduce failures before correction:

- An unknown outreach-reply ID reaches generation and then raises an uncaught
  repository `ValueError` (HTTP 500). Validate its student/course/release scope
  before generation; retain the repository check as defense in depth. Acceptance
  is HTTP 403, zero generation calls, and no persisted turn for invalid IDs.
- Long valid source titles/section names exceed the clarification label's
  240-character output contract and raise `ValidationError`. Bound only the
  display label, preserve full source lineage, and suffix truncation/collision
  cases with stable option numbers. Acceptance is bounded, distinct labels that
  still resolve by both label and option number. Source text and ranking do not
  change; this is output-contract handling, not a new grounding method.

## Proactive delivery race

Deterministic interleaving regressions also reproduce stale delivery
checks: a second trigger can consume the one-message cap, or the student can
snooze/change quiet hours, after preflight but before materialization. Those three
still deliver in the baseline. Additional interleavings reproduce delivery
after account or membership revocation; release withdrawal already cancels its
trigger. The commit boundary now also revalidates the current student/release
scope. Recheck current preferences and the durable
message count after acquiring the SQLite writer lock, before inserting message,
citations, or outbox. Preserve the existing quiet-hour calculation in one shared
preference method. Acceptance is suppression for cap/snooze and deferral for
quiet hours, with no extra message. This changes enforcement timing, not the
selected intervention policy or its thresholds.

## UI and fixture follow-through

Course/conversation changes now clear the pending outreach reply reference and
its draft, preventing a reply from one course being submitted in another.
The UI also exposes its existing current-release recovery action for a turn
rejected because authority changed. These small state edits require frontend
lint, tests, and a production build; no layout redesign is included.

Four synthetic history builders previously inserted a no-evidence turn directly
against an already withdrawn release. They now publish the prior release,
record its turn, and replace it with the current release, matching the real
lifecycle. Their cases and expected outcomes are unchanged; historical result
records and frozen evaluation datasets are not rewritten.

## Verification and decision

Keep these correctness fixes. On 2026-09-05, `npm run check` completed with exit
code 0 against the uncommitted working tree based on
`5bb3d632e6b586e458751b61b22791347d80ea5d`. The main Python suite passed
1,952 tests in 754.70 seconds; the frontend passed 51 tests across 11 files.
Repository validators, frontend lint, and the production build also passed.
The local complete log is `/tmp/digital-twin-audit-complete-check.log`; it is
temporary evidence, with the durable outcome recorded here.

Non-blocking warnings were dependency SWIG deprecations, the intentional
duplicate SQLite archive-member fixture, and a frontend bundle over 500 kB.
The existing correctness inventory remains complete at 1,126 files; this audit
updates the changed entries and inherits prior reviews of the remaining files.
It does not claim a fresh independent review of every inventory entry.

The focused reproductions can be rerun with
`uv run pytest tests/api/test_student_api.py tests/digital_twin/test_stateful_clarification.py tests/digital_twin/test_proactive_outreach.py`.
The repository gate retains its existing consumed-data test exclusions.
No provider-backed evaluation, deployment, or new container qualification was
performed. Historical qualifications and factual-quality results are unchanged.

## Audit limits

Review concentrated on student request authorization/commit, publication and
withdrawal, clarification, proactive delivery, and related UI state. The full
repository gate provides broader regression coverage, not a proof of absence
of bugs or an independent real-world security/learning study. The measured
factual-grounding shortfall remains a method limitation, outside this
correctness patch; consumed evaluation data is not reopened for tuning.
