# Architecture Notes

## Pillars

### Identity and Knowledge Ingestion

- Collect instructor-approved course materials.
- Normalize transcripts, slides, forum replies, assignments, rubrics, and FAQs.
- Track source metadata, permissions, and retrieval quality.
- Build a baseline RAG pipeline before adding specialized agent behavior.
- The onboarding flow deliberately remains metadata-only. The grounding layer
  separately parses approved local sources and preserves their permission and
  version lineage.

### Pedagogical Alignment Agent

- Define the instructor's tutoring policy and boundaries.
- Capture tone, preferred analogies, refusal behavior, and assessment style.
- Use examples to calibrate how direct or Socratic the agent should be.
- Evaluate responses against instructor rubrics.
- Implemented onboarding coverage includes tutor policy generation, preview
  evidence, professor feedback revisions, and release blockers.

### Student Interface and Instructor Dashboard

- Provide student-facing tutoring flows.
- Capture anonymized interaction summaries where allowed.
- Surface recurring knowledge gaps to instructors.
- Keep instructor review and override workflows explicit.
- Deliver authenticated professor/student workflows, durable state, private
  storage, and staging deployment for the controlled pilot.
- Proactive interaction and full learning-gap analytics are deferred until the
  grounded deployed pilot is evaluated.

## Agent Contracts

The implementation-facing AI agent scaffolds live in
[agents/README.md](agents/README.md). They split the product into smaller,
testable contracts:

- Onboarding Orchestrator Agent
- Source Governance Agent
- Tutor Policy Agent
- Preview Evidence Agent
- Revision Review Agent
- Student Tutoring Agent
- Learning Gap Analytics Agent

Sprint 1 implements the first five through deterministic workflow code. The
student and analytics agents remain planned.

## Active grounding work

Sprint 2 is proving one provider-backed path without coupling the architecture
to an LMS. The refactor establishes these stable layers first:

```text
apps/web                          professor review frontend
        ↓ HTTP
services/api/app                 factory, schemas, dependencies, routes
        ↓ commands
src/digital_twin/onboarding      interview and professor-release domain
src/digital_twin/tutor_policy.py canonical shared policy schema
        ↓ future tutoring use
src/digital_twin/grounding       provider-neutral grounding contracts
```

The grounding contract sequence is:

```text
CourseDocument → DocumentChunker → DocumentChunk → Retriever → RetrievalHit
                                                               ↓
TutorPolicy ───────────────────────────────→ TutorGenerator → TutorAnswer
                                                             ├─ citations
                                                             ├─ warnings
                                                             └─ usage trace
```

`SourceArtifact` and `ApprovalRecord` now gate local parsing. `CourseDocument`
carries the approved source version, permission snapshot, content hash, ordered
segments, and an opaque source locator. Chunks preserve this lineage in explicit
fields and metadata. Deterministic term-overlap and BM25 retrieval filter
non-tutoring and superseded chunks before returning scored source evidence. The
generation path filters evidence permissions again, applies deterministic
policy rules before any provider call, builds a versioned prompt, parses a
structured answer, validates citations against retrieved hits, and records
latency, tokens, and approximate cost. See
[local-ingestion.md](local-ingestion.md) for parsing and chunking,
[local-retrieval.md](local-retrieval.md) for ranking, and
[live-generation.md](live-generation.md) for the generation control and live
adapter boundary.

Cross-cutting implementation selection is separate from these runtime
contracts. The [evaluation architecture](evaluation-architecture.md) defines
shared candidate records and the complete versioned system profile, while the
[component inventory](component-inventory.md) shows which boundaries are
selected, pending, or disabled. This preserves typed domain interfaces while
making algorithms, models, prompts, and policies measurable and replaceable.

Synthetic chunker, retriever, and generator implementations live under
`tests/fixtures/` and make the contracts executable without network calls.

### Sprint 2 implementation boundary

The provider-neutral contracts, local ingestion baseline, evaluated BM25
retrieval baseline, harder BM25/dense/RRF comparison, deterministic generation
preflight, system-wide component profile, durable result registry, and a
swappable evidence-sufficiency boundary are implemented. Retrieval v2 and
evidence-sufficiency v1 both produced `Refine` decisions with no replacement,
so BM25 v1 with explicit any-hit behavior remains only the provisional
rollback/control path. A LiteLLM adapter and local Ollama benchmark mode exist,
but neither is wired to an API route or selected provider model. The first
Gemma 3 4B exploratory run passed structure and policy checks but found three
support failures in 18 model answers under a post-run diagnostic rubric; it
therefore selected nothing.
The following remain separate execution sub-issues under roadmap issue #7:

- Prospective fixed-DeepSeek and prompt qualification completing #24
- Open-set answerability/evidence-verifier comparison in #43
- Untouched end-to-end grounded-tutoring evaluation in #25

The DeepSeek API is the primary generator product constraint, with synthetic
evaluation only and a cumulative USD 10 #24 cap, but its exact configuration
and prompt selection remain pending. Production embedding selection, Canvas,
persistence, and live evaluation remain pending. Local BGE-small embeddings have been
benchmarked for ranking and semantic evidence agreement but were not selected.
The current any-hit control must not feed an end-to-end grounding claim. Canvas
can be added later as an optional source adapter if a safe guest course contains
useful material.

### Deployable-pilot planning boundary

The 2026-07-22 rescope makes a real staging deployment and supervised pilot part
of the final outcome. The current FastAPI/Vite and in-memory onboarding stack is
not deployable as-is. Before implementation resumes, #11 must freeze the
alternatives, metrics, privacy rules, and hard gates for:

- invited-user authentication and session revocation;
- professor/student roles and course membership;
- transactional persistence and private source storage;
- persistent conversation state and duplicate/stale response handling;
- provider data processing, consent, retention, deletion, and log redaction;
- staging/production separation, TLS, secrets, health checks, rate limits,
  backup/restore, rollback, monitoring, and incident response; and
- professor UAT plus supervised student usability and reliability evidence.

No hosting, identity, database, or storage vendor is selected by this rescope.
Each is an architecture decision requiring a control, bounded candidates,
operational evidence, failure cases, and rollback. See the
[deployable pilot rescope](../research/00_admin/2026-07-22-deployable-pilot-rescope.md).

## Open Design Decisions

- Production citation rendering and locator navigation
- Live prompt variant selection and exact DeepSeek model/configuration freeze
- Agent prompt boundaries and provider-failure behavior
- Student privacy and consent model
- End-to-end answer-quality rubric and evidence-sufficiency threshold
- Identity provider, role/course authorization model, and session lifecycle
- Database, private object storage, migrations, retention, and deletion
- Hosting topology, environments, monitoring, backup/restore, and rollback
- Real-student provider approval and synthetic-user fallback
