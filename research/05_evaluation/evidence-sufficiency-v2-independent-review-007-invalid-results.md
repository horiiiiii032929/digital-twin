# Evidence-sufficiency v2 independent-review 007 invalid result

## Decision

**Invalid execution; revoke authorization, stop the OpenRouter reviewer path,
and draw no reviewer-quality, dataset-quality, or method-quality conclusion.**

The sensitivity-first stop worked as designed. The first OpenRouter request
failed before a provider response, and all 12 bulk review batches were
suppressed. This run and the OpenRouter reviewer path must not be retried.

## Execution

- Clean execution revision: `74f442dd9747f83f53dfb31ff9fa7f7c19e63fe4`.
- Reviewer request: `openai/gpt-5.4-mini` with compatible OpenAI-to-Azure
  same-model fallback through OpenRouter.
- Expected backend: `openai/gpt-5.4-mini-20260317`.
- Instrument SHA-256:
  `91dd02a32d91c0a19b6516399b3510734f25ac289960007af84ddfecd33f133c`.
- Review-packet SHA-256:
  `a6cdda77cb824cc620577cc1fcab23ec17166fa78ba525faaf3ff811b062eed7`.
- Reviewer-binding SHA-256:
  `f9eb91d458ae261dd18f1e1c9adea0b58ca8671299ba701f832bbbc20e8bf794`.
- Runner SHA-256:
  `ff2b016f8a3aa6e9286ddab1053ac2ed25e0487e25bdb5fca4333a1d55ae9d87`.
- Raw ignored output SHA-256:
  `8113c89f16e0d749a2788ee443be8f127446b3f722c06e6378cb0c359360dc39`.
- Data boundary: synthetic-public only; no private or held-out data read.

## Observed result

- Calls attempted / provider responses: 1 / 0.
- Bulk calls attempted: 0 / 12.
- Accepted judgments: 0 / 132.
- Provider-reported input / output tokens: 0 / 0.
- Provider-reported cost: USD 0.
- Final state: `invalid-execution` with HTTP 400 `Provider returned error`.
- Router metadata: direct routing in Singapore, not BYOK. Three endpoints were
  known, but only the OpenAI endpoint was reported compatible and it was not
  selected successfully; Azure did not become available under the contract.

Immediately after the stop, the same credential authenticated against the
OpenRouter current-key endpoint with HTTP 200. This distinguishes account-key
authentication from the failed inference route. OpenRouter returned no request
ID, generation ID, or more specific upstream message, so the exact cause cannot
be established from the retained response.

## Cross-review finding

There is no priority packet because no judgment exists. The deterministic
stop, accounting, source boundary, and diagnostic record are internally
consistent. This is an unambiguous operational failure and requires no case
adjudication.

## Why no quality conclusion is valid

Review 007 says nothing about GPT-5.4 mini sensitivity or specificity, the
120-case draft, or any evidence-sufficiency candidate. The higher ceiling was
not approached and was not the blocker. Metadata discovery and request
compatibility did not prove successful inference.

## Next gate

Keep review 007 immutable and authorization revoked. Do not create another
OpenRouter routing or prompt successor. Issue #105 now requires one explicit
method-level choice between a directly authenticated reviewer path already
proven operational in this repository and a deterministic plus bounded
researcher-review protocol. Dataset freezing, candidate evaluation, method
selection, and deployment remain unauthorized.

