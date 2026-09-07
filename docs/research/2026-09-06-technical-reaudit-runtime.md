# Student and autonomous runtime technical re-audit

6 September 2026. Scope: student admission/generation/commit, repository turn
transactions and authority, proactive materialization, autonomous job commits,
wake-up cancellation and recovery. This is a code/contract audit with synthetic
fixtures and local SQLite, not model-quality evaluation or full-line correctness
certification. Existing dirty work and failed semantic experiments are preserved.

## Reproduced findings and repairs

- Bound teaching-profile withdrawal was absent from ordinary student admission
  and the final turn transaction. A still-published release could generate/save
  new content after its instructor profile was withdrawn. Admission now checks
  the exact profile ID/hash/approval; save_turn repeats the check while holding
  the SQLite writer lock. Approved predecessors superseded by a successor remain
  valid for their exact current published release; explicit withdrawal blocks
  new turns. Already stored history is not erased. The API exposes a 409 conflict
  for unavailable teaching profiles. Two before/during-generation tests failed
  before repair; the valid superseded case already passed.
- Autonomous commit read pending/leased status before acquiring a cross-worker
  write lock. A separate connection could cancel the goal between this read and
  insertion, causing an inconsistent commit failure after message materialization.
  A write lock now spans the status read and final records. The regression forces
  administrative cancellation at the first insert; it must wait until commit.
- Wake-up materialization similarly allowed cancellation after scope validation
  but before insertion, allowing a cancelled wake to produce a new pending
  opportunity. It now acquires the writer lock before reading wake status and
  checking goal/policy. The test forces cancellation at insertion and verifies
  cancellation applied afterward still cancels the new opportunity.

These changes enforce existing authority and atomicity requirements; they add no
new model, agent strategy or release selection. They do not hold database locks
across model generation. Narrow nonblocking student writer retries remain intact.

## Evidence

Failing regressions retained in `/tmp/technical-reaudit-profile-before.log`,
`/tmp/technical-reaudit-autocommit-before.log` and
`/tmp/technical-reaudit-wakeup-before.log`. Tests use two actual SQLite connections
and controlled async generation or SQL callbacks, not sleep-only race assumptions.

```sh
.venv/bin/python -m pytest tests/digital_twin/test_autonomous_commit_serialization.py tests/digital_twin/test_governed_autonomy.py tests/api/test_turn_teaching_profile_authority.py tests/api/test_async_turn_writer_retry.py -q
```

Final root-scope result: **51 passed**, with five existing dependency warnings,
recorded in `/tmp/technical-reaudit-root-final.log`. An independent reviewer
inspected the changed authority/transaction boundaries and reran all five new
cases successfully.
The separate frontend, provider and ingestion/publication reviews have their own
scope notes. The consolidated audit records the required full-suite outcome after
all parallel changes settle.

## Checkpoint contention follow-up

The second full-suite run exposed SQLite contention during 25 concurrent
student conversations. Three diagnostic replays reproduced 30, 3 and 0 failed
requests out of 100 each. Sanitized exception frames located SQLITE_BUSY in
LangGraph checkpoint writes and the graph's model-call ledger. Each saver had
its own mutex despite sharing the same database.

Checkpoint operations and the six model-ledger writer transactions now share a
mutex per event loop and resolved database path. SQLite transactions remain
authoritative across processes. The mutex is never held over graph execution
or provider calls; weak registry entries avoid retaining idle locks or loops.
Four focused tests cover path aliases, cancellation rollback, loop separation
and actual overlapping provider calls. Three corrected serial-provider replays
each saved all 100 responses with zero failed requests and unchanged sources.
The [registered comparison](../../research/05_evaluation/checkpoint-writer-coordination-development-20260906-001-results.md)
preserves every baseline trial, subsequent verification and its limitations.
This is local contention control, not distributed scheduling or a demonstrated
teaching-quality improvement.

## Same-database autonomy integration follow-up

After the required full-suite run completed, extend the identical coordination helper to the autonomous graph's saver and three model-ledger writer contexts. This closes another writer family using the same database; planner/generator awaits remain outside the mutex. This final source version is distinct from the earlier reactive-only 400-request comparison and is not retroactively covered by those measurements.

Control evidence in `/tmp/autonomy-coordination-control.log`: four real-SQLite held-writer probes failed for autonomous reservation, completion, failure update and graph checkpointing. These deterministic probes explicitly inject `timeout=0` in the test process; they are not natural production-timeout observations. A mixed-graph control reached both synthetic generators concurrently, once each, but failed the shared-mutex assertion (`/tmp/autonomy-coordination-mixed-control.log`).

After extension, `tests/digital_twin/test_autonomy_checkpoint_coordination.py` adds five checks. Each held-writer task must remain pending until release, then complete with the expected durable ledger status/output or no-action graph result. The mixed test runs actual student T1V2 and autonomous graph families against one SQLite file, requires both mock generators to enter a barrier before either can finish, preserves exactly one generation per family and two saved student messages, and verifies saver coordination. No external model calls occur.

Final targeted command: `.venv/bin/python -m pytest -q tests/digital_twin/test_autonomy_checkpoint_coordination.py tests/digital_twin/test_async_checkpoint_coordination.py`: **9 passed**, five existing SWIG deprecation warnings,16.74s. Log `/tmp/autonomy-coordination-final-tests.log`. `ruff check src/digital_twin/student/autonomy_runtime.py tests/digital_twin/test_autonomy_checkpoint_coordination.py`: passed (`/tmp/autonomy-coordination-ruff.log`); system Ruff used because the repository venv has no Ruff binary. `git diff --check` passed for both files. Broader impacted regression review remains root-owned; no claim of another full-suite run or distributed/multi-process liveness is made.

The subsequent root-owned impacted suite passed **75 tests** in 29.13 seconds
with five existing dependency warnings. It includes reactive/autonomous graphs,
worker composition, eligibility, restart/idempotency, authority and cancellation
regressions; see the [consolidated audit](2026-09-06-technical-reaudit.md) for the
exact command. This checks the final integration source after the earlier full
2,539-case suite, not a second full-suite rerun.
