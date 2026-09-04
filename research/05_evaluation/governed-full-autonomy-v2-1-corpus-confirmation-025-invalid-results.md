# Corpus confirmation 025 (invalid attempt)

## Outcome

**Invalid execution.** All 670 responses completed and were persisted, then
scoring raised `AttributeError: module
'scripts.build_governed_full_autonomy_v2_1_corpus_confirmation_025' has no
attribute 'DAY'`. The new builder did not re-export the clock day length the
shared runner reads from its package. No product, response, case, or gold
content was involved.

The attempt is revoked and stays invalid. It selects nothing.

## What did complete

- 670 of 670 responses persisted and hash-verified
- 1,828 provider calls, 1,785 identity-bearing, exact returned model
  `gpt-5.6-luna`
- 931,361 input and 191,306 output tokens, USD 0.41583940
- Direct transport identity canary passed
- Hidden gold opened only after every response was durable

## Recovered score, disclosed as a diagnostic only

Because the responses were durable and gold opened only after them, scoring
them is a pure function of (responses, gold). A guarded recovery entrypoint
produced `completed-keep` with all twenty registered gates passing, action
accuracy 1.000, and independent `safe_grounded_autonomous_success` 1.000 across
670 cases.

**That score is not release evidence.** This repository's convention is not to
post-hoc rescore an invalid attempt: confirmations 014 and 021 both record "do
not rescore". The distinction here is real -- no gate, threshold, or gold
changed, and only a missing module attribute stopped scoring from starting --
but it is not a distinction the author of the defect should apply to their own
run. The score is published so the evidence is not hidden, and it is labelled a
diagnostic in the record.

## Decision

Revoke 025, draw no release conclusion, and add the missing export plus a
guarded scoring recovery entrypoint. Run the identical method and corpus regime
once on a fresh package. The successor is
`governed-full-autonomy-v2-1-corpus-confirmation-027`, which is the decision
evidence and is not permitted to fall back to this recovered score.

## Limitations

Public synthetic sources and personas. Distractor sources differ from the
answering source only by protocol number, so identification is harder than
typical course prose. Establishes no professor fidelity, usability, or learning
claim.
