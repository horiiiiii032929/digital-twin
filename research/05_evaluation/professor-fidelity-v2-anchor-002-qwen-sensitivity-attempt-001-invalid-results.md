# Professor-fidelity v2 anchor 002 Qwen sensitivity attempt 001 invalid results

Result ID: `professor-fidelity-v2-anchor-002-qwen-sensitivity-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid and stopped; rerun prohibited

Decision: Drop local Qwen as an active calibration judge for this anchor and
retain it only as evidence of cross-model sensitivity.

## Result

The local `qwen3:4b` run at exact digest `359d7dd4bcda` checkpointed 2/12 cases
and 10 calls. During case 3, a returned evidence quote could not be uniquely
aligned to the displayed response, so the contract-v4 runner failed closed and
wrote no final result.

- Clean code revision:
  `a34ff6ecca595901ed41941ae7f209ed94e90a06`.
- Ignored private checkpoint SHA-256:
  `35dcaf21f4e3ed4b82732b21586e7c066be7ed8aaf2999ac3d34cbbb9aa6f8c1`.
- External calls and cost: zero.
- Thinking: explicitly disabled.
- Gemma calls, development access, and held-out access: zero.

On the overlapping invalid partial sample, Qwen agreed with primary DeepSeek on
6/40 single-dimension labels (15%; weighted kappa 0). This is not a completed
cross-family metric, but it reinforces the prior finding that this Qwen binding
is not a trustworthy citation or pedagogy clearance mechanism.

Attempt 001 must not be resumed or rerun.
