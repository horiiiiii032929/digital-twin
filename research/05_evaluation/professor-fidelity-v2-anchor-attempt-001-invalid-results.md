# Professor-fidelity v2 anchor attempt 001 invalid results

Result ID: `professor-fidelity-v2-anchor-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid; stopped on the first provider response before one complete
case

Decision: Refine the generator binding prospectively. Do not accept the changed
V4 Flash fingerprint and do not rerun this exact attempt.

## Boundary

- Intended split: the separately sealed 12-case professor-fidelity anchor.
- Intended conditions: C0-C3, 48 total outputs.
- Intended generator: selected DeepSeek V4 Flash non-thinking/P2 binding.
- Clean code revision: `9e05e15`.
- Development v1.2.3 authoring draft, seal, and held-out ledger were not read or
  created.

## Observed result

The first external request returned provider fingerprint
`a26a7955944dc5c60445bff77fac9c8e`, not the qualified fingerprint
`fp_a18b46594c_prod0820_fp8_kvcache_20260402`. The runner stopped immediately.

- External calls: one.
- Completed cases: 0/12.
- Completed condition outputs: 0/48.
- Result file: absent.
- Checkpoint file: absent.
- Held-out access: zero.
- Gemma calls: zero.

Usage and cost were not durably captured because the implementation checked
the fingerprint before writing the first response telemetry. This is a
limitation of the failed attempt and must not be reconstructed as a measured
zero.

## Interpretation

The selected V4 Flash result remains valid historical evidence, but its exact
served binding is no longer available. Accepting the new fingerprint without
qualification would silently replace a selected component and invalidate the
comparison.

The prospective successor is
`generator-qualification-v2-v4-pro-development-001`: current GA DeepSeek V4
Pro, unchanged strict-evidence P2, unchanged public synthetic development
cases, exact V4 Pro fingerprint, one attempt, and a USD 1 stop. A passing
development run may advance only to cross-model review and bounded anchor
calibration; it cannot select the profile or open generator held-out.

## Next action

Run the frozen V4 Pro development qualification from a new clean revision,
register its result whether favorable or unfavorable, and keep the 41-case
independent-human authoring audit as the separate prerequisite for sealing the
course-tutor development/held-out split.
