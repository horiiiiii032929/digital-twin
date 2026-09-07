# Evaluation result: schema18-foundation-development-20260906-001

## Run identity

- Completed / **Go Deeper**, 2026-09-06 Singapore time (2026-09-05 16:35 UTC).
- Source revision `e441193c7fa1260ed327ebf43c59483f85817be8`, **dirty**.
- Owner: repository-authorized Codex development verification.
- [Machine record](records/schema18-foundation-development-20260906-001.json).
- Raw output: `reports/generated/schema18-foundation-development-20260906-001/result.json`.
- Existing harness: `scripts/verify_deployable_foundation.py`; original harness ID
  `deployable-product-foundation-v7-post-correctness-requalification-001` retained
  separately. The current result has a distinct ID and does not overwrite it.
- Python 3.12.13, macOS 26.5.2 arm64. Verifier hash is retained in the record.

## Decision context

Question: did schema18 source-review persistence break the existing credentialed
foundation, backup or clean restore? Prediction: all existing 42 checks remain
passing. The harness's retained synthetic A1 control uses AnyHit and deterministic
generation. Its historical baseline was not rerun; this is regression evidence,
not a new architecture tournament. The unchanged hard gates require all checks,
zero request errors, GET p95 at most 750 ms, ingestion within 10 seconds and peak
RSS below 4 GiB.

## Data, configuration and reproduction

The verifier creates a fresh temporary runtime, synthetic accounts, one course
and synthetic PDF. The dataset ID remains
`synthetic-deployable-foundation-v7-post-correctness`; it is development data with
no private material. The fixed 42-item checklist spans account and publication
flow, citation access, restart, backup/restore and rollback. It is not a sample
of independent student outcomes; confidence intervals are not meaningful here.

The application is in staging mode with secure cookies, a 3,600-second session,
100 login attempts/minute and 1,000 authenticated requests/minute. Requests run
inside FastAPI TestClient; no actual server port, Docker container, TLS trust or
provider is exercised. AnyHit is explicitly injected. No final profile is
selected by this run.

Repeat the same harness via:

```sh
uv run pytest -q tests/test_verify_deployable_foundation.py
```

For a new durable result, call `run_acceptance()` in an exclusive fresh output
wrapper, retain the original harness ID and assign a new run ID. Do not reuse
this result's path. The recorded source state was dirty and only the verifier
hash was captured; the full dirty tree was not snapshotted. Exact reproduction
of all uncommitted runtime bytes is therefore not established.

## Aggregate and operational results

| Measure | Result | Interpretation |
| --- | ---: | --- |
| Existing hard checks | 42/42 | All passed; individual checks retained in record |
| Backup schema / files | 18 / 7 | Checksums and clean restored workflow passed |
| Queue-to-ingested PDF | 61.508 ms | Synthetic local ingestion only |
| Backup / restore | 19.230 / 9.311 ms | Small temporary runtime |
| Course-list GET errors | 0/100 | Sequential TestClient requests |
| Course-list GET p50 / p95 | 3.279 / 7.363 ms | Does not measure tutoring latency |
| Peak RSS | 334,839,808 bytes | Below 4 GiB harness threshold |
| External calls / cost | 0 / USD 0 | No external generation |

No failing gate or schema18 recovery defect was found. The measured 233.712
requests/second is a sequential in-process course-list loop, **not deployed
capacity or LLM-backed throughput**. It must not be presented as such.

## Separate routine test evidence

A separate 24-test execution passed. The new tests in
`tests/services/test_schema18_product_recovery.py` confirm reviewed txt/Markdown
job bytes, checksums, attestation and release-ready chunks after clean restore.
They also run three independent students through two actual ASGI tutoring POSTs
each, checking cited replies and durable turns. Those six requests use
network-free deterministic test components. They are not part of the 42-check
run's counts or timing metrics and provide no factual-quality/capacity estimate.

## Decision and follow-up

**Go Deeper**: keep schema18 integration for development; select no new component
and change no release profile. Run the eventual exact deployed candidate through
model-backed tutoring POST load, controlled restart and clean restore, including
pending outreach and duplicate-delivery checks. The
[recovery verification note](../../docs/research/2026-09-06-schema18-recovery-verification.md)
contains that execution plan.

This result establishes a synthetic regression pass, not final-candidate
qualification, public hosting, professor fidelity or educational benefit. The
important distinction is that a schema migration can be verified independently
without treating a cheap GET timing loop as the performance of the tutor.
