# Evaluation result: final-profile-asgi-tutoring-concurrency-development-20260906-001

## Run identity

Completed on 2026-09-06; **Refine**. Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty;
start/end source hashes match. [Machine record](records/final-profile-asgi-tutoring-concurrency-development-20260906-001.json).
Raw artifacts: `reports/generated/final-profile-asgi-tutoring-concurrency-development-20260906-001/` (manifest, entire delivered responses,
provider attempt ledger, summary and environment). No existing run was overwritten.

## Decision context and configuration

The [prospective plan](../04_experiments/2026-09-06-asgi-tutoring-concurrency-plan.md)
asks whether 25 simultaneous synthetic conversations, four sequential turns each,
complete the actual student-route contract. The actual final-profile service uses
approved explanatory context and the question-specific v2 generator. The original
manifest has a stale v1 descriptive label; delivered trace IDs and source hashes
identify v2. Original artifacts retain this error, not a rewritten history.

The deterministic injected-provider contract is the operational baseline; this is
the first real-provider shared-runtime execution. Two synthetic protocol cards and
four fixed messages are repeated across 25 students. This fixed development load
is not a statistical sample of student outcomes; no confidence interval or semantic
quality score is justified. Production login is replaced by synthetic account
headers. Actual service authority, persistence and citation scope checks remain.

## Aggregate and operational results

| Measure | Result |
| --- | ---: |
| Completed tutoring POST contracts | 100/100 |
| HTTP/provider failures | 0/0 |
| Retained student+tutor messages | 200/200 |
| Concurrent client requests / provider calls | 25 / 1 |
| Actual provider calls | 150 |
| Delivered actions | 94 answer, 3 question, 3 no-evidence |
| End-to-end request p50 / p95 | 104.420 / 148.576 seconds |
| Total measured loop | 436.020 seconds |
| Reported provider cost | USD 0.0646906 |
| Input / output tokens | 146333 / 29520 |
| Source hashes unchanged | Yes |

All calls used the required model identity, all 25 students exercised it, and the
100 POST/citation-lineage/persistence hard contracts passed. This does not make all
answers correct: three explicit misconception prompts produced no-evidence, and
three first turns asked questions. Complete content remains available for separate
quality review. The runner's narrow Go Deeper operational label is retained in the
raw summary; this decision is **Refine** because the load exposes serialization.

## Failure classification and limitations

`BudgetedLlmClient.chat` holds its asyncio lock during provider await. The durable
started/completed ledger confirms only one external call at a time despite 25
queued routes. This is the measured operational bottleneck, not a demonstrated
25-way model capacity result. The earlier SQLite event-loop contention defect was
fixed before this run and its genuine checkpoint/duplicate/revocation regressions
passed; no lock failure recurred here.

Hardware was an Apple M1 Pro, 17179869184 bytes RAM, macOS-26.5.2-arm64-arm-64bit.
Parent npm/check and finite G5 work were co-resident; their CPU contention makes
these timings descriptive rather than an isolated benchmark. No production p95,
Docker, sockets, TLS, distributed workers, real student learning, or independent
professor-fidelity claim follows. A quieter repeat would not fix the observed
serial provider budget, so no selective timing rerun is used.

## Reproduction and decision

Load the configured provider credential locally, then run:

```sh
uv run python -m scripts.run_asgi_tutoring_concurrency_development --execute --students 25 --turns 4 --maximum-calls 500 --maximum-cost-usd 5 --output-dir reports/generated/asgi-serial-new
```

The exact instrument authorization is required, and output must be exclusive.
Retain the serial default as control and evaluate an explicit concurrency candidate
with conservative in-flight cost reservations, finite admission caps, cancellation
accounting and unknown-cost fail-closed behavior. No release profile is promoted.
