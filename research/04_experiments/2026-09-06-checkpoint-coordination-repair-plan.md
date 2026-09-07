# Checkpoint write coordination correctness repair

Decision question: can shared in-process SQLite checkpoint/model-ledger coordination remove reproducible busy-write failures without serializing tutoring/model generation or repeating provider calls?

Control: current per-turn AsyncSqliteSaver instances each own an independent lock; six separate model-call ledger write contexts compete for the same database. Natural 25-student/4-turn contract trials produced 30, 3 and 0 failed requests per100. Stack evidence identifies SQLITE_BUSY in saver `aput_writes` and model-ledger writes. This is a runtime contention defect, not a passing retry or a measured live-model quality result.

Candidate: one weakly retained asyncio lock per running event loop and resolved database path. Share it across saver instances and acquire it only around short ledger connections/transactions. Preserve SQL transactions and existing timeout values. Never hold the lock during graph invocation or model generation, and never replay a graph/model call. Separate event loops have separate locks; SQLite remains authoritative across processes.

Checks before adoption: deterministic separate-instance/path-alias mutual exclusion; distinct-loop compatibility and weak lifetime; cancellation releases the lock after connection closure/rollback; provider work can overlap; regression for saver writes waiting behind the shared ledger writer; full existing ASGI contract matrix. Metrics: failed requests, persisted message counts, exact provider attempts/attribution, and provider concurrency. Retain all failed baseline artifacts. Passing synthetic contracts does not qualify deployment capacity or answer quality.

## Autonomous integration follow-up

The same database also serves `GovernedAutonomousTutoringGraph`. Its saver and
three model-ledger writer transactions must participate in the same coordination
boundary. Control probes retain the current autonomous implementation and hold
a real coordinated SQLite write transaction. A probe-only zero busy timeout
makes uncoordinated access observable immediately; this is deliberate fault
injection, not a natural production failure-rate measurement. Four controls
fail with SQLITE_BUSY. A separate mixed-graph control already permits model
overlap but fails the shared-lock invariant.

The minimal candidate applies the existing helper to these four boundaries;
it changes no model, timeout, retry policy or transaction contents. Acceptance
requires all four writers to wait for local coordination and finish after
release, plus a mixed student/autonomous run in which both synthetic generators
enter concurrently and run exactly once, two student messages persist, and the
autonomous trace records one generation. Existing autonomy, reactive dialogue,
restart and authority regressions must also pass. Do not edit runtime source
during the currently running full suite; apply and verify this final integration
separately and retain the ordering in the audit record.
