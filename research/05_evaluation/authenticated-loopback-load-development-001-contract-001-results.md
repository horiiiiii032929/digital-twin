# authenticated-loopback-load-development-001-contract-001

The initial evaluator failed to preserve its shutdown budget summary: the child exited -15 after four successful requests. The raw `contract-only` decision is preserved but is superseded here by **Refine: incomplete evaluator evidence**. This is a harness shutdown defect, not a product/provider failure. The successor installs a graceful signal handler and requires normal exit and complete provider evidence.

## Method and provenance

Instrument `authenticated-loopback-load-development-001`; [prospective plan](../04_experiments/2026-09-06-authenticated-loopback-load-plan.md). Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty=True; per-file hashes remained unchanged. Raw output: `reports/generated/authenticated-loopback-load-development-001-contract-001`. Exact configuration, source hashes and artifact checksums are retained in the [record](records/authenticated-loopback-load-development-001-contract-001.json). The two attempts used different evaluator revisions and are not a timing comparison.

One synthetic mixed-source course and two credentialed synthetic learners each sent the same two sequential questions through an isolated Uvicorn server and real loopback HTTPS. Source upload, approval, publication and domain-model setup precede requests. The generator was injected: **4 injected calls, 0 external calls, USD 0**. Four requests are coverage within one scenario, not four independent samples.

## Results and gates

All four requests returned an answer with nonempty course/release/conversation-bound citations; HTTP failures, lineage failures and non-answer actions were zero. Both conversations retained four messages (eight total). Request p95 was 179.618 ms; peak sampled child RSS was 266878976 bytes. The fixed 15-second route gate is retained, but injected latency is not evidence about provider-backed capacity. Child exit: -15. Complete provider shutdown evidence: False. Source hashes unchanged: true. No statistical uncertainty or broad capacity estimate is warranted by this contract.

## Failure classification and decision

Operational evaluator shutdown/measurement failure; retain the unsuccessful attempt and use the successor to verify the repair.

A local task-only certificate was used without changing system trust. Neither attempt tests public TLS, cloud/Docker deployment, long-running uptime, live model quality, realistic multi-turn tutoring or human learning. No selected profile or default was changed. The immutable historical profile binding is only staging setup, not candidate qualification.
