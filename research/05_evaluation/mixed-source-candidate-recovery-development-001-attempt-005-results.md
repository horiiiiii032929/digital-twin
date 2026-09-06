# Evaluation result: mixed-source-candidate-recovery-development-001-attempt-005

## Identity and decision

**Keep integration coverage only.** Recorded on 2026-09-06, revision `e441193c7fa1260ed327ebf43c59483f85817be8`,
dirty; source hashes unchanged: True. [Machine record](records/mixed-source-candidate-recovery-development-001-attempt-005.json).
The original manifest, summary and any ledgers remain under
`reports/generated/mixed-source-candidate-recovery-development-001-attempt-005/`. No attempt was overwritten.

Initial mixed-source journey passed; final trial adds cross-origin mutation and cross-course ingestion-job injection negatives.

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
| Executed / passed assertions | 139 / 139 |
| Distinct assertion labels | 106 |
| Injected / external provider calls | 12 / 0 |
| External provider cost | USD 0 |
| Wall time | 2.418377s |
| Peak process RSS | 275,054,592 bytes |

Assertion counts describe a sequential contract, not sample size, accuracy or
capacity. Every executed assertion and failed stage appears in the record. No
confidence interval or educational effect is estimated. Failure details are
classified as setup/integration rather than a model-quality score.

The full journey retained four reviewed source jobs, both published releases and
approved profiles/domain models. Five real service turns generated a visible
source-level gap group; the active denominator was six, including the non-gap
learner. Smaller groups remained suppressed. Professor review was reread from
its audit outcome. Withdrawal blocked generation before and after restore.

After backup verification, the original runtime directory was moved aside; the
new application restored source bytes/checksums, jobs, cohort/review and twelve
course-A messages. A new sentinel-course turn used its own forty-tick source,
not the same-named nine-tick source in the other course. Both source families and
authority behavior therefore remained exercised after relocation. Backup schema
was 18 with 12 data files. No model-quality conclusion follows from fixture answers.

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
