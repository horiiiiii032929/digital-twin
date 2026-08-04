# Student workflow slice learning log

## Component

I built the first durable, course-isolated student tutoring path: account and
membership checks, immutable release binding, conversations, messages,
citations, redacted audit events, M2/BM25 retrieval, and deterministic grounded
generation.

## Prediction

I expected SQLite plus an injectable repository to be sufficient for the local
restart claim. The main expected failure was accidental trust in route or UI
filtering instead of checking the account, membership, conversation owner, and
release again inside the domain service.

## How it works

The API receives a synthetic account identifier and passes it to the student
service. The service verifies the active student account, active course
membership, conversation owner, and current published release before every
turn. It loads approved chunks from that immutable release, builds the selected
retriever from the profile, uses BM25 if the embedder fails, runs the approved
policy and deterministic generator, validates every citation against presented
hits, and saves both messages, citations, and audit events in one transaction.

SQLite is not hidden inside the domain behavior. The `StudentRepository`
interface makes persistence replaceable, while the SQLite implementation gives
the local prototype real restart behavior. Stable client request IDs make a
repeated submission return the original persisted turn instead of generating a
second answer.

## Evidence

- Tests: 9 student API tests, plus the existing repository suite.
- Experiment or evaluation: `student-workflow-slice-v1-synthetic`.
- Metrics: 14/14 synthetic acceptance checks passed; zero network calls and
  zero private-data use.
- Pull request or artifact: `docs/student-workflow.md` and
  `npm run verify:student-workflow`.

## What failed or surprised me

The existing application had professor onboarding but no student-facing domain
or API. A release status check alone was also insufficient: a conversation can
point to an older release that remains marked published, so the service must
compare it with the course's current published release. Citation presence also
needed enforcement after generation rather than assuming every generator
implementation would obey the prompt contract.

## What I learned

Course isolation is a repeated domain invariant, not a one-time login check.
Persistence, authorization, retrieval fallback, citation identity, and audit
redaction have to share the same account/course/release lineage for the result
to be defensible.

## Next decision

Keep the SQLite and repository boundary as the bounded local R3 foundation.
Refine authentication, professor release administration, migration,
backup/restore, concurrent capacity, and live generator behavior before any
release-candidate claim.
