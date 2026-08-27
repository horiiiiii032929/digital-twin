# Two-reviewer calibration attempt 004 build

## Decision

**Go Deeper.** Attempt 004 is ready for one separately authorized 40-control
calibration. This is network-free build evidence only; it is not reviewer,
factual-QA, product, visual, or release-quality evidence.

## Run identity

- Date: 2026-08-26
- Implementation revision: `6e09c7a1498dc985c2369f3533713e2bd06ad7e7`
- Attempt: `academic-factual-qa-confirmation-002-calibration-attempt-004`
- Binding: `academic-factual-qa-confirmation-002-reviewer-bindings-003`
- Data: the unchanged 40 sealed controls and immutable 40/40 Codex votes
- Provider inference calls, tokens, and cost: zero
- Private data read or uploaded: no

## Method

Attempts 001–003 and their unfavorable evidence remain unchanged. Attempt 004
removes DeepSeek from this panel and binds only two model families: the existing
calibrated Codex reviewer and exact Gemini 3.7 Flash through Google AI Studio.
Deterministic source truth remains authoritative. Attempt-003 Gemini votes are
not imported; a live run must review all 40 controls in ten fresh batches.

Only timeout, connection failure, HTTP 429/5xx, and empty content are retryable.
Each failed batch may be retried once, with at most two retries globally. Every
failed call and retry remains in the atomic ledger. Parsed malformed output,
schema or semantic violations, token or identity drift, and quality failures
are terminal and are never retried.

## Verification

- The clean network-free simulation produced ten fresh Gemini call records and
  40 Gemini votes; Codex and Gemini each scored 1.00 on action accuracy,
  mutation sensitivity, specificity, and citation-defect sensitivity.
- Pass, valid quality failure, two recovered transport failures, exhausted
  per-batch retry, malformed output, identity drift, budget stop, and exact
  two-reviewer aggregation paths are covered by focused tests.
- The metadata-only live preflight matched the exact model revision, Google AI
  Studio endpoint, pricing, parameters, routing, and retention policy. It found
  the OpenRouter credential and made zero inference calls.
- The live preflight remains blocked by the intentional instrument, bounded
  freeze, and paid-execution locks.
- The complete repository gate passes 963 Python tests, 46 frontend tests,
  frontend lint and production build, 552/552 audited files, and 75/75 frozen
  entrypoints.

## Cost and boundaries

Ten primary Gemini batches plus at most two retries reserve USD 0.211968; the
emergency stop remains USD 3. No Codex or DeepSeek call is permitted by this
attempt. The 200 confirmation cases, visual work, live T0 execution, private
data, and the larger academic stages remain closed.

## Next checkpoint

If separately authorized, freeze only attempt 004, refresh metadata within 24
hours, and execute the 40 controls once. Publish `invalid-execution`,
`completed-refine`, or `completed-go-deeper`, revoke authority, and stop. Only
a pass may make the sealed 200-case panel eligible for a separate decision.
