# Governed full-autonomy V2.1 actual-product confirmation 016

## Outcome

Confirmation 016 is `invalid-execution`. The runner persisted both frozen
public canary cases, made zero provider calls, spent USD 0, and stopped before
bulk execution. Hidden gold was not created or opened, so no product-quality
measurement or release decision is drawn from this attempt.

## Root cause

Finding `SE7-4` is a canary-selection harness defect. The V3 grounding fix made
the selected T1-v2 reactive canary eligible for the deterministic factual fast
path. The case therefore correctly made no Luna call, while the frozen canary
assertion still required a Luna identity. The assertion failed even though both
canary responses completed safely.

This is not a provider outage and not a product-quality failure. The runner did
not attempt a network request before stopping.

## Corrective boundary

Attempt 017 is the single permitted harness-only correction. It reuses the exact
016 public and hidden packages, methods, prompts, cases, gold, gates, models, and
budgets. Only the second canary changes to a T1-v2 autonomous case whose due
opportunity necessarily exercises the selected Luna provider path. Attempt 016
remains immutable and its authority is revoked.

## Limitations

- Only two public canary responses were persisted.
- Hidden gold remained unopened, so the run provides no academic quality result.
- Real professor fidelity, real student usability, and learning improvement are
  outside this checkpoint.
