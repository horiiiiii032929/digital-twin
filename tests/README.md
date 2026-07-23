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

Retrieval regression coverage loads the 25-case versioned set at
`../research/05_evaluation/retrieval_v1.json` and compares term overlap with
BM25 over the same approved chunks. Run `npm run verify:retrieval` for the full
per-case result artifact.

Generation coverage checks professor release approval, graded-work redirection,
approved-evidence filtering, prompt boundaries, structured provider output,
invented citations, provider failures, token/cost traces, and sanitized warnings.
`npm run verify:generation` runs the 25-case deterministic preflight with no
network or paid model calls.

Component-profile tests ensure the experimental profile covers every
decision-bearing component, evidence links resolve, and a candidate cannot be
selected after failing a hard gate or required metric. Run
`npm run verify:profile` for the readable profile summary.

Evaluation-instrument tests cover judge input/output alignment, exact evidence
spans, unique simulator event transitions, state-card linkage, missing-output
denominators, and the frozen artifact manifest. Run
`npm run verify:evaluation-instruments` for the complete instrument audit.
