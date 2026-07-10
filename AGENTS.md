# Repository Guidelines

## Project Structure & Module Organization

This repository is a research and prototype workspace for a Digital Twin teaching system. Keep domain code in `src/`, API transport code in `services/`, frontend applications in `apps/`, repeatable utilities in `scripts/`, tests and manual verification notes in `tests/`, and implementation-facing documentation in `docs/`. Research process material belongs in `research/`, with experiment plans under `research/04_experiments/` and evaluation material under `research/05_evaluation/`. Use `data/raw/`, `data/interim/`, `data/processed/`, and `data/external/` for local datasets only; these buckets are ignored by default. Generated reports go in `reports/generated/`, while long-lived report assets belong in `reports/`.

## Build, Test, and Development Commands

The repository uses uv for Python and npm workspaces for the frontend:

- `uv sync --locked --dev`: install the locked Python API and test dependencies.
- `npm ci`: install the locked frontend dependencies.
- `npm run dev:api`: start the FastAPI service on port 8000.
- `npm run dev:web`: start the Vite frontend on port 5173.
- `npm run check`: run Python tests, frontend tests, lint, and the production build.
- `rg --files`: inspect tracked repository files quickly.
- `git status --short`: confirm changed files before opening a PR.

Document any new build, evaluation, or ingestion command in the relevant `README.md` when adding tooling, and keep `npm run check` aligned with required CI checks.

## Coding Style & Naming Conventions

Prefer small, explicit modules and scripts with descriptive snake_case names, for example `scripts/validate_sources.py` or `src/retrieval_baseline.py`. Use Python conventions when adding Python code: 4-space indentation, snake_case functions and variables, PascalCase classes, and clear type hints for public helpers. Keep Markdown headings sentence-style and concise. Avoid committing generated outputs unless they are intentional review artifacts.

## Testing Guidelines

Place automated tests, fixtures, and manual verification notes under `tests/`. Cover source normalization, retrieval behavior, prompt and policy configuration, evaluation scoring, and privacy/data exclusion checks. Name Python tests `test_<behavior>.py` and test functions `test_<expected_outcome>`. Prefer synthetic or anonymized fixtures over real course, instructor, or student data.

## Commit & Pull Request Guidelines

Recent commits use short, imperative summaries such as `Scaffold research workspace`; keep that style and make the first line specific. Pull requests should follow `.github/PULL_REQUEST_TEMPLATE.md`: include a summary, linked GitHub Project item or issue, iteration, area, evidence, verification steps, documentation updates, and confirmation that sensitive data is excluded.

## Security & Configuration Tips

Treat instructor materials, transcripts, student interactions, and consent records as sensitive. Do not commit `.env` files, raw datasets, local model artifacts, run outputs, or private consent records. Use synthetic examples in docs and tests, and record dataset permissions before using sources in experiments.
