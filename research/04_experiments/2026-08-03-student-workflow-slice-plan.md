# Minimum student workflow slice v1

Date: 2026-08-03

Status: implemented and development-verified on 2026-08-04; not a
product-completeness claim.

## Purpose

Provide the smallest student-facing vertical slice needed to evaluate the
Digital Twin research claims after R2. The slice exists to test course
authorization, published-release control, persistent grounded turns, citation
identity, and provider failure recovery. It is not a complete student product.

## Scope

The slice contains one synthetic professor, two synthetic students, two
courses, one published release per course, and one withdrawn release. All
records are local and synthetic.

### Required records

- `Account`: stable ID, role, active/revoked state;
- `Course`: stable course ID and owner professor ID;
- `CourseMembership`: account, course, role, and active state;
- `DigitalTwinRelease`: immutable profile/policy/source-version references and
  published or withdrawn state;
- `Conversation`: student, course, release, and timestamps;
- `Message`: role, content, structured tutor action, and redacted trace;
- `Citation`: source/document/version/locator identity for a tutor message; and
- `AuditEvent`: minimized lifecycle, denial, fallback, and recovery event.

## Required journey

1. A synthetic professor creates or selects a course and publishes a release
   only after the R2-compatible profile and deterministic gates pass.
2. An invited student signs in and sees only assigned published courses.
3. The student starts a conversation and submits a grounded question.
4. The tutor uses selected M2 or BM25 rollback retrieval, applies the approved
   policy, generates a bounded answer or safe action, validates citations, and
   persists the turn.
5. The student can reload the conversation and inspect the citation locator.
6. A provider failure records a redacted fallback event and returns the BM25
   or deterministic safe action without fabricating evidence.
7. Withdrawal immediately blocks new student turns for that release while
   preserving the audit record and prior conversation lineage.

## Authorization and recovery checks

The implementation must fail closed for:

- student access to an unassigned course;
- professor access to another professor's private course;
- cross-course conversation or citation lookup;
- withdrawn or stale release use;
- inactive or revoked account;
- missing course or release scope;
- citation whose source/version/locator is not in the presented evidence; and
- provider failure without a registered fallback.

Restart survival, duplicate request handling, timeout, malformed output, and
provider outage are acceptance cases. The current in-memory onboarding store is
not sufficient evidence for restart survival; the slice needs a small durable
repository or an explicitly bounded persistence test double before the R3
result can claim persistence.

## Suggested transport boundary

Keep the domain interfaces provider-neutral and add a separate student router
under `/api/student`:

- `GET /api/student/courses` — assigned published courses;
- `POST /api/student/courses/{course_id}/conversations` — create a scoped
  conversation;
- `GET /api/student/conversations/{conversation_id}` — retrieve own history;
- `POST /api/student/conversations/{conversation_id}/messages` — submit one
  turn; and
- `GET /api/student/messages/{message_id}/citations` — inspect validated source
  locators.

The authentication implementation may begin as a synthetic account/session
repository for local evaluation, but the role and course checks must be real
domain checks rather than UI-only filters.

## Acceptance evidence

The first R3 slice is complete when a scripted test records:

- one successful professor publish;
- one successful authorized student turn;
- one persisted conversation reload;
- one valid citation lookup;
- one denied cross-course access;
- one denied cross-role access;
- one withdrawn-release denial;
- one revoked-account denial;
- one selected-M2 retrieval turn;
- one BM25 fallback turn after provider failure;
- one malformed-generation bounded failure; and
- one redacted audit trace with no course text or secrets.

These counts are acceptance evidence, not human usability or learning
outcomes. The final R3 evaluation adds multi-turn simulated-student journeys,
capacity measurements, backup/restore, and release rollback after this slice
is stable.

## Implementation order

1. Introduce domain repositories and scope checks with synthetic fixtures.
2. Add the student API router and structured response contracts.
3. Connect the selected M2 factory and `FallbackRetriever` to the turn service.
4. Add persistence/restart and provider-failure acceptance tests.
5. Add the smallest student web view only after the API journey is green.

Do not add proactive learning-gap analytics, Canvas, multimodal tutoring,
public signup, grading, or production tenancy to this slice.

## Development outcome

The API-first slice was implemented with an injectable SQLite repository,
synthetic account header, selected-profile retrieval factory, deterministic
generator control, citation validation, idempotent request IDs, and redacted
audit events. All 14 frozen synthetic acceptance checks passed. See the
[`student-workflow-slice-v1-synthetic` result](../05_evaluation/student-workflow-slice-v1-synthetic-results.md)
and the active [student workflow guide](../../docs/student-workflow.md).
