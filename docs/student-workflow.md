# Student tutoring workflow

## Scope

The current student slice is a local, synthetic-account implementation for
bounded workflow and demo evaluation. It is not production authentication or
human-usability evidence. It adds durable, course-isolated tutoring and a
responsive student workspace without changing the selected retrieval,
generation, policy, or professor-onboarding contracts.

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
  version, page, region, bounding box, checksum, crop reference, and locator
  lineage for an owned tutor message.
- `GET /api/student/messages/{message_id}/citations/{citation_id}/crop` returns
  an approved original PNG crop only after the same student/course/release
  authorization check; raw local paths are never returned.

The local professor publication boundary connects an onboarding session to a
durable release:

- `PUT /api/professor/courses/{course_id}/sources/{artifact_id}` accepts one
  bounded approved PDF body, applies professor/course authorization before
  processing, and returns release-ready region chunks. OCR and description
  providers remain injected; this synchronous local endpoint moves to the
  durable job/object-storage boundary in the deployment work;
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

## Student web workspace

The Vite application exposes the professor workspace at `/` and the student
tutor at `/student`. The student route uses the same published-release API and
does not construct the professor controller. It provides:

- assigned-course selection and a release-availability state;
- release-bound new and restored conversations;
- a focused tutoring conversation with grounded answer markers;
- desktop citation inspection and a mobile citation sheet with source version,
  page/region metadata, approved original-crop preview, locator, and release
  lineage;
- stable request identifiers so an explicit retry cannot duplicate a turn;
- draft preservation and distinct recovery actions for transport failure and a
  withdrawn or replaced release; and
- responsive 1440px, 768px, and 390px layouts with text-labelled state and
  44-pixel coarse-pointer targets.

Only the active course ID and conversation IDs are stored in versioned browser
storage. Messages, answers, and citations are reloaded from the API and remain
authoritative there. Browser storage failure therefore removes convenience,
not authorization or source lineage.

Seed and run the synthetic local demo with:

```bash
npm run seed:student-demo
npm run dev:api
npm run dev:web
```

Then open <http://localhost:5173/student>. The default synthetic identity is
`student-a-synthetic`; `VITE_STUDENT_ACCOUNT_ID` may override it for a local
fixture. This header is not a credential or a production session mechanism.

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

The first command executes 19 network-free synthetic acceptance checks covering
the successful journey, selected M2 path, fallback, isolation, revocation,
restart, idempotency, citations, malformed generation, redacted audit
telemetry, evaluation-gated draft publication, atomic replacement, withdrawal,
rollback, and stale-conversation denial.

## Limitations

- `X-Account-ID` is a synthetic local session boundary, not credential-based
  authentication.
- Full professor course/source administration and credentialed authorization
  are not yet exposed; the current publication API is a synthetic local
  boundary.
- The accepted path uses a synthetic embedder and deterministic generator;
  live provider qualification remains R2 work.
- Backup/restore, schema migration, multi-process contention, capacity, formal
  accessibility conformance, and human usability remain untested.
- The browser remembers only a minimal local conversation index. There is no
  server-side conversation-list endpoint, rename/delete flow, search, or
  cross-device history synchronization.
- The result supports bounded workflow behavior only, not usability, adoption,
  satisfaction, engagement, or learning-effectiveness claims.
