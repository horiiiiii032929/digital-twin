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
├── docs/                   # Active architecture/guides plus historical archive
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
- `npm run verify:ingestion`: verify the local parsing and chunking baseline.
- `npm run verify:retrieval`: run the network-free retrieval v1 regression set.
- `npm run benchmark:retrieval`: compare BM25, local BGE-small, and RRF on
  retrieval v2; this optional command may download ignored local model files.
- `npm run calibrate:evidence-sufficiency`: select evidence-gate configurations
  on calibration data without evaluating the frozen held-out set.
- `npm run benchmark:evidence-sufficiency`: compare any-hit, BM25-score,
  lexical-coverage, and semantic-agreement evidence gates.
- `npm run verify:generation`: run the deterministic generation, policy,
  citation, no-evidence, and provider-suppression regression set.
- `npm run benchmark:generation-local`: run the unselected local Ollama Gemma 3
  4B candidate in strict JSON mode and write ignored per-case output under
  `reports/generated/`.
- `npm run verify:evaluation-results`: validate the durable evaluation-result
  registry and its referenced artifacts.
- `npm run verify:retrieval-v3-instruments`: validate the frozen IT5002
  retrieval-v3 candidates, metrics, held-out lock, and public open-set example
  without downloading or running a model.
- `npm run verify:profile`: validate the versioned component profile.
- `npm run test:api`: run current Python tests for the API/domain scaffold.
- `npm run test:web`: run frontend tests.
- `npm run lint:web`: run frontend lint checks.
- `npm run build:web`: build the frontend.

Use Python from `.python-version` and Node.js from `.node-version`. GitHub
Actions runs `npm run check` for pushes to `main` and for pull requests.

## Current implementation status

Start with the dated [current project status](docs/current-status.md) for the
active branch, evidence decisions, GitHub queue, and next human gate.

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
- Permission-gated local UTF-8 text, Markdown, and selectable-text PDF parsing.
- Stable source-version, content-hash, page, locator, and figure provenance.
- Deterministic heading/paragraph chunking with inherited tutoring permission.
- Evaluated BM25 retrieval with permission and active-version filtering plus
  explicit source evidence.
- Retrieval v2 comparison of BM25, local BGE-small dense retrieval, and
  reciprocal-rank fusion. The result is `Refine`, with no v2 replacement.
- A versioned component profile, evaluation records, result registry, and CI
  validators that prevent undocumented implementation replacement.
- An explicit, swappable evidence-sufficiency boundary and a 50-case held-out
  comparison. The result is `Refine`, with no safe gate selected.
- Deterministic grounded-generation, tutor-policy, citation-validation, and
  provider-failure controls behind replaceable interfaces.
- A LiteLLM adapter and local Ollama benchmark path with latency, token, model,
  and reported-cost traces.
- A frozen synthetic generator-qualification boundary for DeepSeek V4 Flash:
  P0/P1 failed development citation correctness, while strict-evidence P2
  passed all 48-case development floors, 36/36 repeated stability attempts,
  104/104 one-time held-out attempts, and a 20/20 second-review sample. The
  exact generator and P2 prompt are selected in the experimental profile with
  the deterministic rollback; the second review was not independent human
  judgment.
- A registered local Gemma 3 4B exploratory result: structural checks passed,
  but factual-support review passed only 15/18 model answers, so no generator or
  prompt was selected.
- The one-time 60-case cross-course held-out comparison selected M2 hybrid RRF
  for the experimental profile, with BM25 retained as the explicit rollback.
- A bounded synthetic-account student workflow with fail-closed course/release
  authorization, SQLite conversation persistence, citations, idempotency,
  provider fallback, and restart recovery.
- An evaluation-gated publication lifecycle with durable drafts, atomic release
  replacement, withdrawal, rollback, and stale-conversation denial. The v2
  synthetic architecture result passes 19/19 acceptance checks.

Current evidence and limitations:

- The 13-lecture IT5002 pilot is development evidence, not the final research
  boundary or selected method.
- In its 13 answerable development cases, local Qwen3 reranking retrieved
  complete evidence for 10 cases versus 3 for heading-aware BM25.
- The separate 59-case one-time rapid run failed after 29 cases. It is
  registered as invalid, retired, and never rerun.
- All observed no-evidence results used calibration cases and therefore are not
  independent final evidence.
- Jina was retired before hosted execution and is not a selection dependency.
  Local Qwen3 remains the semantic provider binding for the M0-M3 study.
- Local M3 preserved 80.0% complete-evidence success after optimization, but
  its best tested p95 was 28.13 seconds. It remains a research candidate and is
  deployment-ineligible on the reference hardware. The held-out comparison
  selected M2, which reached 85% complete evidence@3 at 164 ms warm p95; BM25
  remains the rollback.
- Synthetic product activation now covers the bounded student and publication
  path, but it is not release-ready evidence. The product still lacks a
  credentialed identity boundary, complete professor/admin and source
  lifecycles, valid professor-fidelity and end-to-end evidence,
  migration/backup/restore and concurrency evidence, and bounded capacity
  results.

The active baseline is a professor-configurable pedagogical Digital Twin for
multiple professors and courses, not a one-course RAG pilot. Its central
technical study compares heading BM25, dense, hybrid, and reranked hybrid
retrieval across a verified heterogeneous-course benchmark. The product must
also demonstrate professor-policy fidelity, evaluation-before-publication,
course-isolated student tutoring, rollback, failure recovery, and bounded
simulated capacity.

See the
[authoritative scope](research/00_admin/2026-07-27-frontier-digital-twin-scope.md)
for the research programme, claims, data boundary, and compressed schedule. The
technical and evidence freeze is 2026-08-16; September is reserved for report,
presentation, revision, and contingency.

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
