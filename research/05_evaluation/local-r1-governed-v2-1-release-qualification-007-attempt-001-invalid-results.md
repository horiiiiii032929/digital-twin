# Local R1 governed V2.1 release qualification 007 attempt 001

## Outcome

`invalid-execution`. The API failed closed during Compose startup before the
live journey, provider calls, or hidden-data access.

The qualified runtime file correctly contained no credential. The launch
process sourced only that file, so the API did not receive the separately
stored `OPENAI_API_KEY` from the ignored repository-root environment.

## Root cause and correction boundary

This was an environment credential-forwarding defect, not product-quality
evidence. The only permitted correction was to load the root credential into
the process environment without printing or copying it, preserve it while
loading the non-secret qualified selectors, and start a fresh stack.

No product method, source, profile, evidence gate, image source, or
qualification check changed.

## Claim boundary

- 0 of 43 operational journey checks executed.
- 0 provider calls, 0 tokens, and USD 0 cost.
- No hidden or sealed package was read.
- No release decision is drawn from this attempt.
