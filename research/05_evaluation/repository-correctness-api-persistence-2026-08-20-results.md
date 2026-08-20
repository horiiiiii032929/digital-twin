# Repository correctness API and persistence checkpoint — 2026-08-20

Status: complete checkpoint; repository-wide correctness program remains active

## Decision

Keep the corrected API, identity, publication, persistence, ingestion-queue,
and operational-readiness boundaries. Continue the frontend, verification,
tooling, and evaluation-configuration audit before any dataset, model/provider,
held-out, deployment-qualification, or release execution resumes.

## Corrected findings

- Bound live generator and retrieval adapters to exact selected-profile
  configuration and rejected provider-returned model or revision drift.
- Revalidated copied domain models at every SQLite write boundary so unchecked
  `model_copy(update=...)` values cannot bypass release, identity, citation, or
  state invariants.
- Made account-plus-credential provisioning, password-plus-session revocation,
  account revocation, and their identity audit records atomic.
- Made course-plus-owner creation atomic; made account roles, course ownership,
  and membership roles immutable; and added a database uniqueness invariant for
  one published release per course.
- Prevented direct repository publication from bypassing evaluation, evidence,
  and professor-policy gates. Published releases retain their historical passed
  evaluation when a later diagnostic preflight fails under a changed runtime.
- Rejected expired-worker completion, renewal, and failure writes; required job
  result lineage to match the claimed course source; and validated recovery
  timestamps and terminal job states.
- Bounded chunked uploads while streaming, validated source metadata before
  object storage, and aligned the staging upload limit with a 64 MiB reverse-
  proxy ceiling.
- Bounded rate-limit key storage, rejected malformed operational metrics and
  CORS origins, and made readiness check every durable runtime connection with
  a fail-closed 503 response.

## Verification

- Complete Python suite: **615 passed**.
- Focused API, identity, publication, ingestion, lifecycle, migration, and
  repository-integrity suites passed after each correction.
- Repository execution freeze remained active for all 50 protected entrypoints.
- Repository inventory remains 427 files; **156 are hash-bound and audited** and
  **271 remain pending**.
- Active runtime category: **96/96 audited**, with no open finding in the ledger.

## Boundaries and limitations

This checkpoint used only synthetic/public local fixtures. It made no model or
provider call, read no private or held-out source, changed no component
selection, and renewed no deployment claim. The frontend, remaining tests,
tooling, evaluation configurations, result/profile reconciliation, and
independent cross-review are still pending. The overall correctness decision
therefore remains **Refine / continue audit**.
