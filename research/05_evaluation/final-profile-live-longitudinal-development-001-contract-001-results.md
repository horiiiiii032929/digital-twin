# Final-profile longitudinal contract smoke 001

## Decision

Keep the production-factory bridge for further development. This is a
**network-free contract smoke**, not a live model evaluation or release pass.
The initial four histories completed three virtual days with one restart each.
All 11 injected client attempts returned deliberately malformed-output errors.
Actual provider calls, tokens, and cost were zero.

## Design and provenance

The [plan](../04_experiments/2026-09-05-project-completion-plan.md) defines the
development question and future quality gates. Two personas and paired reactive
and autonomous modes use new synthetic development sources with seed 4107.
The production application factory selects BM25, the dominance gate,
deterministic factual claims, and Luna planning interfaces. The transport is
explicitly replaced for this run. Course setup uses a synthetic fixture and
does not validate document ingestion, publication preflight, or UI interaction.

The [machine record](records/final-profile-live-longitudinal-development-001-contract-001.json)
retains the source revision, dirty state, runner/runtime hashes, configuration,
dataset identity, per-history restart counts, and artifact hashes. Per-case
outputs and attempt ledgers remain under the ignored generated directory named
in that record. The run is intentionally too small to estimate quality.

## Observations and limits

- Four histories completed without a history-level exception; each restarted once.
- Recorded timing violations were zero, but the injected failures do not test
  real model decision quality.
- Some short histories contained no assessed attempts. Their assessment metrics
  are null and must not be interpreted as a pass.
- The long-run scorer remains a synthetic diagnostic; independent factual and
  contrasting-profile quality assessment is still required.
- Existing 025 and consumed factual data were not modified, run, or rescored.

## Reproduction

```bash
uv run python -m scripts.run_final_profile_longitudinal --validate
uv run python -m scripts.run_final_profile_longitudinal --contract-smoke --days 3 --output-dir reports/generated/final-profile-contract-fresh
```

Use a new output directory. The runner rejects an existing directory and writes
attempt records before dispatch. Live execution has separate bounded authority
and is not enabled by running this contract check.
