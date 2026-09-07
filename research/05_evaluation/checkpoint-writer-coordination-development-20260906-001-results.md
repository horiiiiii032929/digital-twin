# Checkpoint writer coordination: development result

## Run identity and current decision

`checkpoint-writer-coordination-development-20260906-001`, 6 September 2026. **Keep for the reproduced local SQLite writer repair. The original full-trial provider-overlap gate was not demonstrated.** This record preserves a reproduced operational failure and three completed bounded repair repeats. It does not select a generator, qualify a release or establish deployment capacity.

Baseline revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty tree. Each trial records exact source-start hashes and unchanged-at-end verification in its manifest/summary. Baseline source bytes were not snapshotted during execution. A subsequent verified archive now contains all 191 baseline and 192 candidate manifest-listed files, matched to their captured hashes; this is an after-run reconstruction, not an original run-time snapshot. [Machine record](records/checkpoint-writer-coordination-development-20260906-001.json) retains all hashes. Original temporary outputs are copied under `reports/generated/checkpoint-writer-coordination-development-20260906-001/baseline/` with diagnostic log and reproduction script.

Plan: [Checkpoint write coordination correctness repair](../04_experiments/2026-09-06-checkpoint-coordination-repair-plan.md). Runtime observed during record preparation: Python 3.12.13, SQLite 3.53.4, aiosqlite 0.22.1, LangGraph 1.2.11/checkpoint-sqlite 3.1.1, Pydantic 2.13.4, FastAPI 0.141.1, HTTPX 0.28.1. These versions were not separately embedded in the original baseline manifests.

## Decision context and workload

Question: can common coordination for SQLite checkpoint and short model-ledger transactions remove write collisions while preserving provider concurrency? Control is the current independent writer behavior. Candidate is a per-event-loop/per-database async coordination boundary around saver operations and short ledger transactions; provider awaits must remain outside that boundary. Prediction and candidate gates are fixed after failure discovery and before candidate observations.

Use the existing `final-profile-asgi-tutoring-concurrency-development-001` instrument: 25 synthetic students, four ordered messages each, 100 total requests per trial, in-process ASGI with factory-built tutoring services. Two fictional protocol cards and an explanatory synthetic teaching profile are reused. Natural coroutine scheduling is **not seeded** and repeats do not reproduce identical interleavings. There are no real students, private materials or external inference calls.

The injected `MalformedContractClient` returns `{}` with fixture usage. Consequently, completed requests deliver `safe-graph-failure`. That is expected containment for this fixture, not a correct or useful tutoring answer. Provider model/token/cost fields are synthetic accounting labels, not actual inference or billing.

## Baseline observations

| Trial | Requests | Request failures | Persistence count check | Provider calls | Wall seconds | Successful p95 ms |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Baseline 1 | 100 | 30 | Fail | 150 | 37.337 | 12,987.084 |
| Baseline 2 | 100 | 3 | Fail | 149 | 20.783 | 9,718.353 |
| Baseline 3 | 100 | 0 | Pass | 150 | 20.108 | 8,665.747 |
| Candidate 1, concurrency 1 | 100 | 0 | Pass | 150 | 20.852 | 10,523.077 |
| Candidate 2, concurrency 1 | 100 | 0 | Pass | 150 | 25.019 | 10,832.094 |
| Candidate 3, concurrency 1 | 100 | 0 | Pass | 150 | 19.245 | 5,623.026 |
| Candidate, configured concurrency 5 | 100 | 0 | Pass | 150 | 26.462 | 10,878.390 |

Across baseline repeats, 33/300 requests failed (descriptive 11%); two of three schedules exhibited failure. Retaining the zero-failure repeat is important: one passing load run would have missed the defect. Provider overlap was one in all trials. Sources were unchanged and cleanup succeeded in all three. Synthetic reported cost totaled $0.449; actual external provider calls/cost were zero. Memory was not measured.

