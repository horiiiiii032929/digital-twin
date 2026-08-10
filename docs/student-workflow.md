# Student tutoring workflow

## Scope

The current student slice is a local, synthetic-account implementation for R3
acceptance testing. It is not production authentication or human-usability
evidence. It adds durable, course-isolated tutoring without changing the
professor onboarding workflow.

## Data flow

```text
X-Account-ID synthetic session
  -> active student account
  -> active course membership
  -> current published Digital Twin release
  -> selected M2 retriever or explicit BM25 fallback
  -> approved tutor policy
  -> deterministic grounded generator
  -> citation validation
  -> atomic SQLite conversation/message/citation/audit write
```

The local API uses SQLite because the earlier in-memory onboarding repository
cannot demonstrate restart persistence. Domain access remains behind an
injectable repository interface so a later deployment can compare or adopt a
different database without changing authorization and tutoring behavior.

## API

The bounded local authentication fixture supplies `X-Account-ID`. Missing,
revoked, non-student, unassigned, cross-course, cross-student, stale-release,
and withdrawn-release requests fail closed.

- `GET /api/student/courses` lists assigned courses with current published
  releases.
- `POST /api/student/courses/{course_id}/conversations` creates a conversation
  bound to the current release.
- `GET /api/student/conversations/{conversation_id}` reloads the owning
  student's persisted history.
- `POST /api/student/conversations/{conversation_id}/messages` accepts
  `content` and a stable `request_id`; exact duplicates return the original
  turn, while reuse for different content is rejected as a conflict.
- `GET /api/student/messages/{message_id}/citations` returns validated source,
  version, and locator lineage for an owned tutor message.

The local professor publication boundary connects an onboarding session to a
durable release:

- `POST /api/professor/courses/{course_id}/releases` creates a draft from a
  reviewed onboarding policy and chunk set;
- `PATCH /api/professor/releases/{release_id}/evaluation` records the frozen
  evaluation gate;
- `POST /api/professor/releases/{release_id}/publish` requires passed
  evaluation, approved policy, and approved tutoring chunks;
- `POST /api/professor/releases/{release_id}/withdraw` removes the current
  student-facing release; and
- `POST /api/professor/releases/{release_id}/rollback` restores a previously
  withdrawn, still-eligible release.

Publishing atomically withdraws the previous course release. Conversations
bound to that previous release fail closed rather than silently switching
knowledge or policy versions.

The default ASGI application stores local records under the ignored
`data/interim/student-workflow/` directory. Tests and verification commands use
temporary databases and synthetic content only.

## Retrieval and generation boundary

The service loads the active `student-tutor-v1` profile. An injected compatible
embedder activates selected M2 hybrid retrieval. Missing or failed embedding
falls back to BM25 and records only implementation identifiers and a sanitized
failure type. Question text and provider exception messages are not copied into
audit events.

The deterministic grounded generator remains the product-development control.
It does not select a live generator or establish professor fidelity. Any
generation exception, unsupported citation, or answer action without a
citation becomes a persisted safe failure.

## Verification

```bash
npm run verify:student-workflow
npm run check
```

The first command executes 14 network-free synthetic acceptance checks covering
the successful journey, selected M2 path, fallback, isolation, revocation,
withdrawal, restart, idempotency, citations, malformed generation, and redacted
audit telemetry.

## Limitations

- `X-Account-ID` is a synthetic local session boundary, not credential-based
  authentication.
- Full professor course/source administration and credentialed authorization
  are not yet exposed; the current publication API is a synthetic local
  boundary.
- The accepted path uses a synthetic embedder and deterministic generator;
  live provider qualification remains R2 work.
- Backup/restore, schema migration, multi-process contention, capacity, and the
  student web interface remain untested.
- The result supports bounded workflow behavior only, not usability, adoption,
  satisfaction, engagement, or learning-effectiveness claims.
