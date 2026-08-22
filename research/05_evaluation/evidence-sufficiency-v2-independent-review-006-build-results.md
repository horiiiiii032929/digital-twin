# Evidence-sufficiency v2 independent-review 006 build result

## Decision

**Go Deeper with snapshot-pinned GPT-5.4 mini as the single confirmation
candidate; keep provider execution and every downstream decision closed.**

Review 006 prospectively replaces only the unexecuted review-005 model binding.
Reviews 002–005 remain unchanged. The choice was made before any review-006
quality result, using current model tier, exact snapshot availability,
cross-family independence, endpoint capability, and bounded cost. No provider
inference, private-source access, held-out evaluation, dataset freeze,
component selection, or release promotion occurred.

## Frozen candidate

- Implementation revision: `908605b5d5173703a86da342141ec8615a7486d8`
- Instrument: `evidence-sufficiency-v2-independent-review-006`
- Instrument SHA-256:
  `943a92d63bb1930b83b8e3bd7802487e2d862f79fad31258b61b5492bb6cee99`
- Review-packet SHA-256:
  `40c8bea9f9316a12b1a55fba8aadaac82a6a8434c70499c8ee0aafd8eb94a64e`
- Runner SHA-256:
  `e735e9cd7f226fb014b2c4ba2503ce2e69523433671008fbbc087ca5352af408`
- Network-free simulation SHA-256:
  `ae5a5fe482428b1240a295b4d37e75a28fb2316fcb5b47275c28b805dfff9953`
- Provider/model inference calls: zero
- Private or held-out data read: zero

The requested model is `openai/gpt-5.4-mini`. Routing is restricted to the
OpenRouter `openai` standard endpoint with fallback disabled and required
parameter support. The live endpoint identifies the dated backend as
`openai/gpt-5.4-mini-20260317`, with a 400,000-token context window and strict
structured-output support. The request omits unsupported `temperature`, fixes
reasoning effort to `none`, and fixes seed `0`.

## Bounds

- Unchanged synthetic-public 120-case draft and 12 sensitivity controls.
- One sensitivity-first call followed, only on success, by 12 review batches.
- Maximum 13 calls, zero retries, and no fallback routing.
- USD 0.429 maximum reservation under a USD 0.50 emergency ceiling.
- The reviewer is advisory and cannot change deterministic source truth.
- Provider execution, private inputs, candidate evaluation, dataset freezing,
  and automatic selection remain unauthorized.

## Verification

- Focused review tests: 42 passed.
- Network-free simulation: 13/13 calls and 132/132 judgments completed.
- Simulated sensitivity: 6/6 clean and 6/6 defect controls handled correctly.
- Complete repository gate: 801 Python tests and 46 frontend tests passed,
  together with documentation, freeze, inventory, lint, and production-build
  checks.
- Repository correctness inventory: 490/490 audited.
- Execution freeze: 61/61 protected entrypoints; zero external execution.

## Live no-call preflight

The live metadata-only preflight found the configured credential without
exposing it, an unused output path, fresh model and exact endpoint metadata,
and no provider mismatch. Because the verification worktree was intentionally
dirty, it reported the three authorization locks plus `working-tree-dirty`.
After publication, a clean preflight must still require exactly the three
intentional locks:

1. `provider-review-not-authorized`;
2. `instrument-not-frozen`;
3. `bounded-freeze-authorization-missing`.

## Limitation and next gate

This proves build and endpoint compatibility, not GPT-5.4 mini reviewer quality
or dataset quality. Do not run review 005 as a fallback and do not compare
multiple reviewers after seeing their verdicts. A separate checkpoint must
refresh metadata, freeze only review 006, add only it to the bounded allowlist,
and obtain explicit paid-run approval before the first provider call.
