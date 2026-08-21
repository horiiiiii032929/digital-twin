# Deployable product foundation V10 malformed-verifier correction

## Run identity

- Result ID: `deployable-product-foundation-v10-malformed-verifier-correction-001`
- Component: evidence-sufficiency fail-closed runtime boundary
- Status: valid build-only correction
- Date: 2026-08-21
- Implementation revision: `c416f00f8b27ea46b7cd82d9da453fb6c62c39f6`
- Data: synthetic unit fixtures only; no decision split opened
- Provider/model calls: zero
- Private or held-out data read: no
- Cost: USD 0

## Finding and correction

Post-V9 adversarial review found that an injected verifier returning a malformed
plain object could escape the fail-closed path when the gate later accessed a
missing signal field. V10 validates every verifier response through the typed
`EvidenceSupportSignals` contract inside the protected call boundary. Raised
errors and malformed returned objects now both produce a redacted abstention.

The corrected focused suite passes 30/30 tests, including the new malformed
object regression. The v2 instrument remains build-only and its preflight still
reports `blocked-dataset-not-frozen` with zero calls and no decision-split read.

## Decision

**Refine; keep publication fail closed and select no release candidate.** The
runtime boundary correction is kept. The new 120-case decision set, independent
review, exact candidate, calibration, one-time decision execution, current image
build, and publication result remain pending.

V9 remains valid historical build evidence for the original boundary but is
superseded by this correction for current-match claims.
