# Evaluation result: deployable-product-foundation-v2-container-001

## Run identity

- Component: single-host container build, HTTPS runtime, and recovery boundary
- Status: local container qualification complete; public-host rehearsal pending
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Code revision: `1fcd6fd94747dc484ecf692271ff6398845706eb`
- Working tree: clean implementation revision; evidence documentation followed
- Plan: inherited frozen gates and decision rule from
  `2026-08-19-deployable-product-foundation-plan.md`
- Runtime: Docker Engine 28.5.1, Linux ARM64 containers on an Apple Silicon
  development host
- Data: synthetic administrator, professor, student, course, approved policy,
  authored one-page PDF, release, conversation, answer, and citation only
- Network/model boundary: public registries supplied build dependencies; zero
  external model calls and no private or held-out data
- Generated live result:
  `reports/generated/deployable-product-foundation-live-container/result.json`
- Generated result SHA-256:
  `473fa49b6bca16959e15b1353041d98a2b87b707bf1efcb706420b7739399008`

## Why this run exists

The preceding V1 development result passed its in-process gates but did not
claim a container build because registry metadata resolution stalled. This
corrective run exercised the documented Compose build and live runtime. It
found two real deployment defects before the final run:

1. API and worker services concurrently exported the same image tag, creating
   a BuildKit race after both image contents had built.
2. The staging ASGI entrypoint eagerly instantiated the legacy demo database
   under the read-only application tree before selecting configured storage.

The worker now reuses the one API build, and the demo compatibility store is
imported only in explicit demo mode. The Caddy image was also hardened from a
root process to a dedicated UID/GID 1000 user. Regression tests cover the
shared-image graph and staging entrypoint.

## Exact candidate

- Candidate: `a1-single-node-staging-v2`
- API image:
  `sha256:f879ae4cb275174b9b233a5a7276a6510cec3453dc16a83f40f3891fbe3bde42`,
  252,671,671 bytes, runtime user `app`
- Web image:
  `sha256:cb87eb79cdbbda694c864b220f76ae008446535a0308b3f068103d555976a582`,
  21,904,167 bytes, runtime user `caddy`
- Resolved bases: Node 24 Alpine
  `sha256:71d7f07420e0acab162781f0bae22c18a1d04d4704594a6cd7d1f5cbb87cb0d7`,
  UV Python 3.12 Bookworm Slim
  `sha256:d2dad1ecbe1e1aeb7e67bb23aa6da33d85b0ea513a82fbcafc695024527b2c77`,
  and Caddy 2.10 Alpine
  `sha256:aee41d1ced04e14296ef53ad4f59ad6c7e48b6eda03459d46b34c61d1c1d3e03`
- Same-origin Caddy HTTPS, secure opaque cookies, deterministic generator,
  SQLite schema v5/WAL, content-addressed objects, and leased worker

## Result

The final candidate passed **25/25 live HTTPS checks**:

- 15/15 complete journey checks through Caddy HTTPS: readiness, administrator
  login, secure cookie flags, invitations, unsafe-origin and synthetic-header
  rejection, professor course/membership/policy configuration, asynchronous
  PDF ingestion, deterministic release preflight/publication, isolated student
  access, grounded answer, source/page/bounding-box lineage, and authorized
  original-region crop;
- 5/5 checks after checksum-verified restoration into a separate Compose
  project and fresh database/object/Caddy volumes; and
- 5/5 checks after switching back to the untouched original project/volume,
  covering container restart and operational rollback durability.

The documented multi-stage build completed and exported both images. HTTP
redirected to HTTPS with 308. Readiness returned database and object-store
success through HTTP/2. Caddy issued a local-CA certificate and served HSTS,
CSP, permissions, referrer, content-type, and frame protections. Local Caddy
TLS proves the packaged HTTPS path, not public DNS or publicly trusted
certificate issuance.

## Operational measurements

| Measure | Result | Gate |
| --- | ---: | ---: |
| Full live journey | 15/15 | 100% |
| Clean-restore replay | 5/5 | 100% |
| Original-volume rollback replay | 5/5 | 100% |
| Live API p95, 25 requests | 6.760 ms | <= 750 ms |
| Queue to worker completion | 818.463 ms | <= 10,000 ms |
| Full live journey duration | 1,664.224 ms | diagnostic |
| API / worker / web memory | 228.4 / 72.65 / 14.32 MiB | combined < 4 GiB |
| Final backup | 93 KiB, schema v5, 13 data files | checksum-valid |
| Final backup SHA-256 | `e40b8bea73a233ea50974f6aa6ae49706a788d534e4383c018575324797f9900` | diagnostic |
| External provider calls / cost | 0 / USD 0 | zero for this run |

The memory observation is one no-load snapshot, not a production capacity or
concurrency claim. Public network and external generation latency remain
outside these measurements.

## Security and recovery review

- API and worker run as the non-root `app` user; Caddy runs as non-root
  `caddy` while retaining only the base image's low-port bind capability.
- A scan of 245 final candidate log lines found no synthetic passwords or the
  uploaded course sentence. Request logs contain routes, identifiers, status,
  and timing rather than bodies.
- The verifier accepts only an HTTPS origin, trusts either the system roots or
  an explicitly supplied CA file, and reads all three passwords from
  environment variables. The sanitized result contains no credentials.
- The final archive restored schema v5 and 13 data files into newly created
  volumes. Credential login, course, conversation, citation, and pixel-identical
  citation crop then passed over a newly issued local certificate.
- The original project remained stopped but intact during restore and passed
  the same replay after the restored project released ports 80/443.

## Decision

- Outcome: **Go Deeper**
- Selected local container candidate: `a1-single-node-staging-v2`
- Preserved rollback: `A0-local-demo`, plus the untouched previous staging
  image tag and data volume during recovery
- Superseded limitation: the V1 unclaimed image-build limitation is resolved;
  the historical result remains unchanged
- Issue #88 closure: not yet

The frozen decision rule still requires public-host evidence before Keep. The
only remaining architecture gates are public DNS and trusted certificate
issuance, a clean restore on the chosen host, and the same credentialed
professor-upload-to-student-citation walkthrough over that public HTTPS origin.
This run does not establish real-course quality, human usability, external
generator behavior, multi-host scale, institutional SSO, or a production SLA.
