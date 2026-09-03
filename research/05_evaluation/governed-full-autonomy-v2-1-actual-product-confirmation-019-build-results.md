# Governed full-autonomy V2.1 actual-product confirmation 019 build

## Outcome

Confirmation 019 is `build-only-qualified` at clean revision `9e24021`. It is
the sole harness-only successor to invalid confirmation 018. The scientific
package is unchanged: the same 820 public-synthetic cases, prompts, model,
hidden gold, hard gates, and source families 351–400 remain hash-bound. Provider
and paid execution are disabled at this checkpoint.

## Root-cause correction

Finding `SE7-8` is closed in code. Confirmation 018 incorrectly required each
product-route canary to contain only semantically completed provider records,
even though the strict direct canary had already proved transport, exact model
identity, and valid structured-output capability. This rejected an actual Luna
response whose correlated fields were malformed even though the product safely
fell back.

Confirmation 019 separates those responsibilities:

- the direct canary still requires a completed, schema-valid response with the
  exact `gpt-5.6-luna` identity;
- each product-route canary requires an observed provider attempt, exact
  returned identity, and safe product completion;
- malformed semantic output remains a measurable product-fallback event rather
  than being misclassified as route non-execution.

The historical runner keeps the previous behavior by default. Only the
versioned 019 context enables the corrected product-route interpretation.

## Network-free measurements

| Condition | Cases | Reference-action accuracy | Safety contracts | Goal termination | Restart consistency |
| --- | ---: | ---: | ---: | ---: | ---: |
| T0 grounded control | 150 | 100% | 100% | 100% | 100% |
| T1-v1 reactive control | 150 | 100% | 100% | 100% | 100% |
| T1-v2 reactive | 150 | 100% | 100% | 100% | 100% |
| T1-v2 autonomous | 370 | 100% | 100% | 100% | 100% |
| Overall | 820 | 100% | 100% | 100% | 100% |

The simulation covered 220 proactive cases. Unauthorized actions, incorrect
recipients or course/release bindings, invalid citation lineage, consent or
timing violations, duplicate revisions/actions/deliveries, unbounded loops,
and model-owned authoritative mutations were all zero. Provider calls and cost
were zero by design.

## Verification

- 1,716 Python tests and 50 frontend tests passed.
- Frontend lint, TypeScript checking, and production build passed.
- Repository correctness inventory was 1,002/1,002 before adding this result,
  with zero pending or open findings.
- Execution-freeze coverage was 156/156 protected entrypoints.
- The 820-case simulation passed through the actual services, SQLite,
  LangGraph, VirtualClock, worker, outbox, and delivery paths.
- Exact Luna identity remains mandatory because Luna has no dated snapshot.

## Decision

Proceed once to the bounded provider-backed confirmation after a separate
authorization commit and a clean no-call preflight. No release architecture is
selected from build evidence. If 019 is invalid or fails quality, this package
branch stops; there is no third harness correction or same-package tuning loop.

## Limitations

- Network-free simulation cannot establish provider completion, semantic
  quality, latency, token use, or cost.
- Only public synthetic sources and learners are used.
- Real professor fidelity, real student usability, and learning improvement
  are not established.
