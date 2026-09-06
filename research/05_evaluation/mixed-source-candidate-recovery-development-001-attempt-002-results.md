# Evaluation result: mixed-source-candidate-recovery-development-001-attempt-002

## Identity and decision

**Refine the harness setup; no product quality conclusion.** Recorded on 2026-09-06, revision `e441193c7fa1260ed327ebf43c59483f85817be8`,
dirty; source hashes unchanged: True. [Machine record](records/mixed-source-candidate-recovery-development-001-attempt-002.json).
The original manifest, summary and any ledgers remain under
`reports/generated/mixed-source-candidate-recovery-development-001-attempt-002/`. No attempt was overwritten.

Staging rejected missing qualification binding; existing immutable base binding/profile supplied next, never forged.

## Design, data and comparison

The [prospective plan](../04_experiments/2026-09-06-mixed-source-candidate-recovery-plan.md)
connects previously separate ingestion/candidate, cohort and clean-restore tests.
This is one joined scenario across two synthetic courses and three source formats:
PDF lecture, UTF-8 transcript and reviewed Markdown forum, plus a second-course PDF
sentinel reusing the source name. Six course-A learners provide the minimum useful
privacy design: five gap learners and one active non-gap learner. A seventh learner
belongs only to the sentinel course. They are fixtures, not independent subjects
sampled from a university population.

The actual staging application uses credentials, sessions, Origin checks, queued
ingestion and the worker, profile approval, domain model and publication APIs,
current opt-in question-specific/profile composition, withdrawal and backup/restore.
Approved onboarding policy is a disclosed setup fixture. The provider is a
source-bound deterministic fixture, not a live model or a semantic oracle. Existing
immutable release binding enables the historical staging base; it does not qualify
the changed injected candidate. No guards or approvals were bypassed.

## Observed execution

| Measure | Result |
| --- | ---: |
| Executed / passed assertions | 0 / 0 |
| Distinct assertion labels | 0 |
| Injected / external provider calls | 0 / 0 |
| External provider cost | USD 0 |
| Wall time | 0.000236s |
| Peak process RSS | 317,030,400 bytes |

Assertion counts describe a sequential contract, not sample size, accuracy or
capacity. Every executed assertion and failed stage appears in the record. No
confidence interval or educational effect is estimated. Failure details are
classified as setup/integration rather than a model-quality score.

## Reproduction and limits

```sh
uv run python -m scripts.run_mixed_source_recovery_development --execute --output-dir reports/generated/mixed-contract-new
```

Exact instrument authorization and a new directory are required. The current
runner includes setup corrections; historical attempts retain their own hashes
and unfavorable outcomes. No private data or external provider credential is
needed. The workload does not exercise a browser, actual TLS connection, Docker,
distributed workers, live mixed-source generation or professor/student learning.
Its short duration is not a load result. No selected release profile changes.
