# Governed full-autonomy V2.1 actual-product confirmation 018

## Outcome

Confirmation 018 is `invalid-execution`. The direct OpenAI transport and exact
Luna identity canary passed. Both actual-product canary cases then completed
safely, but the autonomous case's Luna response failed the local correlated
schema invariant and used the deterministic fallback. The harness consequently
rejected the product canary before bulk execution.

Two public canary responses were persisted. Hidden gold remained unopened, the
remaining 818 cases were not run, and no quality or release conclusion is drawn.

## Accounting

| Stage | Calls | Input tokens | Output tokens | Cost (USD) | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| Direct transport | 1 | 315 | 178 | 0.0002766 | Passed; exact `gpt-5.6-luna` |
| Reactive product route | 3 | 1,101 | 169 | 0.0004230 | Completed safely; two exact Luna responses and one injected provider failure |
| Autonomous product route | 1 | 560 | 89 | 0.0002188 | Exact Luna identity; schema validation failed; safe fallback completed |
| Total | 5 | 1,976 | 436 | 0.0009184 | Invalid before bulk |

Retries were zero. Provider identity did not drift.

## Finding SE7-8

The direct canary already proves transport, identity, and a valid structured
response. The product-route canary has a different responsibility: prove that
the actual product invoked the selected provider and handled the result safely.
The 018 harness instead required a semantically completed model record from
every product route. It therefore treated an exact-identity malformed response
plus safe product fallback as if the provider route had not executed.

This prevents the main evaluation from measuring the very provider-failure
fallback it preregisters. It is a canary-role defect, not evidence that the
autonomous product violated a safety or policy gate.

## Decision

Preserve 018 as invalid and revoke its authority. Permit one harness-only 019
successor with the same unopened hidden package, methods, prompts, models, and
hard gates. The direct canary will continue to require a completed exact-model
structured response. Product-route canaries will require an observed
identity-bearing provider attempt plus safe product completion, allowing a
malformed semantic response to enter the evaluation as a provider-fallback
event rather than aborting before bulk.

## Limitations

- No hidden-gold scoring or product-quality inference was possible.
- The two public canary inputs and outputs are now known.
- Only public synthetic sources and learners were used.
- Real professor fidelity, real student usability, and learning improvement
  are not established.
