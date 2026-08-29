# Local R1 operator runbook

Status: production-like local release candidate; no hosted-production claim

This runbook starts the invite-only Course Digital Twin at
`https://localhost:8443`. It runs the API, ingestion worker, scheduled-outreach
worker, and Caddy-served web application in containers. It selects the exact
network-free-qualified T1 profile and retains T0 as a one-setting rollback. No
model provider key is passed to these services.

## One-time setup

Create a private environment file and replace every placeholder with a long,
unique local value:

```bash
cp deploy/local-r1.env.example .env.local-r1
chmod 600 .env.local-r1
```

Keep `.env.local-r1` outside Git. `APP_LEARNING_GAP_HMAC_SECRET` must be an
unpredictable value of at least 32 bytes. The three staging passwords are used
only by the local bootstrap and acceptance verifier.

## Build and start

```bash
npm run local-r1:config
npm run local-r1:build
npm run local-r1:up
npm run local-r1:status
```

Copy Caddy's local root certificate for verification tools:

```bash
docker compose --env-file .env.local-r1 -f compose.local-r1.yml \
  cp web:/data/caddy/pki/authorities/local/root.crt \
  reports/generated/local-r1-caddy-root.crt
chmod 600 reports/generated/local-r1-caddy-root.crt
```

Caddy's certificate is intentionally private. A normal browser will show a
certificate warning until the operator explicitly trusts this local root in
the operating-system keychain. Do not weaken secure cookies or commit the root
key. The automated verifier supplies the root certificate only to its own TLS
client.

Provision the first administrator without printing the password:

```bash
set -a
source .env.local-r1
set +a
docker compose --env-file .env.local-r1 -f compose.local-r1.yml run --rm \
  -e BOOTSTRAP_ADMIN_PASSWORD api python -m scripts.bootstrap_admin \
  --email admin@foundation.local --display-name "Foundation administrator"
unset BOOTSTRAP_ADMIN_PASSWORD
```

## Acceptance journey

The journey creates synthetic professor and student accounts, ingests a
generated PDF, approves a ten-case teaching profile preview, publishes a
release, delivers a consent-gated cited check-in, completes a two-turn T1
conversation, opens the original citation region, and checks the five-learner
privacy threshold:

```bash
set -a
source .env.local-r1
set +a
npm run verify:staging-https -- \
  --base-url https://localhost:8443 \
  --ca-file reports/generated/local-r1-caddy-root.crt \
  --admin-email admin@foundation.local \
  --expected-tutoring-mode bounded-tutoring-graph \
  --output reports/generated/local-r1-live-journey.json
```

After restarting all services, verify the same durable workflow:

```bash
docker compose --env-file .env.local-r1 -f compose.local-r1.yml restart
npm run verify:staging-https -- \
  --base-url https://localhost:8443 \
  --ca-file reports/generated/local-r1-caddy-root.crt \
  --resume reports/generated/local-r1-live-journey.json
```

## Backup and clean restore

Pause state-changing workers, produce a checksum-verified archive, and resume
the workers:

```bash
docker compose --env-file .env.local-r1 -f compose.local-r1.yml \
  stop ingestion-worker outreach-worker
docker compose --env-file .env.local-r1 -f compose.local-r1.yml \
  run --rm --no-deps \
  -v "$(pwd)/reports/generated:/host-output" \
  api python -m scripts.backup_runtime \
  --output /host-output/local-r1-runtime-backup.zip
chmod 600 reports/generated/local-r1-runtime-backup.zip
docker compose --env-file .env.local-r1 -f compose.local-r1.yml \
  start ingestion-worker outreach-worker
```

Restore only into a fresh Compose project and a different HTTPS port:

```bash
COMPOSE_PROJECT_NAME=digital-twin-r1-restore \
LOCAL_R1_HTTPS_PORT=8444 \
docker compose --env-file .env.local-r1 -f compose.local-r1.yml run --rm \
  --no-deps \
  -v "$(pwd)/reports/generated/local-r1-runtime-backup.zip:/tmp/runtime.zip:ro" \
  api python -m scripts.restore_runtime --archive /tmp/runtime.zip

COMPOSE_PROJECT_NAME=digital-twin-r1-restore \
LOCAL_R1_HTTPS_PORT=8444 \
docker compose --env-file .env.local-r1 -f compose.local-r1.yml up -d
```

Copy the restored project's Caddy root and rerun the acceptance verifier with
`--resume`. Keep the original project and volume until the restored workflow
passes.

## T0 rollback and T1 restore

Change one configuration value and recreate the three runtime services:

```bash
APP_STUDENT_TUTORING_MODE=grounded-assistant \
docker compose --env-file .env.local-r1 -f compose.local-r1.yml up -d \
  --force-recreate api ingestion-worker outreach-worker

npm run verify:staging-https -- \
  --base-url https://localhost:8443 \
  --ca-file reports/generated/local-r1-caddy-root.crt \
  --resume reports/generated/local-r1-live-journey.json \
  --mode-check --expected-tutoring-mode grounded-assistant
```

Restore the default T1 selection by running the same `up -d --force-recreate`
command without the environment override, then rerun `--mode-check` with
`bounded-tutoring-graph`.

## Stop without deleting evidence

```bash
npm run local-r1:down
```

The command preserves named volumes. Do not add `--volumes` until a verified
backup exists and the local evidence is no longer needed.

## Release boundary

This qualification supports a local R1 claim only. It does not establish
durable hosting, professor fidelity, external usability, learning outcomes,
LLM answer quality, true visual reasoning, or the sealed 10,000-case academic
result. Those claims remain gated by their separate issues and evidence.
