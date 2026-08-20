# Digital Twin Web Prototype

React/Vite frontend for the Sprint 1 chat-led onboarding prototype.

## Commands

- `npm run dev:web`: start the Vite dev server from the repository root.
- `npm run build:web`: run TypeScript and production build checks.
- `npm run test:web`: run Vitest API client tests.
- `npm run lint:web`: run Oxlint.

The frontend reads `VITE_*` values from the repository-root `.env` and expects
the FastAPI service through the local `/api` development proxy. Override the
origin with `VITE_API_BASE_URL` only when the frontend and API are hosted
separately.
