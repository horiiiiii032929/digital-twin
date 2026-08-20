# Repository correctness runtime-boundary checkpoint — 2026-08-19

Status: complete checkpoint; repository-wide correctness program remains active

## Decision

Keep the corrected runtime, persistence, ingestion, identity, provider-budget,
backup, and deletion boundaries. Continue the repository audit before any new
dataset generation, model/provider evaluation, held-out execution, deployment
qualification, or release claim.

## Corrected findings

- Replaced destructive SQLite `REPLACE` updates and made release content
  immutable after creation.
- Made migrations distinguish `None` from an explicitly empty set, reject
  unknown future versions, and initialize identity through the same versioned
  schema.
- Added a durable storage-deletion queue so failed raw or derived artifact
  deletion remains retryable; shared references are retained and old orphaned
  files are reconciled only after a grace period.
- Rejected backup/object-store symlinks, duplicate and oversized archive
  members, and partial restore; restore now stages and verifies the complete
  runtime directory before an atomic replacement.
- Bound staging release chunks to successful professor-owned ingestion jobs
  resolved on the server. Browser-supplied chunks are rejected in staging.
- Added lease renewal and safe cancellation rules for ingestion workers, plus
  cleanup of newly created derived artifacts after failed ingestion.
- Made concurrent duplicate student turns converge on one persisted response
  and derive citation titles from authoritative chunk metadata.
- Bounded password-hash parameters, equalized the missing-account password
  verification path, failed provider cost control closed when cost reporting is
  unavailable, and blocked provider options from overriding protected request
  behavior.
- Removed all known Python and JavaScript dependency vulnerabilities in the
  preceding dependency-remediation checkpoint.

## Verification

- `npm run check`: passed
- Python: 502 tests passed
- Frontend: 30 tests passed
- Frontend lint and production build: passed
- Repository execution freeze: 50/50 protected entrypoints guarded
- Repository correctness inventory: 427 files accounted for
- Python and JavaScript dependency audits: zero known vulnerabilities

Focused regressions cover migration downgrade refusal, relationship-preserving
updates, immutable releases, source-job provenance, concurrent request IDs,
lease renewal, mid-write cancellation refusal, deletion retry, shared files,
orphan reconciliation, symlink substitution, bounded backup verification, and
clean-target restore failure.

## Boundaries and limitations

This checkpoint used synthetic/public local fixtures only. It made no
model/provider call, read no private or held-out source content, and changed no
component selection. Historical retrieval and deployment results remain bound
to their recorded revisions. The deployable V6 current-match claim remains
suspended, and onboarding, retrieval, generation, evaluation, broader tooling,
frontend, and evidence/claim reconciliation audits are still pending.

Decision: **Keep / continue audit**.
