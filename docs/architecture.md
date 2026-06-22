# Architecture Notes

## Pillars

### Identity and Knowledge Ingestion

- Collect instructor-approved course materials.
- Normalize transcripts, slides, forum replies, assignments, rubrics, and FAQs.
- Track source metadata, permissions, and retrieval quality.
- Build a baseline RAG pipeline before adding specialized agent behavior.

### Pedagogical Alignment Agent

- Define the instructor's tutoring policy and boundaries.
- Capture tone, preferred analogies, refusal behavior, and assessment style.
- Use examples to calibrate how direct or Socratic the agent should be.
- Evaluate responses against instructor rubrics.

### Student Interface and Instructor Dashboard

- Provide student-facing tutoring flows.
- Capture anonymized interaction summaries where allowed.
- Surface recurring knowledge gaps to instructors.
- Keep instructor review and override workflows explicit.

## Open Design Decisions

- Identity source format and versioning
- Retrieval chunking and citation format
- Prompt and policy configuration schema
- Student privacy and consent model
- Evaluation baseline and scoring rubric
