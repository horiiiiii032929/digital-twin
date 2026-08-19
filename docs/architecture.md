# Digital Twin architecture

Status: active target architecture

Scope authority:
[`2026-07-27-frontier-digital-twin-scope.md`](../research/00_admin/2026-07-27-frontier-digital-twin-scope.md)

## Architectural objective

The system is a multi-course pedagogical Digital Twin, not a RAG endpoint. It
must preserve five independently testable concerns:

1. professor identity and teaching behaviour;
2. governed course knowledge;
3. pedagogical tutoring policy;
4. student interaction state; and
5. evaluation and professor publication control.

Provider-specific code stays outside the domain. Every decision-bearing
component remains replaceable through a stable interface and a versioned
profile.

## System context

```text
Administrator
  └─ invite accounts, assign courses, inspect operations

Professor
  └─ create course → govern sources → configure Digital Twin
     → preview/evaluate → publish/withdraw/rollback

Student
  └─ join assigned course → ask question → receive cited tutoring,
     clarification, refusal, or no-evidence response
```

The final project retains a local demo and now has a single-host staging
package. Public signup, institutional SSO, and LMS coupling are not required;
public HTTPS staging is required before the deployable foundation closes.

## Runtime boundaries

```text
apps/web
  professor, student, and administrator journeys
        │ HTTP
        ▼
services/api
  authentication/session boundary, request schemas, orchestration adapters
        │ commands and queries
        ▼
src/digital_twin
  ├─ identity/course membership
  ├─ onboarding and professor policy
  ├─ source governance and grounding
  ├─ tutoring conversation state
  ├─ evaluation and publication
  └─ audit/recovery contracts
        │ provider interfaces
        ▼
services/
  embeddings, reranking, generation, persistence, and storage adapters
```

The repository now contains two explicit profiles. `A0-local-demo` retains the
synthetic account header and in-memory onboarding state. In
`A1-single-node-staging`, administrators invite credentialed accounts, opaque
digest-only cookie sessions determine identity, professor onboarding is owned
and durable, SQLite schema v5 stores transactional course/release/conversation
state, a content-addressed volume stores source bytes, and a leased worker runs
idempotent ingestion. Caddy serves the role-routed web app and same-origin API
over automatic HTTPS. A1 passed the local 41/41 development qualification but
is not a released production architecture until the external host rehearsal
and downstream pilot gates pass.

## Core domain model

### Account and tenancy

- `Account`: invite-only administrator, professor, or student identity.
- `Course`: professor-owned isolation boundary.
- `Membership`: explicit account-to-course role.
- One `DigitalTwinRelease` belongs to one professor-owned course or section.
  Individual lectures are versioned sources inside that release, not separate
  Digital Twins.

### Source governance

- `SourceArtifact`: original approved source and sensitivity/permission state.
- `SourceVersion`: immutable content hash, parser revision, inclusion state,
  and rollback link.
- `CourseDocument` and `DocumentChunk`: normalized content with course,
  source-version, locator, and tutoring-permission lineage.

Every source and chunk must carry immutable institution, professor, course,
term, release, lecture, source, version, and permission identifiers. Retrieval
must apply the authorized course/release/source scope before lexical search,
embedding search, fusion, or reranking. Missing scope fails closed. Cross-course
federation requires an explicit professor-approved set of course releases; it
must never arise from semantic similarity alone.

Solution files, answer keys, student submissions, student data, credentials,
and secrets never enter the tutoring corpus.

### Professor Digital Twin

- `ProfessorProfile`: teaching approach, tone, examples, and tutoring moves.
- `TutorPolicy`: boundaries, integrity behaviour, directness, scaffolding, and
  safe actions.
- `DigitalTwinDraft`: course sources, profile, policy, component profile, and
  evaluation suite under review.
- `DigitalTwinRelease`: immutable professor-approved publication with rollback.

### Student tutoring

- `Conversation` and `Turn`: course- and student-isolated persistent state.
- `EvidenceBundle`: ranked approved chunks plus required provenance.
- `TutorAnswer`: answer/scaffold/clarify/refuse/abstain action, citations,
  warnings, and usage trace.

### Evaluation and operations

