# Evaluation result: final-profile-asgi-tutoring-concurrency-development-20260906-002

## Run identity and decision

Completed on 2026-09-06. **Keep the explicit bounded concurrency candidate for
development; Refine teaching quality.** Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty;
start/end source hashes unchanged. [Machine record](records/final-profile-asgi-tutoring-concurrency-development-20260906-002.json).
Full synthetic responses, attempt ledger, manifest and summary remain under
`reports/generated/final-profile-asgi-tutoring-concurrency-development-20260906-002/`.

## Prospective comparison

The [plan](../04_experiments/2026-09-06-asgi-tutoring-concurrency-plan.md)
compares an explicit provider concurrency cap of five with the retained
[serial baseline](final-profile-asgi-tutoring-concurrency-development-20260906-001-results.md). Both use 25 synthetic students, four sequential
messages per student, the actual shared factory-built service/student router,
Luna, approved explanatory profile and question-specific v2 generation. The
candidate reserves conservative per-request ceilings before admission, accounts
for completed and uncertain cost, and caps both in-flight calls and total calls.
Missing usage, cancellation and a disappearing advertised ceiling fail closed.
Clients without the ceiling capability retain serial behavior; default remains1.

The exact same fixed operational workload is reused, not a hidden quality set.
The candidate changes budget/provider and opt-in factory/runner plumbing; the
record lists all six source files changed between runs. Generation implementation
and synthetic packet hashes did not change. The old manifest's v1 descriptive
label is corrected prospectively by importing the actual generator ID; its raw
baseline remains untouched. Models are stochastic and no random seed or statistical
independence of student outcomes is claimed.

## Aggregate and operational comparison

| Measure | Serial baseline001 | Candidate002 |
| --- | ---: | ---: |
| Tutoring POST contracts | 100/100 | 100/100 |
| Provider calls / failures | 150 / 0 | 150 / 0 |
| Concurrent routes / actual provider calls | 25 / 1 | 25 / 5 |
| Persisted messages | 200/200 | 200/200 |
| Request p50 | 104.420s | 21.337s |
| Request p95 | 148.576s | 31.968s |
| Loop elapsed | 436.020s | 92.820s |
| Answer / question / no-evidence / safe failure | 94 / 3 / 3 / 0 | 91 / 5 / 3 / 1 |
| Reported cost | USD0.0646906 | USD0.0650912 |

Candidate usage was146,572 input and29,814 output tokens. All provider identity,
request scope, citation lineage and persistence hard contracts passed. Exact
started/completed ledger order shows peak five external calls rather than merely
five tasks waiting on a serial wrapper. The lower observed latency supports the
planned operational correction; it is not a production p95 guarantee or an
isolated causal speedup estimate. Parent checks and finite Terra work were
co-resident on the same Apple M1 Pro with 17179869184 bytes RAM. Peak
process RSS was not measured. No quieter or favorable-only rerun was performed.

## Failures and limitations

`student-06-turn-1` returned a safe graph failure after two successful provider
calls. The intent was correct_misconception; the generator proposed a hint with an
exact supported S1 span. This is a graph/content-validation outcome, not an HTTP,
provider-identity or budget admission failure. Complete content and diagnostics
remain available; no hidden rescore or prompt repair occurred during this run.
Three other turns returned no-evidence and five asked questions. These nine
non-answer responses are retained verbatim in the sanitized record. Response
presence and100HTTPsuccess do not establish semantic adequacy.

The execution is in-process ASGI with synthetic identity injection, excluding
production authentication middleware, sockets, TLS, Docker and distributed
workers. There are no real students, professor-fidelity labels or learning-effect
measurements. Source hashes and dirty revision are retained, but no immutable
full source-byte archive was made. Conservative cost ceilings depend on configured
prices and the bounded text-only schema/output contract; unknown transports are
not silently granted concurrency.

A first launch wrapper failed dotenv path discovery before importing the runner,
creating output or making any provider call. Its trace remains recorded in the
environment note; the corrected explicit local credential path started this run.
No evaluation request was replayed.

## Reproduction and selection

```sh
uv run python -m scripts.run_asgi_tutoring_concurrency_development --execute --students 25 --turns 4 --provider-max-concurrency 5 --maximum-calls 500 --maximum-cost-usd 5 --output-dir reports/generated/asgi-concurrent-new
```

Load the local credential before execution; exact instrument authorization and a
fresh output directory are required. A separate current-code766-test run passed,
covering real checkpoint contention, duplicate/revocation behavior, cost/call
admission, mixed ceiling capability, cancellation, unknown usage and both25-by-4
network-free contracts. These tests are not added to live metrics.

Keep the explicit candidate5 option for development and the serial default/control.
No release profile is changed. Address graph validation and teaching quality
separately, then verify an authenticated deployed workload before claiming scalable
production service.
