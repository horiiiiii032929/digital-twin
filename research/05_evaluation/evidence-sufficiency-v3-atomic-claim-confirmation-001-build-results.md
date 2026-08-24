# Atomic-claim evidence confirmation 001 build

## Decision

**Go Deeper.** The method-level successor to failed comparison 001 is ready for
one separately authorized local 120-case confirmation. The split remains
unopened, no local model was loaded, and no product component is selected.

## Method

- Implementation revision: `94e8ac56466417b70146f2fe2e3fc9f8fb0d73f7`
- New boundary: validate generated atomic factual claims after generation,
  instead of predicting answerability from the question and passages
- Deterministic authority: active retrieved lineage, claim/citation schema,
  exact claim-set coverage, and final release or safe fallback
- Model authority: advisory entailment scores only
- High-precision control: normalized exact-quote containment
- Candidate: DeBERTa NLI with evidence as premise and claim as hypothesis
- Product binding and automatic promotion: prohibited

The candidate reuses the pinned Apache-2.0
`cross-encoder/nli-deberta-v3-base` revision
`6c749ce3425cd33b46d187e45b92bbf96ee12ec7`. This is a task-bound method
confirmation, not a new model search or leaderboard.

## Prospective dataset and gates

The fresh synthetic-public confirmation contains 120 cases: 40 supported and
80 reject cases. Twelve balanced slices cover exact and paraphrased single and
multi-claim drafts, contradictions, unsupported additions, wrong lineage,
stale and cross-course sources, partial support, missing citations, and
malformed claim contracts. It does not reuse the consumed v2 split.

The candidate must achieve zero false releases, at least 90% supported and
multi-claim retention, 100% mutation/lineage/malformed rejection, p95 at or
below 500 ms, and less than 2 GiB added memory. Thresholds cannot be tuned on
the confirmation result.

## Verification

- Network-free simulation passed supported, unsupported, and unknown-lineage
  paths without loading the model or opening the split.
- No-call preflight is blocked only by candidate, local-model, and confirmation
  authority.
- Full repository gate passed at clean revision `94e8ac5`: 856 Python tests,
  46 frontend tests, frontend lint, and production build.
- Repository correctness inventory: 517/517 audited.
- Execution freeze: 67/67 protected entrypoints, zero missing guards.
- Provider calls, paid cost, private data, and held-out access: zero.

## Stop boundary

Do not open the confirmation split or load the local model until a separate
authorization checkpoint changes only the three local authorities and the
bounded freeze entry. After execution, directly audit at most 12 prioritized
failures or controls, publish every outcome, and revoke authorization. A pass
permits a separate product-binding checkpoint; it does not itself promote T1,
deploy, or authorize a human pilot.
