# Evaluation result: deployable-product-foundation-v1-development-001

## Run identity

- Component: single-host deployment and conversation orchestration architecture
- Status: local development qualification complete; external HTTPS rehearsal pending
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Code revision: `9855579f252a417beaeba0fad658a614fea65c22`
- Working tree: dirty with the prospective issue #88 implementation
- Dataset/corpus: synthetic invited accounts, one authored PDF, approved policy,
  one course/release/conversation/answer, restart, clean restore, and 100
  read-only capacity requests
- Network/private data: zero external calls; no private course or student data
- Reproduction: `npm run verify:deployable-foundation` then
  `npm run benchmark:deployable-foundation-development`
- Generated artifact:
  `reports/generated/deployable-product-foundation-v1-development-001/result.json`
- Generated artifact SHA-256:
  `f0f7c4b5b1c964e457ce7bc4f781008893fb4db13ac7bfe848e9b107f03f3c91`

## Decision context

The control was the existing `A0-local-demo`: synthetic account headers,
in-memory onboarding, synchronous local ingestion, no HTTPS package, and manual
recovery. The candidate was `A1-single-node-staging`: invite credentials,
opaque cookie sessions, server-enforced roles/tenancy, SQLite migrations/WAL,
content-addressed files, leased ingestion jobs, Caddy HTTPS packaging,
redacted observability, lifecycle controls, and verified backup/restore.

The candidate kept the selected retrieval, prompt/generator, policy, and
citation contracts replaceable. The local run used the deterministic generator
and made no provider call; DeepSeek activation and hard call/USD caps were
tested separately without spending provider budget.

## Result

The candidate passed **41/41 frozen local checks**. The journey covered:

- administrator login and professor/student invitation;
- professor course creation, membership assignment, policy approval, PDF
  enqueue/idempotency, worker completion, deterministic release preflight, and
  publication;
- student credential login, assigned-course isolation, grounded answer,
  source/version/page/bounding-box citation, and authorized original crop;
- API/repository restart with account, object, conversation, and citation
  survival;
- checksum-verified backup and clean-target restore;
- explicit fallback to the existing synthetic `A0` demo; and
- password rotation/reset/revocation, rate limits, origin checks, migrations,
  worker recovery, export/retention/deletion, alert thresholds, and provider
  budget tests in the verification suite.

Rendered browser QA also exercised professor setup-to-delivery navigation,
course creation, reload and deep-link recovery, and course switching at the
default desktop viewport and a 390 x 844 mobile viewport. The console had no
warnings or errors. This is synthetic interaction QA, not human usability
evidence.

## Operational measurements

| Measure | Result | Frozen gate |
| --- | ---: | ---: |
| 100-request error rate | 0.0% | 0.0% |
| API p50 / p95 | 2.345 / 2.964 ms | p95 <= 750 ms |
| Throughput | 412.911 requests/s | diagnostic |
| Queue-to-ingestion complete | 52.455 ms | <= 10,000 ms |
| Peak process RSS | 324,616,192 bytes (0.30 GiB) | < 4 GiB |
| Database / runtime files | 204,800 / 251,579 bytes | diagnostic |
| Backup / restore | 9.325 / 7.810 ms | complete and checksum-valid |
| Backup | 52,971 bytes, schema v5, seven data files | diagnostic |
| External provider calls / cost | 0 / USD 0 | zero for this run |

The benchmark ran on one Apple Silicon development host through FastAPI's test
client. It excludes public network/TLS and external generation latency, so the
numbers are qualification evidence for the local foundation, not production
capacity claims.

## Security and recovery review

`X-Account-ID` failed closed in staging. Secure/HttpOnly/Strict cookies,
unsafe-request Origin enforcement, role/course/user checks, source signature
and size validation, path containment, safe error messages, structured
content-free logs, and administrator-only metrics passed automated checks.
Migrations passed clean install, legacy upgrade, checksum drift rejection, and
transactional rollback. Leased jobs passed duplicate, cancel, retry, and
expired-worker recovery cases.

Lifecycle review found and corrected one prospective issue before this result:
successful ingestion records are retained while releases may depend on their
source lineage. Course deletion now removes the database graph and tracked raw
plus derived source, region, and figure files. Account/course deletion remains
an explicit confirmed operator action and does not silently erase backups.

## Decision

- Outcome: **Go Deeper**
- Selected candidate for staging rehearsal: `A1-single-node-staging`
- Rollback: `A0-local-demo`, deterministic generation, BM25 retrieval,
  previous image tag, and previous data volume
- Issue #88 closure: not yet; public DNS/certificate issuance and a host-side
  restore/walkthrough remain the final external evidence

This follows the pre-registered rule: all local gates passed, but an external
host/domain rehearsal is still missing. The Docker Compose graph validates.
Two container build attempts stalled while resolving public base-image metadata
from Docker Hub/GHCR in the current environment and were stopped without
changing runtime state; this is recorded as an environment limitation rather
than a passed image-build claim.

## Cost and limitations

A 2-vCPU/4-GiB DigitalOcean Basic Droplet is listed at USD 24/month as of
2026-08-19 and is used only as a planning comparator. Domain, backup, tax,
external inference, and excess egress are separate; no host was purchased or
selected. See [official pricing](https://www.digitalocean.com/pricing/droplets).

The result does not establish public HTTPS, real-course ingestion quality,
external-provider latency/cost, multi-host scaling, MFA/SSO, encrypted off-host
backup, external paging, human usability, learning impact, or a production SLA.
The next evidence must be a controlled staging deployment followed by the
separate pilot/release evaluation; it must not open historical held-out data.
