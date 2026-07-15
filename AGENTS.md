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

## Evaluation-First Engineering

Treat evaluability as a system property for the entire repository. Every new
algorithm, model, prompt, parser, ranking method, agent behavior, or architecture
boundary must be easy to compare, replace, and reproduce. Build the simplest
inspectable baseline first, then adopt a more complex alternative only when
project-specific evidence demonstrates a useful improvement.

Before implementation, define the decision question, prediction, baseline,
candidate alternatives, evaluation dataset, metrics, and important failure
cases. Keep algorithms and providers behind explicit interfaces so the same
inputs can be run through multiple implementations. Version the dataset,
configuration, model or provider name, prompt, random seed where applicable,
and code revision used for every recorded evaluation.

Every measurable component must include:

- a deterministic or seeded baseline and at least one explicit comparison when
  a replacement is proposed;
- a versioned synthetic or explicitly approved evaluation set that covers
  normal, boundary, adversarial, no-evidence, privacy, and failure cases where
  relevant;
- quality metrics chosen before the run, plus relevant latency, memory, token,
  and cost measurements;
- a reproducible command that emits inspectable per-case results and an aggregate
  summary;
- regression tests for accepted behavior and thresholds;
- failed-case classification that distinguishes data, parsing, chunking, query,
  ranking, model, policy, integration, and operational causes as applicable;
- a decision record stating whether to keep, refine, go deeper, or drop the
  candidate, with links to evidence and known limitations.

Architecture decisions must be evaluated too. Record the alternatives and
tradeoffs for deployment topology, data flow, trust and privacy boundaries,
failure recovery, observability, scaling, portability, operational complexity,
and rollback. A successful demo is not sufficient evidence for an architecture
choice. Do not describe a method as state of the art based only on a paper,
benchmark leaderboard, or vendor claim; evaluate it against the repository's
baseline and representative course use cases first.

Record accepted component implementations in the versioned experimental or
release profile under `research/05_evaluation/profiles/`. A profile selection
must link to evidence, name the implementation and configuration version, and
retain a control or fallback when applicable. Do not silently replace a selected
component in orchestration code; evaluate it, record the decision, update the
profile, and run component plus end-to-end regression checks.

Store experiment plans and learning logs under `research/04_experiments/`,
evaluation datasets and rubrics under `research/05_evaluation/`, repeatable
evaluation code under `scripts/`, and durable evidence summaries under
`reports/` or the relevant research documentation. Follow
`docs/quality-and-learning-plan.md` as the shared definition of done.

## Commit & Pull Request Guidelines

Recent commits use short, imperative summaries such as `Scaffold research workspace`; keep that style and make the first line specific. Pull requests should follow `.github/PULL_REQUEST_TEMPLATE.md`: include a summary, linked GitHub Project item or issue, iteration, area, evidence, verification steps, documentation updates, and confirmation that sensitive data is excluded.

## Security & Configuration Tips

Treat instructor materials, transcripts, student interactions, and consent records as sensitive. Do not commit `.env` files, raw datasets, local model artifacts, run outputs, or private consent records. Use synthetic examples in docs and tests, and record dataset permissions before using sources in experiments.
