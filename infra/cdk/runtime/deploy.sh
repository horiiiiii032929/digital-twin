#!/bin/bash
set -euo pipefail
umask 077
cd /opt/digital-twin/release
# The archive is extracted under umask 077; the non-secret proxy config must be readable by UID 1000.
chmod 0644 Caddyfile
mountpoint -q /var/lib/digital-twin
exec 9>/opt/digital-twin/deploy.lock
flock -n 9
SECRET_FILE=$(mktemp /run/digital-twin-secret.XXXXXX)
ENV_FILE=$(mktemp /run/digital-twin-env.XXXXXX)
trap 'rm -f "$SECRET_FILE" "$ENV_FILE"' EXIT
aws secretsmanager get-secret-value --secret-id "$RUNTIME_SECRET_ARN" \
  --region "$AWS_REGION" --query SecretString --output text > "$SECRET_FILE"
export SECRET_FILE ENV_FILE
python3 - <<'PY'
import json, os
from pathlib import Path
secret = json.loads(Path(os.environ['SECRET_FILE']).read_text())
names = ('OPENAI_API_KEY', 'APP_LEARNING_GAP_HMAC_SECRET')
for key in names:
    value = secret.get(key)
    if not isinstance(value, str) or not value.strip() or any(c in value for c in '\r\n\x00'):
        raise SystemExit(f'Runtime secret requires a nonempty, single-line {key}')
if len(secret['APP_LEARNING_GAP_HMAC_SECRET']) < 32:
    raise SystemExit('HMAC secret must contain at least 32 characters')
url = os.environ['APP_URL']
if not url.startswith('https://') or any(c in url for c in '\r\n'):
    raise SystemExit('Invalid HTTPS application URL')
Path(os.environ['ENV_FILE']).write_text(Path('runtime.env').read_text() +
    f'APP_ALLOWED_ORIGINS={url}\n' + ''.join(f'{key}={secret[key]}\n' for key in names))
PY
REGISTRY=${API_IMAGE%%/*}
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker pull "$API_IMAGE"
docker pull "$WEB_IMAGE"
docker logout "$REGISTRY"
docker network inspect digital-twin >/dev/null 2>&1 || docker network create digital-twin
# Validate the release binding before taking the running service down.
docker run --rm --env-file "$ENV_FILE" "$API_IMAGE" python -c \
  'from services.api.app.config import AppSettings; AppSettings.from_env()'
COMMON=(--network digital-twin --restart unless-stopped --init --read-only
  --tmpfs /tmp:rw,noexec,nosuid,size=256m --security-opt no-new-privileges:true
  --cap-drop ALL --pids-limit 256 --log-driver awslogs
  --log-opt "awslogs-region=$AWS_REGION" --log-opt "awslogs-group=$LOG_GROUP")
# Stop workers first. Preserve old images and the data volume for explicit rollback.
for service in worker api web; do
  if docker container inspect "digital-twin-$service" >/dev/null 2>&1; then
    docker stop --time 60 "digital-twin-$service"
    docker rm "digital-twin-$service"
  fi
done
docker run -d --name digital-twin-api "${COMMON[@]}" --memory 2g \
  --env-file "$ENV_FILE" --mount type=bind,src=/var/lib/digital-twin,dst=/var/lib/digital-twin \
  --log-opt awslogs-stream=api "$API_IMAGE" \
  uvicorn services.api.app.pilot:create_pilot_app --factory --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips='*'
READY=false
for attempt in $(seq 1 60); do
  if docker exec digital-twin-api python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready', timeout=3)"; then
    READY=true; break
  fi
  sleep 5
done
[ "$READY" = true ] || { echo 'API readiness failed; inspect CloudWatch logs and roll back.' >&2; exit 1; }
python3 bootstrap_admin.py
docker run -d --name digital-twin-worker "${COMMON[@]}" --memory 1g \
  --env-file "$ENV_FILE" --mount type=bind,src=/var/lib/digital-twin,dst=/var/lib/digital-twin \
  --log-opt awslogs-stream=worker "$API_IMAGE" python -m scripts.run_ingestion_worker
docker run -d --name digital-twin-web "${COMMON[@]}" --memory 256m \
  --cap-add NET_BIND_SERVICE -p 80:80 --tmpfs /data:rw,size=32m --tmpfs /config:rw,size=16m \
  --mount type=bind,src=/opt/digital-twin/release/Caddyfile,dst=/etc/caddy/Caddyfile,readonly \
  --log-opt awslogs-stream=web "$WEB_IMAGE"
printf 'Release containers started. Verify HTTPS and administrator access at %s.\n' "$APP_URL"
