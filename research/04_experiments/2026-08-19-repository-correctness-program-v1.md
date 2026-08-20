# Repository correctness program v1

Date: 2026-08-19

Status: active pre-evaluation freeze

## Decision and scope

No new dataset generation, held-out inspection or execution, component
selection, or model/provider evaluation may begin until a repository-wide
correctness freeze is complete. Deterministic local checks over public,
synthetic, or already-authorized unsealed inputs remain permitted when they do
not alter an evaluation dataset or selection decision.

The program covers every tracked executable and execution-affecting file,
including runtime code, API services, frontend code, evaluation and operations
scripts, tests, migrations, notebooks, CI, deployment files, and dependency or
environment configuration. Every inventoried file must finish with exactly one
disposition:

- `active_audited`;
- `refactor_required`;
- `historical_guarded`; or
- `remove`.

An inventory entry is accounting evidence only. It does not establish that the
file is correct.

## Correctness dimensions

Every active path is reviewed against the dimensions relevant to its role:

1. input, output, state, and failure contracts;
2. permission, privacy, academic-integrity, and course-isolation boundaries;
3. provenance, version, checksum, split, and reproducibility integrity;
4. algorithm and metric definitions, denominators, aggregation, and edge cases;
5. timeout, malformed-input, unavailable-provider, partial-write, retry, and
   rollback behavior;
6. authentication, authorization, data lifecycle, backup, and restore;
7. user-visible loading, empty, error, stale, inaccessible, and recovery states;
8. tests that would fail if the accepted behavior regressed; and
9. documentation and stakeholder claims that match executable evidence.

Passing tests are necessary but are not sufficient evidence of logical or
methodological correctness.

## Ordered work

1. Build the complete executable-code inventory and audit ledger.
2. Correct factual-QA v3 governance and sequencing defects.
3. Audit ingestion and multimodal conversion.
4. Audit retrieval and evidence sufficiency.
5. Audit generation, policy, providers, and model identity.
6. Audit evaluation code, judge validity, statistics, and split protection.
7. Audit API, security, persistence, lifecycle, operations, and deployment.
8. Audit professor and student frontend flows against the real API contract.
9. Reconcile results, profiles, commands, decisions, current status, and claims.
10. Perform an independent second review and complete the correctness freeze.

Work is split into focused commits and pull requests where practical. Historical
evidence remains immutable; corrections receive new result or decision records.

## Hard exit gates

The correctness freeze may be created only when:

- every inventoried file has a final disposition and current source hash;
- no unresolved high- or medium-severity finding remains;
- accepted low-severity limitations have an owner, rationale, and containment;
- every active high-risk boundary has focused regression and failure tests;
- historical or deferred external entrypoints fail closed against accidental use;
- source eligibility and mandatory exclusions are content-safe before transfer;
- evaluation metrics and stakeholder claims are independently recomputed or
  traced to durable evidence;
- the complete local check, dependency audits, and CI pass from a clean commit;
- no credential, private source content, student data, or held-out content is
  committed; and
- a versioned freeze record binds the code revision, inventory, tests, remaining
  caveats, documentation, and GitHub state.

Until then the overall decision remains **Refine** and evaluation execution
remains unauthorized.
