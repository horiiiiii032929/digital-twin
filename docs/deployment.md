# Staging deployment and recovery

Status: deployable single-host candidate; public host rehearsal pending

The candidate packages the session-authenticated web app, FastAPI service,
recoverable ingestion worker, SQLite WAL database, content-addressed source
store, and Caddy automatic HTTPS on one host. It is intended for a small
invite-only pilot, not horizontal scale or an institutional SLA.

## Required boundary

The host must provide two vCPUs, four GiB RAM, persistent Docker volumes, a
public DNS name pointing to the host, and inbound TCP 80/443 plus UDP 443.
The measured development envelope used 0.30 GiB peak RSS. As a transparent
planning comparator, a DigitalOcean Basic 2-vCPU/4-GiB/80-GiB Droplet is listed
at USD 24/month as verified on 2026-08-21; backups, domain, tax, provider
inference, and egress outside the included allowance are separate. This is an
estimate, not a hosting selection. See the
[official Droplet pricing](https://www.digitalocean.com/pricing/droplets).

Create a private deployment environment file:

```bash
cp deploy/staging.env.example .env.staging
chmod 600 .env.staging
```

Set `APP_DOMAIN`, `TLS_EMAIL`, and a random bootstrap password. Keep
`APP_GENERATOR_MODE=deterministic` for the R1 demo: the four-model cascade did
not select an OpenAI generator. Do not set `OPENAI_PROFILE_SELECTED` or claim
LLM-backed autonomy. Any future direct Responses API profile still requires a
new passing result, `store: false`, exact identity checks, and process-local
call/cost caps. Never put real secrets in the example file or Git.

Keep `APP_STUDENT_TUTORING_MODE=grounded-assistant` in staging. The bounded T1
tutoring graph is implemented behind an explicit local demo/test mode, but the
runtime validator rejects it in staging until its finite multi-turn evaluation
and release-profile decision are complete.

## Temporary public R1 demo

The Sunday release candidate uses `compose.preview.yml` and a pinned
`cloudflared` image to expose the loopback web origin through a random
`trycloudflare.com` URL. Quick Tunnels are development/testing infrastructure,
do not provide an uptime SLA, and are not durable hosting. The preview disables
SSE, limits the runtime to 250 provider calls/USD 5, uses synthetic accounts and
open-licensed sources only, and preserves private Docker volumes when stopped.

```bash
npm run verify:r1-preview
npm run start:r1-preview
npm run stop:r1-preview
```

The start command launches the origin first, obtains the generated HTTPS URL,
then recreates API and worker services with that exact allowed origin. The URL
is written to the ignored `reports/generated/r1-preview-url.txt` for the local
walkthrough; it is not a production endpoint or repository artifact.

## Build and start

Validate before touching runtime state:

```bash
docker compose --env-file .env.staging -f compose.staging.yml config --quiet
docker compose --env-file .env.staging -f compose.staging.yml build
```

Assign an immutable image tag, start the services, and wait for readiness:

```bash
export APP_IMAGE_TAG=foundation-v1
docker compose --env-file .env.staging -f compose.staging.yml up -d
docker compose --env-file .env.staging -f compose.staging.yml ps
curl --fail "https://${APP_DOMAIN}/api/health/ready"
```

Caddy requests and renews the public certificate automatically. Certificate
issuance cannot pass until DNS and ports are correct. Do not weaken secure
cookies or substitute an HTTP staging origin.

## Local container and HTTPS qualification

Before using a public host, the same images and secure-cookie path can be
qualified on `localhost` with Caddy's private local certificate authority. This
does not replace the public DNS/certificate gate, but it exercises the built
images, reverse proxy, API, worker, volumes, TLS, and credentialed workflow
together. Use an isolated Compose project so existing containers and volumes
remain untouched:

```bash
export APP_DOMAIN=localhost
export TLS_EMAIL=local@example.invalid
export APP_IMAGE_TAG=foundation-v2-local
docker compose -p digital-twin-local \
  --env-file deploy/staging.env.example -f compose.staging.yml build
docker compose -p digital-twin-local \
  --env-file deploy/staging.env.example -f compose.staging.yml \
  up -d --no-build --wait
docker compose -p digital-twin-local \
  --env-file deploy/staging.env.example -f compose.staging.yml \
  cp web:/data/caddy/pki/authorities/local/root.crt /tmp/digital-twin-root.crt
```

Read synthetic/local qualification passwords without writing them to a file,
bootstrap the administrator, and run the live verifier:

```bash
read -s STAGING_ADMIN_PASSWORD
read -s STAGING_PROFESSOR_PASSWORD
read -s STAGING_STUDENT_PASSWORD
export STAGING_ADMIN_PASSWORD STAGING_PROFESSOR_PASSWORD STAGING_STUDENT_PASSWORD
BOOTSTRAP_ADMIN_PASSWORD="$STAGING_ADMIN_PASSWORD" docker compose \
  -p digital-twin-local --env-file deploy/staging.env.example \
  -f compose.staging.yml run --rm -e BOOTSTRAP_ADMIN_PASSWORD api \
  python -m scripts.bootstrap_admin --email admin@foundation.local \
  --display-name "Foundation administrator"
npm run verify:staging-https -- \
  --base-url https://localhost \
  --ca-file /tmp/digital-twin-root.crt \
  --admin-email admin@foundation.local \
  --output reports/generated/deployable-product-foundation-live/result.json
```

The result contains only synthetic account identifiers, workflow identifiers,
checks, timings, and a citation-crop checksum. It contains no passwords. After
restarting the containers or restoring the archive into a new Compose project,
replay the exact state check with:

```bash
npm run verify:staging-https -- \
  --base-url https://localhost \
  --ca-file /tmp/digital-twin-root.crt \
  --resume reports/generated/deployable-product-foundation-live/result.json
```

Provision the first administrator without printing the password:

```bash
read -s BOOTSTRAP_ADMIN_PASSWORD
export BOOTSTRAP_ADMIN_PASSWORD
docker compose --env-file .env.staging -f compose.staging.yml run --rm \
  -e BOOTSTRAP_ADMIN_PASSWORD api python -m scripts.bootstrap_admin \
  --email admin@example.edu --display-name "Pilot administrator"
unset BOOTSTRAP_ADMIN_PASSWORD
```

The administrator signs in and invites professors/students. Users should
replace temporary passwords from the account menu. Administrators can reset or
revoke an account through the authenticated admin API.

The professor opens **Course delivery** from the tutor-setup rail, creates or
resumes a course, assigns invited student account IDs, uploads approved PDFs,
and monitors recoverable ingestion jobs. A draft freezes the current approved
tutor policy plus all successful course uploads. **Run release checks** applies
deterministic gates for the active component profile, professor policy approval,
retrieval permissions, course isolation, and citation lineage. Staging rejects
a manual `passed` flag; the publish control appears only after preflight passes.

## Operations

- `GET /api/health/live` proves the process can answer.
- `GET /api/health/ready` checks the database and object-store boundary.
- `GET /api/operations/metrics` is administrator-only and returns bounded
  request counts, status counts, p50/p95, threshold alerts, and provider budget.
- API and Caddy logs are JSON. They contain identifiers, routes, status, and
  timing—not request bodies, passwords, prompts, or course text.
- The worker uses leased jobs. An interrupted job is reclaimed after lease
  expiry until its retry budget is exhausted.

Treat any non-empty `alerts` array, failed readiness, repeated worker restart,
provider budget exhaustion, or backup failure as an operator alert. The pilot
has no external pager integration; route container logs/metrics to an approved
institutional sink before broader use.

Run retention, export, or deletion only after a verified backup:

```bash
docker compose --env-file .env.staging -f compose.staging.yml exec api \
  python -m scripts.manage_runtime_data prune
docker compose --env-file .env.staging -f compose.staging.yml exec api \
  python -m scripts.manage_runtime_data export-account \
  --account-id ACCOUNT_ID --output /tmp/account-export.json
```

Deletion requires `--confirm` to exactly match the account/course ID.
Successful ingestion records are retained while releases may depend on their
lineage. Professor accounts with owned courses cannot be deleted until each
course is explicitly deleted. Course deletion removes database state plus
tracked raw and derived source artifacts. Cleanup intent is committed in a
durable queue with the database deletion, so a filesystem failure remains
visible and retryable. Shared artifacts are retained while another ingestion
job references them.

Retry pending storage cleanup explicitly after correcting the filesystem
problem:

```bash
docker compose --env-file .env.staging -f compose.staging.yml exec api \
  python -m scripts.manage_runtime_data drain-deletions
```

Retention also reconciles old unreferenced raw and derived artifacts after a
one-hour grace period. Staging release creation accepts ingestion job IDs and
resolves their successful, professor-owned chunks on the server; it does not
trust chunks returned by a browser.

## Backup and clean restore

Drain or stop the worker, create the archive outside the runtime data volume,
and copy it off-host:

```bash
docker compose --env-file .env.staging -f compose.staging.yml stop worker
docker compose --env-file .env.staging -f compose.staging.yml exec api \
  python -m scripts.backup_runtime --output /tmp/runtime-backup.zip
docker compose --env-file .env.staging -f compose.staging.yml \
  cp api:/tmp/runtime-backup.zip ./runtime-backup.zip
chmod 600 runtime-backup.zip
```

Never overwrite the active volume during a restore rehearsal. Use a distinct
Compose project so the old volumes remain the rollback:

```bash
export COMPOSE_PROJECT_NAME=digital-twin-restored
docker compose --env-file .env.staging -f compose.staging.yml run --rm --no-deps \
  -v "$(pwd)/runtime-backup.zip:/tmp/runtime-backup.zip:ro" api \
  python -m scripts.restore_runtime --archive /tmp/runtime-backup.zip
docker compose --env-file .env.staging -f compose.staging.yml up -d
```

Verify readiness, invited login, published course, conversation, and citation
crop before retiring the old project/volume.

## Rollback

For an application-image rollback, set `APP_IMAGE_TAG` to the retained previous
tag and run `up -d` without deleting volumes. For a bad publication, use the
professor release withdrawal/rollback API. For a foundation-wide fallback,
stop staging and run `APP_MODE=demo` plus `VITE_AUTH_MODE=demo` with
`npm run dev:api` and `npm run dev:web`; this restores the synthetic local demo
and does not delete staging evidence.

The reproducible local qualification commands are:

```bash
npm run verify:deployable-foundation
npm run benchmark:deployable-foundation-development
```
