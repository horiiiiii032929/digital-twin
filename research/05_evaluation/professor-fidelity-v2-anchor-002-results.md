# Professor-fidelity v2 anchor 002 results

Result ID: `professor-fidelity-v2-anchor-002`

Date: 2026-08-14

Status: Generation complete; machine calibration ineligible

Decision: Refine. Retain the anchor as diagnostic evidence, do not select P3,
and do not open professor-fidelity development or held-out.

## Binding and boundary

- Dataset: separately sealed 12-case anchor, 4 conditions, 48 requested
  responses.
- Generator: official `deepseek-v4-pro`, non-thinking, P3/v4, temperature 0,
  no retry.
- Exact fingerprint:
  `a307abda487cd1b463329ccb945ce396`.
- Retrieval: selected `qwen3-hybrid-v1` over 508 bound course chunks; C1/C2
  used frozen oracle evidence and C3 used retrieval.
- Policy binding: `professor-fidelity-policy-bindings-v3-p3`, SHA-256
  `9c00b6eed9d67541fcc8a099a0ba9d69f581c371fc26502357671e5549d3199d`.
- Clean code revision:
  `b19ade38407bb0b3187a307068f6a833693f679d`.
- Ignored private result SHA-256:
  `6290755a44848a6c8a2239a4cee5d09e02c8f7007f2620a0f1c1a05df28a8cf1`.
- Development and held-out access: zero.

## Generation and deterministic result

All 48/48 responses completed with one model and fingerprint. Generator cost
was USD 0.013958715 for 25,671 input and 3,209 output tokens; p50/p95 latency
was 1.725/2.957 seconds. Retrieval made 44 local requests with zero retries or
failures and no external retrieval cost.

| Condition | Hard gates | Structural | Action | Citation ID | Citation source |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 | 4/12 | 1/12 | 9/12 | 4/12 | 4/12 |
| C1 | 10/12 | 9/12 | 9/12 | 12/12 | 12/12 |
| C2 | 10/12 | 9/12 | 10/12 | 12/12 | 12/12 |
| C3 | 6/12 | 5/12 | 9/12 | 11/12 | 7/12 |

These are structural and deterministic diagnostics, not semantic citation
completeness or professor approval. C2 improves action passing by one response
over C1 but does not improve structural or hard-gate passing. C3 is materially
weaker than oracle-evidence C1/C2 on source correctness and hard gates.

## Machine-review outcome

Primary DeepSeek attempt 002 completed but failed the frozen repeat-consistency
gate. Swapped DeepSeek and local-Qwen sensitivity attempts each stopped invalid
before completion. A blinded 48-response human-reference packet was prepared
and remains unfilled. See the separately registered machine-review results.

The result therefore cannot estimate a calibrated pedagogy effect, semantic
citation completeness, professor fidelity, learning outcomes, or production
readiness.
