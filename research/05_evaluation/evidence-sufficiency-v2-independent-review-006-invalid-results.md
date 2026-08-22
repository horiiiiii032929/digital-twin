# Evidence-sufficiency v2 independent-review 006 invalid result

## Decision

**Invalid execution; revoke authorization, drop this exact OpenRouter/GPT
binding, and draw no reviewer-quality, dataset-quality, or method-quality
conclusion.**

The sensitivity-first stop worked as designed. The first OpenRouter request
failed before a provider response, and all 12 bulk review batches were
suppressed. The frozen run must not be retried.

## Execution

- Clean execution revision: `329d6655306a02437a362485a02366a911ad7959`.
- Reviewer request: `openai/gpt-5.4-mini` through first-party OpenAI-only
  OpenRouter routing with fallback disabled.
- Expected backend: `openai/gpt-5.4-mini-20260317`.
- Instrument SHA-256:
  `76de1f17f1c86ab32aa28a2746f0e44a25881c85379123eab1b836ee8b662fc4`.
- Review-packet SHA-256:
  `40c8bea9f9316a12b1a55fba8aadaac82a6a8434c70499c8ee0aafd8eb94a64e`.
- Reviewer-binding SHA-256:
  `a997dc8e002d2919312443a36302ad003f0710aad7f5049f96f8d7548cc16259`.
- Runner SHA-256:
  `e735e9cd7f226fb014b2c4ba2503ce2e69523433671008fbbc087ca5352af408`.
- Raw ignored output SHA-256:
  `eb2cabbd780aaff4293dc350187dae0ba14633ecfa8963c4c98bfda6073b0940`.
- Data boundary: synthetic-public only; no private or held-out data read.

## Observed result

- Calls attempted / provider responses: 1 / 0.
- Bulk calls attempted: 0 / 12.
- Accepted judgments: 0 / 132.
- Provider-reported input / output tokens: 0 / 0.
- Provider-reported cost: USD 0.
- Final state: `invalid-execution` with HTTP 400 `Provider returned error`.
- Router metadata: direct routing in Singapore, not BYOK; one compatible
  first-party OpenAI backend was reported available, but it was not selected
  successfully.

Immediately after the stop, the same credential authenticated against the
OpenRouter current-key endpoint with HTTP 200. This distinguishes account-key
authentication from the failed inference route. OpenRouter returned no request
ID, generation ID, or more specific upstream message, so the exact cause cannot
be established from the retained response.

## Cross-review finding

There is no priority case packet to inspect because no judgment exists. The
deterministic stop, accounting, source boundary, and diagnostic record are
internally consistent. This is an unambiguous operational failure rather than
a case requiring researcher adjudication.

## Why no quality conclusion is valid

Review 006 says nothing about GPT-5.4 mini sensitivity or specificity, the
120-case draft, or any evidence-sufficiency candidate. The metadata preflight
proved discovery and binding compatibility, not successful inference. The
exact execution binding is therefore dropped without changing the unopened
draft.

## Next gate

Keep instrument 006 immutable and authorization revoked. Do not start another
OpenRouter prompt or routing refinement. Issue #105 now needs one explicit
method-level decision: use a directly authenticated reviewer path already
proven operational in the repository, or replace model review with a bounded
deterministic plus researcher audit protocol. Dataset freezing, candidate
evaluation, method selection, and deployment remain unauthorized.
