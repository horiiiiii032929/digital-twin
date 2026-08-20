FROM node:24-alpine@sha256:d32cdf619f63fe0471182d08996dd516c6275bb5fd31ae06e55a570bd9e1ad43 AS web-build
WORKDIR /build
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci
COPY apps/web apps/web
ARG VITE_AUTH_MODE=session
ARG VITE_API_BASE_URL=
ENV VITE_AUTH_MODE=${VITE_AUTH_MODE}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm --workspace apps/web run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58 AS api
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY services services
COPY src src
COPY scripts/run_ingestion_worker.py scripts/run_ingestion_worker.py
COPY research/05_evaluation/profiles research/05_evaluation/profiles
RUN uv sync --locked --no-dev \
    && useradd --create-home --uid 10001 app \
    && install -d -o app -g app /var/lib/digital-twin
USER app
EXPOSE 8000
CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]

FROM caddy:2.10-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d AS web
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=web-build /build/apps/web/dist /srv
RUN addgroup -S -g 1000 caddy \
    && adduser -S -D -H -u 1000 -G caddy caddy \
    && chown -R caddy:caddy /data /config /srv /etc/caddy
USER caddy
EXPOSE 80 443 443/udp
