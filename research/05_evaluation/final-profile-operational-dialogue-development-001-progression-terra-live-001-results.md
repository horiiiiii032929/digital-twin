# Terra v2 finite progression comparator 001

## Decision

Do not replace Luna based on this finite development comparison. All 24 Terra
calls returned valid model output, but the sixteen delivered turns still
contained two safe graph failures and weak pedagogical continuation. Reported
cost was $0.084888, compared with $0.0113548 for the prior Luna pilot.
The [independent assistant review](dialogue-progression-terra-live-001-assistant-review.md)
found no replacement evidence; no release profile was changed.

## Observations

The explanatory profile's initial turn asked for an explanation rather than
giving one. Two incorrect-attempt turns failed closed. New-topic behavior and
other exact source responses do not establish better tutoring. Both models
produced eight questions, six answers and two safe graph failures in aggregate,
but these occurred at different stages, so action counts hide material
qualitative differences.

The [prospective plan](../04_experiments/2026-09-06-operational-dialogue-development-plan.md)
uses the same four histories and sixteen fixed stimuli as the
[Luna pilot](final-profile-operational-dialogue-development-001-progression-live-001-results.md).
This overrides only reactive generation/semantic-planning model identity; it
does not evaluate a full Terra autonomy configuration. All four histories and
restarts completed, and captured source hashes remained unchanged. The
[record](records/final-profile-operational-dialogue-development-001-progression-terra-live-001.json)
retains requested/returned identity, exact configuration/source hashes, dirty
revision, cost and raw artifact hashes. Full output remains in
`reports/generated/final-profile-operational-dialogue-development-001-progression-terra-live-001`.

## Limitations and reproduction

This is an unblinded development comparison with reused synthetic stimuli,
not a held-out benchmark or learning study. SQLite/concurrency instrumentation
was corrected after the Luna pilot; per-case serial behavior remained in use.
Co-resident G6 workload confounds latency comparisons. No private student or
course data were used. Exact spans do not guarantee a useful partial hint.

With the configured credential privately loaded, use a fresh directory:

```bash
uv run python -m scripts.run_operational_dialogue_development --progression-live --progression-model gpt-5.6-terra --output-dir reports/generated/terra-progress-fresh
```

The $2 reservation bound at $0.06 per call permits at most 33 dispatches,
within the nominal 100-call cap. All 24 calls completed within that bound.
