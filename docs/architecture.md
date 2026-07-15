# Architecture Notes

## Pillars

### Identity and Knowledge Ingestion

- Collect instructor-approved course materials.
- Normalize transcripts, slides, forum replies, assignments, rubrics, and FAQs.
- Track source metadata, permissions, and retrieval quality.
- Build a baseline RAG pipeline before adding specialized agent behavior.
- Implemented onboarding coverage is limited to metadata-only source inventory
  and deterministic source labels.

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
- Student tutoring and analytics are planned after the professor approval loop
  is stable.

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

Sprint 2 will prove one provider-backed path without coupling the architecture
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
                                                             └─ warnings
```

`SourceArtifact` and `ApprovalRecord` now gate local parsing. `CourseDocument`
carries the approved source version, permission snapshot, content hash, ordered
segments, and an opaque source locator. Chunks preserve this lineage in explicit
fields and metadata. Deterministic term-overlap and BM25 retrieval filter
non-tutoring and superseded chunks before returning scored source evidence. The
asynchronous generator returns answer content, explicit citations, and warnings. See
[local-ingestion.md](local-ingestion.md) for the parser, figure, and deterministic
chunking design and [local-retrieval.md](local-retrieval.md) for ranking and
evaluation.

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
retrieval baseline, and system-wide component profile are implemented.
The following remain separate execution sub-issues under roadmap issue #7:

- Live generation and tutor-policy enforcement (#24)
- Grounded tutoring smoke demonstration (#25)

Provider selection, embeddings, Canvas, persistence, and live generation are not
implemented. Canvas can be added later as an optional source adapter if a safe
guest course contains useful material.

## Open Design Decisions

- Production citation rendering and locator navigation
- Prompt and policy configuration schema
- Agent prompt boundaries and model/provider selection
- Student privacy and consent model
- Evaluation baseline and scoring rubric
