# digital-twin

Research and prototype workspace for a Digital Twin teaching system. The project
goal is to capture an educator's course knowledge, tone, and teaching approach
so students can get contextual tutoring support while instructors get actionable
learning-gap summaries.

GitHub Project: https://github.com/users/horiiiiii032929/projects/1

## Project Pillars

- Identity and Knowledge Ingestion Engine: course material ingestion, transcript
  processing, and a RAG baseline grounded in instructor-owned sources.
- Pedagogical Alignment Agent: response policy, tone matching, examples, and
  teaching-style controls.
- Student Interface and Instructor Dashboard: student tutoring flows, instructor
  review surfaces, and learning-gap reporting.

## Repository Layout

```text
.
├── .github/                # GitHub issue and PR templates linked to the project
├── data/                   # Local research data buckets, ignored by default
├── docs/                   # Project brief, architecture, project-link notes
├── experiments/            # Experiment configs and local run outputs
├── models/                 # Local model artifacts, ignored by default
├── notebooks/              # Exploratory notebooks
├── references/             # Papers, links, and citation notes
├── reports/                # Generated figures and final report assets
├── research/               # Research workflow notes and templates
├── scripts/                # Repeatable project utilities
├── src/                    # Application and prototype source code
└── tests/                  # Automated and manual verification notes
```

## Development Commands

- `python -m pip install -e ".[dev]"`: install the Python API and test dependencies.
- `npm install`: install the frontend workspace dependencies after `apps/web` exists.
- `npm run dev:api`: start the FastAPI backend on <http://localhost:8000>.
- `npm run dev:web`: start the Vite frontend on <http://localhost:5173>.
- `npm run test:api`: run Python domain and API tests.
- `npm run test:web`: run frontend tests.
- `npm run build:web`: build the frontend.

See [docs/github-project.md](docs/github-project.md) for how repository issues
map to the linked GitHub Project fields.
