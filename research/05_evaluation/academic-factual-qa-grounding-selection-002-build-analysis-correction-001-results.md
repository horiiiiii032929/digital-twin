# Grounding selection 002 build analysis correction 001

## Outcome

The original build-only `Go Deeper` claim overstated execution readiness. The
candidate and control manifests declared adapter version `v2-action-router`,
while the factory returned a `v1` adapter. The final permitted long-run attempt
therefore stopped before provider I/O with an adapter/system-manifest identity
error. This is an integration defect, not factual-quality evidence.

The correction adds an explicit identity-bearing action-router adapter and
requires both frozen manifests to equal that implementation contract during
build validation. A deliberately drifted manifest now fails before provider
construction. It does not change questions, hidden gold, retrieval, prompts,
models, quality gates, or historical results.

## Verification

- Focused adapter, execution, simulation, and preflight checks: 10 passed.
- Complete repository gate: Python 1,443 passed; frontend 50 passed; lint and
  production build passed.
- Repository correctness: 827/827 audited with zero pending findings.
- Execution freeze: 121/121 protected entrypoints passed.
- Provider calls, tokens, cost, product responses, and hidden-gold access: zero.

## Decision

Record **Go Deeper** for the corrected integration boundary only. Historical
attempts 001 and 002 remain immutable and there is no attempt 003 under their
instrument. Any quality evaluation must use a separately versioned #153
successor and fresh exclusive outputs.

The next valid 500+100 result follows the finite software improvement loop:

- `Keep` opens a source-disjoint confirmation while retaining T0 rollback.
- `Refine` identifies one dominant failure slice and creates one method-level
  successor on fresh development evidence.
- `invalid-execution` permits only a preregistered harness correction and makes
  no quality claim.

## Limitations

This correction proves contract consistency and regression safety only. It does
not establish factual grounding, autonomous tutoring quality, professor
fidelity, usability, learning outcomes, or release readiness.