The diagnostic log identifies `SQLITE_BUSY` at checkpoint `aput`/`aput_writes` and model-ledger `_generate_once`, distinguishing database writer contention from provider/schema failure. Exact affected request IDs, statuses and latencies remain in `responses.jsonl`; original provider records remain in `provider.jsonl`. The full repository check first exposed the issue (2,534 tests passed, one failed); independent natural repeats then reproduced it. The repair must fix the coordination boundary rather than retry until a schedule happens to pass.

## Prospective gates and validity

Repeat the identical 25×4 workload three times with provider concurrency one, then once with concurrency five. Require zero request exceptions, complete persistence-count checks, no cleanup errors and unchanged source hashes in every candidate trial. Original prospective gate: the concurrency-five full trial must demonstrate provider overlap, and targeted tests must demonstrate that provider awaits are not serialized by the database lock. An explicit interpretation amendment was recorded while that trial was running, before its result: the no-await malformed fixture cannot demonstrate concurrent provider work merely by raising the configured cap. If its observed peak is one, the original full-trial-overlap gate remains unmet. A separate barrier regression demonstrates two overlapping provider calls; that can support a narrowly scoped writer-repair Keep but cannot be substituted into a claim that all original gates passed or that five-way throughput was qualified. Retain all repeats; a failed candidate trial remains failed.

Sample size is chosen to reproduce the concrete shared-database race, not to estimate an independent-user failure probability. Requests share process, event loop and database; do not calculate an independence-based confidence interval or claim a causal latency gain from these unseeded schedules. The comparison covers a single-process SQLite architecture, not multiple workers/processes, network sockets/TLS, Docker, production authentication/middleware or database-server deployment.

Three candidate trials now complete all 300 requests without exception, with persistence checks/source hashes/cleanup passing and 450 fake provider calls. Four focused coordination regressions also pass, including the two-provider barrier case. Candidate manifests and provider/response ledgers are archived under the same generated result directory. The configured-concurrency-five full workload also completes 100 requests with no exceptions, passing persistence/source/cleanup checks and 150 fake provider calls. Its actual observed provider peak is one: the original overlap gate is not demonstrated by this artifact. The Keep decision is narrowed to writer correctness and independently tested overlap 2; it does not claim all original gates passed. No release-profile change is authorized by this record.

## Reproduction and learning

The archived `reproduce_asgi_reaudit.py` invokes `run_asgi_tutoring_concurrency_development.run` with `contract=True`, `students=25`, `turns=4`, an injected `MalformedContractClient` and provider concurrency one, three times. Its diagnostic wrapper records exception type/SQLite code/stack locations only. Use a new output directory; retain the original baseline files. The runner itself refuses reuse of an existing output directory.

The lesson is about transaction ownership: serializing external calls does not serialize all checkpoint/model-ledger writes. A database-scoped coordination boundary can address the local conflict without holding a lock while waiting for a model. The serial-provider repeats and configured-five workload support the local operational repair; they do not establish an absence of future failures.

## Invalid local run retained

A separate local ASGI run (`pytest-680/test_actual_shared_service_rou1/fresh`) had 0 request errors and passing persistence but failed source identity: `async_sqlite_coordination.py` changed from `bdd23454…` to `98284f0d…` during the run. The implementer reports an annotation-only change, but this remains an invalid frozen-source trial and is excluded from the qualified repetitions. Its manifest, summary and ledgers are archived as `invalid-source-change/`; full hashes are in the machine record. It is neither omitted nor counted as an extra successful candidate repeat.

Latency varies across natural schedules and is reported descriptively; there is no controlled speedup claim. Requests are dependent, and no human or learner outcome evidence was collected.

## Final scoped decision

Keep the common SQLite writer coordination: three matched serial-provider schedules improve from 33/300 request exceptions to 0/300, and the additional configured-five workload has 0/100. All four qualified candidate runs preserve counts, source identity and clean shutdown. Comparison source hashes differ only in `tutoring_graph.py` and the new `async_sqlite_coordination.py`; exact hashes are retained. The separate source-mutated trial remains invalid.

