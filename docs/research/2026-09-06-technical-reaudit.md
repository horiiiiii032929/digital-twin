# Technical re-audit, 6 September 2026

The follow-up audit reproduced and corrected defects in student authority,
autonomous transaction ordering, ingestion, publication, provider accounting and
frontend request lifecycles. This is evidence of specific repairs and regression
coverage, not certification that the entire repository is free of defects.
Existing experimental failures and the selected release profile are unchanged.

The working tree is dirty and includes prior work. Base revision:
`e441193c7fa1260ed327ebf43c59483f85817be8`. Reviewed execution-file hashes are
recorded in the versioned correctness audit/inventory; the base revision alone
does not identify the repaired working tree. No commit or deployment was made.

## Scope and evidence

| Boundary | Repairs and review | Scoped verification |
| --- | --- | --- |
| Student and autonomous runtime | Profile withdrawal before generation and at commit; serialize autonomous commit and wake-up materialization against cancellation. [Review](2026-09-06-technical-reaudit-runtime.md). | 51 tests passed; five new regressions also independently reviewed and rerun. |
| Ingestion and instructor authority | Hash parsed bytes; unique worker-invocation leases; reject reserved profile fields; allocate profile versions atomically; recheck publication authority; reject revoked professor accounts. [Review](2026-09-06-technical-reaudit-ingestion-approval.md). | 92 tests passed, including eight new regression cases. |
| Providers and generation boundaries | Enforce available cost ceilings for serial calls; validate integer limits; reject missing observed model identity; preserve nested legacy-client accounting. [Review](2026-09-06-technical-reaudit-generation.md). | 213 tests passed, then 67 nested-budget/preview checks passed. |
| Frontend state and authentication | Discard stale course requests; clear inaccessible workspaces; scope professor panels and account state; prevent concurrent credential mutations. [Review](2026-09-06-technical-reaudit-frontend.md). | 71 tests passed; lint and production build passed. |

These counts overlap and must not be summed. Regressions use synthetic data,
controlled deferred promises, and actual independent SQLite connections where
transaction ordering matters. Frontend hook tests use a deterministic adapter;
React DOM scheduling and these particular UI changes were not replayed in a
browser. Earlier browser evidence remains a separate result.

The correctness inventory records 30 changed/new files reviewed in this audit
and preserves prior scope history. Its 1,241 total entries include earlier
reviews of unchanged files; they are not 1,241 fresh reviews during this audit.

## Required integrated verification

The first integrated `npm run check` reached **2,510 passed / 19 failed** in
the 2,529-case Python suite (926.86 seconds). This unsuccessful run is retained
at `/tmp/technical-reaudit-full-check.log`; it must not be reported as a pass.
Eighteen failures shared an operational-metrics schema that rejected new
provider reservation fields. The schema now preserves these optional fields
with finite, non-negative cost validation and strict boolean validation; absent
legacy fields remain absent on serialization. Rejected-cost records also carry
the required failure code. The other failure expected an old withdrawal error
message; its replacement asserts the explicit authorization code, zero provider
calls and unchanged messages. The guard was not weakened. Follow-up suites
passed 69 and 24 tests respectively, without adding their overlapping counts.
The second full check finished with **2,534 passed / 1 failed** in 1,710.19
seconds, retained at `/tmp/technical-reaudit-full-check-retry.log`. All nineteen
previous failures passed. The remaining failure was two SQLite operational
errors in the 25-student, four-turn serial-provider contract. Natural diagnostic
replays reproduced SQLITE_BUSY in LangGraph checkpoint writes and model-call
ledger writes (30, 3 and 0 failures across three 100-request runs). A shared mutex now coordinates short checkpoint/model-ledger transactions per
event loop and database path, without enclosing generation. Three serial
replays each passed all 100 requests, followed by a configured-concurrency-five
100-request replay without failures. Four focused regressions also passed,
including a separate barrier proving two model calls overlap. The
[registered comparison](../../research/05_evaluation/checkpoint-writer-coordination-development-20260906-001-results.md)
retains baseline failures and limits; these malformed-provider fixtures are not
teaching-quality or production-capacity evidence. Neither failed full run is
reported as successful. A third invocation stopped before the Python suite because
the new comparison record did not use the required record envelope. The record
was corrected and validated without changing the measured results. All preceding
required stages had passed; the exact remaining ten stages were then resumed.
That resume completed with exit 0: **2,539 Python tests passed** (six dependency
warnings, 2,726.85 seconds), **71 frontend tests passed**, and lint and production
build passed. Thus the configured checks completed across the final prefix and
resume, rather than one uninterrupted successful `npm run check` invocation.
The prefix and resume logs, exact resume command and pre-integration correctness
inventory are retained under `reports/generated/technical-reaudit-20260906/`.
This full-suite result precedes the final autonomous-writer integration described
separately below; it must not be attributed to that later source version.
This command includes documentation and
evaluation validators, runtime regressions, frontend tests, lint and build.
Its Python command retains the four historical-artifact exclusions configured
in `package.json`; excluded files are not claimed as checked by that command.

## Final autonomous-writer integration

After the full suite finished, the same coordination helper was applied to the
autonomous graph saver and its three model-ledger writer contexts. No generation
await is held under the mutex. Four real-SQLite fault-injection controls had
failed with a probe-only zero busy timeout; a separate mixed-graph control
already allowed generation overlap but failed the shared-mutex invariant.
The final five regressions require observable waiting, expected durable outputs,
and one concurrent synthetic generation per graph family. Together with the
four existing coordination tests, **nine tests passed**. A broader final-source
suite then passed **75 tests** in 29.13 seconds, covering both graph families,
autonomous eligibility, restart/idempotency, cancellation, authority, writer
retries and worker composition. These counts overlap and are not added to the
2,539-case result from the preceding source version. Ruff passed on the helper,
both graph implementations and both coordination regression modules.

Reproduce the final impacted regression suite:

```sh
.venv/bin/python -m pytest tests/digital_twin/test_autonomy_checkpoint_coordination.py tests/digital_twin/test_async_checkpoint_coordination.py tests/digital_twin/test_governed_autonomy.py tests/digital_twin/test_autonomous_commit_serialization.py tests/digital_twin/test_autonomy_eligibility.py tests/digital_twin/test_tutoring_graph.py tests/api/test_async_turn_writer_retry.py tests/api/test_turn_teaching_profile_authority.py tests/test_autonomous_worker_composition.py -q
```

On the final source, the correctness inventory, technical/deployable freeze and
selected-profile validators passed. Local Markdown links and evaluation records
were also validated. The selected profile hash remains
`7a2465951fecb0c1ad20cc9daad14d92499f7838ba13c50dddd6acc2f8a8aea3`.

The source-specific 400-request comparison remains evidence for the preceding
reactive-only repair. It is not relabelled as a load trial of this final integration.
The final integration log is retained under
`reports/generated/technical-reaudit-20260906/technical-reaudit-final-integration-tests.log`.

## Remaining limits

Passing technical tests does not reverse failed semantic-quality gates. The
final-response audit still missed known critical cases; no experimental
candidate was promoted, no fresh or sealed evaluation set was consumed, and no
external LLM calls were needed for this correctness audit. Representative
permitted course evaluation, actual instructor fidelity and human learning
outcomes remain unqualified. Legacy transports without a conservative cost
estimator can still overshoot a budget by one serialized call; unknown costs
block further admission. The existing frontend bundle-size warning remains.
