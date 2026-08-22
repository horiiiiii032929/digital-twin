# Evidence-sufficiency v2 independent-review 004 invalid result

## Decision

**Invalid execution; revoke authorization, drop this exact OpenRouter/Mistral
binding, and draw no reviewer-quality, dataset-quality, or method-quality
conclusion.**

The sensitivity-first stop worked as designed. The first native OpenRouter
request failed without a provider response, and all 12 bulk review batches were
suppressed.

## Execution

- Clean execution revision: `ba0b4961b9f5d49102bed38bb7c9f3bfde00135b`.
- Reviewer request: `mistralai/mistral-small-2603` through first-party
  Mistral-only OpenRouter routing with fallback disabled.
- Instrument SHA-256:
  `f128f037a040bf1a34c593603eba7db5d5a1f7a8ffbd1851249acd746b6a6f39`.
- Review-packet SHA-256:
  `75fc54d28a708df7a36150f0519db6eb7429b6e625ebbde7feceecfa817f8fbd`.
- Reviewer-binding SHA-256:
  `dd5beabb78b4b130fe124fcb4cf5bd4f921bd060264d56bee7fd3e0c210bb989`.
- Runner SHA-256:
  `b62203a3926635a0db922e9860dcf9f056cb1e098691c657c80d8173fe30b685`.
- Raw ignored output SHA-256:
  `b1c0844f4fa59a45f11a387bbfa5a9643193b3351797b37eaa3aa581c7051007`.
- Data boundary: synthetic-public only; no private or held-out data read.

## Observed result

- Calls attempted / provider responses: 1 / 0.
- Bulk calls attempted: 0 / 12.
- Accepted judgments: 0 / 132.
- Provider-reported input / output tokens: 0 / 0.
- Provider-reported cost: USD 0.
- Final state: `invalid-execution` with native HTTP 401 `Provider returned
  error`.
- Router metadata: direct routing in Singapore, not BYOK; two first-party
  Mistral attempts returned statuses 400 and 401; two endpoints were reported
  available but neither was selected successfully.

Immediately after the stop, the same credential authenticated against
OpenRouter's documented read-only
[current-key endpoint](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key)
with HTTP 200 and a paid-account response. This distinguishes account-key
authentication from the failed inference route. OpenRouter did not return a
request ID, generation ID, or more specific provider message, so the exact
upstream cause cannot be established from the retained response.

## Cross-review finding

There is no priority case packet to inspect because no judgment exists. The
deterministic stop, accounting, source boundary, and router-diagnostic record
are internally consistent. This is an unambiguous operational failure, not a
case requiring researcher adjudication.

## Why no quality conclusion is valid

Review 004 says nothing about Mistral sensitivity or specificity, the 120-case
draft, or any evidence-sufficiency candidate. The native transport remains
useful diagnostic build evidence, but this exact OpenRouter/Mistral execution
binding has now failed after the earlier wrapper and structured-output attempts
also produced no usable review. It should not be retried as another prompt or
transport refinement.

## Next gate

Keep instrument 004 immutable and authorization revoked. Choose one different
bounded reviewer path at a method-level checkpoint, preferably a provider path
already proven to return structured responses in this repository. Any new paid
attempt requires a successor ID and separate authorization. Dataset freezing,
candidate evaluation, method selection, and deployment remain unauthorized.
