# Repository correctness full sweep — 2026-08-20

Status: complete and merged through PR #98 at `db2f5e9`

## Decision

Keep the corrected repository state merged on `main` and close the
repository-correctness audit. Do not treat this as a deployment, model-selection,
or evaluation result. Keep the execution freeze active until the next evaluation
action is separately authorized.

## Scope and findings

- Audited all 426 tracked executable or execution-affecting files: 426 audited,
  zero pending, and zero open findings.
- Corrected frontend draft synchronization so a server refresh cannot erase an
  unsaved professor policy edit.
- Prevented a server-reported approved release from overriding locally detected
  source, policy, preview, or checklist blockers.
- Made direct freeze-validator execution work and strengthened guard detection
  against nested or unreachable syntactic tokens.
- Required the repository verification gate to fail when pending or open audit
  records exist.
- Versioned the evaluation-run completion-timestamp correction as v2, preserving
  the frozen v1 schema and evidence unchanged.
- Marked the Gemma-specific cross-course v1 schema historical and immutable.
- Removed the obsolete hard-coded current-RAG plotting script and stale usage
  documentation; historical result records remain preserved.
- Sent multimodal validation diagnostics to stderr so machine-readable stdout
  remains clean.

## Verification

- `npm run check`: passed.
- Python: 621 tests passed; six non-failing third-party/test-fixture warnings.
- Frontend: 46 tests passed; Oxlint and production TypeScript/Vite build passed.
- Ruff and Python compile checks passed for scripts and tests.
- Evaluation, multimodal, retrieval-v3, model-policy, profile, result, technical
  freeze, deployable freeze, staging configuration, and documentation gates
  passed.
- Execution freeze: 50/50 protected entrypoints covered; zero model/provider
  calls and zero private/held-out reads.

## Boundaries and limitations

This sweep used synthetic/public local fixtures only. It did not rerun a model
benchmark, open held-out data, select a component, renew the V6 deployable
current-match claim, or perform a new cross-browser/human-usability study.
Mounted end-to-end frontend coverage for every auth and conversation race is a
useful future hardening task, but no unresolved correctness finding remains in
the audited ledger.
