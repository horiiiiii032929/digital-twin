# Local R1 correctness-fix qualification 011

## Decision and prediction

Before execution: can the runtime correctness fixes retain the qualified local
composition's startup, publication, outreach, citation, persistence, recovery,
and rollback behavior? Predict all 43 existing HTTPS acceptance checks pass,
with no application/checkpoint errors. Keep only if every hard gate passes.

Historical control is qualification 010; the candidate is the corrected source
with the unchanged final profile, BM25/dominance gate, deterministic generation,
text/OCR fallback, and governed V2.1 Luna H+E1 planner selection. This is a
correctness qualification, not a component-quality comparison or new model run.
The source commit and exact image IDs will be recorded before interpreting results.

## Data and gates

Use the versioned `scripts.verify_https_staging` synthetic PDF/account journey:
25 live checks, 6 restart checks, 6 clean-restore checks, 3 T0 checks, and 3
governed-mode restoration checks. One run per stage; preserve failed attempts.
This finite checklist covers required operations, not population accuracy;
confidence intervals are not meaningful. No real students or private corpus,
consumed factual evaluation, tuning, or provider-backed inference is included.

Run the new authority, outreach, and clarification regression tests against the
built API image using a disposable test container; inspect browser desktop and
390x844 login behavior, labels, keyboard order, and console errors. The main
repository gate already passed 1,952 Python and 51 frontend tests for the fixes.
Hard gates: all acceptance/regression checks pass, no extra unauthorized writes,
no critical browser defect, no application/checkpoint errors, verified backup,
and live API p95 <=750 ms. Record latency, build/journey time, container memory,
image size, provider calls/tokens/cost, versions and configuration hashes.

## Isolation and reproduction

Use Compose project `digital-twin-r1-q011` on loopback port 8454 with image tag
`r1-qualification-011`, then fresh project `digital-twin-r1-q011-restore` on
8455. Preserve qualification 010's running project and all existing volumes.
Use the qualified environment example's exact selectors and newly generated
synthetic-account credentials in ignored `.env.local-r1-q011`. An inert test
provider key permits configured-client construction without a billable credential;
only deterministic fast paths are qualified. Any provider attempt is a failure.

Follow `docs/local-r1-runbook.md`: Compose config/build/up, bootstrap administrator,
`scripts.verify_https_staging` with final profile and internal CA, restart/resume,
backup to a new archive, fresh-volume restore/resume, T0 mode-check, and governed
restoration mode-check. Store all outputs under ignored
`reports/generated/local-r1-q011/`; commit sanitized counts, hashes, and failure
classifications in a result summary and machine record and register every attempt.
Stop the test projects after qualification while preserving their evidence volumes.

## Decision boundary

Retain the previous qualified release and T0 rollback. A passing result permits
only a new local operational qualification. Factual grounding remains 63.25%,
and visual, professor-fidelity, human-learning and hosted-production limits remain.
No hash-bound component profile changes are planned.
