# Governed full-autonomy V2.1 actual-product confirmation 018 build

## Outcome

Confirmation 018 is `build-only-qualified` at clean revision `4f2f124`. It
contains 820 unique public-synthetic cases on fresh source families 351–400,
with public inputs and hidden gold stored separately and hash-bound. The full
actual-product network-free run passed all reference-action and safety
contracts across T0, T1-v1, T1-v2 reactive, and T1-v2 autonomous. Provider and
paid execution remain disabled at this checkpoint.

## Canary correction

The confirmation separates three questions that attempts 016 and 017 had
incorrectly combined:

- a direct Responses API transport canary must return exact `gpt-5.6-luna`;
- a T1-v2 reactive product canary must contain an observed completed Luna call;
- a T1-v2 autonomous product canary must contain an observed completed Luna
  call.

Each canary has its own durable accounting. A transport, identity, route, or
accounting failure stops before the remaining 818 product cases and leaves
hidden gold unopened.

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

- 1,712 Python tests and 50 frontend tests passed.
- Frontend lint, TypeScript checking, and production build passed.
- Repository correctness inventory is 998/998 with zero pending findings.
- Execution-freeze coverage is 155/155 protected entrypoints.
- The 820-case simulation passed through the actual services, SQLite,
  LangGraph, VirtualClock, worker, outbox, and delivery paths.
- Luna metadata was refreshed from official OpenAI documentation. Because Luna
  has no dated snapshot, exact returned identity is mandatory for every live
  call.

## Decision

Proceed once to the bounded provider-backed confirmation after a separate
authorization commit and a clean no-call preflight. This build does not select
H+E1/V3 for release and does not establish provider quality.

## Limitations

- Network-free simulation cannot establish provider completion, semantic
  quality, latency, token use, or cost.
- Only public synthetic sources and learners are used.
- Real professor fidelity, real student usability, and learning improvement
  are not established.
