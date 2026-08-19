# Deployable product foundation plan

Date: 2026-08-19

Run ID: `deployable-product-foundation-v1-development-001`

Status: frozen before implementation and measurement

## Decision question

Can the bounded local Course Digital Twin become a secure, recoverable,
invite-only staging product on one modest host without changing the selected
retrieval, generator, tutor-policy, or multimodal evidence decisions?

## Baseline and candidate

- `A0-local-demo`: synthetic `X-Account-ID`, in-memory onboarding state,
  synchronously parsed local files, implicit SQLite schema creation, localhost
  CORS, no deployment package, and manual recovery.
- `A1-single-node-staging`: password-authenticated invite-only accounts, opaque
  revocable cookie sessions, enforced administrator/professor/student RBAC,
  SQLite WAL with ordered schema migrations, content-addressed filesystem
  object storage, a leased database-backed ingestion queue, same-origin web/API
  deployment behind automatic HTTPS, structured redacted logs, readiness and
  metrics endpoints, rate limits, backup/restore, and release rollback.
- Alternative not selected by this run: managed Postgres, S3-compatible object
  storage, and an external queue. Those adapters become necessary before
  horizontal scaling, but add credentials, cost, network failure modes, and
  operational dependencies that are not required to test an invite-only pilot
  on one host.

The current demo remains an explicit rollback. Infrastructure interfaces and
data exports must leave a future managed-service migration possible.

## Prediction

`A1-single-node-staging` should satisfy the complete professor-upload through
student-citation workflow after API and worker restarts, reject synthetic
identity outside demo/test mode, restore from a clean backup, and remain within
a two-vCPU/four-GiB staging envelope. It will not establish horizontal scaling,
multi-region recovery, institutional SSO, or production SLA evidence.

## Data and permissions

- Synthetic invited accounts, courses, policies, PDFs, and questions only.
- No private course material, real student data, external model call, or paid
  provider is permitted in this run.
- Existing selected component profiles and sealed/held-out evaluation sets are
  read-only and are not rerun.

## Architecture boundaries

### Identity and tenancy

- No public signup.
- Passwords use a versioned `scrypt` hash with per-account salt.
- Session credentials are random opaque tokens; only SHA-256 token digests are
  stored. Sessions expire, can be revoked, and are delivered in `HttpOnly`,
  `Secure` outside local mode, `SameSite=Strict` cookies.
- Unsafe cookie-authenticated requests require an allowed same-origin value.
- `X-Account-ID` is accepted only in explicit `demo` or `test` mode.
- Every professor, student, source, release, conversation, citation, and job
  access remains role- and course-scoped.

### Persistence and jobs

- One SQLite database uses WAL, foreign keys, a busy timeout, and explicit
  ordered migrations.
- Original and derived files are content-addressed and written atomically below
  a configured data root. Raw paths are never returned to clients.
- Ingestion jobs are idempotent, leased, retryable, cancellable, and recover
  expired `running` leases after worker failure.
- Publication remains transactional and release rollback remains available.

### Deployment and operations

- A reproducible container build serves the web and API through an HTTPS
  reverse proxy with persistent database/object volumes.
- Configuration is environment-specific and fails closed when staging secrets,
  origins, or data paths are unsafe.
- Logs contain request/job identifiers and aggregate timings, not credentials,
  raw prompts, course text, or student message content.
- Liveness, readiness, bounded operational metrics, backup, restore, retention,
  and rollback commands are documented and tested.

## Metrics and hard gates

| Measure | Frozen gate |
| --- | --- |
| Synthetic identity rejection | `X-Account-ID` rejected in staging, 100% |
| Credential/session behavior | login, expiry, logout/revocation, and disabled-account denial, 100% |
| Role/course/user isolation | all cross-role, cross-user, and cross-course cases denied, 100% |
| Restart durability | account, source, job, release, conversation, answer, citation, and audit state survive restart, 100% |
| Job recovery | duplicate enqueue is idempotent; retry, cancel, failure, and expired-lease recovery pass, 100% |
| Migration | clean install and upgrade from the current schema pass; failed migration rolls back, 100% |
| Backup/restore | restored clean environment reproduces database and object checksums, 100% |
| End-to-end workflow | invited professor upload/publish to invited student answer/original-region citation, 100% |
| Security controls | secure cookie flags, origin enforcement, file validation, size quota, rate limit, redacted logs, and secret exclusion pass, 100% |
| Availability | liveness stays independent; readiness fails when required database/object boundaries fail, 100% |
| Capacity | 100 synthetic student requests: error rate 0%, API p95 at most 750 ms excluding external generation, peak RSS below 4 GiB |
| Ingestion operations | synthetic PDF queue-to-complete p95 at most 10 s on the development host |
| Rollback | documented switch to `A0-local-demo` succeeds without deleting staging evidence |

Record p50/p95 latency, throughput, peak RSS, database/object bytes, error rate,
log-redaction checks, and estimated single-host monthly cost. A gate is not
relaxed after measurement.

## Failure classes

Classify failures as identity, authorization, session, migration, persistence,
object-storage, queue/lease, ingestion, publication, recovery, configuration,
network/TLS, observability, security, capacity, or evaluator defects.

Any committed credential/private artifact, authorization leak, missing source
lineage, unrecoverable destructive migration, unregistered result, or access to
sealed/held-out content invalidates the run.

## Reproduction

Planned commands:

```text
npm run verify:deployable-foundation
npm run benchmark:deployable-foundation-development
npm run check
```

Detailed generated output remains ignored under
`reports/generated/deployable-product-foundation-v1-development-001/`. A
sanitized result summary and canonical machine-readable record are committed.

## Decision rule

- **Keep** `A1` only if every hard gate passes and a clean deployment/restore
  rehearsal succeeds.
- **Refine** if the architecture is sound but a repairable security,
  operational, or capacity gate fails.
- **Go Deeper** if all local gates pass but an external host/domain rehearsal
  is the only missing evidence.
- **Drop** if the candidate weakens isolation, loses durable state, cannot
  restore, or requires irreversible coupling that removes the demo rollback.

## Limitations

- A one-host qualification cannot establish horizontal scale or multi-region
  availability.
- Local filesystem objects require a persistent attached volume and verified
  off-host backups.
- Password login is suitable for an invite-only pilot, not institutional SSO.
- HTTPS deployment requires a user-controlled host/domain or approved tunnel;
  local container tests cannot prove public DNS and certificate issuance.
