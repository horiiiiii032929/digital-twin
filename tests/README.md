# Tests

Use this folder for automated tests, fixtures, and manual verification notes.

Testing should cover:

- Source normalization
- Retrieval behavior
- Prompt and policy configuration
- Evaluation scoring
- Privacy and data exclusion checks

Manual verification notes:

- [onboarding-prototype.md](manual/onboarding-prototype.md)

Local ingestion verification uses the committed synthetic corpus under
`fixtures/course_corpus/` plus a generated synthetic PDF. Run
`npm run verify:ingestion`; no real course material is required or committed.
