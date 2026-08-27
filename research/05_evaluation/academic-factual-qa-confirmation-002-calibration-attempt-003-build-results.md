# Gemini calibration attempt 003 build

## Decision

**Go Deeper.** Attempt 003 is technically ready for one bounded 40-control
calibration. This is build and metadata evidence only; it is not reviewer,
factual-QA, product, or multimodal quality evidence.

## Run identity

- Date: 2026-08-26
- Implementation revision: `a43ec854e5a489de0a5ab71566990da597b9646c`
- Attempt: `academic-factual-qa-confirmation-002-calibration-attempt-003`
- Binding: `academic-factual-qa-confirmation-002-reviewer-bindings-002`
- Dataset: unchanged 40 sealed controls; the 200 confirmation cases remain unopened
- Real provider inference calls, tokens, and cost: zero
- Private data read or uploaded: no

## What changed

The two invalid Mistral attempts remain unchanged. Attempt 003 reuses their
deterministic truth, blinded packet, and immutable 40/40 Codex calibration
votes. It changes only the failed reviewer slot to OpenRouter
`google/gemini-3.7-flash`, revision `20260813`, routed exclusively to the
standard `google-ai-studio` endpoint with fallback disabled. Direct DeepSeek V4
Pro remains the third reviewer.

The provider schema omits constraints outside the conservative Gemini subset.
Exact vote coverage and IDs, uniqueness, rationale bounds, visible-evidence
lineage, action consistency, citations, and semantic invariants remain
authoritative deterministic checks after parsing.

## Verification

- The complete simulation produced exactly 20 provider-call records: one
  Gemini canary, one DeepSeek canary, and nine remaining batches per provider.
- All three simulated reviewers passed action accuracy, mutation sensitivity,
  specificity, and citation-defect sensitivity at 1.00.
- Failure tests stop on the first canary error, runtime identity drift, malformed
  output, token/cost limits, stale bindings, and invalid resume without retry.
- The fresh live metadata-only preflight found the exact model revision,
  standard endpoint, prices, supported parameters, routing, 55-day retention
  policy, and both credentials with no drift. It made no inference call.

## Cost and boundaries

At the checked endpoint prices, ten maximum Gemini calls reserve USD 0.17664
and ten DeepSeek calls reserve USD 0.229786, for USD 0.406426 total. The hard
stop remains USD 3. Attempt 003 cannot open confirmation, visual evaluation,
live T0 product execution, private data, or the later 600/10,000-case stages.

## Next checkpoint

Freeze only attempt 003, repeat the clean live preflight, and execute the
40-control calibration once. Publish `invalid-execution`, `completed-refine`,
or `completed-go-deeper`, revoke the one-time authority, and stop before the
200-case panel.
