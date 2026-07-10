# digital-twin

Research and prototype workspace for a Digital Twin teaching system. The project
goal is to capture an educator's course knowledge, tone, and teaching approach
so students can get contextual tutoring support while instructors get actionable
learning-gap summaries.

GitHub Project: [Digital Twin Delivery](https://github.com/users/horiiiiii032929/projects/1)

## Project Pillars

- Identity and Knowledge Ingestion Engine: course material ingestion, transcript
  processing, and a RAG baseline grounded in instructor-owned sources.
- Pedagogical Alignment Agent: response policy, tone matching, examples, and
  teaching-style controls.
- Student Interface and Instructor Dashboard: student tutoring flows, instructor
  review surfaces, and learning-gap reporting.

See [docs/agents/README.md](docs/agents/README.md) for the implementation-facing
AI agent contracts that sit under these pillars.

The project's technical standard, learning commitments, and strengthened Sprint
2 acceptance criteria are defined in
[docs/quality-and-learning-plan.md](docs/quality-and-learning-plan.md).

## Repository Layout

```text
.
├── .github/                # GitHub issue and PR templates linked to the project
├── data/                   # Local research data buckets, ignored by default
├── docs/                   # Architecture, agent contracts, and project notes
├── experiments/            # Experiment configs and local run outputs
├── models/                 # Local model artifacts, ignored by default
├── notebooks/              # Exploratory notebooks
├── references/             # Papers, links, and citation notes
├── reports/                # Generated figures and final report assets
├── research/               # Research workflow notes and templates
├── scripts/                # Repeatable project utilities
├── services/               # FastAPI transport and application factory
├── src/                    # Domain, policy, and grounding contracts
└── tests/                  # Automated and manual verification notes
```

## Development Commands

- `uv sync --locked --dev`: install the locked Python API and test dependencies into `.venv`.
- `npm ci`: install the locked frontend workspace dependencies.
- `npm run dev:api`: start the FastAPI backend on <http://localhost:8000>.
- `npm run dev:web`: start the Vite frontend on <http://localhost:5173>.
- `npm run check`: run the complete local and CI verification suite.
- `npm run check:docs`: validate repository-local Markdown links.
- `npm run test:api`: run current Python tests for the API/domain scaffold.
- `npm run test:web`: run frontend tests.
- `npm run lint:web`: run frontend lint checks.
- `npm run build:web`: build the frontend.

Use Python from `.python-version` and Node.js from `.node-version`. GitHub
Actions runs `npm run check` for pushes to `main` and for pull requests.

## Current Implementation Status

Implemented in the Sprint 1 prototype:

- Chat-led onboarding workflow with deterministic follow-up handling.
- Metadata-only source inventory with permission, sensitivity, and label state.
- Structured tutor policy generation with release blockers.
- Preview evidence cases with source audit, decisions, and custom prompt review.
- Confirm/discard revision loop for professor feedback.
- Approval checklist that gates draft release status.
- Modular onboarding domain, API factory/routes, and frontend adapters with
  compatibility facades for the original imports.

Implemented as Sprint 2 foundations:

- Provider-neutral document, chunk, retrieval, citation, and tutor-answer models.
- Chunker, retriever, and asynchronous tutor-generator protocols.
- Synthetic, network-free fixtures used only by tests.

Still planned:

- Persistent storage, authentication, and multi-user sessions.
- Real source ingestion, retrieval, citation, and source-conflict checks.
- Provider-backed tutor response generation.
- Student-facing tutoring and learning-gap analytics.

Active Sprint 2 work is tracked by roadmap issue #7 and execution sub-issues
#19-#25. Real parsing, retrieval, provider-backed generation, tutor-policy
enforcement, and visible source evidence remain delivery work. Canvas remains
an optional future connector.

## Sprint 1 Onboarding Prototype

The current prototype supports the professor review loop for chat-led Course
Digital Twin setup: metadata-only source inventory, generated tutor policy,
evidence-backed preview cases, chat-based revision proposals, and a persisted
approval checklist.

Sprint 1 keeps uploads metadata-only and uses a deterministic source catalog for
preview grounding. It does not read local file contents or call a live search
provider.

Prof. Lek reviewed the onboarding direction and approved continuing with the
chat-led approach. Canvas should remain an optional source connector rather than
a required dependency; approved local or synthetic documents are the baseline
for the next grounding prototype.

See [docs/onboarding-prototype.md](docs/onboarding-prototype.md) for the reviewer
flow and [tests/manual/onboarding-prototype.md](tests/manual/onboarding-prototype.md)
for manual verification steps.

See [reports/issue-6-professor-feedback.md](reports/issue-6-professor-feedback.md)
for the Sprint 1 review decision and its implementation implications.

See [docs/github-project.md](docs/github-project.md) for how repository issues
map to the linked GitHub Project fields.
