# Confirmation 017 postmortem regression 001

## Outcome

The known 820-case package passed the network-free actual-product regression at
clean revision `49952b1`: 820/820 cases matched every reference action and every
safety contract across T0, T1-v1, T1-v2 reactive, and T1-v2 autonomous.

This closes the code causes recorded as `SE7-6` and `SE7-7`. It does not change
confirmation 017 from `invalid-execution`, qualify the Luna provider path, or
select a release.

## Measurements

| Condition | Cases | Reference-action accuracy | Safety contracts | Goal termination | Restart consistency |
| --- | ---: | ---: | ---: | ---: | ---: |
| T0 grounded control | 150 | 100% | 100% | 100% | 100% |
| T1-v1 reactive control | 150 | 100% | 100% | 100% | 100% |
| T1-v2 reactive | 150 | 100% | 100% | 100% | 100% |
| T1-v2 autonomous | 370 | 100% | 100% | 100% | 100% |
| Overall | 820 | 100% | 100% | 100% | 100% |

All unauthorized actions, wrong recipients, wrong course/release bindings,
invalid citation lineages, consent violations, duplicate deliveries, unbounded
loops, and model-owned authority mutations were zero. Provider-failure fallback
and pedagogical-transition validity were 100%. Provider calls and cost were
zero.

## Decision

Keep the lifecycle and clock corrections in the codebase. Do not promote H+E1
or V3 from this result. A future provider-backed claim requires a fresh package
and separate direct-transport and product-route canaries. The 016 package is now
a known regression set and cannot be reused for a fresh confirmatory claim.

## Limitations

- This is network-free regression evidence on a package opened during the
  postmortem.
- It does not measure provider completion, identity, semantic quality, latency,
  tokens, or cost.
- It does not establish real professor fidelity, student usability, or learning
  improvement.
