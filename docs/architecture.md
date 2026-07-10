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

`CourseDocument` carries an approved source label. Chunks preserve document
identity and locators in metadata. Retrieval returns scored chunks, while the
asynchronous generator returns answer content, explicit citations, and warnings.
The protocols do not select a parser, embedding model, vector store, or LLM.

Synthetic chunker, retriever, and generator implementations live under
`tests/fixtures/` and make the contracts executable without network calls.

### Sprint 2 implementation boundary

This refactor includes contracts and test fixtures only. The following remain
separate execution sub-issues under roadmap issue #7:

- Local document parsing and deterministic chunking (#22)
- Retrieval and visible source evidence (#23)
- Live generation and tutor-policy enforcement (#24)
- Grounded tutoring smoke demonstration (#25)

Provider selection, embeddings, Canvas, persistence, real document parsing, and
live RAG are not implemented in this refactor. Canvas can be added later as an
optional source adapter if a safe guest course contains useful material.

## Open Design Decisions

- Identity source format and versioning
- Retrieval ranking and production citation locators
- Prompt and policy configuration schema
- Agent prompt boundaries and model/provider selection
- Student privacy and consent model
- Evaluation baseline and scoring rubric
