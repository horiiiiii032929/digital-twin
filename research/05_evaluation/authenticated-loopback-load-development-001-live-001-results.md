# authenticated-loopback-load-development-001-live-001

**Keep bounded loopback development only.** All six preregistered authenticated network bursts passed the unchanged 15-second route p95 gate, with 180 real model-backed POSTs, no HTTP/provider/lineage/non-answer failures and 360 saved messages. This qualifies the measured local workload only; teaching quality and general deployment capacity remain unqualified.

## Decision question and method

Can the explicit bounded v3 candidate retain response lineage, persistence, authentication and latency under repeated local bursts? The [prospective plan](../04_experiments/2026-09-06-authenticated-loopback-load-plan.md) fixed 5/25/25/5/5/25 learners, two sequential questions each, three repetitions per load and a 15-second gate. Two factual question templates were repeated across 90 synthetic learners: these are six operational repetitions, not 180 independent teaching-quality samples. Low-load and high-load settings use the same questions; no interval or population capacity estimate is inferred from three dependent repetitions.

An owned single-process Uvicorn server used a fresh loopback socket and task-only certificate trusted by the HTTP client. Actual credential/session/Origin middleware was used, and synthetic identity-header bypass was rejected. A mixed PDF/transcript/forum course was uploaded and processed through the API/worker before source approval, publication and domain-model setup. Account/policy fixtures are synthetic. No user Docker, existing server or trust store was modified.

## Configuration and provenance

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty=true. All start/end source hashes matched; an immutable source ZIP is recorded by SHA-256. See [machine record](records/authenticated-loopback-load-development-001-live-001.json) for exact hashes, configuration, case index and ledger. Raw evidence: `reports/generated/authenticated-loopback-load-development-001-live-001`. Flags: approved profile context, question-specific generation and bounded contract enabled; named-referent v4 disabled. Luna, 1500 output tokens, provider concurrency5, cap300 calls/USD10. The selected profile/defaults remain unchanged; its historical binding supplies staging setup only.

## Results

| Repetition | Learners | POSTs | Route p95 seconds | HTTP / lineage / non-answer failures | Fixed15s gate |
|---|---:|---:|---:|---|---|
| 1 | 5 | 10 | 3.508 | 0 / 0 / 0 | Pass |
| 2 | 25 | 50 | 14.375 | 0 / 0 / 0 | Pass |
| 3 | 25 | 50 | 14.101 | 0 / 0 / 0 | Pass |
| 4 | 5 | 10 | 3.483 | 0 / 0 / 0 | Pass |
| 5 | 5 | 10 | 3.231 | 0 / 0 / 0 | Pass |
| 6 | 25 | 50 | 13.310 | 0 / 0 / 0 | Pass |

All180 actual calls completed as `question_specific_profile_tutoring`; peak provider overlap5. Reported cost USD0.0774456, input tokens217980, output tokens28208; unknown-cost calls0 and cost-reporting failure=false. Admission wait p50 8.289s and p95 10.930s includes budget/ledger overhead. Peak sampled child RSS374784000 bytes; total setup-plus-run elapsed116.754s. All90 conversations retained four messages and the child exited0 after complete budget cleanup.

## Failures, uncertainty and limits

There were no observed operational failures in this run. The first high-load p95 was14.375s, close to the15s limit; this is not headroom for larger loads. HTTP success and an `answer` action do not establish semantic accuracy, instructor fidelity or learning benefit. This is a short closed-loop burst experiment on one local host, not open-loop sustained arrivals, production TLS/cloud/Docker, long-context tutoring, streaming, overload beyond25 learners, uptime or recovery under load. Co-resident process and host metadata are retained; no controlled speedup claim is made against earlier in-process v2 trials with different questions/configuration.

The separate contract001 shutdown defect and corrected contract002 remain registered. No unfavorable result was omitted or threshold changed. Broader deployment and pedagogical conclusions remain Refine despite this operational pass.
