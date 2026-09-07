# digital-twin

Research software for a professor-configured Course Digital Twin: approved course
sources, teaching policies, grounded student dialogue, governed proactive support
and instructor review. The submitted report and experimental records distinguish
implemented behaviour, synthetic evaluation and unresolved research questions.

## Submitted report and reproducibility

- [Submitted abstract, report and LaTeX package](reports/submitted/2026-09-06/README.md)
- [Report source and build instructions](research/06_reports/final/README.md)
- [Verification results and prerequisites](docs/post-submission-verification.md)
- [Evaluation result registry](research/05_evaluation/result-registry.md)
- [Repository cleanup and reference preservation](docs/repository-maintenance.md)

The submitted PDFs and their cited evidence retain their original paths and
hashes. Post-submission tooling changes do not alter historical evaluation results.

## Development Commands

Use the Python and Node versions in `.python-version` and `.node-version`.
Install `rsvg-convert` with `brew install librsvg` on macOS or
`sudo apt-get install librsvg2-bin` on Debian/Ubuntu, then run:

```sh
uv sync --locked --dev
npm ci
npm run setup:evaluation-sources
npm run check
```

Source preparation fetches five pinned public repositories into ignored storage.
The standard checks need no model API key. Existing changed source checkouts are
rejected instead of overwritten.

| Task | Command |
| --- | --- |
| Start API | `npm run dev:api` |
| Start web app | `npm run dev:web` |
| Python tests | `npm run test:api` |
| Frontend tests | `npm run test:web` |
| Lint and build | `npm run lint:web` and `npm run build:web` |
| Documentation links | `npm run check:docs` |
| Submitted report references and hashes | `npm run check:report-links` |
| Dependency audit | `npm run audit:dependencies` |

The [script catalog](scripts/README.md) describes component-specific commands.
Historical tests requiring original ignored outputs remain available through
`npm run test:historical-artifacts` and
`npm run verify:historical-generated-artifacts`. They need their bound artifacts;
these commands do not authorize new provider calls or sealed evaluations.

## Local product demo

Run the API and web commands in separate terminals. Open
<http://localhost:5173/> for the professor workspace and
<http://localhost:5173/student> for the student tutor. The development demo uses
synthetic in-memory fixtures; its `X-Account-ID` boundary is demonstrative.
See [deployment and recovery](docs/deployment.md) for credentialed deployment.

## Project Pillars

- **Knowledge ingestion:** course sources, permissions, parsing and retrieval.
- **Pedagogical alignment:** professor configuration and governed tutoring behaviour.
- **Student and instructor interfaces:** dialogue, proactive support and review.

Start with the [documentation map](docs/README.md) and
[agent contracts](docs/agents/README.md). The
[quality and learning plan](docs/quality-and-learning-plan.md) defines the
project's evaluation requirements.

## Repository Layout

| Directory | Purpose |
| --- | --- |
| `src/`, `services/`, `apps/` | Domain code, API and frontend |
| `tests/`, `scripts/` | Regression tests and repeatable utilities |
| `deploy/`, `.github/` | Deployment configuration and CI |
| `docs/` | Implementation guides and historical design archive |
| `research/` | Requirements, literature, plans, datasets and evaluation records |
| `reports/` | Durable reports, submitted snapshot and figure assets |
| `data/`, `models/`, `experiments/runs/` | Ignored local inputs and run products |

## Current implementation status

The [post-submission verification record](docs/post-submission-verification.md)
and its linked CI runs describe repository reproducibility. The
[dated implementation log](docs/current-status.md) preserves research decisions,
limitations and superseded milestones. Consult versioned
[component profiles](research/05_evaluation/profiles/) for selection evidence;
a passed code check does not promote an experimental component.

## Invite-only staging candidate

Use [deployment guidance](docs/deployment.md) and the
[deployment threat model](docs/deployment-threat-model.md). Earlier staging
claims and blockers remain in the
[historical implementation notes](docs/archive/readme-implementation-history-20260907.md#invite-only-staging-candidate).

## Sprint 1 Onboarding Prototype

The [onboarding guide](docs/onboarding-prototype.md),
[manual checks](tests/manual/onboarding-prototype.md) and
[professor feedback](reports/issue-6-professor-feedback.md) retain this milestone.
The previous README narrative is preserved in the
[historical implementation notes](docs/archive/readme-implementation-history-20260907.md#sprint-1-onboarding-prototype).

GitHub Project: [Course Digital Twin Release](https://github.com/users/horiiiiii032929/projects/1).
