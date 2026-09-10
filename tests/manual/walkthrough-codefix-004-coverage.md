# Walkthrough codefix 004 coverage supplement

This supplements, without rewriting, [the original 106-case ledger](aws-pilot-lifecycle-001-coverage.md). Original dispositions remain 35 pass, 27 partial, 14 fail, 8 blocked and 22 not run. Local deterministic checks do not replace AWS/model evidence.

| Area | New evidence | Remaining boundary |
| --- | --- | --- |
| H-001 / H-002 | Fixed; hook regressions and browser delayed/failed metadata recovery pass | Historical AWS cause unproven |
| Repeated chat | Three browser turns, one reload under faults, read-only retries | Live model quality, near-limit input and full disconnect not retested |
| Citation metadata | Partial failure, retry, stale-response and new-turn association hook tests | Positive citation detail drawer not retested in browser |
| Authentication | Student → professor → student B → student A; scoped history restored | Credential reset, expiry and revocation browser scenarios not rerun |
| Professor | Course navigation roundtrip and one synthetic text upload to succeeded | Full fresh publication blocked by existing review prerequisites |
| Check-ins | Consent on/pause/resume/off UI passes | Delivery/acknowledgement/goals require disabled worker; remain blocked |
| UI | Desktop/mobile metadata errors and composer visible; sampled console clean | Not an exhaustive accessibility audit |
| B-002/B-004/B-005 | Existing accounting/API and frontend tests pass | No new deployment |
| B-003 | Synthetic-preview wording verified | Generation and approval design unchanged |
| B-001/B-006/B-007/B-008/B-009 | Documented limitations preserved | No retrieval/refusal/assessment/model changes |

See [full results](../../research/05_evaluation/walkthrough-codefix-004-results.md) and [machine evidence](../../research/05_evaluation/records/walkthrough-codefix-004.json).

## Subsequent matched-runtime retest

[slide-local-005](../../research/05_evaluation/slide-local-005-results.md) adds eight live audited turns under verified pilot/slide settings, positive citation-detail rendering, stored evidence comparison and professor prerequisites/navigation. It discovered and repaired two additional coding defects (seed password generation and overlapping Sources/account controls). Earlier unexecuted or worker-blocked scenarios remain so; no original disposition is overwritten.
