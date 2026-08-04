# Student workflow slice v1 synthetic results

Result ID: `student-workflow-slice-v1-synthetic`

## Run identity

- Component: end-to-end student workflow architecture.
- Status: completed.
- Date and owner: 2026-08-04, project researcher.
- Code revision: `0c3c9d24aaad5511aa55036ac369c01522f00fdd` plus the
  documented dirty implementation worktree.
- Reproduction command: `npm run verify:student-workflow`.
- Runtime: Python 3.12, standard-library SQLite, FastAPI/Pydantic domain
  contracts, synthetic in-process embedder, deterministic generator.
- Generated artifact path: stdout JSON; every check is synthetic and committed
  in the verification script.
- Predecessor: none; the in-memory onboarding store was not a student workflow
  or restart-persistence result.

## Decision context

The question was whether the smallest local student slice could enforce account,
course, conversation, and release scope while persisting grounded turns and
surviving restart. The prediction was that an injectable SQLite repository
would pass this bounded journey and that authorization drift would be the main
failure risk. The control was the prior in-memory/no-student-API state. The
candidate was SQLite persistence with domain-level checks and selected-profile
orchestration.

Hard gates were zero unauthorized success, withdrawal enforcement, citation
lineage, restart persistence, safe provider/generation failure, idempotent
duplicate handling, redacted audits, no network calls, and no private data.

## Data and configuration

The fixture contains one synthetic professor, two active students, one revoked
student, two courses, two current published releases, one withdrawn release,
and three synthetic approved chunks. It is deterministic acceptance coverage,
not a statistical sample; confidence intervals are not meaningful.

The selected `student-tutor-v1` M2 profile is loaded unchanged. A deterministic
keyword embedder exercises the primary M2 route. A query-failing embedder
exercises BM25 fallback. The deterministic grounded generator is the normal
control and a raising synthetic generator exercises malformed-provider failure.

## Aggregate results

| Candidate | Checks passed | Authorization violations | Network calls | Private-data cases |
| --- | ---: | ---: | ---: | ---: |
| SQLite student slice v1 | 14/14 | 0 | 0 | 0 |

Passed checks were assigned course listing, conversation creation, selected-M2
turn, citation persistence, citation lookup, duplicate idempotency, cross-course
denial, cross-student denial, revoked-account denial, restart persistence,
withdrawal denial, BM25 provider fallback, redacted audit, and malformed
generation safe failure.

## Failures and operational results

No acceptance check failed. The run made no external call, used no paid tokens,
and cost USD 0. Latency, memory, database size, backup/restore time, migration,
multi-process contention, and concurrent capacity were not measured and cannot
be inferred from this result.

## Decision

Outcome: **Keep** the injectable SQLite repository and domain authorization as
the bounded local R3 foundation. Retain selected M2 with BM25 fallback and the
deterministic generator control. This does not select authentication,
conversation orchestration for concurrency, or a live generator, and it does
not promote the system profile to release candidate.

## Limitations and follow-up

- The account header is a synthetic session mechanism, not authentication.
- Professor/admin course and release lifecycle APIs remain incomplete.
- The M2 path uses a synthetic embedder; live local model capacity is untested.
- No student interface, human participant, usability, or learning outcome was
  evaluated.
- Backup/restore, migration, concurrency, capacity, and local packaging remain
  R3 follow-up work.
- R2 must still qualify the exact generator/prompt and compare professor policy
  with the generic controls.