The concurrency-five no-await fixture observed only one provider call in flight, so the original full-trial-overlap gate is explicitly not demonstrated. A focused barrier test establishes two overlapping provider calls and supports the narrower claim that the lock does not span provider work. No selected provider-cap change, five-way concurrency qualification, throughput gain, deployment promotion or generator-quality claim follows. All 600 candidate provider calls and their $0.600 accounting total are injected fixtures; actual inference cost is zero.

## Record-format correction

The subsequent full check stopped at evaluation-record validation because this record omitted the common `run_id` and `code_revision` envelope fields. The loader therefore attempted the stricter component-selection schema. This was an evidence-format failure, not a new runtime failure. The corrected record uses the repository's existing `ResearchEvaluationRunRecordV1` whole-system envelope, which preserves detailed operational evidence and the scoped decision without falsely requiring an all-gates-passed component selection. The original malformed record and full-check failure log are retained; no trial, invalidation or failed gate was changed.

After correction, `python -m scripts.validate_evaluation_results` passed and `python scripts/validate_markdown_links.py` validated 1,948 local links. A loader round-trip also confirmed retention of all three baseline trials, three serial candidate trials, the configured-five trial and the invalid source-mutated trial.

## Hash-verified source reconstruction

After the runs, the baseline `tutoring_graph.py` was reconstructed by removing exactly the coordination import, saver-lock assignment/comment and six coordinated-connection replacements from the candidate file. Its SHA256 exactly matches all three baseline manifests (`6d7b835c8af42906d7945b966109fc9a2a4aee7084b89ffef73d7a98547a032c`). Other source files were archived only where their current bytes matched the captured hash. Coverage is 191/191 baseline files and 192/192 candidate files, including the helper; no missing source files remain in the captured manifests.

The ZIPs and per-file provenance manifest are under `reports/generated/checkpoint-writer-coordination-development-20260906-001/post-run-source-archive/`. The original test fixture was not in the start-hash set; its current copy/hash is separately labelled post-run fixture provenance. Dependency versions are unchanged. No claim is made that these after-run archives existed when the trials executed.

## Limited autonomy integration follow-up

The recorded 400 candidate requests still qualify only their captured **reactive** source snapshot. A subsequent, separately archived extension now shares the existing database-operation lock with the autonomous runtime's saver and three reserve/complete/fail ledger transactions. This does not retroactively expand the original load evidence.

Control probes exposed four SQLite failures while a transaction was held (reservation, completion, failure update and graph checkpointing). They used test-only `timeout=0`, so these are deterministic contention probes, not natural production-timeout measurements. A separate mixed-graph control reached both synthetic generators once each but failed the shared-saver-lock assertion. Both failed logs and the original probe source are retained.

After integration, the five new autonomy checks plus four existing coordination checks pass: **9 passed in 16.74 seconds**, with five existing SWIG deprecation warnings. The held-writer tests require each task to remain pending until release and then produce the expected durable result. The mixed reactive/autonomous test requires both mock generators to enter a barrier before finishing, exactly one generation per family, two persisted student messages and common saver-lock identity. Planner/generator awaits remain outside the coordinated transactions. Ruff and the source diff whitespace check passed. The subsequent root-owned impacted regression suite passed 75 tests in 29.13 seconds with five existing dependency warnings; its log is separately archived. This validates the final integration with targeted tests, not a full-suite rerun. The preceding 2,539-case full suite and 71 frontend tests belong to the earlier source state.

**Keep the limited mechanically verified autonomous writer integration.** No additional 400-request autonomous load experiment, full-system qualification, real-learner/model-quality evidence, distributed liveness or five-provider concurrency claim is made. See [Runtime re-audit](../../docs/research/2026-09-06-technical-reaudit-runtime.md). The machine record's separate `autonomy_integration_followup` preserves final runtime/test hashes, all failed control logs, final 9-test log, patch and original probe under `reports/generated/checkpoint-writer-coordination-development-20260906-001/autonomy-integration/`. Earlier measured trial records and source archives are unchanged.
