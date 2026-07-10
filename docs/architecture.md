# Architecture Notes

## Pillars

### Identity and Knowledge Ingestion

- Collect instructor-approved course materials.
- Normalize transcripts, slides, forum replies, assignments, rubrics, and FAQs.
- Track source metadata, permissions, and retrieval quality.
- Build a baseline RAG pipeline before adding specialized agent behavior.
- Current Sprint 1 coverage is limited to metadata-only source inventory and
  deterministic source labels.

### Pedagogical Alignment Agent

- Define the instructor's tutoring policy and boundaries.
- Capture tone, preferred analogies, refusal behavior, and assessment style.
- Use examples to calibrate how direct or Socratic the agent should be.
- Evaluate responses against instructor rubrics.
- Current Sprint 1 coverage includes tutor policy generation, preview evidence,
  professor feedback revisions, and release blockers.

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

## Open Design Decisions

- Identity source format and versioning
- Retrieval chunking and citation format
- Prompt and policy configuration schema
- Agent prompt boundaries and model/provider selection
- Student privacy and consent model
- Evaluation baseline and scoring rubric
