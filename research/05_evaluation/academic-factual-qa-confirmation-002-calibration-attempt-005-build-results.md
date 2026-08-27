# Resilient Gemini calibration attempt 005 build

## Decision

**Go Deeper.** Attempt 005 is ready for one separately authorized 40-control
calibration using a bounded high-availability transport. This is build and
preflight evidence only; it is not reviewer-, product-, or release-quality
evidence.

## Run identity

- Date: 2026-08-26
- Implementation revision: `df9c0adf391262276d2cf2fad96e35a58f7e3a23`
- Attempt: `academic-factual-qa-confirmation-002-calibration-attempt-005`
- Binding: `academic-factual-qa-confirmation-002-reviewer-bindings-004`
- Data: unchanged 40 controls and immutable 40/40 Codex votes
- Provider inference calls, tokens, and cost: zero
- Private data read or uploaded: no

## Method correction

Attempts 001–004 and their unfavorable evidence remain unchanged. Attempt 005
keeps the Gemini 3.7 Flash revision fixed but replaces the single-endpoint route
with an explicit OpenRouter allowlist: Google Vertex global priority, Vertex
global default, Google AI Studio priority, and AI Studio default. OpenRouter may
fall back only within this list. Every completed call records the actual
provider and service tier while model revision remains the stable identity.

The shared strict parameter set uses seed 0 and omits temperature because the
live Vertex endpoints do not advertise temperature support. Structured output
remains provider-constrained and deterministically post-validated. This is a
prospective method change, so no attempt-003 or attempt-004 Gemini vote is
imported.

## Verification

- The network-free simulation produced 40 fresh Gemini votes in ten calls; both
  reviewers scored 1.00 on all four calibration metrics.
- Focused tests cover model-stable provider fallback, per-call route accounting,
  bounded retries, malformed output, identity drift, cost stops, and resume.
- Live metadata found all four exact routes, zero model/price/policy drift, and
  at least two endpoints above the frozen health threshold.
- The OpenRouter credential is present. The live preflight remains blocked by
  the intentional authorization, freeze, and clean-worktree gates.
- The complete repository gate passes 965 Python tests, 46 frontend tests,
  frontend lint and production build, 554/554 audited files, and 75/75 frozen
  entrypoints.
- No provider inference was made.

## Cost and boundaries

The worst eligible route prices reserve USD 0.3815424 for ten primary calls and
two possible retries. The emergency stop remains USD 3. The sealed 200 cases,
visual evaluation, T0 product run, private data, and larger academic stages
remain closed.

## Next checkpoint

After a clean publication commit, refresh metadata and run one no-call
preflight. Paid execution still requires explicit authorization. A valid pass
makes the sealed 200-case panel eligible for a separate decision; any invalid or
quality-failing result is preserved and stops progression.