- `EvaluationSuite`, `EvaluationRun`, and `EvaluationResult`: versioned cases,
  configuration, per-case evidence, aggregate metrics, failures, and decision.
- `AuditEvent`: minimized, redacted lifecycle and recovery evidence.

## Grounded tutoring flow

```text
question + course + release
        │
        ├─ authorize membership and published release
        ├─ retrieve only approved active course chunks
        ├─ rerank through the selected or rollback profile
        ├─ assemble evidence with source/version/locator lineage
        ├─ apply professor policy and academic-integrity rules
        ├─ generate through the selected provider adapter
        ├─ validate citations and safe action
        └─ persist the turn, usage, warnings, and redacted audit event
```

The cross-course retrieval ladder is M0 heading-aware BM25, M1 dense, M2
BM25+dense hybrid, and M3 hybrid plus reranking. Local Qwen3 is the selected M2
embedding binding for the experimental profile; Jina was retired before hosted
execution. M3 remains a research-quality reference with BM25 as rollback.

## Evaluation-before-publication

A professor may preview a draft at any time. Publication requires:

- all included sources are approved, current, and permitted for tutoring;
- required professor-profile and tutor-policy fields are approved;
- deterministic privacy, permission, citation, and integrity gates pass;
- the frozen preview/evaluation suite has no unresolved release blocker;
- the component profile is selected or explicitly uses a documented rollback;
- the professor explicitly approves the immutable release.

Updating sources, policy, prompts, models, or retrieval configuration creates a
new draft. It never mutates a published release silently.

## Trust and privacy boundaries

- Browser and API input is untrusted.
- Every read and write is scoped by account, role, course, and release.
- Raw course content and prompts are excluded from ordinary logs.
- External provider calls use an allowlist and record provider, model, purpose,
  data class, cost cap, and fallback.
- Approved course material may leave the workstation only under the active
  provider/data decision. Excluded material never does.
- Deterministic rules are authoritative for permission, isolation, citation
  identity, and academic-integrity hard gates; LLM judges do not override them.
- Zero unauthorized chunks in the retrieval candidate set is a hard gate, not
  an average quality metric. The same check applies before reranking,
  generation, citation display, and conversation persistence.

See [evaluation-data-flow-and-threat-model.md](evaluation-data-flow-and-threat-model.md)
for the current detailed research boundary. It must receive a versioned
successor before external course-data use.
See [deployment-threat-model.md](deployment-threat-model.md) for the credential,
host, object, queue, backup, and optional provider boundary implemented by A1.

## Failure and recovery design

Every external or durable boundary exposes a visible failure rather than a
fabricated answer. Required scenarios include:

- unsupported or failed ingestion;
- unavailable embedding, reranking, or generation provider;
- insufficient or cross-course evidence;
- stale release or duplicate turn;
- persistence restart and migration failure;
- withdrawal and rollback;
- backup and restore; and
- rate/capacity exhaustion.

The local deployment package must pin configuration, isolate secrets, expose
health checks, use redacted structured logs, and document backup/restore and
rollback.

## Repository ownership

| Path | Responsibility |
| --- | --- |
| `src/` | Provider-neutral domain logic and interfaces |
| `services/` | API transport and provider/infrastructure adapters |
| `apps/` | User-facing applications |
| `scripts/` | Reproducible evaluation, ingestion, and operational commands |
| `tests/` | Automated tests, synthetic fixtures, and manual verification |
| `research/` | Literature, requirements, datasets, plans, results, and decisions |
| `docs/` | Active implementation and architecture documentation |
| `reports/` | Durable figures, claim matrix, and final communication assets |

Historical designs and superseded plans live in explicit `archive/` folders.
They remain traceable but are never treated as current instructions.

## Open decisions

- public staging host/domain, certificate rehearsal, and approved off-host
  backup location;
- institutional SSO/MFA and a managed database/object/queue boundary before
  horizontal or higher-risk deployment;
- selected retrieval/generator capacity with representative concurrent load;
- external alert delivery and provider-data approval for private course use;
- real PDF/OCR/layout qualification and human professor/student usability; and
- the privacy-approved pilot and release-candidate path.

Each decision requires a prospective comparison or architecture record before
selection.
