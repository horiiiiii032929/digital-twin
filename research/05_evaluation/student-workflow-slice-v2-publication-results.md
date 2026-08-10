# Student workflow slice v2 publication results

Result ID: `student-workflow-slice-v2-publication-synthetic`

## Run identity

- Component: release publication and student workflow architecture.
- Status: completed.
- Date and owner: 2026-08-06, project researcher.
- Code revision: `e8c0ff2` with dirty implementation changes.
- Reproduction command: `npm run verify:student-workflow`.
- Runtime: Python 3.12, FastAPI/Pydantic, standard-library SQLite, synthetic
  onboarding policy, chunks, accounts, and deterministic tutor controls.
- Generated artifact path: stdout JSON; the deterministic cases are committed
  in `scripts/verify_student_workflow_slice.py`.
- Predecessor: `student-workflow-slice-v1-synthetic`, which passed the bounded
  student journey but did not expose professor release publication.

## Decision question

Can a reviewed onboarding policy become a durable draft release that is
evaluation-gated, published atomically, withdrawn safely, and rolled back
without allowing a stale student conversation to cross release boundaries?

The prediction was that a domain lifecycle service over the existing SQLite
repository could add publication control without regressing any of the 14 v1
student checks. The baseline was v1's manually seeded published releases. The
candidate was an explicit draft/evaluate/publish/withdraw/rollback state machine
with atomic current-release replacement. A graph/workflow engine was considered
unnecessary until branching or recovery evidence demonstrates a need for it.

Hard gates were all 14 predecessor checks passing, publication denied before a
passed evaluation, policy and tutoring-chunk approval enforced, one current
release per course, stale conversations denied after replacement, rollback
restoring only an eligible prior release, zero authorization violations, no
network calls, and no private data.

## Data and exact boundary

The deterministic fixture contains one synthetic professor-owned course, the
v1 synthetic accounts and course memberships, a reviewed onboarding policy,
approved course-scoped chunks, an existing published release, and a replacement
draft. It is architecture acceptance coverage, not a statistical sample;
confidence intervals are not meaningful.

The candidate uses `ReleaseLifecycleService` and the SQLite repository behind
typed interfaces. Draft creation snapshots the onboarding policy and approved
chunks. Publication requires `evaluation_status=passed`, an approved policy,
and at least one approved tutoring chunk, then withdraws the previous release
and publishes the candidate in one transaction. Conversations remain bound to
their original release and fail closed when that release is no longer current.

## Aggregate result

| Candidate | Checks passed | Unauthorized release use | Network calls | Private data |
| --- | ---: | ---: | ---: | ---: |
| SQLite publication boundary v2 | 19/19 | 0 | 0 | 0 |

The new checks covered draft creation, evaluation gating, current-release
replacement, stale-conversation denial, and rollback restoration. The existing
student checks also continued to pass for authorization, citations, restart
persistence, fallback, redacted audit events, and safe generation failure.

No acceptance check failed. The run made no external call, used no paid tokens,
and cost USD 0. Latency, memory, database size, migration time, backup/restore,
multi-process contention, and concurrent capacity were not measured.

## Decision

Outcome: **Keep** the release lifecycle as a bounded local R3 foundation.
Publication requires passed evaluation, approved policy, and approved tutoring
chunks. Publishing withdraws the previous course release in one SQLite
transaction, and conversations bound to the previous release fail closed.

SQLite plus explicit domain transitions remains the control and reversal path;
the lifecycle can be replaced behind the repository/service interfaces if
concurrency or operational evidence later fails. This result does not select
conversation orchestration for production or promote the component profile to
release-candidate status.

## Limitations and follow-up

- This does not qualify credentialed authentication or full professor/admin
  course and source administration.
- The account header, onboarding policy, chunks, and student content are
  synthetic test boundaries.
- The accepted M2 route uses the synthetic architecture harness; exact live
  generator/prompt and sealed runtime qualification remain R2 work.
- Schema migration across deployed versions, backup/restore, retention,
  deletion, multi-process concurrency, bounded capacity, and operator recovery
  are not evidenced.
- No frontend student journey, human usability, learning outcome, or public
  hosting claim is supported.
