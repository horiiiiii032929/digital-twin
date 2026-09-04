# Corpus confirmation 026 (invalid attempt)

## Outcome

**Invalid execution.** 305 of 670 responses were persisted when the process was
killed. The resume then failed with `ValueError: release content is immutable
after creation`, and writing that failure produced a terminal result, which the
runner correctly refuses to resume.

Hidden gold was never opened for this package.

## Cause

The defect is in the shared confirmation harness, not in the multi-source
corpus change. Resume skips cases already present in the response ledger, but
the case that was in flight when the process died is absent from the ledger and
is therefore re-run -- against the per-case product database it left behind.
`save_release` refuses a second release with the same identity regardless of
content, so that one case could never complete. Any confirmation killed
mid-case had the same problem; it had simply never been exercised.

## What did complete

- 305 of 670 responses persisted
- 863 provider calls, exact returned model `gpt-5.6-luna`
- 431,928 input and 82,737 output tokens, USD 0.18567
- Direct transport identity canary passed
- Hidden gold unopened

## Decision

Revoke 026 and draw no quality conclusion. Clear the per-case database before
opening it so a killed case can be re-run, and give each release chunk its own
ordinal. Because the package's hidden gold was never opened, bind that
identical unopened public and gold payload to one harness-only successor,
`governed-full-autonomy-v2-1-corpus-confirmation-027`. This is the route
confirmation 024 took after 023, recorded there as
`reused_after_invalid_pre_gold_attempt`.

## Limitations

Public synthetic sources and personas. No release, quality, or safety
conclusion is drawn from a partial ledger.
