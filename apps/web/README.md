# Digital Twin Web Prototype

React/Vite frontend for the Sprint 1 chat-led onboarding prototype.

## Commands

- `npm run dev:web`: start the Vite dev server from the repository root.
- `npm run build:web`: run TypeScript and production build checks.
- `npm run test:web`: run Vitest API client tests.
- `npm run lint:web`: run Oxlint.

The frontend expects the FastAPI service on `http://localhost:8000`. Override it
with `VITE_API_BASE_URL` when needed.
