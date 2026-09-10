# Cheap-candidate composed recovery003

Decision: **Keep integration contract; semantic adoption remains pending.**

V19 Luna-low draft/Luna-medium audit with assessed-count, analytic-only planning,
V2 source assessment, recovery and context retrieval passed152/152checks. This
includes credentialed roles, mixed PDF/text/Markdown sources, cohort privacy,
withdrawal, source-isolated responses and backup restore. Exact audit identity is
now passed through the factory instead of inferred through a budget wrapper.

The earlier added cheap-composition test failed at `cited-candidate-0`, exposing
the wrapper identity bug. After correction all four mixed-source tests passed;
this named run records the corrected code epoch. No external provider calls.
Elapsed 2.067s; peakRSS 329154560bytes;
19 injected calls. Source unchanged during run.

[Full record](records/post-report-product-integration-003-contract-001.json) includes configuration, checks, revision, dirty
state and archived source hashes. This is one dependent synthetic journey and
cannot establish semantic correctness, real learning or production readiness.

Reproduce: `uv run python -m scripts.run_mixed_source_recovery_development --execute --post-report --candidate v19-luna-luna-medium --output-dir reports/generated/<fresh-id>`.

Additional worker regressions passed23tests, including exact API/worker role
identity for the cheap candidate and persisted single delivery after normal
restart or a simulated crash after delivery, with successful or timed-out wording
strategy. The proactive pathway uses bounded wording; it does not exercise the
reactive generation audit. This distinction remains visible in the interpretation.
