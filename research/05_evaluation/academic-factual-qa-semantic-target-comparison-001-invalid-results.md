# Semantic-target grounding comparison attempt 001 invalid result

## Decision

`Invalid execution`. Draw no semantic-target quality conclusion from attempt
001. Preserve the raw response packages and run exactly one harness-only
correction without changing the cases, gold, methods, or gates.

## What happened

The network-free run persisted all responses before opening hidden gold, used
the clean revision `6e9eb16`, and made zero provider calls. The typed-target
baseline completed all 500 cases. The semantic-target candidate produced 46
`operational-failure` responses because its internal ranking score reached
1.05 after deterministic context and phrase bonuses, while the shared
`EvidenceSufficiencyDecision` contract requires a normalized score no greater
than 1.0.

The runner incorrectly labelled the raw result `completed-refine`; this
summary is the prospective analysis correction. Its diagnostic candidate
metrics, including 69.5% grounded success, are not interpreted as method
quality because the candidate execution was incomplete. The unaffected
baseline diagnostic was 91.0%, but it also remained below the unchanged
grounded, claim, and citation gates.

## Correction boundary

- Clamp only the internal score at the normalized public-contract boundary.
- Make any per-condition operational failure produce `invalid-execution`.
- Reuse the exact 500 public cases, hidden gold, two architectures, scoring,
  and hard gates.
- Use a fresh exclusive output and attempt ID.
- Permit no second harness correction and no same-data method tuning.

## Limits

This is an operational finding, not evidence for selecting or rejecting the
semantic-target method. It supports no release, professor-fidelity, usability,
learning-outcome, or provider-backed autonomy claim.
