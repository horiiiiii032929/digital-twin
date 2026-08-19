FROM node:24-alpine AS web-build
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

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS api
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
COPY scripts scripts
COPY research/05_evaluation/profiles research/05_evaluation/profiles
COPY research/05_evaluation/records research/05_evaluation/records
COPY README.md ./
RUN uv sync --locked --no-dev \
    && useradd --create-home --uid 10001 app \
    && install -d -o app -g app /var/lib/digital-twin
USER app
EXPOSE 8000
CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]

FROM caddy:2.10-alpine AS web
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=web-build /build/apps/web/dist /srv
RUN addgroup -S -g 1000 caddy \
    && adduser -S -D -H -u 1000 -G caddy caddy \
    && chown -R caddy:caddy /data /config /srv /etc/caddy
USER caddy
EXPOSE 80 443 443/udp
