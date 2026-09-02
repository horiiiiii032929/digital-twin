# Local R1 operator runbook

Status: production-like local release candidate; no hosted-production claim

This runbook starts the invite-only Course Digital Twin at
`https://localhost:8443`. It runs the API, ingestion worker, scheduled-outreach
worker, and Caddy-served web application in containers. The committed example
retains the historical T1-v1 safe default. The qualified private environment
selects the exact governed V2.1 profile and retains T0 as a one-setting
rollback. Deterministic fast paths do not call a provider; complex V2.1 turns
require the locally configured OpenAI credential.

## One-time setup

Create a private environment file and replace every placeholder with a long,
unique local value:

```bash
cp deploy/local-r1.env.example .env.local-r1
chmod 600 .env.local-r1
```

Keep `.env.local-r1` outside Git. `APP_LEARNING_GAP_HMAC_SECRET` must be an
unpredictable value of at least 32 bytes. The three staging passwords are used
only by the local bootstrap and acceptance verifier. Leave
`OPENAI_API_KEY` empty for the default deterministic qualification.

The committed example intentionally selects:

```text
APP_GENERATOR_MODE=deterministic
APP_STUDENT_TUTORING_MODE=bounded-tutoring-graph
APP_T1_QUALIFICATION_RESULT_PATH=/app/research/05_evaluation/records/autonomous-tutoring-r1-confirmation-002.json
```

Do not point governed V2.1 at that historical T1-v1 result. Staging fails
closed unless the governed mode is bound to a separate passing record whose
selected implementation is `governed-autonomous-tutoring-graph-v2-1`.

The historical governed V2.1 experiment used the following values. They are
retained for diagnosis only and must not be treated as a current qualified
release configuration:

```text
APP_GENERATOR_MODE=deterministic
APP_EVIDENCE_GATE_MODE=question-targeted-ambiguity-safe-v2
APP_STUDENT_PROFILE_PATH=/app/research/05_evaluation/profiles/student-tutor-r1-local-candidate-v2.json
APP_STUDENT_TUTORING_MODE=governed-autonomous-tutoring-graph-v2.1
APP_AUTONOMY_PLANNER_MODE=openai-gpt-5.6-terra
APP_T1_QUALIFICATION_RESULT_PATH=/app/research/05_evaluation/records/governed-full-autonomy-v2-1-confirmation-001.json
```

That historical qualification record does not bind the evidence gate and its
release selection was revoked by `main-commit-audit-resolution-001`. Current
startup therefore rejects this block by design. Keep the committed bounded
T1-v1/T0 configuration until a fresh architecture comparison selects and binds
a successor.

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
  --profile-version v2.1-grounding-011 \
  --expected-tutoring-mode governed-autonomous-tutoring-graph-v2.1 \
  --output reports/generated/local-r1-live-journey.json
```

After restarting all services, verify the same durable workflow:

```bash
docker compose --env-file .env.local-r1 -f compose.local-r1.yml restart
npm run verify:staging-https -- \
  --base-url https://localhost:8443 \
  --ca-file reports/generated/local-r1-caddy-root.crt \
  --resume reports/generated/local-r1-live-journey.json \
  --output reports/generated/local-r1-restart-journey.json
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

Restore governed V2.1 only with a qualification record that binds the exact
profile, planner, and evidence gate. The historical confirmation-001 record
does not contain the required evidence-gate binding and is not a current
release authorization.

## Governed autonomy operating workflow

The V2.1 product implementation and exact local profile are qualified for the
development Mac. The governed workflow is:

1. The professor creates and approves an explicit teaching profile.
2. A release binds the approved profile and current evidence.
3. The professor defines approved objectives, actions, frequency, and pause or
   kill-switch state.
4. The worker leases one due opportunity and completes one finite planning,
   grounding, validation, and delivery job.
5. The professor can inspect structured decisions, deterministic checks,
   delivery, linked learner outcomes, and next wake-up; an individual learner
   goal can be cancelled without stopping the whole course.
6. The student can consent, pause check-ins for seven days, resume, reply,
   dismiss, and inspect active learning goals.

Run its network-free implementation acceptance check with:

```bash
npm run verify:governed-autonomy-v2-1-implementation
```

This exercises 30 simulated days, restart, bounded execution, duplicate
suppression, and goal expiry against the real governed autonomy service. It is
software regression evidence, not provider-backed academic evaluation.

Validate and simulate the separately frozen provider boundary with:

```bash
npm run validate:governed-autonomy-v2-1-provider-integration
npm run simulate:governed-autonomy-v2-1-provider-integration
npm run preflight:governed-autonomy-v2-1-provider-integration
```

The preflight performs OpenAI model-metadata checks but makes no inference
call. Historical provider-integration limits remain evidence for that earlier
checkpoint; the selected local profile is instead bound to the passing
confirmation record above. The API continues to fail closed if the governed
mode is paired with a missing, failing, or T1-v1-only qualification record.

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
